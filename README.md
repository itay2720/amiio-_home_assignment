# Real Estate Asset Management – Multi-Agent System

A prototype multi-agent system built with **LangGraph** and **GPT-4o** that assists with real estate asset management tasks via natural language. Ask about profit & loss, property details, property comparisons, or general real estate knowledge through a Streamlit chat interface.

---

## Setup

### 1. Install dependencies

```bash
cd real_estate_agent
pip install -r requirements.txt
```

### 2. Set your OpenAI API key

```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY = "sk-..."

# macOS / Linux
export OPENAI_API_KEY="sk-..."
```

### 3. Place the data file

Put `properties.csv` (or convert `data.parquet` to CSV first) in `real_estate_agent/data/properties.csv`.

To convert from parquet:
```python
import pandas as pd
pd.read_parquet("data.parquet").to_csv("real_estate_agent/data/properties.csv", index=False)
```

### 4. Run the app

```bash
streamlit run real_estate_agent/app.py
```

---

## Example Queries

- "What is the total P&L for Building 180 in 2024?"
- "Show me all expenses for Q1 2025"
- "Compare the profit of Building 180 and PropCo"
- "What is a cap rate in real estate?"
- "Which tenants have the highest income?"

---

## Architecture

The system is composed of one **supervisor** that classifies the request, specialized **worker nodes** that query the dataset, and a **formatter** that generates the final natural language response.

### Agent Roles

| Agent | Role |
|---|---|
| `supervisor` | Classifies intent and extracts canonical filters using GPT-4o |
| `pl` | Aggregates profit/loss data from the dataset |
| `property` | Retrieves raw property/tenant records |
| `compare` | Computes total profit per property for side-by-side comparison |
| `general` | Answers general real estate knowledge questions using GPT-4o |
| `clarify` | Asks a targeted follow-up question when the input is ambiguous |
| `formatter` | Converts raw data rows into a clear natural language answer |

### LangGraph Workflow

```
                    ┌─────────────┐
        user input  │  supervisor │  (GPT-4o: classify intent + extract filters)
       ────────────►│             │
                    └──────┬──────┘
                           │  conditional route on intent
           ┌───────────────┼───────────────┬──────────────┬──────────────┐
           ▼               ▼               ▼              ▼              ▼
         [pl]         [property]       [compare]      [general]      [clarify]
           │               │               │              │              │
           └───────────────┴───────────────┘              │              │
                           │                              │              │
                           ▼                              │              │
                       [formatter]                        │              │
                           │                              │              │
                           └──────────────────────────────┴──────────────┘
                                                          ▼
                                                        [END]
```

### Data Flow

```
User question
    → supervisor: GPT-4o returns { intent, filters } with exact canonical values
    → data node: Pandas query on properties.csv filtered by the extracted values
    → formatter: GPT-4o narrates the query results as a professional response
    → Streamlit: displays the answer + expandable debug panel
```

---

## Design Decisions

### LLM-based Entity Resolution (instead of fuzzy matching)

The supervisor injects the full list of canonical property names, tenant names, and ledger types into its system prompt and instructs GPT-4o to return the **exact canonical spelling** from those lists. This approach handles:

- Partial names ("Building 18" → "Building 180")
- Semantic aliases ("the warehouse" → a specific building)
- Multilingual input (the dataset contains Dutch/English descriptions)

A traditional fuzzy-matching library (RapidFuzz) was initially used as a post-processing step, but it was redundant once the LLM was already performing the matching. Removing it simplifies the pipeline and improves accuracy on ambiguous inputs.

### Separate `general` Intent

The assignment specifies "all types of question need to be handled," including general knowledge. A dedicated `general` node answers questions like "what is a cap rate?" or "how does depreciation work?" using GPT-4o without touching the dataset. Without this node, such questions would fall through to `clarify`, degrading the user experience.

### LLM-powered `clarify` Node

Instead of returning a hardcoded fallback message, the clarify node makes a targeted GPT call that suggests relevant property names or time periods based on the user's question. This keeps the conversation productive when the system cannot determine intent.

### Formatter as a Separate Node

Separating data retrieval (pandas) from response generation (GPT-4o) keeps concerns clean and makes it easy to test each part independently. The formatter receives the raw data rows and the original question and produces a professional, human-readable answer.

### Single DataFrame Load

The CSV is loaded once at module import in `tools/data.py` and reused across all queries. This avoids repeated I/O on every request.

---

## Dataset

**Source:** `data.parquet` (provided separately), converted to CSV.

**Columns:**

| Column | Description |
|---|---|
| `entity_name` | Legal entity owning the property (e.g. "PropCo") |
| `property_name` | Property identifier (nullable for entity-level entries) |
| `tenant_name` | Tenant name (nullable) |
| `ledger_type` | `income` or `expenses` |
| `ledger_group` | Grouping within ledger type |
| `ledger_category` | Sub-category |
| `ledger_code` | Numeric accounting code |
| `ledger_description` | Human-readable description (Dutch/English) |
| `month` | Period in `YYYY-MMM` format (e.g. `2025-M01`) |
| `quarter` | Period in `YYYY-QN` format (e.g. `2025-Q1`) |
| `year` | 4-digit year string |
| `profit` | Signed float; positive = income, negative = expense |

---

## Challenges & Solutions

| Challenge | Solution |
|---|---|
| Many rows have `property_name = None` (entity-level entries) | Used `dropna=False` in `groupby` and graceful empty-DataFrame checks in each node |
| Ledger descriptions are bilingual (Dutch/English) | LLM handles language-agnostic interpretation in both supervisor and formatter |
| Users may refer to properties informally | LLM entity resolution maps informal names to canonical ones in the supervisor prompt |
| Ambiguous time references ("this year", "last quarter") | Supervisor prompt instructs GPT-4o to infer sensible defaults (e.g. "this year" → "2025") |
| `error` field was defined but never used | Each data node now wraps queries in try/except and the formatter surfaces errors gracefully |

---

## Project Structure

```
real_estate_agent/
├── app.py              # Streamlit chat UI
├── graph.py            # LangGraph graph definition
├── state.py            # AgentState TypedDict
├── config.py           # API key and data path
├── requirements.txt
├── data/
│   └── properties.csv
├── nodes/
│   ├── supervisor.py   # Intent classification + filter extraction (GPT-4o)
│   ├── pl.py           # P&L aggregation
│   ├── property.py     # Property detail retrieval
│   ├── compare.py      # Multi-property profit comparison
│   ├── general.py      # General real estate knowledge (GPT-4o)
│   ├── clarify.py      # Targeted clarification questions (GPT-4o)
│   └── formatter.py    # Natural language response generation (GPT-4o)
└── tools/
    └── data.py         # CSV loader + pandas query functions
```
