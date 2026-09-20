# VentureIntel

> Type a company name, walk away. Come back to a structured competitive intelligence report — sourced, verified, and exported to PDF — generated entirely by a local AI with no cloud LLM required.

This is a multi-agent competitive research tool built for product and strategy teams. You give it a company name. A LangGraph pipeline fires up, pulls data from six different sources in parallel, runs four specialist AI agents, cross-checks every finding algorithmically, and assembles everything into a PDF report with an executive summary, competitor breakdowns, and a risk score matrix.

Everything runs locally via Ollama + Phi-3. No OpenAI. No Anthropic. Your data stays on your machine.

---

# VentureIntel — Complete System Architecture

## 1. Architecture Overview

VentureIntel is a multi-agent startup due-diligence platform. A **React** frontend collects a target company and analysis configuration, sends it to a **FastAPI** backend, which hands the request to a **LangGraph** orchestrator running **7 specialized agents**. Agents call **web search / MCP tools**, scrape and normalize evidence from **24+ sources**, ground their reasoning in a **RAG** pipeline, persist structured results in **PostgreSQL**, and use **Redis** for caching and intermediate state. An **Investment Synthesis Agent** aggregates all agent outputs into a VC-grade report, which is persisted and returned to the React dashboard.

Confirmed technologies used throughout: Python, FastAPI, React, LangGraph, LangChain, PostgreSQL, Redis, MCP, RAG, web search, web scraping, and LLM-based extraction/reasoning. Anything else (specific vector databases, message queues, cloud providers, observability stacks) is explicitly marked `Conceptual` / `Logical Component` / `Optional` below, since it was not confirmed as an implemented technology.

---

## 2. Master System Architecture

This is the full end-to-end system, organized into nine layers from the browser down to the persisted investment report.

```mermaid
flowchart TB
    classDef frontend fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
    classDef backend fill:#dcfce7,stroke:#16a34a,color:#14532d
    classDef orchestration fill:#fef9c3,stroke:#ca8a04,color:#713f12
    classDef agent fill:#fde68a,stroke:#b45309,color:#78350f
    classDef tool fill:#e9d5ff,stroke:#7e22ce,color:#3b0764
    classDef data fill:#fee2e2,stroke:#dc2626,color:#7f1d1d
    classDef llm fill:#c7d2fe,stroke:#4338ca,color:#1e1b4b
    classDef output fill:#bbf7d0,stroke:#15803d,color:#052e16
    classDef conceptual fill:#f3f4f6,stroke:#6b7280,stroke-dasharray: 4 3,color:#374151

    subgraph L1["Layer 1 — Presentation (React)"]
        UI_INPUT["Startup / Company Input"]:::frontend
        UI_CONFIG["Analysis Configuration"]:::frontend
        UI_STATUS["Research Status / Agent Progress"]:::frontend
        UI_REPORT["Final Investment Report View"]:::frontend
        UI_MARKET["Market Analysis View"]:::frontend
        UI_COMP["Competitor Analysis View"]:::frontend
        UI_RISK["Risk Analysis View"]:::frontend
    end

    subgraph L2["Layer 2 — API / Application (FastAPI)"]
        API_EP["API Endpoints"]:::backend
        API_VALID["Request Validation"]:::backend
        API_SESSION["Analysis Session Creation"]:::backend
        API_ASYNC["Background / Async Processing"]:::backend
        API_FMT["Response Formatting"]:::backend
    end

    subgraph L3["Layer 3 — Agent Orchestration (LangGraph)"]
        LG_STATE["Shared State"]:::orchestration
        LG_ROUTE["Agent Routing"]:::orchestration
        LG_PARALLEL["Parallel Execution Controller"]:::orchestration
        LG_DEPS["Dependency Management"]:::orchestration
        LG_RETRY["Retry / Error Handling"]:::orchestration
        LG_AGG["Result Aggregation"]:::orchestration
    end

    subgraph L4["Layer 4 — 7 AI Agents"]
        A1["1. Company Research Agent"]:::agent
        A2["2. Market Intelligence Agent"]:::agent
        A3["3. Competitor Analysis Agent"]:::agent
        A4["4. Financial / Business Model Agent"]:::agent
        A5["5. Product / Technology Agent"]:::agent
        A6["6. Risk & Red Flag Agent"]:::agent
        A7["7. Investment Synthesis Agent"]:::agent
    end

    subgraph L5["Layer 5 — Intelligence / Tool Layer"]
        MCP["MCP Tool Interface"]:::tool
        WS["Web Search"]:::tool
        SCRAPE["Web Scraping"]:::tool
        DOC_RET["Document Retrieval"]:::tool
        EXTRACT["Structured Extraction"]:::tool
        SRP["Search Result Processing"]:::tool
        NORM["Source Normalization"]:::tool
        DEDUPE["Deduplication"]:::tool
        EVID["Evidence Extraction"]:::tool
    end

    subgraph L6["Layer 6 — Knowledge / Data Layer"]
        subgraph PG["PostgreSQL (Persistent)"]
            PG_COMPANY["Company Records"]:::data
            PG_RESEARCH["Research Results"]:::data
            PG_SRC["Source Metadata"]:::data
            PG_COMP["Competitor Data"]:::data
            PG_MARKET["Market Data"]:::data
            PG_SESSION["Analysis Sessions"]:::data
            PG_REPORT["Generated Reports"]:::data
        end
        subgraph RAG["RAG Pipeline"]
            RAG_INGEST["Document Ingestion"]:::tool
            RAG_CHUNK["Chunking"]:::tool
            RAG_EMBED["Embeddings"]:::tool
            RAG_VEC["Vector Retrieval (Conceptual store)"]:::conceptual
            RAG_CTX["Context Assembly"]:::tool
            RAG_EVID["Retrieved Evidence"]:::tool
        end
    end

    subgraph L7["Layer 7 — Caching / State (Redis)"]
        REDIS_CACHE["Cache"]:::data
        REDIS_STATE["Intermediate Agent State"]:::data
        REDIS_DEDUP["Repeated-Research Avoidance"]:::data
        REDIS_SESSION["Session State"]:::data
        REDIS_TEMP["Temporary Results"]:::data
    end

    subgraph L8["Layer 8 — LLM / Reasoning"]
        LLM_INFER["LLM Inference"]:::llm
        LLM_EXTRACT["Structured Extraction"]:::llm
        LLM_REASON["Reasoning"]:::llm
        LLM_SYNTH["Synthesis"]:::llm
        LLM_REPORT["Report Generation"]:::llm
    end

    subgraph L9["Layer 9 — Output"]
        OUT_REPORT["VC-Grade Investment Report"]:::output
        OUT_EXEC["Executive Summary"]:::output
        OUT_MKT["Market Size"]:::output
        OUT_COMP["Competitors"]:::output
        OUT_BM["Business Model"]:::output
        OUT_TECH["Technology"]:::output
        OUT_RISK["Risks"]:::output
        OUT_EVID["Evidence / Sources"]:::output
        OUT_CONSID["Investment Considerations"]:::output
    end

    UI_INPUT --> API_EP
    UI_CONFIG --> API_EP
    API_EP --> API_VALID --> API_SESSION --> API_ASYNC
    API_ASYNC -->|Initialize State| LG_STATE
    LG_STATE --> LG_ROUTE --> LG_PARALLEL --> LG_DEPS
    LG_PARALLEL -->|Parallel Research| A1 & A2 & A3 & A4 & A5 & A6
    A1 & A2 & A3 & A4 & A5 & A6 -->|Agent Result| LG_AGG
    LG_AGG -->|Dependent Input| A7

    A1 & A2 & A3 & A4 & A5 & A6 -->|Tool Call| MCP
    MCP --> WS & SCRAPE & DOC_RET
    WS & SCRAPE --> SRP --> NORM --> DEDUPE --> EVID --> EXTRACT
    EXTRACT -->|Retrieved Evidence| RAG_INGEST --> RAG_CHUNK --> RAG_EMBED --> RAG_VEC --> RAG_CTX --> RAG_EVID
    RAG_EVID -->|Grounded Context| A1 & A2 & A3 & A4 & A5 & A6

    A1 & A2 & A3 & A4 & A5 & A6 -->|Shared State Write| LG_STATE
    LG_STATE -->|Cache Lookup| REDIS_CACHE
    REDIS_CACHE -->|Cache Hit| LG_ROUTE
    LG_STATE --> REDIS_STATE & REDIS_SESSION & REDIS_TEMP
    REDIS_DEDUP -.->|Skip Redundant Research| LG_PARALLEL

    A1 & A2 & A3 & A4 & A5 & A6 & A7 -->|LLM Call| LLM_INFER
    LLM_INFER --> LLM_EXTRACT & LLM_REASON
    A7 --> LLM_SYNTH --> LLM_REPORT

    LG_AGG -->|Persist| PG_RESEARCH
    EVID -->|Persist| PG_SRC
    A2 -->|Persist| PG_MARKET
    A3 -->|Persist| PG_COMP
    API_SESSION -->|Persist| PG_SESSION
    LLM_REPORT -->|Persist| PG_REPORT
    PG_COMPANY --- PG_RESEARCH --- PG_SRC --- PG_COMP --- PG_MARKET --- PG_SESSION --- PG_REPORT

    LLM_REPORT --> OUT_REPORT
    OUT_REPORT --> OUT_EXEC & OUT_MKT & OUT_COMP & OUT_BM & OUT_TECH & OUT_RISK & OUT_EVID & OUT_CONSID
    OUT_REPORT -->|Response Formatting| API_FMT
    API_FMT -->|API Response| UI_REPORT
    UI_REPORT --> UI_MARKET & UI_COMP & UI_RISK
    API_ASYNC -.->|Progress Events| UI_STATUS
```

