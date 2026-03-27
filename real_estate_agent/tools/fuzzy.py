from rapidfuzz import process
from tools.data import get_unique_values


def fuzzy_match(user_input: str, column: str, threshold: int = 80) -> str | None:
    if not user_input:
        return None
    choices = get_unique_values(column)
    result = process.extractOne(user_input, choices)
    if result and result[1] >= threshold:
        return result[0]
    return None
