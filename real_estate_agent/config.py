import os
from pathlib import Path

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "data" / "properties.csv"