---

## 3. End-to-End Request Sequence

Full lifecycle from user input to rendered report, including cache hit/miss branches, tool failure, agent retry, invalid source handling, LLM failure, and final fallback.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant React
    participant FastAPI
    participant LangGraph
    participant Redis
    participant Postgres
    participant Agents as Parallel Agents (6)
    participant Tools as MCP / Web Search / Scraper
    participant RAGP as RAG Pipeline
    participant LLM
    participant Synth as Investment Synthesis Agent

    User->>React: Enter startup / company name
    React->>FastAPI: POST /analysis (analysis request)
    FastAPI->>FastAPI: Validate request
    alt Invalid request
        FastAPI-->>React: 400 Validation Error
        React-->>User: Show validation error
    else Valid request
        FastAPI->>Postgres: Create analysis session
        FastAPI->>LangGraph: Initialize shared state
        LangGraph->>Redis: Check cache / prior state
        alt Cache hit
            Redis-->>LangGraph: Cached research / state
            LangGraph->>Synth: Use cached evidence
        else Cache miss
            LangGraph->>LangGraph: Generate research tasks
            par Parallel agent execution
                LangGraph->>Agents: Dispatch Company Research task
                LangGraph->>Agents: Dispatch Market Intelligence task
                LangGraph->>Agents: Dispatch Competitor Analysis task
                LangGraph->>Agents: Dispatch Financial/Business Model task
                LangGraph->>Agents: Dispatch Product/Technology task
                LangGraph->>Agents: Dispatch Risk & Red Flag task
            end
            Agents->>Tools: Web search / MCP tool call
            alt Tool call fails
                Tools-->>Agents: Error / timeout
                Agents->>Tools: Retry (bounded)
                alt Retry exhausted
                    Agents->>LangGraph: Report degraded / partial result
                else Retry succeeds
                    Tools-->>Agents: Sources retrieved
                end
            else Tool call succeeds
                Tools-->>Agents: Sources retrieved
            end
            Agents->>Tools: Scrape / extract content
            alt Source invalid or malformed
                Tools-->>Agents: Invalid source flagged
                Agents->>Agents: Discard, try alternate source
            else Source valid
                Tools-->>Agents: Extracted, normalized evidence
            end
            Agents->>RAGP: Submit evidence for retrieval context
            RAGP-->>Agents: Retrieved, grounded context
            Agents->>LLM: Structured extraction / reasoning call
            alt LLM call fails / rate limited
                LLM-->>Agents: Error
                Agents->>LLM: Retry with backoff
                alt Retry still fails
                    Agents->>LangGraph: Emit agent error state
                else Retry succeeds
                    LLM-->>Agents: Structured output
                end
            else LLM call succeeds
                LLM-->>Agents: Structured output
            end
            Agents->>LangGraph: Write agent output to shared state
            LangGraph->>Postgres: Persist research results
            LangGraph->>Redis: Cache intermediate results
        end
        LangGraph->>LangGraph: Validate evidence
        LangGraph->>LangGraph: Cross-agent aggregation
        LangGraph->>Synth: Provide aggregated agent outputs
        Synth->>LLM: Synthesis / report generation call
        alt Contradictory or low-confidence evidence
            Synth->>Synth: Flag caveat, lower confidence score
        end
        LLM-->>Synth: Final VC-style analysis
        Synth->>Postgres: Persist final report
        Postgres-->>FastAPI: Report saved (report_id)
        FastAPI->>FastAPI: Format response
        FastAPI-->>React: 200 OK (investment report)
        React-->>User: Render investment report
    end
