from tools.data import query_pl


def pl_node(state: dict) -> dict:
    try:
        df = query_pl(state.get("filters", {}))
        if df.empty:
            return {**state, "data": [], "answer": "No P&L data found for the given filters."}
        return {**state, "data": df.to_dict(orient="records"), "error": ""}
    except Exception as exc:
        return {**state, "data": [], "error": f"P&L query failed: {exc}"}
