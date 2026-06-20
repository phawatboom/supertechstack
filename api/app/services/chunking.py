from __future__ import annotations


SENTENCE_ENDINGS = (". ", "? ", "! ", "\n")


def clean_text(text: str) -> str:
    return " ".join(text.split())


def find_chunk_end(
    text: str,
    target_end: int,
    max_end: int,
) -> int:
    """Find the nearest preferred boundary without exceeding max_end."""
    if target_end >= len(text):
        return len(text)

    candidates: list[int] = []
    search_stop = min(max_end + 1, len(text))

    for ending in SENTENCE_ENDINGS:
        position = text.find(ending, target_end, search_stop)

        if position != -1:
            boundary = position + len(ending)

            if boundary <= max_end:
                candidates.append(boundary)

    if candidates:
        return min(candidates)

    for position in range(target_end, max_end):
        if text[position].isspace():
            return position

    return target_end


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 100,
    lookahead: int = 100,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    if lookahead < 0:
        raise ValueError("lookahead cannot be negative")

    cleaned_text = clean_text(text)

    if not cleaned_text:
        return []

    chunks: list[str] = []
    start = 0
    text_length = len(cleaned_text)

    while start < text_length:
        target_end = min(start + chunk_size, text_length)
        max_end = min(target_end + lookahead, text_length)
        end = find_chunk_end(cleaned_text, target_end, max_end)
        chunk = cleaned_text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = max(end - overlap, start + 1)

    return chunks
