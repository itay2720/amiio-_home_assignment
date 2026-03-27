from langgraph.graph import StateGraph, END
from state import AgentState
from nodes.supervisor import supervisor_node
from nodes.pl import pl_node
from nodes.property import property_node
from nodes.compare import compare_node
from nodes.clarify import clarify_node
from nodes.formatter import formatter_node
from nodes.general import general_node


def route(state: AgentState) -> str:
    return state.get("intent", "clarify")


builder = StateGraph(AgentState)

builder.add_node("supervisor", supervisor_node)
builder.add_node("pl", pl_node)
builder.add_node("property", property_node)
builder.add_node("compare", compare_node)
builder.add_node("clarify", clarify_node)
builder.add_node("formatter", formatter_node)
builder.add_node("general", general_node)

builder.set_entry_point("supervisor")
builder.add_conditional_edges("supervisor", route)

for node in ["pl", "property", "compare"]:
    builder.add_edge(node, "formatter")

builder.add_edge("general", END)
builder.add_edge("clarify", END)
builder.add_edge("formatter", END)

graph = builder.compile()