```

---

## 4. LangGraph Multi-Agent Architecture

Detailed orchestration graph: state initialization, parallel fan-out across six agents, dependency-gated synthesis, conditional retry routing, and shared state fields.

```mermaid
flowchart LR
    classDef orchestration fill:#fef9c3,stroke:#ca8a04,color:#713f12
    classDef agent fill:#fde68a,stroke:#b45309,color:#78350f
    classDef state fill:#e0e7ff,stroke:#4338ca,color:#1e1b4b
    classDef terminal fill:#111827,stroke:#111827,color:#ffffff

    START([START]):::terminal --> INIT["Initialize State"]:::orchestration
    INIT --> PLAN["Research Planning"]:::orchestration
    PLAN --> FANOUT{"Parallel Fan-Out"}:::orchestration

    subgraph PARALLEL["Parallel Agents (independent, no cross-dependency)"]
        A1["Company Research Agent"]:::agent
        A2["Market Intelligence Agent"]:::agent
        A3["Competitor Analysis Agent"]:::agent
        A4["Financial / Business Model Agent"]:::agent
        A5["Product / Technology Agent"]:::agent
        A6["Risk & Red Flag Agent"]:::agent
    end

    FANOUT --> A1
    FANOUT --> A2
    FANOUT --> A3
    FANOUT --> A4
    FANOUT --> A5
    FANOUT --> A6

    A1 --> RESULTS["Parallel Results Collected"]:::orchestration
    A2 --> RESULTS
    A3 --> RESULTS
    A4 --> RESULTS
    A5 --> RESULTS
    A6 --> RESULTS

    RESULTS --> VALID{"Evidence Validation"}:::orchestration
    VALID -->|invalid / low confidence| REVALIDATE["Flag for re-research"]:::orchestration
    REVALIDATE -.->|conditional retry| FANOUT
    VALID -->|valid| AGG["Cross-Agent Aggregation"]:::orchestration

    AGG --> SYNTH["Investment Synthesis Agent\n(depends on all 6 prior agents)"]:::agent
    SYNTH --> REPORT["Report Generation"]:::orchestration
    REPORT --> PERSIST["Persistence"]:::orchestration
    PERSIST --> END([END]):::terminal

    subgraph SHARED["Shared LangGraph State"]
        S1["company"]
        S2["company_profile"]
        S3["sources"]
        S4["market_data"]
        S5["competitors"]
        S6["business_model"]
        S7["technology"]
        S8["risks"]
        S9["financial_signals"]
        S10["evidence"]
        S11["agent_results"]
        S12["confidence"]
        S13["final_analysis"]
        S14["report"]
    end
    class S1,S2,S3,S4,S5,S6,S7,S8,S9,S10,S11,S12,S13,S14 state

    A1 -.->|writes| S2
    A2 -.->|writes| S4
    A3 -.->|writes| S5
    A4 -.->|writes| S6 & S9
    A5 -.->|writes| S7
    A6 -.->|writes| S8
    A1 & A2 & A3 & A4 & A5 & A6 -.->|writes| S3 & S10 & S11
    VALID -.->|writes| S12
    SYNTH -.->|writes| S13
    REPORT -.->|writes| S14
```

---

## 5. Agent Internal Architecture

Generic per-agent pipeline, followed by how each of the seven agents specializes it.

```mermaid
flowchart TB
    classDef step fill:#fde68a,stroke:#b45309,color:#78350f
    classDef io fill:#dbeafe,stroke:#2563eb,color:#1e3a8a

    IN["Input (from shared state)"]:::io --> TASK["Task Interpretation"]:::step
    TASK --> QGEN["Query Generation"]:::step
    QGEN --> TOOLSEL["Tool Selection"]:::step
    TOOLSEL --> WSMCP["Web Search / MCP Call"]:::step
    WSMCP --> SRC["Source Retrieval"]:::step
    SRC --> SCRAPE["Scraping"]:::step
    SCRAPE --> EXTRACT["Content Extraction"]:::step
    EXTRACT --> CLEAN["Cleaning"]:::step
    CLEAN --> EVID["Evidence Extraction"]:::step
    EVID --> RAGQ["RAG Retrieval"]:::step
    RAGQ --> CTX["Context Construction"]:::step
    CTX --> LLMSTEP["LLM Reasoning"]:::step
    LLMSTEP --> STRUCT["Structured Output"]:::step
    STRUCT --> VALID["Validation"]:::step
    VALID --> OUT["Shared State Write"]:::io
