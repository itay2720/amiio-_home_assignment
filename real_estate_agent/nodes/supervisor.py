import json
from openai import OpenAI
from config import OPENAI_API_KEY
from tools.data import get_unique_values
from tools.llm_resolve import llm_resolve_properties

client = OpenAI(api_key=OPENAI_API_KEY)


def supervisor_node(state: dict) -> dict:
    properties = get_unique_values("property_name")
    tenants = get_unique_values("tenant_name")
    ledger_types = get_unique_values("ledger_type")
    years = get_unique_values("year")
    quarters = get_unique_values("quarter")

    system_prompt = f"""You are a real estate data assistant. Extract the user's intent and filters from their question.

Known property names (use EXACT spelling from this list, or null):
{properties}

Known tenant names (use EXACT spelling from this list, or null):
{tenants}

Known ledger types (use EXACT spelling from this list, or null):
{ledger_types}

Available years: {years}
Available quarters: {quarters}

Return ONLY valid JSON with this structure:
{{
  "intent": "pl" | "property" | "compare" | "general" | "clarify",
  "filters": {{
    "property_name": "<exact canonical name from list above, or null>",
    "tenant_name": "<exact canonical name from list above, or null>",
    "year": "<string or null>",
    "quarter": "<string or null>",
    "month": "<string or null, format 2024-M01>",
    "ledger_type": "<exact canonical name from list above, or null>",
    "properties": ["<exact name 1>", "<exact name 2>"]
  }}
}}

Intent guide:
- "pl": profit & loss, financial summary, income/expense totals, revenue/cost questions
- "property": details about a specific property or tenant
- "compare": comparing two or more properties side by side
- "general": general real estate knowledge not requiring the dataset (e.g. market trends, definitions, advice)
- "clarify": truly ambiguous or incomplete — cannot determine intent even with inference. Do NOT use "clarify" just because property names are unrecognized; if the intent is clear (e.g. user says "compare", "P&L", "details"), use the correct intent and leave filters null/empty.

Important:
- For "compare", populate "properties" with the list of exact property names being compared.
- Always prefer matching to a known name over returning null; only return null if genuinely absent.
- For time filters, infer reasonable defaults (e.g. "this year" → current year "2025")."""

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["question"]},
        ],
    )

    parsed = json.loads(response.choices[0].message.content)
    intent = parsed.get("intent", "clarify")
    filters = parsed.get("filters", {})

    filters = {k: v for k, v in filters.items() if v}

    # Post-validate extracted property names and re-resolve any that don't match
    # the canonical list (e.g. user typed an address or nickname).
    if intent == "compare":
        known = get_unique_values("property_name")
        raw_props = filters.get("properties") or []
        if isinstance(raw_props, str):
            raw_props = [raw_props]

        valid = [p for p in raw_props if p in known]
        unmatched = [p for p in raw_props if p not in known]

        if unmatched:
            # Re-resolve each unmatched token individually to avoid false positives
            for token in unmatched:
                resolved = llm_resolve_properties(token, known)
                for r in resolved:
                    if r not in valid:
                        valid.append(r)

        # If the supervisor found no properties at all, try resolving from the
        # full question so partial/implicit references are caught.
        if not valid:
            resolved = llm_resolve_properties(state["question"], known)
            valid = list(dict.fromkeys(resolved))  # deduplicate, preserve order

        if valid:
            filters["properties"] = valid
        elif "properties" in filters:
            del filters["properties"]

    return {**state, "intent": intent, "filters": filters}
