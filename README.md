# SWE-Forge

### Adaptive, Self-Verifying Autonomous Software Engineering Platform

SWE-Forge is an explicit orchestration, verification, and safety layer built on top of [Open SWE](https://github.com/langchain-ai/open-swe) by LangChain.

Open SWE provides the execution infrastructure — sandboxing, model/provider middleware, integrations, MCP transport, and the surrounding software-engineering platform.

**SWE-Forge adds the control layer above it:** deterministic LangGraph orchestration, structured planning, dynamic multi-agent execution, repository intelligence, bounded self-repair, independent review, security/risk gating, adaptive model routing, experience memory, and quantitative evaluation.

> **Open SWE = execution substrate**  
> **SWE-Forge = orchestration + verification + safety**

---

## Why SWE-Forge?

Autonomous coding agents can generate code, but reliable software engineering requires more than producing a patch.

A reliable coding system must answer:

- **Where should the change be made?**
- **Which agents or capabilities are relevant to the task?**
- **Did the implementation actually work?**
- **What should happen when verification fails?**
- **Should the resulting change be allowed to ship?**

SWE-Forge makes these decisions explicit through a typed, stateful LangGraph workflow rather than leaving the entire control loop inside an LLM prompt.

---

# Architecture

```text
                              START
                                |
                         Task Intake
                                |
                    Repository Analysis
                     AST + Import Graph
                                |
                   Task Complexity Analysis
                       + Experience Memory
                                |
                            Planning
                      Structured TaskPlan
                                |
                    Dynamic Agent Selection
                                |
                         Implementation
                                |
                         Verification
                         Real pytest
                         /       \
                    passed       failed
                       |             |
                       |       Failure Analysis
                       |             |
                       |          Recovery
                       |             |
                       |       Re-verification
                       |             |
                       |        Escalation
                       |             |
                       +-------------+
                                |
                     Independent Review
                       /             \
                  approved          rejected
                     |                  |
                     |             Recovery
                     |                  |
                     +------------------+
                                |
                       Security Analysis
                                |
                           Risk Gate
                         /           \
                     LOW/MED         HIGH
                        |              |
                        |       Human Approval
                        |              |
                        +------+-------+
                               |
                         Finalization
                               |
                              END
```

### Workflow characteristics

- **17 LangGraph nodes**
- **5 conditional routers**
- **2 bounded recovery loops**
- **4 terminal nodes**
- **7 terminal statuses + initial `pending` state**
- Explicit typed state transitions
- Structured outputs for important LLM decisions
- Deterministic recovery and risk-routing logic

Detailed architecture:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/ARCHITECTURE_DIAGRAM.md`](docs/ARCHITECTURE_DIAGRAM.md)

---

# What I Built

SWE-Forge is intentionally separated from the upstream Open SWE implementation.

| Capability | SWE-Forge Implementation |
|---|---|
| Workflow orchestration | LangGraph `StateGraph` |
| Structured planning | Pydantic-validated planning models |
| Agent dispatch | 6 specialized agents + reviewer + diagnostician |
| Repository intelligence | Python AST + import graph |
| Tool layer | 12 LangChain `StructuredTool` tools |
| Tool calling | `bind_tools → tool_calls → ToolMessage` |
| Verification | Real pytest execution |
| Failure handling | Deterministic failure taxonomy |
| Self-repair | Bounded recovery loop |
| Model routing | Per-role model tiers + retry/fallback |
| Execution control | Hard execution budgets |
| Independent review | Separate review gate |
| Security | Secret/dangerous-pattern scanning |
| Risk control | Deterministic additive risk scoring |
| Experience memory | BM25 retrieval |
| MCP | Deny-by-default orchestration layer |
| Observability | Durable local traces + optional LangSmith |
| Evaluation | Controlled ablation/evaluation harness |
| Reproducibility | Run manifests, seeds, versions and commit information |

The complete technology-level ownership mapping is available in:

- [`docs/CUSTOMIZATIONS.md`](docs/CUSTOMIZATIONS.md)
- [`docs/LANGCHAIN_LANGGRAPH.md`](docs/LANGCHAIN_LANGGRAPH.md)

---

# What Makes SWE-Forge Different From Open SWE?

SWE-Forge does **not** attempt to replace Open SWE.

Instead, it adds an explicit orchestration layer around the existing execution infrastructure.

| Capability | Open SWE | SWE-Forge |
|---|---|---|
| Agent execution | Deep Agents / ReAct-style execution | Explicit workflow around execution |
| Control flow | Primarily agent-driven | Typed LangGraph routing |
| Repository model | Execution infrastructure | AST + import graph |
| Agent selection | Agent execution model | Task-driven specialized-agent dispatch |
| Verification | Existing execution infrastructure | Explicit verification node + recovery |
| Failure handling | Provider/execution retries | Failure taxonomy + bounded self-repair |
| Review | PR-review functionality | In-run independent review gate |
| Model routing | Existing provider/model infrastructure | Per-role execution policy |
| Experience memory | — | BM25 retrieval |
| Evaluation | Existing project evaluation capabilities | SWE-Forge orchestration ablations |

Open SWE remains the execution substrate. SWE-Forge focuses on making the **decision and control process explicit, inspectable, and measurable**.

---

# LangChain & LangGraph Ownership

A major design goal of SWE-Forge is to demonstrate genuine hands-on use of the LangChain ecosystem rather than simply inheriting upstream usage.

## LangGraph

SWE-Forge owns a separate graph implementation containing:

- Custom `SWEForgeState`
- Custom graph construction
- Custom nodes
- Conditional routers
- Recovery transitions
- State updates
- Bounded loops
- Explicit terminal states
- Graph compilation
- Registered graph entry points

Primary implementation:

```text
agent/sweforge/graph/
├── workflow.py
└── entrypoint.py
```

## LangChain

SWE-Forge implements and integrates multiple LangChain tools with:

- Typed input schemas
- Validation
- Structured outputs
- Error handling
- Agent integration
- Actual tool-calling loops

The tool registry contains tools for capabilities such as:

- Repository analysis
- Repository graph queries
- Relevant-file discovery
- Test discovery
- Validation execution
- Git diff inspection
- Failure analysis
- Change-risk analysis

Primary implementation:

```text
agent/sweforge/tools/
```

## Structured Outputs

Important model decisions use explicit Pydantic schemas rather than relying exclusively on free-form model responses.

Examples include:

- Task planning
- Agent selection
- Failure diagnosis
- Review decisions
- Security/risk assessment

This allows routing and state transitions to operate on validated structures rather than parsed prose.

## LangSmith

LangSmith instrumentation is supported for observability when credentials are available.

The system remains functional without LangSmith through its local tracing/observability layer.

More detail:

[`docs/LANGCHAIN_LANGGRAPH.md`](docs/LANGCHAIN_LANGGRAPH.md)

---

# Key Engineering Mechanisms

## 1. Adaptive Multi-Agent Execution

Tasks are analyzed and mapped to specialized agent roles rather than sending every task through the same implementation path.

The workflow supports specialized implementation, review, diagnosis, and security responsibilities.

Agent selection is part of the execution path rather than being a display-only recommendation.

---

## 2. Repository Intelligence

SWE-Forge builds a structural representation of the repository using:

- Python AST analysis
- Import relationships
- Symbol-level information
- Repository graph queries
- Relevant-file ranking

This provides deterministic repository evidence that can be used during planning and implementation.

The repository-intelligence subsystem is deliberately separated from the LLM decision layer.

---

## 3. Bounded Self-Repair

When verification fails:

```text
Verification
      ↓
Failure Classification
      ↓
Diagnosis
      ↓
Repair
      ↓
Re-verification
```

Recovery is bounded.

If the workflow cannot recover within its execution limits, it transitions to escalation rather than looping indefinitely.

---

## 4. Independent Review

Implementation and review are separate stages.

The reviewer receives the implementation result independently and can reject a change that technically passes verification but does not satisfy the intended requirements.

This creates a second quality gate before security/risk evaluation.

---

## 5. Deterministic Risk Gate

SWE-Forge performs security/risk analysis after implementation and review.

The risk layer includes:

- Secret scanning
- Dangerous-pattern detection
- Deterministic risk scoring
- Human-approval routing for high-risk changes

An LLM may contribute findings, but it cannot simply lower the deterministic gate.

---

## 6. Hard Execution Budgets

Execution budgets are enforced by the orchestration layer.

Budgets can constrain resources such as:

- Model calls
- Tool calls
- Recovery attempts
- Execution time

Budget exhaustion is represented explicitly in the graph rather than being treated as an ordinary model decision.

---

## 7. Model Retry & Fallback

SWE-Forge separates retry behavior from model-tier fallback.

The execution policy records individual attempts and can move between configured model tiers when the policy allows it.

This makes model selection and fallback observable rather than implicit.

---

## 8. Experience Memory

Previous run information can be stored and retrieved using BM25-based retrieval.

BM25 was selected for the default path because software-engineering queries are identifier-heavy and the approach remains deterministic without requiring an external vector database.

---

# Evaluation

SWE-Forge includes a controlled evaluation harness designed to measure its orchestration mechanisms rather than make unsupported claims about frontier-model capability.

## Evaluation Design

The primary ablation compares cumulative SWE-Forge workflow variants:

```text
A. Baseline
      ↓
B. + Repository Intelligence
      ↓
C. + Bounded Self-Repair
      ↓
D. + Independent Review
      ↓
E. Full SWE-Forge
```

The evaluation uses scripted deterministic model behavior so that the orchestration mechanisms are isolated from uncontrolled model variability.

## Results

| Variant | Task Success | Verification | Recovery | Human Gate |
|---|---:|---:|---:|---:|
| Baseline | 50% | 50% | — | 0 |
| + Repository Intelligence | 50% | 50% | — | 0 |
| + Self-Repair | **83%** | **83%** | 67% | 0 |
| + Independent Review | **83%** | **83%** | 75% | 0 |
| Full SWE-Forge | 67%* | **83%** | 75% | **1** |

\* The lower headline success rate for the full workflow reflects the risk gate correctly blocking a high-risk change rather than treating unsafe execution as success.

## Other Verified Results

- **6/6** designed routing scenarios reached their expected terminal states.
- Self-repair increased task success from **50% → 83%** in the shipped ablation.
- A green-but-incorrect implementation was rejected by the independent review gate.
- A credential-committing change was blocked by the risk gate with a **90/100 HIGH** risk score and human approval required.
- Recovery terminates after bounded attempts rather than looping indefinitely.

## Evaluation Boundary

These experiments evaluate **SWE-Forge orchestration mechanisms**.

They do **not** establish:

- SWE-Forge vs. Open SWE performance
- SWE-bench performance
- Frontier-model capability
- Real-world autonomous coding success rates
- Real production model cost

The Open SWE head-to-head and live-model evaluations remain unavailable without the required credentials and execution environment.

Full methodology:

[`docs/EVALUATION.md`](docs/EVALUATION.md)

---

# What the Evaluation Taught Us

One of the useful results is a negative result.

Repository intelligence did not change end-to-end task success in the scripted-model ablation because the harness pins the planner's decisions. This means the experiment cannot establish that richer repository evidence improves a live model's decisions.

Instead of hiding that result, SWE-Forge reports it explicitly and measures the repository-intelligence subsystem directly.

This distinction is important:

> **Implemented ≠ measured end-to-end ≠ proven universally effective.**

The project keeps those categories separate throughout its documentation.

---

# Technology Stack

| Technology | Why it is used |
|---|---|
| **LangGraph** | Explicit stateful orchestration, routing and bounded loops |
| **LangChain** | Typed, validated tools and model/tool interaction |
| **Pydantic** | Structured outputs and validated workflow decisions |
| **Python AST** | Deterministic repository structure analysis |
| **LangSmith** | Optional execution tracing and observability |
| **BM25** | Deterministic experience retrieval for identifier-heavy queries |
| **Open SWE** | Sandbox, execution, provider infrastructure and integrations |

Technologies were intentionally not added merely to increase the technology list.

Each major technology solves a concrete architectural problem.

---

# Quick Start

## Clone

```bash
git clone https://github.com/Vaishnavi0090/swe-forge.git
cd swe-forge
```

## Create Environment

```bash
python -m venv .venv
```

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

## Install SWE-Forge Dependencies

```bash
pip install -r requirements-sweforge.txt
```

No API key is required for the deterministic tests, repository analyzer, showcase, or evaluation harness.

---

# Quick Demo

Enable the local execution gate for the shipped deterministic fixtures.

### macOS / Linux

```bash
export SWEFORGE_ALLOW_LOCAL_EXEC=1
```

### Windows PowerShell

```powershell
$env:SWEFORGE_ALLOW_LOCAL_EXEC="1"
```

Run the system showcase:

```bash
python -m agent.sweforge.cli showcase
```

Run the security/risk-gate demonstration:

```bash
python -m agent.sweforge.cli demo --scenario pipeline_secret_risk_gate
```

Check available demonstrations:

```bash
python -m agent.sweforge.cli demo --list
```

Inspect repository intelligence:

```bash
python -m agent.sweforge.cli analyze --repo . --task "sandbox circuit breaker timeout"
```

Check configuration:

```bash
python -m agent.sweforge.cli doctor
```

More detailed walkthrough:

[`docs/DEMO.md`](docs/DEMO.md)

---

# Running Tests

Run the SWE-Forge test suite:

```bash
python -m pytest -c pytest-sweforge.ini
```

The tests are designed to run without model-provider credentials or network access.

Run documentation consistency checks:

```bash
python -m evaluation.check_docs
```

Run the deterministic evaluation:

```bash
python -m evaluation.runner
```

Generate evaluation reports:

```bash
python -m evaluation.evaluator
```

Run reproducibility checks:

```bash
python -m evaluation.runner --repeat 3 --seed 0
```

Run the component-level experiments:

```bash
python -m evaluation.run_all_experiments
```

---

# Running a Real Task

Real model execution requires provider credentials.

Create a local environment file:

```bash
cp .env.example .env
```

Then configure the required provider/model settings.

Run:

```bash
python -m agent.sweforge.cli run \
  --repo /path/to/repository \
  --task "Describe the software change you want to implement"
```

Never commit `.env` or provider credentials.

---

# Project Structure

```text
agent/sweforge/
│
├── agents/
│   ├── roles.py
│   ├── specialized.py
│   └── tool_loop.py
│
├── graph/
│   ├── workflow.py
│   └── entrypoint.py
│
├── planning/
│   └── planner.py
│
├── repository/
│   ├── analyzer.py
│   └── graph_index.py
│
├── verification/
│   ├── backends.py
│   └── verifier.py
│
├── recovery/
│   └── classifier.py
│
├── routing/
│   ├── model_router.py
│   └── execution_policy.py
│
├── security/
│   └── risk.py
│
├── memory/
│   └── store.py
│
├── tools/
│   └── registry.py
│
├── observability/
│   └── trace.py
│
├── state/
│   └── graph_state.py
│
├── schemas.py
├── budget.py
├── runner.py
└── cli.py

evaluation/
├── scenarios.py
├── runner.py
├── evaluator.py
├── metrics.py
├── benchmarks/
└── live/

tests_sweforge/
└── SWE-Forge-specific tests

docs/
├── ARCHITECTURE.md
├── ARCHITECTURE_DIAGRAM.md
├── LANGCHAIN_LANGGRAPH.md
├── CUSTOMIZATIONS.md
├── EVALUATION.md
├── SECURITY.md
├── DEMO.md
├── FINAL_PROJECT_STATUS.md
├── PROJECT_CLAIMS.md
├── RESUME_CLAIMS.md
└── INTERVIEW_GUIDE.md
```

---

# Security

SWE-Forge autonomously modifies repositories, so safety is treated as a first-class concern.

The security layer provides:

- Open SWE sandbox execution for untrusted code
- Host-execution gating
- Secret scanning
- Dangerous-pattern detection
- Deterministic risk scoring
- Human approval for high-risk changes
- Explicit terminal state for approval-required execution

The risk system is a **defence-in-depth mechanism**, not a complete security product.

See:

[`docs/SECURITY.md`](docs/SECURITY.md)

---

# Observability & Reproducibility

SWE-Forge maintains local execution traces so runs remain inspectable even when LangSmith is disabled.

When configured, LangSmith can additionally provide model/tool/node-level observability.

Reproducibility information includes:

- Git commit SHA
- Software versions
- Seed information
- Run metadata
- Execution decisions
- Tool interactions
- Recovery information
- Terminal state

---

# Current Scope & Limitations

The project deliberately distinguishes between capabilities that are implemented, capabilities that have been experimentally measured, and capabilities that require external infrastructure.

## Currently Unavailable

Each capability below is reported with an explicit status rather than a placeholder number. Where a capability could not be exercised, the harness records that fact instead of synthesising a result.

| Capability | Reported status | Where it is recorded |
|---|---|---|
| Real-world benchmark (SWE-bench or similar) | `NOT_AVAILABLE` | `REAL_WORLD_BENCHMARK_STATUS` in `evaluation/benchmarks/harness.py`; the benchmark dry-run downloads and executes nothing |
| Open SWE head-to-head | `comparable_pairs = 0` | `evaluation/results/experiment_b.json`; no head-to-head conclusion may be drawn from it |
| Live-model evaluation | `UNAVAILABLE` | `evaluation/live/`; reported as UNAVAILABLE whenever no provider credential is configured |
| Live GitHub PR creation | `UNAVAILABLE` | `agent/sweforge/github/finalization.py`; needs a GitHub App installation |
| Live MCP server | not exercised | MCP orchestration is tested against deterministic fixtures only |

### Live-model evaluation

No provider credential is included in the repository. The live evaluation harness exists but no live result is claimed.

### Open SWE head-to-head

The adapter resolves the genuine upstream `agent.server.get_agent`, but a complete paired benchmark requires model and sandbox credentials.

Therefore, no Open SWE vs. SWE-Forge performance result is claimed.

### SWE-bench / Public Benchmark Result

No SWE-bench number is claimed.

### Live MCP Server

MCP orchestration is implemented and tested using deterministic fixtures. No external MCP result is fabricated.

### Live GitHub PR Creation

Risk-gated preparation is implemented and mock-tested, but live PR creation requires the appropriate GitHub App installation.

## Known Implementation Limitations

- Repository AST analysis currently focuses on Python.
- Some call-graph relationships involving aliases or dynamic calls are not resolved.
- Risk weights are hand-tuned rather than learned from a labelled security dataset.
- Evaluation fixtures are intentionally small and deterministic.
- Live-model behavior has not been used to establish general autonomous coding performance.

Full status:

[`docs/FINAL_PROJECT_STATUS.md`](docs/FINAL_PROJECT_STATUS.md)

---

# Documentation

| Document | Description |
|---|---|
| [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Detailed system architecture and design decisions |
| [`ARCHITECTURE_DIAGRAM.md`](docs/ARCHITECTURE_DIAGRAM.md) | System and evaluation architecture diagrams |
| [`LANGCHAIN_LANGGRAPH.md`](docs/LANGCHAIN_LANGGRAPH.md) | LangChain/LangGraph ownership and implementation |
| [`CUSTOMIZATIONS.md`](docs/CUSTOMIZATIONS.md) | Technology-level source traceability |
| [`EVALUATION.md`](docs/EVALUATION.md) | Evaluation methodology, results and limitations |
| [`SECURITY.md`](docs/SECURITY.md) | Threat model and risk controls |
| [`DEMO.md`](docs/DEMO.md) | Guided demonstration |
| [`FINAL_PROJECT_STATUS.md`](docs/FINAL_PROJECT_STATUS.md) | Final verified project status |
| [`PROJECT_CLAIMS.md`](docs/PROJECT_CLAIMS.md) | Claim/evidence classification |
| [`RESUME_CLAIMS.md`](docs/RESUME_CLAIMS.md) | Defensible resume-level claims |
| [`INTERVIEW_GUIDE.md`](docs/INTERVIEW_GUIDE.md) | Technical interview questions and answers |
| [`UPSTREAM_AUDIT.md`](docs/UPSTREAM_AUDIT.md) | Open SWE capability and extension-point audit |
| [`UPSTREAM_README.md`](docs/UPSTREAM_README.md) | Preserved upstream Open SWE README |

---

# Resume-Level Summary

> **SWE-Forge — Adaptive Self-Verifying Software Engineering Agent**
>
> Built an explicit LangGraph orchestration layer over Open SWE with structured planning, dynamic multi-agent dispatch, repository intelligence, bounded self-repair, independent review, deterministic security/risk gating, adaptive model routing, experience memory, and a controlled evaluation harness.

---

# Attribution

SWE-Forge is built on the [Open SWE](https://github.com/langchain-ai/open-swe) open-source project by LangChain, Inc.

Open SWE provides the execution foundation, including sandbox infrastructure, provider/model middleware, integrations, MCP clients, the PR-review product, dashboard infrastructure, and its existing test suite.

**SWE-Forge does not claim those upstream components as original work.**

SWE-Forge adds the orchestration and verification layer, primarily contained in:

```text
agent/sweforge/
evaluation/
tests_sweforge/
docs/
```

The upstream MIT license and copyright notice are retained in [`LICENSE`](LICENSE).

---

# License

See [`LICENSE`](LICENSE) for the applicable license and upstream attribution.
