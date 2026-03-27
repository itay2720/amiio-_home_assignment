You are building a multi-agent real estate asset management system.
Tech stack: Python, LangGraph, OpenAI GPT-4o, Pandas, Streamlit, RapidFuzz.

=== PROJECT STRUCTURE ===

real_estate_agent/
├── app.py              # Streamlit UI
├── graph.py            # LangGraph graph definition (MAIN FILE)
├── state.py            # AgentState TypedDict
├── nodes/
│   ├── supervisor.py   # Intent detection + filter extraction
│   ├── pl.py           # P&L calculations
│   ├── property.py     # Property details
│   ├── compare.py      # Property comparison
│   ├── clarify.py      # Handle unclear input
│   └── formatter.py    # Format final response
├── tools/
│   ├── data.py         # CSV loader + pandas queries
│   └── fuzzy.py        # Fuzzy matching on property/tenant names
├── config.py           # OPENAI_API_KEY, CSV_PATH
└── data/properties.csv

=== STATE (state.py) ===

class AgentState(TypedDict):
    question: str
    intent: str           # "pl" | "property" | "compare" | "clarify"
    filters: dict         # {property_name, tenant_name, year, quarter, month, ledger_type}
    data: list            # query result rows
    answer: str
    error: str

=== DATA LAYER (tools/data.py) ===

Load CSV once at import.
Columns: entity_name, property_name, tenant_name, ledger_type,
         ledger_group, ledger_category, ledger_code, ledger_description,
         month, quarter, year, profit

Expose these functions only:
- get_unique_values(col) → list          # for fuzzy matching
- query_pl(filters: dict) → DataFrame    # filter + sum profit
- query_property(filters: dict) → DataFrame
- query_compare(properties: list, filters: dict) → dict  # {property: sum}

=== FUZZY MATCHING (tools/fuzzy.py) ===

from rapidfuzz import process

def fuzzy_match(user_input: str, column: str, threshold=80) -> str | None:
    choices = get_unique_values(column)
    result = process.extractOne(user_input, choices)
    if result and result[1] >= threshold:
        return result[0]
    return None

Use this in supervisor.py after GPT extracts raw values.

=== NODES ===

--- supervisor.py ---
One GPT-4o call. System prompt includes:
- List of known properties (from get_unique_values("property_name"))
- List of known tenants
- Available years and quarters
Task: return JSON with {intent, raw_filters}
Then run fuzzy_match on each extracted string value.
Save to state: intent + filters (cleaned).

--- pl.py ---
Call query_pl(state["filters"])
Compute total profit.
Save result rows to state["data"].

--- property.py ---
Call query_property(state["filters"])
Save to state["data"].

--- compare.py ---
Extract list of properties from state["filters"]["properties"]
Call query_compare(properties, filters)
Save dict to state["data"].

--- clarify.py ---
Set state["answer"] = "Could not understand your request. Please specify property name, time period, or request type."
No LLM call needed.

--- formatter.py ---
One GPT-4o call.
Input: question + data from state.
Output: clean natural language answer.
Save to state["answer"].

=== GRAPH (graph.py) ===

from langgraph.graph import StateGraph, END

def route(state) -> str:
    return state["intent"]  # "pl" | "property" | "compare" | "clarify"

builder = StateGraph(AgentState)
builder.add_node("supervisor", supervisor_node)
builder.add_node("pl", pl_node)
builder.add_node("property", property_node)
builder.add_node("compare", compare_node)
builder.add_node("clarify", clarify_node)
builder.add_node("formatter", formatter_node)

builder.set_entry_point("supervisor")
builder.add_conditional_edges("supervisor", route)

for node in ["pl", "property", "compare"]:
    builder.add_edge(node, "formatter")

builder.add_edge("clarify", END)
builder.add_edge("formatter", END)

graph = builder.compile()

=== STREAMLIT UI (app.py) ===

Simple chat interface:
- st.chat_input for user question
- st.chat_message for history
- Call graph.invoke({"question": user_input})
- Display state["answer"]
- Show expandable "Debug" section with state["intent"] + state["filters"]

=== RULES ===
- Keep each file under 80 lines
- No classes, only functions
- Load CSV once (module level), never inside a function
- All GPT calls use response_format={"type": "json_object"} where JSON is expected
- Handle empty DataFrame results gracefully in every node
- Do not over-engineer — no retry logic, no async, no streaming

Build file by file in this order:
1. state.py
2. config.py  
3. tools/data.py
4. tools/fuzzy.py
5. nodes/ (all 6)
6. graph.py
7. app.py