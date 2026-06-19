from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

API_DIR = Path(__file__).resolve().parents[2]
load_dotenv(API_DIR / ".env")

EMBEDDING_MODEL = "text-embedding-3-small"

embedding_client = OpenAI()


def create_embedding(text: str) -> list[float]:
    cleaned_text = text.replace("\n", " ").strip()

    if not cleaned_text:
        return []

    response = embedding_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=cleaned_text,
    )

    return response.data[0].embedding


def create_embeddings(texts: list[str]) -> list[list[float]]:
    cleaned_texts = [text.replace("\n", " ").strip() for text in texts]
    cleaned_texts = [text for text in cleaned_texts if text]

    if not cleaned_texts:
        return []

    response = embedding_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=cleaned_texts,
    )

    return [item.embedding for item in response.data]
