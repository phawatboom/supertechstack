import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.post import Post, PostVersion, PublicationChunk
from app.models.source import Source
from app.schemas.post import PostStatus, PostVisibility
from app.services.chunking import chunk_text
from app.services.content_representations import (
    derive_plain_text,
    normalize_markdown_content,
)
from app.services.embeddings import create_embeddings

SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def create_slug(title: str) -> str:
    slug = SLUG_PATTERN.sub("-", title.lower()).strip("-")
    return slug[:80] or "post"


def create_excerpt(markdown_content: str, max_length: int = 280) -> str:
    plain_text = derive_plain_text(markdown_content)

    if len(plain_text) <= max_length:
        return plain_text

    truncated = plain_text[: max_length + 1].rsplit(" ", 1)[0].strip()
    return truncated or plain_text[:max_length].strip()


def create_unique_slug(
    database_session: Session,
    workspace_id: int,
    title: str,
    exclude_post_id: int | None = None,
) -> str:
    base_slug = create_slug(title)
    slug = base_slug
    suffix = 2

    while True:
        slug_query = database_session.query(Post.id).filter(
            Post.workspace_id == workspace_id,
            Post.slug == slug,
        )

        if exclude_post_id is not None:
            slug_query = slug_query.filter(Post.id != exclude_post_id)

        if slug_query.first() is None:
            return slug

        suffix_text = f"-{suffix}"
        slug = f"{base_slug[: 255 - len(suffix_text)]}{suffix_text}"
        suffix += 1


def create_post_from_source(
    database_session: Session,
    source: Source,
    author_id: str,
    *,
    title: str | None = None,
    excerpt: str | None = None,
    cover_image_url: str | None = None,
    visibility: PostVisibility = "private",
) -> Post:
    post_title = (title or source.title).strip()

    if not post_title:
        raise ValueError("Post title cannot be blank")

    markdown_content = normalize_markdown_content(source.markdown_content)
    post = Post(
        workspace_id=source.workspace_id,
        source_id=source.id,
        author_id=author_id,
        title=post_title,
        slug=create_unique_slug(database_session, source.workspace_id, post_title),
        markdown_content=markdown_content,
        excerpt=excerpt or create_excerpt(markdown_content),
        cover_image_url=cover_image_url,
        visibility=visibility,
        status="draft",
    )

    try:
        database_session.add(post)
        database_session.commit()
        database_session.refresh(post)
    except Exception:
        database_session.rollback()
        raise

    return post


def publish_post_if_needed(post: Post, status: PostStatus | None) -> None:
    if status == "published" and post.published_at is None:
        post.published_at = datetime.utcnow()


def _latest_post_version(
    database_session: Session,
    post_id: int,
) -> PostVersion | None:
    return (
        database_session.query(PostVersion)
        .filter(PostVersion.post_id == post_id)
        .order_by(PostVersion.version_number.desc())
        .first()
    )


def _post_matches_version(post: Post, version: PostVersion) -> bool:
    return (
        post.title == version.title
        and post.slug == version.slug
        and post.markdown_content == version.markdown_content
        and post.excerpt == version.excerpt
        and post.cover_image_url == version.cover_image_url
        and post.visibility == version.visibility
    )


def create_post_version_if_needed(
    database_session: Session,
    post: Post,
) -> PostVersion | None:
    if post.status != "published":
        return None

    if post.published_at is None:
        post.published_at = datetime.utcnow()

    latest_version = _latest_post_version(database_session, post.id)

    if latest_version is not None and _post_matches_version(post, latest_version):
        return latest_version

    plain_text = derive_plain_text(post.markdown_content)
    version = PostVersion(
        post_id=post.id,
        version_number=1 if latest_version is None else latest_version.version_number + 1,
        author_id=post.author_id,
        title=post.title,
        slug=post.slug,
        markdown_content=post.markdown_content,
        plain_text=plain_text,
        excerpt=post.excerpt,
        cover_image_url=post.cover_image_url,
        visibility=post.visibility,
        published_at=post.published_at,
    )
    database_session.add(version)
    database_session.flush()

    chunk_contents = chunk_text(plain_text)
    chunk_embeddings = create_embeddings(chunk_contents)

    if len(chunk_embeddings) != len(chunk_contents):
        raise RuntimeError("Failed to generate embeddings for all publication chunks")

    database_session.add_all(
        [
            PublicationChunk(
                post_version_id=version.id,
                chunk_index=index,
                content=chunk_content,
                embedding=chunk_embeddings[index],
            )
            for index, chunk_content in enumerate(chunk_contents)
        ]
    )

    return version
