import asyncio
import importlib
import json
from unittest.mock import AsyncMock

import httpx
import pytest
from langchain_core.messages import AIMessage
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from agent.tools import web_search

search = importlib.import_module("agent.tools.web_search")


@pytest.fixture(autouse=True)
def isolated_search(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    monkeypatch.delenv("WEB_SEARCH_PROVIDER", raising=False)
    monkeypatch.setattr(
        search, "write_sandbox_output", AsyncMock(side_effect=RuntimeError("no sandbox"))
    )


@pytest.fixture
def mcp_transport(monkeypatch):
    from langchain_mcp_adapters import sessions

    requests = []
    state = {
        "payload": {
            "search_id": "search_fixture",
            "session_id": "fixture",
            "results": [
                {
                    "url": "https://docs.python.org/3/",
                    "title": "Python docs",
                    "excerpts": ["Python reference"],
                },
                {"url": "https://example.org/", "title": "Example", "excerpts": ["Example text"]},
            ],
        },
        "error": False,
        "wait": False,
        "started": asyncio.Event(),
    }

    async def handle(request):
        assert str(request.url) == "https://search.parallel.ai/mcp"
        assert request.headers["user-agent"] == "SWE-Forge/0.1.0"
        assert "authorization" not in request.headers
        if request.method != "POST":
            return httpx.Response(405)
        body = json.loads(request.content)
        requests.append(body)
        method = body["method"]
        if "id" not in body:
            return httpx.Response(202)
        if method == "initialize":
            result = {
                "protocolVersion": body["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fixture", "version": "1"},
            }
        elif method == "tools/call":
            state["started"].set()
            if state["wait"]:
                await asyncio.Event().wait()
            result = {
                "content": [{"type": "text", "text": json.dumps(state["payload"])}],
                "isError": state["error"],
            }
            if isinstance(state["payload"], dict):
                result["structuredContent"] = state["payload"]
        elif method == "tools/list":
            result = {"tools": [{"name": "web_search", "inputSchema": {"type": "object"}}]}
        else:
            raise AssertionError(method)
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": result})

    def factory(**kwargs):
        return httpx.AsyncClient(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr(sessions, "create_mcp_http_client", factory)
    return state, requests


async def dispatch(**args):
    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "web_search",
                "args": {"query": "Python reference documentation", **args},
                "id": "search-1",
                "type": "tool_call",
            }
        ],
    )
    graph = StateGraph(MessagesState)
    graph.add_node("tools", ToolNode([web_search]))
    graph.set_entry_point("tools")
    graph.set_finish_point("tools")
    output = await graph.compile().ainvoke(
        {"messages": [message]}, config={"configurable": {"thread_id": "search-test-thread"}}
    )
    return json.loads(output["messages"][-1].content)


async def test_unconfigured_dispatch_consumes_results_and_preserves_session(mcp_transport):
    _, requests = mcp_transport
    first = await dispatch(num_results=1)
    assert first["success"] is True
    data = json.loads(first["results"])
    assert data["results"] == [
        {
            "url": "https://docs.python.org/3/",
            "title": "Python docs",
            "excerpts": ["Python reference"],
        }
    ]
    second = await dispatch(include_contents=False)
    assert all("excerpts" not in item for item in json.loads(second["results"])["results"])
    calls = [r["params"] for r in requests if r["method"] == "tools/call"]
    assert all(c["name"] == "web_search" for c in calls)
    assert calls[0]["arguments"]["objective"] == "Python reference documentation"
    assert calls[0]["arguments"]["search_queries"] == ["Python reference documentation"]
    assert len(calls[0]["arguments"]["session_id"]) == 64
    assert calls[0]["arguments"]["session_id"] == calls[1]["arguments"]["session_id"]


async def test_parallel_override_preserves_configured_exa_key(monkeypatch, mcp_transport):
    monkeypatch.setenv("EXA_API_KEY", "saved-exa-key")
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "parallel")
    assert (await dispatch())["success"] is True
    assert search.os.environ["EXA_API_KEY"] == "saved-exa-key"


async def test_saved_exa_selection_and_explicit_failure_never_fall_back(monkeypatch, mcp_transport):
    import exa_py

    _, requests = mcp_transport
    calls = []

    class Exa:
        def __init__(self, api_key):
            assert api_key == "saved-exa-key"

        def search(self, query, **kwargs):
            calls.append((query, kwargs))
            return "configured Exa output"

    monkeypatch.setattr(exa_py, "Exa", Exa)
    monkeypatch.setenv("EXA_API_KEY", "saved-exa-key")
    result = await dispatch(include_contents=False, num_results=30)
    assert result["results"] == "configured Exa output"
    assert calls[0][1] == {"num_results": 30, "type": "auto"}
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "exa")
    monkeypatch.setattr(
        Exa, "search", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("Exa failed"))
    )
    assert (await dispatch(include_contents=False))["success"] is False
    assert requests == []


@pytest.mark.parametrize("provider", ["disabled", "exa", "unknown", ""])
async def test_explicit_unavailable_or_disabled_choice_has_no_network(
    monkeypatch, mcp_transport, provider
):
    _, requests = mcp_transport
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", provider)
    assert (await dispatch())["success"] is False
    assert requests == []


@pytest.mark.parametrize("args", [{"query": " "}, {"num_results": 0}])
async def test_invalid_search_does_not_connect(mcp_transport, args):
    _, requests = mcp_transport
    assert (await dispatch(**args))["success"] is False
    assert requests == []


async def test_mcp_error_is_failure_without_provider_fallback(mcp_transport):
    state, _ = mcp_transport
    state["error"] = True
    assert (await dispatch())["success"] is False


async def test_malformed_mcp_payload_is_failure(mcp_transport):
    state, _ = mcp_transport
    state["payload"] = {"unexpected": []}
    assert (await dispatch())["success"] is False


async def test_parallel_timeout_covers_transport(monkeypatch, mcp_transport):
    state, _ = mcp_transport
    state["wait"] = True
    monkeypatch.setattr(search, "WEB_SEARCH_TIMEOUT_SECONDS", 0.1)
    result = await dispatch()
    assert result["success"] is False
    assert "Timeout" in result["error"]


async def test_cancelled_dispatch_propagates(mcp_transport):
    state, _ = mcp_transport
    state["wait"] = True
    task = asyncio.create_task(dispatch())
    await asyncio.wait_for(state["started"].wait(), timeout=3)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_parallel_output_uses_existing_sandbox_contract(monkeypatch, mcp_transport):
    writes = []

    async def write(name, content, extension):
        writes.append((name, content, extension))
        return "/workspace/web-search-fixture.jsonl"

    monkeypatch.setattr(search, "write_sandbox_output", write)
    result = await dispatch()
    assert result["success"] is True
    assert result["results"] is None
    assert result["results_path"] == "/workspace/web-search-fixture.jsonl"
    decoded = "".join(json.loads(line)["text"] for line in writes[0][1].splitlines())
    assert json.loads(decoded)["results"][0]["url"] == "https://docs.python.org/3/"
    assert writes[0][0::2] == ("web-search", "jsonl")


async def test_parallel_inline_output_is_bounded(mcp_transport):
    state, _ = mcp_transport
    state["payload"]["results"][0]["excerpts"] = ["x" * 150_000]
    result = await dispatch()
    assert result["success"] is True
    assert result["result_chars"] > 150_000
    assert len(result["results"]) < 100_100
    assert "results truncated" in result["results"]
