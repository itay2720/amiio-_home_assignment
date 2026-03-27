import json
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def llm_resolve_properties(text: str, known_properties: list[str]) -> list[str]:
    """
    Uses the LLM to map any property references in `text` (addresses, nicknames,
    descriptions, partial names, etc.) to canonical names from `known_properties`.
    Only returns names that exist verbatim in `known_properties`.
    """
    if not text or not known_properties:
        return []

    system_prompt = (
        "You are a property name resolver for a real estate dataset. "
        "The user's message may reference properties using addresses, nicknames, "
        "descriptions, partial names, or any other informal reference. "
        "Your job is to identify which canonical property names from the known list "
        "the user is referring to.\n\n"
        f"Known canonical property names:\n{json.dumps(known_properties, indent=2)}\n\n"
        "Rules:\n"
        "- Return ONLY a JSON object with a single key 'properties' containing a list of matched canonical names.\n"
        "- Only include names that appear verbatim in the known list above.\n"
        "- Do NOT invent or guess names not in the list.\n"
        "- If the user mentions 'both', 'all', or similar — include all properties that seem relevant.\n"
        "- If nothing can be confidently matched, return an empty list.\n\n"
        "Example output: {\"properties\": [\"Building 180\", \"Building 140\"]}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        )
        parsed = json.loads(response.choices[0].message.content)
        resolved = parsed.get("properties", [])
        # Validate that every returned name is actually in the known list
        return [p for p in resolved if p in known_properties]
    except Exception:
        return []