```

```mermaid
flowchart TB
    classDef agentbox fill:#fef3c7,stroke:#b45309,color:#78350f
    classDef schema fill:#dcfce7,stroke:#16a34a,color:#14532d

    subgraph AG1["1. Company Research Agent"]
        direction TB
        AG1_IN["Input: Company name"] --> AG1_1["Search company"] --> AG1_2["Official website"]
        AG1_2 --> AG1_3["Funding information"] --> AG1_4["Founders"] --> AG1_5["Product"] --> AG1_6["Traction signals"]
        AG1_6 --> AG1_OUT["Output schema: structured company_profile"]:::schema
    end

    subgraph AG2["2. Market Intelligence Agent"]
        direction TB
        AG2_IN["Input: Company / product"] --> AG2_1["Market search"] --> AG2_2["Industry data"]
        AG2_2 --> AG2_3["TAM / SAM / SOM"] --> AG2_4["Growth indicators"] --> AG2_5["Trends"]
        AG2_5 --> AG2_OUT["Output schema: market_data (sizing)"]:::schema
    end

    subgraph AG3["3. Competitor Analysis Agent"]
        direction TB
        AG3_IN["Input: Company / product"] --> AG3_1["Competitor discovery"] --> AG3_2["Competitor research"]
        AG3_2 --> AG3_3["Feature comparison"] --> AG3_4["Positioning"]
        AG3_4 --> AG3_OUT["Output schema: competitive_landscape"]:::schema
    end

    subgraph AG4["4. Financial / Business Model Agent"]
        direction TB
        AG4_IN["Input: Company"] --> AG4_1["Pricing"] --> AG4_2["Revenue model"]
        AG4_2 --> AG4_3["Monetization"] --> AG4_4["Funding"] --> AG4_5["Financial signals"]
        AG4_5 --> AG4_OUT["Output schema: business_model + unit_economics_signals"]:::schema
    end

    subgraph AG5["5. Product / Technology Agent"]
        direction TB
        AG5_IN["Input: Product"] --> AG5_1["Technical research"] --> AG5_2["Architecture / capabilities"]
        AG5_2 --> AG5_3["Technology signals"] --> AG5_4["Differentiation"] --> AG5_5["Technical risks"]
        AG5_5 --> AG5_OUT["Output schema: technology profile"]:::schema
    end

    subgraph AG6["6. Risk & Red Flag Agent"]
        direction TB
        AG6_IN["Input: All collected evidence"] --> AG6_1["Contradictions"] --> AG6_2["Regulatory risks"]
        AG6_2 --> AG6_3["Market risks"] --> AG6_4["Competitive risks"] --> AG6_5["Technology risks"] --> AG6_6["Business risks"]
        AG6_6 --> AG6_OUT["Output schema: risk_assessment[]"]:::schema
    end

    subgraph AG7["7. Investment Synthesis Agent"]
        direction TB
        AG7_IN["Input: All 6 agent outputs"] --> AG7_1["Evidence aggregation"] --> AG7_2["Consistency checking"]
        AG7_2 --> AG7_3["Investment thesis"] --> AG7_4["Strengths / risks / opportunities"]
        AG7_4 --> AG7_OUT["Output schema: final VC-style report"]:::schema
    end

    AG1_OUT --> AG7_IN
    AG2_OUT --> AG7_IN
    AG3_OUT --> AG7_IN
    AG4_OUT --> AG7_IN
    AG5_OUT --> AG7_IN
    AG6_OUT --> AG7_IN
```

---

## 6. RAG Architecture

Ingestion path (left) grounds the agent query path (right) in retrieved evidence, which is the mechanism used to reduce ungrounded LLM output.

```mermaid
flowchart TB
    classDef ingest fill:#e9d5ff,stroke:#7e22ce,color:#3b0764
    classDef query fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
    classDef conceptual fill:#f3f4f6,stroke:#6b7280,stroke-dasharray: 4 3,color:#374151
    classDef metric fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-dasharray: 2 2

    subgraph ING["Ingestion Path"]
        SRC["Web Sources / Documents"]:::ingest --> PARSE["Parsing"]:::ingest
        PARSE --> CLEAN["Cleaning"]:::ingest
        CLEAN --> CHUNK["Chunking"]:::ingest
        CHUNK --> META["Metadata Extraction"]:::ingest
        META --> EMBED["Embeddings"]:::ingest
        EMBED --> VECIDX["Vector Index\n(Conceptual — exact store not confirmed)"]:::conceptual
    end

    subgraph QRY["Query / Retrieval Path"]
        AQ["Agent Query"]:::query --> QEMBED["Query Embedding"]:::query
        QEMBED --> SIM["Similarity Retrieval"]:::query
        SIM --> TOPK["Top-K Evidence"]:::query
        TOPK --> MFILT["Metadata Filtering"]:::query
        MFILT --> CTXASM["Context Assembly"]:::query
        CTXASM --> LLMCALL["LLM"]:::query
        LLMCALL --> GROUNDED["Grounded Response"]:::query
        GROUNDED --> EVREF["Evidence References"]:::query
    end

    VECIDX --> SIM

    NOTE1["Reported project evaluation result: 28% hallucination reduction"]:::metric
    NOTE2["Reported project evaluation result: 91% factual accuracy"]:::metric
    GROUNDED -.-> NOTE1
    GROUNDED -.-> NOTE2
