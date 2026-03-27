import json
import re
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def _clean_answer(text: str) -> str:
    if not text:
        return ""

    # Fix cases like "m i n u s" and "i n r e v e n u e" into normal words.
    text = re.sub(r"(?<!\w)([A-Za-z])(?:\s+([A-Za-z])){2,}", lambda m: m.group(0).replace(" ", ""), text)
    # Collapse excessive whitespace while preserving paragraph breaks.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def formatter_node(state: dict) -> dict:
    error = state.get("error", "")
    if error:
        return {**state, "answer": f"An error occurred while retrieving data: {error}"}

    data = state.get("data")
    if not data:
        return state

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a real estate financial analyst. "
                        "Return a clear, concise final answer for the user.\n\n"
                        "Style rules:\n"
                        "- 2-6 sentences max.\n"
                        "- Lead with the direct answer in the first sentence.\n"
                        "- Use plain English and avoid step-by-step arithmetic narration unless explicitly requested.\n"
                        "- Include only the most relevant figures.\n"
                        "- Format money as $1,234.56.\n"
                        "- Do not repeat numbers with different spacing.\n"
                        "- Do not output character-by-character text.\n"
                        "- If no results exist, state that clearly and suggest one short follow-up.\n\n"
                        "Good examples:\n"
                        '- "The total P&L for all your properties this year is $1,200,000."\n'
                        '- "Building 180 generated higher net income than Building 140 in 2025: $95,400 vs $82,100."'
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question: {state['question']}\n\nData:\n{json.dumps(data, indent=2, default=str)}",
                },
            ],
        )
        answer = _clean_answer(response.choices[0].message.content or "")
        return {**state, "answer": answer}
    except Exception as exc:
        return {**state, "answer": f"Failed to generate response: {exc}"}
