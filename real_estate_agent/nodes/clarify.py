from openai import OpenAI
from config import OPENAI_API_KEY
from tools.data import get_unique_values

client = OpenAI(api_key=OPENAI_API_KEY)


def clarify_node(state: dict) -> dict:
    properties = get_unique_values("property_name")
    years = get_unique_values("year")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a real estate assistant. The user asked something ambiguous or incomplete. "
                    "Ask ONE short, targeted clarifying question to help resolve the ambiguity. "
                    "Be specific: suggest relevant property names, time periods, or request types if helpful. "
                    f"Known properties: {properties}. Available years: {years}. "
                    "Do not answer the question — only ask for clarification."
                ),
            },
            {"role": "user", "content": state["question"]},
        ],
    )
    answer = response.choices[0].message.content
    return {**state, "answer": answer}
