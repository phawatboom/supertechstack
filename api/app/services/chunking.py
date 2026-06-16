def clean_text(text:str) -> str:
    return " ".join(text.split())
def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    
    cleaned_text = clean_text(text)

    if not cleaned_text:
        return []
    
    chunks = []
    start = 0

    while start < len(cleaned_text):
        end = start + chunk_size 
        chunk = cleaned_text[start:end].strip()

        if chunk:
            chunks.append(chunk)
        
        start = end - overlap

        if start < 0:
            start = 0
    return chunks

