from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def general_node(state: dict) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a knowledgeable real estate expert and asset management advisor. "
                    "Answer general real estate questions clearly and concisely. "
                    "If the question is about market trends, valuations, investment strategies, "
                    "legal concepts, or asset management best practices, provide a professional answer. "
                    "Do not reference any specific internal dataset."
                ),
            },
            {"role": "user", "content": state["question"]},
        ],
    )
    answer = response.choices[0].message.content
    return {**state, "answer": answer}
