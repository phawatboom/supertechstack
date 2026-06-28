import re


MARKDOWN_LINK_PATTERN = re.compile(r"!?\[([^\]]*)\]\(([^)]*)\)")
MARKDOWN_HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
MARKDOWN_TABLE_SEPARATOR_PATTERN = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$",
    re.MULTILINE,
)
MARKDOWN_STYLE_PATTERN = re.compile(r"(\*\*|__|\*|_|~~|`)")
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def normalize_markdown_content(content: str) -> str:
    """Normalize imported content into the canonical editable representation."""
    lines = [line.rstrip() for line in content.replace("\r\n", "\n").split("\n")]
    normalized = "\n".join(lines).strip()

    if not normalized:
        raise ValueError("Markdown content cannot be blank")

    return normalized


def markdown_to_plain_text(markdown_content: str) -> str:
    """Convert Markdown into a plain-text representation for indexing."""
    text = markdown_content.replace("\r\n", "\n")
    text = MARKDOWN_LINK_PATTERN.sub(r"\1", text)
    text = MARKDOWN_HEADING_PATTERN.sub("", text)
    text = MARKDOWN_TABLE_SEPARATOR_PATTERN.sub("", text)

    cleaned_lines: list[str] = []
    in_fenced_code_block = False

    for line in text.split("\n"):
        stripped_line = line.strip()

        if stripped_line.startswith("```") or stripped_line.startswith("~~~"):
            in_fenced_code_block = not in_fenced_code_block
            continue

        if not in_fenced_code_block:
            stripped_line = re.sub(r"^\s*[-*+]\s+", "", stripped_line)
            stripped_line = re.sub(r"^\s*\d+\.\s+", "", stripped_line)
            stripped_line = re.sub(r"^\s*>\s?", "", stripped_line)
            stripped_line = stripped_line.replace("|", " ")

        cleaned_lines.append(stripped_line)

    text = "\n".join(cleaned_lines)
    text = HTML_TAG_PATTERN.sub("", text)
    text = MARKDOWN_STYLE_PATTERN.sub("", text)
    return " ".join(text.split())


def derive_plain_text(markdown_content: str) -> str:
    plain_text = markdown_to_plain_text(markdown_content)

    if not plain_text:
        raise ValueError("Plain text cannot be blank")

    return plain_text
