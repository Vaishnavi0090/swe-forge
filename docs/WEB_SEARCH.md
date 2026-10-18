# Web search

The Open SWE coding and reviewer graphs' `web_search` tool works without search
credentials through [Parallel Search MCP](https://docs.parallel.ai/integrations/mcp/search-mcp).
Anonymous search uses Fast mode and returns relevant page excerpts, subject to the
service's free-tier limits. Existing `EXA_API_KEY` configurations continue to use Exa.
Set `WEB_SEARCH_PROVIDER=parallel` or `exa` to choose explicitly, or `disabled` to
prevent search requests. A selected provider's failure is returned to the agent
without switching providers. Parallel requests have a 30-second total timeout.

With Parallel, `num_results` caps the returned results (the service may return fewer),
and `include_contents=True` includes excerpts rather than full pages. Use the existing
`fetch_url` tool when a page needs a closer read. Results retain the sandbox JSONL
and bounded inline formats used by the agent. Search queries are sent from the
server process to `https://search.parallel.ai/mcp`; no Parallel credential is needed.


```bash
WEB_SEARCH_PROVIDER=auto  # parallel, exa, or disabled
# EXA_API_KEY=...        # optional; selects Exa in auto mode
```
