from tools.data import query_property


def property_node(state: dict) -> dict:
    try:
        df = query_property(state.get("filters", {}))
        if df.empty:
            return {**state, "data": [], "answer": "No property data found for the given filters."}
        return {**state, "data": df.to_dict(orient="records"), "error": ""}
    except Exception as exc:
        return {**state, "data": [], "error": f"Property query failed: {exc}"}
