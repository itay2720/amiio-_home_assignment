from tools.data import get_unique_values, query_compare
from tools.llm_resolve import llm_resolve_properties


def _as_list(value) -> list:
    if isinstance(value, list):
        return [v for v in value if v]
    if value:
        return [value]
    return []


def _dedupe(items: list) -> list:
    seen = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def compare_node(state: dict) -> dict:
    known = get_unique_values("property_name")
    filters = state.get("filters", {})

    # Gather candidates from both filter keys and validate against known list
    candidates = _as_list(filters.get("properties")) + _as_list(filters.get("property_name"))
    properties = _dedupe([p for p in candidates if p in known])

    # Fallback: ask the LLM to resolve property references from the original question
    if len(properties) < 2:
        resolved = llm_resolve_properties(state["question"], known)
        for r in resolved:
            if r not in properties:
                properties.append(r)

    if len(properties) < 2:
        available_txt = ", ".join(known) if known else "None found"
        return {
            **state,
            "data": {},
            "answer": (
                "I could not identify at least two known properties to compare. "
                f"Available properties are: {available_txt}. "
                "Please ask like: Compare Building 180 vs Building 140 in 2025."
            ),
        }

    try:
        result = query_compare(properties, filters)
        return {**state, "data": result, "error": ""}
    except Exception as exc:
        return {**state, "data": {}, "error": f"Comparison query failed: {exc}"}
