import pandas as pd
from config import CSV_PATH

_df = pd.read_csv(CSV_PATH)


def get_unique_values(col: str) -> list:
    return _df[col].dropna().unique().tolist()


def _apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    mapping = {
        "property_name": "property_name",
        "tenant_name": "tenant_name",
        "year": "year",
        "quarter": "quarter",
        "month": "month",
        "ledger_type": "ledger_type",
    }
    for key, col in mapping.items():
        val = filters.get(key)
        if val:
            df = df[df[col].astype(str).str.lower() == str(val).lower()]
    return df


def query_pl(filters: dict) -> pd.DataFrame:
    df = _apply_filters(_df.copy(), filters)
    if df.empty:
        return df
    return (
        df.groupby(
            ["property_name", "month", "ledger_type", "ledger_group"], dropna=False
        )["profit"]
        .sum()
        .reset_index()
    )


def query_property(filters: dict) -> pd.DataFrame:
    return _apply_filters(_df.copy(), filters)


def query_compare(properties: list, filters: dict) -> dict:
    result = {}
    for prop in properties:
        f = {**filters, "property_name": prop}
        df = _apply_filters(_df.copy(), f)
        result[prop] = round(df["profit"].sum(), 2)
    return result
