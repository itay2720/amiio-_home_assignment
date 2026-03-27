from typing import TypedDict, Any, Literal


class AgentState(TypedDict):
    question: str
    intent: Literal["pl", "property", "compare", "general", "clarify"]
    filters: dict     # {property_name, tenant_name, year, quarter, month, ledger_type}
    data: Any         # query result rows
    answer: str
    error: str