```

---

## 7. Database ER Diagram

```mermaid
erDiagram
    SESSION ||--|| COMPANY : "analyzes"
    SESSION ||--o{ AGENT_RESULT : "produces"
    SESSION ||--|| REPORT : "generates"
    COMPANY ||--o{ FOUNDER : "has"
    COMPANY ||--o{ SOURCE : "referenced by"
    COMPANY ||--o{ RESEARCH_RESULT : "has"
    COMPANY ||--o{ MARKET_DATA : "has"
    COMPANY ||--o{ COMPETITOR : "has"
    COMPANY ||--o{ RISK : "has"
    RESEARCH_RESULT ||--o{ SOURCE : "cites"
    AGENT_RESULT ||--o{ SOURCE : "cites"
    REPORT ||--o{ RISK : "includes"
    REPORT ||--o{ COMPETITOR : "includes"
    REPORT ||--o{ MARKET_DATA : "includes"

    SESSION {
        uuid session_id PK
        uuid user_id
        string analysis_status
        timestamp created_at
        timestamp completed_at
    }
    COMPANY {
        uuid company_id PK
        string name
        string website
        string industry
        timestamp created_at
    }
    FOUNDER {
        uuid founder_id PK
        uuid company_id FK
        string name
        string role
        string background
    }
    SOURCE {
        uuid source_id PK
        uuid company_id FK
        string source_url
        string source_type
        float confidence
        timestamp retrieved_at
    }
    RESEARCH_RESULT {
        uuid result_id PK
        uuid company_id FK
        string agent_type
        text evidence
        float confidence
        timestamp created_at
    }
    AGENT_RESULT {
        uuid agent_result_id PK
        uuid session_id FK
        string agent_type
        text structured_output
        string status
        int retry_count
        timestamp created_at
    }
    MARKET_DATA {
        uuid market_data_id PK
        uuid company_id FK
        string tam
        string sam
        string som
        text growth_indicators
    }
    COMPETITOR {
        uuid competitor_id PK
        uuid company_id FK
        string name
        text feature_comparison
        text positioning
    }
    RISK {
        uuid risk_id PK
        uuid company_id FK
        string risk_category
        text description
        string severity
    }
    REPORT {
        uuid report_id PK
        uuid session_id FK
        text executive_summary
        text report_content
        float confidence_score
        timestamp generated_at
    }
```

*PostgreSQL entities above are persistent. Redis holds transient, non-relational data (cache keys, intermediate agent state, session TTL state) and is not modeled as ER entities — see Diagram 8.*

---

## 8. Redis + PostgreSQL Interaction

```mermaid
flowchart TB
    classDef backend fill:#dcfce7,stroke:#16a34a,color:#14532d
    classDef cache fill:#fee2e2,stroke:#dc2626,color:#7f1d1d
    classDef db fill:#c7d2fe,stroke:#4338ca,color:#1e1b4b
    classDef orchestration fill:#fef9c3,stroke:#ca8a04,color:#713f12

    REQ["Request"]:::backend --> API["FastAPI"]:::backend
    API --> RLOOK["Redis Lookup"]:::cache
    RLOOK -->|Cache Hit| RHIT["Cached research / state"]:::cache
    RHIT --> LG1["LangGraph"]:::orchestration
    LG1 --> RESP1["Response"]:::backend

    RLOOK -->|Cache Miss| LG2["LangGraph"]:::orchestration
    LG2 --> RESEARCH["Research / Tools"]:::orchestration
    RESEARCH --> PG["PostgreSQL\n(persistent structured records)"]:::db
    RESEARCH --> RCACHE["Redis Cache\n(write-through)"]:::cache
    PG --> REPORT["Report"]:::backend
    RCACHE -.->|accelerates repeat queries| RLOOK

    subgraph REDIS_ROLE["Redis responsibilities"]
        R1["Cache"]:::cache
        R2["Temporary / intermediate agent state"]:::cache
        R3["Repeated-query acceleration"]:::cache
        R4["Session state"]:::cache
    end

    subgraph PG_ROLE["PostgreSQL responsibilities"]
        P1["Persistent structured records"]:::db
        P2["Research history"]:::db
        P3["Source metadata"]:::db
        P4["Agent outputs"]:::db
        P5["Generated reports"]:::db
    end
```

---

## 9. MCP Tool Architecture

```mermaid
flowchart LR
    classDef agent fill:#fde68a,stroke:#b45309,color:#78350f
    classDef orchestration fill:#fef9c3,stroke:#ca8a04,color:#713f12
    classDef mcp fill:#e9d5ff,stroke:#7e22ce,color:#3b0764
    classDef tool fill:#dbeafe,stroke:#2563eb,color:#1e3a8a

    AGENT["Agent"]:::agent -->|Tool Request| LANGGRAPH["LangGraph"]:::orchestration
    LANGGRAPH -->|Invoke via MCP| MCPI["MCP Interface\n(tool integration layer)"]:::mcp
    MCPI --> DISC["Tool Discovery"]:::mcp
    DISC --> INVOKE["Tool Invocation"]:::mcp

    INVOKE --> T1["Web Search"]:::tool
    INVOKE --> T2["Web Scraping"]:::tool
    INVOKE --> T3["Company Research Tool"]:::tool
    INVOKE --> T4["Source Retrieval Tool"]:::tool
    INVOKE --> T5["Structured Data Extraction Tool"]:::tool

    T1 & T2 & T3 & T4 & T5 --> RESULT["Result"]:::mcp
    RESULT -->|Result| AGENT_STATE["Agent State (Shared State Write)"]:::agent

    note1["MCP is the tool integration / interface layer.\nNot every external capability shown is necessarily\nan MCP-hosted server — this diagram represents the\nconceptual invocation path."]
```

---

## 10. Web Research Pipeline

```mermaid
flowchart TB
    classDef step fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
    classDef source fill:#fde68a,stroke:#b45309,color:#78350f

    START["Startup"]:::step --> QGEN["Query Generation"]:::step
    QGEN --> MULTIQ["Multiple Search Queries"]:::step
    MULTIQ --> ENGINE["Search Engine"]:::step
    ENGINE --> SOURCES["24+ Information Sources"]:::step

    subgraph CATS["Conceptual Source Categories"]
        C1["Official company website"]:::source
        C2["Product pages"]:::source
        C3["News"]:::source
        C4["Funding information"]:::source
        C5["Investor information"]:::source
        C6["Market research"]:::source
        C7["Competitor websites"]:::source
        C8["Industry reports"]:::source
        C9["Public databases"]:::source
        C10["Other web sources"]:::source
    end

    SOURCES --> C1 & C2 & C3 & C4 & C5 & C6 & C7 & C8 & C9 & C10
    C1 & C2 & C3 & C4 & C5 & C6 & C7 & C8 & C9 & C10 --> COLLECT["Source Collection"]:::step
    COLLECT --> URLNORM["URL Normalization"]:::step
    URLNORM --> DEDUP["Duplicate Removal"]:::step
    DEDUP --> QFILT["Source Quality Filtering"]:::step
    QFILT --> SCRAPE["Scraping"]:::step
    SCRAPE --> CONTENT["Content Extraction"]:::step
    CONTENT --> CLEAN["Cleaning"]:::step
    CLEAN --> EVID["Evidence Extraction"]:::step
    EVID --> META["Metadata"]:::step
    META --> CTX["RAG / Agent Context"]:::step
```

---

## 11. Investment Report Generation Pipeline

```mermaid
flowchart TB
    classDef step fill:#c7d2fe,stroke:#4338ca,color:#1e1b4b
    classDef section fill:#bbf7d0,stroke:#15803d,color:#052e16

    RD["Research Data"]:::step --> AO["Agent Outputs"]:::step
    AO --> EV["Evidence Validation"]:::step
    EV --> CAGG["Cross-Agent Aggregation"]:::step
    CAGG --> CONTRA["Contradiction Detection"]:::step
    CONTRA --> CONF["Confidence Estimation"]:::step
    CONF --> SYN["Investment Synthesis"]:::step
    SYN --> GEN["Structured Report Generation"]:::step
    GEN --> PERSIST["PostgreSQL Persistence"]:::step
    PERSIST --> API["API"]:::step
    API --> UI["React Dashboard"]:::step

    subgraph SECTIONS["Final Report Sections"]
        S1["Executive Summary"]:::section
        S2["Company Overview"]:::section
        S3["Product"]:::section
        S4["Market (TAM/SAM/SOM)"]:::section
        S5["Competitors"]:::section
        S6["Business Model"]:::section
        S7["Traction Signals"]:::section
        S8["Technology"]:::section
        S9["Risks"]:::section
        S10["Opportunities"]:::section
        S11["Investment Thesis"]:::section
        S12["Evidence / Sources"]:::section
        S13["Confidence / Caveats"]:::section
    end

    GEN --> S1 & S2 & S3 & S4 & S5 & S6 & S7 & S8 & S9 & S10 & S11 & S12 & S13
```

---

## 12. Failure & Reliability Architecture

```mermaid
flowchart TB
    classDef fail fill:#fee2e2,stroke:#dc2626,color:#7f1d1d
    classDef step fill:#fde68a,stroke:#b45309,color:#78350f
    classDef conceptual fill:#f3f4f6,stroke:#6b7280,stroke-dasharray: 4 3,color:#374151
    classDef out fill:#bbf7d0,stroke:#15803d,color:#052e16

    F1["Web search fails"]:::fail --> DET["Failure Detection"]:::step
    F2["Website scraping fails"]:::fail --> DET
    F3["Source returns invalid data"]:::fail --> DET
    F4["LLM request fails"]:::fail --> DET
    F5["Rate limit occurs"]:::fail --> DET
    F6["Agent produces malformed output"]:::fail --> DET
    F7["Agent times out"]:::fail --> DET
    F8["PostgreSQL fails"]:::fail --> DET
    F9["Redis fails"]:::fail --> DET
    F10["Contradictory information found"]:::fail --> DET

    DET --> RETRY["Retry / Fallback\n(Logical reliability layer)"]:::conceptual
    RETRY --> ALT["Alternate Source"]:::step
    ALT --> VALID["Validation"]:::step
    VALID -->|still degraded| PARTIAL["Partial Result"]:::step
    VALID -->|unrecoverable| ERRSTATE["Error State"]:::fail
    PARTIAL --> FINAL["Final Report with Caveat"]:::out
    ERRSTATE --> FINAL

    note1["Sophisticated failure-recovery mechanisms not\nexplicitly confirmed as implemented are marked\n'Logical reliability layer' rather than assumed."]:::conceptual
```

---

## 13. Complete System Data Flow

```mermaid
flowchart TB
    classDef n fill:#e5e7eb,stroke:#374151,color:#111827

    U["USER"]:::n --> R["REACT"]:::n
    R --> F["FASTAPI"]:::n
    F --> LG["LANGGRAPH"]:::n
    LG --> SS["SHARED STATE"]:::n
    SS --> P6["PARALLEL 6 AGENTS"]:::n
    P6 --> TM["TOOLS / MCP"]:::n
    TM --> SRC["24+ SOURCES"]:::n
    SRC --> SE["SCRAPING / EXTRACTION"]:::n
    SE --> RAG["RAG"]:::n
    RAG --> DB["POSTGRESQL + REDIS"]:::n
    DB --> EVV["EVIDENCE VALIDATION"]:::n
    EVV --> CAS["CROSS-AGENT SYNTHESIS"]:::n
    CAS --> ISA["INVESTMENT SYNTHESIS AGENT"]:::n
    ISA --> RG["REPORT GENERATION"]:::n
    RG --> DB2["POSTGRESQL"]:::n
    DB2 --> F2["FASTAPI"]:::n
    F2 --> R2["REACT"]:::n
    R2 --> OUT["VC-GRADE INVESTMENT REPORT"]:::n

    EVV -.->|"validation failed — re-research"| P6
    P6 -.->|"tool/agent retry"| TM
    ISA -.->|"insufficient consensus — request more evidence"| SS
```

---

## 14. Deployment Architecture *(Logical Deployment Architecture)*

```mermaid
flowchart LR
    classDef frontend fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
    classDef backend fill:#dcfce7,stroke:#16a34a,color:#14532d
    classDef ai fill:#fef9c3,stroke:#ca8a04,color:#713f12
    classDef data fill:#fee2e2,stroke:#dc2626,color:#7f1d1d
    classDef ext fill:#e9d5ff,stroke:#7e22ce,color:#3b0764

    BROWSER["Browser"] --> FRONT["React Frontend"]:::frontend
    FRONT --> BACK["FastAPI Backend"]:::backend
    BACK --> LGR["LangGraph Runtime"]:::ai
    LGR --> LLMP["LLM Provider\n(not explicitly specified)"]:::ai
    BACK --> PG["PostgreSQL"]:::data
    BACK --> REDIS["Redis"]:::data
    LGR --> EXTS["External Web / Search Services"]:::ext
    LGR --> MCPL["MCP / Tool Layer"]:::ext

    subgraph LAYERS["Logical Deployment Architecture"]
        direction TB
        FRONT
        BACK
        LGR
        PG
        REDIS
        EXTS
        MCPL
    end
```

---

## 15. Complete System State Machine

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> REQUEST_RECEIVED: user submits analysis
    REQUEST_RECEIVED --> VALIDATING
    VALIDATING --> FAILED: invalid request
    VALIDATING --> INITIALIZING: valid request
    INITIALIZING --> RESEARCHING
    RESEARCHING --> PARALLEL_AGENT_EXECUTION
    PARALLEL_AGENT_EXECUTION --> RETRYING: tool / LLM / agent failure
    RETRYING --> PARALLEL_AGENT_EXECUTION: retry succeeds
    RETRYING --> FAILED: retries exhausted
    PARALLEL_AGENT_EXECUTION --> COLLECTING_EVIDENCE
    COLLECTING_EVIDENCE --> VALIDATING_EVIDENCE
    VALIDATING_EVIDENCE --> RESEARCHING: evidence insufficient / contradictory
    VALIDATING_EVIDENCE --> SYNTHESIZING: evidence sufficient
    SYNTHESIZING --> GENERATING_REPORT
    GENERATING_REPORT --> PERSISTING
    PERSISTING --> COMPLETED
    PERSISTING --> FAILED: persistence error
    FAILED --> [*]
    COMPLETED --> [*]
```

---

## 16. Parallel Execution Timeline

Shows why six agents running concurrently, rather than sequentially, is what drives the hours-to-minutes reduction in due-diligence time.

```mermaid
sequenceDiagram
    actor User
    participant React
    participant FastAPI
    participant LangGraph
    participant CompanyResearch as Company Research
    participant MarketIntel as Market Intelligence
    participant Competitor as Competitor Analysis
    participant Financial as Financial Analysis
    participant ProductTech as Product/Technology
    participant Risk as Risk Analysis
    participant Synth as Investment Synthesis

    User->>React: Submit company
    React->>FastAPI: Analysis request
    FastAPI->>LangGraph: Dispatch parallel research

    par t0 — all six agents start simultaneously
        LangGraph->>CompanyResearch: Start
    and
        LangGraph->>MarketIntel: Start
    and
        LangGraph->>Competitor: Start
    and
        LangGraph->>Financial: Start
    and
        LangGraph->>ProductTech: Start
    and
        LangGraph->>Risk: Start
    end

    Note over CompanyResearch,Risk: All six agents execute concurrently —<br/>wall-clock time ≈ slowest single agent,<br/>not the sum of all six

    CompanyResearch-->>LangGraph: Result (t1)
    MarketIntel-->>LangGraph: Result (t1)
    Competitor-->>LangGraph: Result (t1)
    Financial-->>LangGraph: Result (t1)
    ProductTech-->>LangGraph: Result (t1)
    Risk-->>LangGraph: Result (t1)

    LangGraph->>LangGraph: Aggregation
    LangGraph->>Synth: Aggregated evidence
    Synth-->>LangGraph: Final analysis (t2)
    LangGraph->>FastAPI: Report ready
    FastAPI->>React: Response
    React->>User: Rendered report
```

---

## 17. Portfolio Architecture

A clean, high-level diagram suitable for a resume or README hero image.

```mermaid
flowchart TB
    classDef n fill:#111827,stroke:#111827,color:#ffffff
    classDef note fill:#fef9c3,stroke:#ca8a04,color:#713f12,stroke-dasharray: 2 2

    R["React"]:::n --> F["FastAPI"]:::n
    F --> LG["LangGraph"]:::n
    LG --> AG["7 Specialized Agents"]:::n
    AG --> MCP["MCP + Web Intelligence"]:::n
    MCP --> RAG["RAG"]:::n
    RAG --> DB["PostgreSQL + Redis"]:::n
    DB --> LLM["LLM Reasoning"]:::n
    LLM --> SYN["Investment Synthesis"]:::n
    SYN --> REP["VC-Grade Report"]:::n

    N1["24+ sources"]:::note -.-> MCP
    N2["7 agents"]:::note -.-> AG
    N3["Parallel execution"]:::note -.-> AG
    N4["RAG grounded reasoning"]:::note -.-> RAG
    N5["100+ reports"]:::note -.-> REP
    N6["Reported: 91% factual accuracy"]:::note -.-> REP
    N7["Reported: 28% hallucination reduction"]:::note -.-> REP
```

---

### Notes on scope and honesty in this documentation

- Confirmed technologies throughout: **Python, FastAPI, React, LangGraph, LangChain, PostgreSQL, Redis, MCP, RAG, web search, web scraping, LLM-based extraction/reasoning.**
- Marked `Conceptual` / `Logical Component` because they were not explicitly confirmed: the exact **vector store** product behind RAG retrieval, and the **deployment/infrastructure** stack (no Kubernetes, Kafka, cloud provider, message queue, or observability stack has been assumed).
- The **91% factual accuracy** and **28% hallucination reduction** figures are labeled as reported project evaluation results, not as guaranteed or independently verified metrics.

---

## Tech stack

| | |
|---|---|
| **Frontend** | React, Create React App, Nginx |
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Agent framework** | LangGraph `StateGraph` with `MemorySaver` checkpointing |
| **LLM** | Phi-3 via Ollama — runs entirely locally, no cloud API |
| **Embeddings** | BGE-M3 (`BAAI/bge-m3`) — also local |
| **Vector store** | ChromaDB (embedded for local dev, HTTP client for Docker) |
| **Retrieval** | Dense ANN (cosine) + BM25 keyword scoring + RRF fusion |
| **Verification** | Deterministic — RapidFuzz cross-source fuzzy matching, no LLM |
| **Task queue** | Celery + Redis |
| **Database** | PostgreSQL (sessions, agent results, reports, risk scores) |
| **Reporting** | Jinja2 HTML templates → WeasyPrint PDF |
| **Monitoring** | Prometheus + Grafana, `prometheus-fastapi-instrumentator` |
| **Structured logging** | `structlog` |

---

## Getting started

### Option A: Docker (recommended)

You need Docker Desktop and ~8 GB of disk space for the Phi-3 model.

```bash
git clone https://github.com/your-org/competitor-intel.git
cd competitor-intel

cp .env.example .env
# Fill in any API keys you want (all optional — demo data is used without them)

docker compose up --build
```

The first startup pulls the Phi-3 model automatically via `ollama pull phi3`. This takes a few minutes on first run. After that, services are available at:

| Service | URL |
|---|---|
| App | http://localhost:80 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Grafana | http://localhost:3001 (admin / admin) |
| Prometheus | http://localhost:9090 |

### Option B: Local dev without Docker

For faster iteration — no containers, no model download wait.

**Backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# SQLite is used automatically if DATABASE_URL isn't set
# ChromaDB runs embedded (no server needed)
# Ollama still needs to be running locally for the LLM
uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
REACT_APP_API_URL=http://localhost:8000 npm start
```

---

## Running Ollama locally

Ollama serves Phi-3 on port 11434. If you're running Option B, install and start it separately:

```bash
# Install Ollama: https://ollama.com
ollama serve
ollama pull phi3
```

The backend health check at `/health` will tell you whether it can reach Ollama and which model is loaded.

---

## API keys (all optional)

Every external data source degrades gracefully to demo/placeholder data if its key is missing. You can run a fully working research pipeline with no keys at all — you just get demo chunks instead of real search results.

Add real keys to your `.env` to get live data:

| Variable | Source | What it enables |
|---|---|---|
| `BRAVE_API_KEY` | [brave.com/search/api](https://brave.com/search/api) | General web search results |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) | Deep search + raw page content extraction |
| `FIRECRAWL_API_KEY` | [firecrawl.dev](https://firecrawl.dev) | Full website scraping |
| `NEWSAPI_KEY` | [newsapi.org](https://newsapi.org) | News articles |
| `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) | Reddit posts and community discussion |
| `GITHUB_TOKEN` | [github.com/settings/tokens](https://github.com/settings/tokens) | Public repo data, star counts |
| `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` | [langfuse.com](https://langfuse.com) | LLM observability (optional) |

---

## Environment variables

```bash
# ── Local LLM (required — no API key needed, runs locally)
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=phi3

# ── PostgreSQL
DATABASE_URL=postgresql+asyncpg://intel:intel_pass@postgres:5432/intel_db

# ── Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# ── ChromaDB
# Docker: set CHROMA_HOST to the service name
CHROMA_HOST=chromadb
CHROMA_PORT=8000
# Local dev: leave CHROMA_HOST blank — embedded mode activates automatically

# ── Optional API keys (leave blank for demo data)
BRAVE_API_KEY=
TAVILY_API_KEY=
FIRECRAWL_API_KEY=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
GITHUB_TOKEN=
NEWSAPI_KEY=

# ── Report output path
REPORTS_DIR=/tmp/reports
```

---

## How a research job flows

1. You POST `/api/research` with `{ "company_name": "Stripe" }`.
2. The API creates a session in Postgres and returns a `session_id` immediately with status `queued`.
3. A background task starts the LangGraph pipeline (FastAPI `BackgroundTasks` in dev, Celery worker in production).
4. You poll `/api/research/{session_id}/status` to watch agents complete in real time.
5. When status is `completed`, hit `/api/research/{session_id}/report` for the full JSON report.
6. Download the PDF at `/api/research/{session_id}/pdf`.
7. Open the chat UI and ask follow-up questions — the evidence is already indexed in ChromaDB for that session.

The LangGraph pipeline checkpoints after every node. If anything fails mid-pipeline, it resumes from the last successful checkpoint rather than starting over.

---

## How verification works

The verification step is worth understanding because it's the main thing that separates this from "just ask an LLM to make stuff up about a company."

No LLM is involved in verification. Instead:

1. Claims are extracted from all agent outputs using regex — sentences containing numbers, dates, or the company name.
2. Each claim is checked against the raw source chunks using RapidFuzz `token_set_ratio` fuzzy matching (threshold: 42).
3. A claim is only marked as `verified` if it appears in two or more independent sources.
4. The confidence score is calculated as `(source_count / max_sources) × (avg_credibility / 10) × avg_similarity`.
5. Source credibility is weighted — SEC filings = 10, official websites = 9, news = 8, Reddit = 3.

Everything is deterministic and reproducible. Running verification twice on the same data produces the same scores.

---

## Project structure

```
competitor-intel/
├── backend/
│   └── app/
│       ├── agents/
│       │   ├── orchestrator.py          # LangGraph StateGraph + AgentOrchestrator
│       │   ├── graph_state.py           # Typed PipelineState definition
│       │   ├── research_agent.py        # General company research
│       │   ├── competitor_discovery_agent.py  # Identify rivals
│       │   ├── competitor_analysis_agent.py   # Deep-dive each rival
│       │   ├── risk_analysis_agent.py   # 6-category risk scoring
│       │   ├── verification_agent.py    # Deterministic cross-source check
│       │   └── report_agent.py          # Exec summary + PDF via WeasyPrint
│       ├── services/
│       │   ├── mcp_client.py            # 6 MCP-wrapped data source tools
│       │   ├── vector_store.py          # ChromaDB + hybrid retrieval (dense + BM25 + RRF)
│       │   ├── embedding_service.py     # BGE-M3 local embeddings
│       │   ├── llm_client.py            # Ollama / Phi-3 client
│       │   └── text_utils.py            # Chunking + credibility constants
│       ├── models/
│       │   ├── schemas.py               # Pydantic request/response types
│       │   └── db_models.py             # SQLAlchemy ORM models
│       ├── main.py                      # FastAPI app + all routes
│       ├── celery_app.py                # Celery configuration
│       ├── database.py                  # SQLAlchemy async session setup
│       └── config.py                    # Settings via pydantic-settings
│
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.js             # Session list + new research form
│       │   ├── SessionPage.js           # Live pipeline status view
│       │   └── ReportPage.js            # Full report + risk scores + chat
│       └── utils/api.js                 # API client
│
└── infra/
    ├── docker-compose.yml               # All 9 services
    ├── init.sql                         # Postgres schema
    ├── nginx.conf                       # Reverse proxy config
    └── prometheus.yml                   # Scrape config
```

---

## Available API endpoints

| Method | Path | What it does |
|---|---|---|
| `POST` | `/api/research` | Start a new research job |
| `GET` | `/api/research/{id}/status` | Poll pipeline progress + per-agent status |
| `GET` | `/api/research/{id}/report` | Full structured report JSON |
| `GET` | `/api/research/{id}/pdf` | Download PDF report |
| `GET` | `/api/sessions` | List last 50 research sessions |
| `POST` | `/api/chat` | Ask a question against a session's evidence |
| `POST` | `/api/chat/stream` | Same, streamed token by token |
| `GET` | `/api/mcp/tools` | List registered MCP tools and their status |
| `GET` | `/api/graph/schema` | LangGraph node/edge schema for visualisation |
| `GET` | `/api/llm/status` | Ollama health + model info |
| `GET` | `/api/chroma/status` | ChromaDB collection count + mode |
| `GET` | `/health` | Overall health check |
| `GET` | `/metrics` | Prometheus metrics endpoint |

---

## GPU support

By default, Ollama runs on CPU. For GPU acceleration, uncomment the `deploy` section in `docker-compose.yml` under the `ollama` service (requires `nvidia-container-toolkit`):

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

---

## Contributing

1. Fork the repo and create a feature branch
2. Run the backend locally with `uvicorn app.main:app --reload`
3. Add tests for any new agent logic or retrieval changes
4. Open a pull request with a description of what changed and why

For new data sources, implement the MCP tool contract in `mcp_client.py` — a tool is just an async function that returns `List[dict]` chunks with `content`, `source_url`, `source_type`, and `credibility_score` fields, registered via `MCPToolRegistry`.
