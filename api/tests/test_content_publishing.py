import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.models.chunk import Chunk
from app.models.post import Post
from app.models.source import Source
from app.models.workspace import Workspace
from app.routes.posts import (
    create_source_post,
    list_posts,
    list_public_feed_posts,
    update_post,
)
from app.routes.sources import delete_source, update_source
from app.schemas.post import CreatePostFromSourceRequest, PostUpdate
from app.schemas.source import SourceUpdate
from app.security import Principal
from app.services.content_representations import markdown_to_plain_text
from app.services.file_extraction import extract_text_from_file
from app.services.source_ingestion import ingest_source_text


@pytest.fixture
def database_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture
def stub_embeddings(monkeypatch):
    def create_embeddings(texts: list[str]) -> list[list[float]]:
        return [[0.0] * 1536 for _ in texts]

    monkeypatch.setattr(
        "app.services.source_ingestion.create_embeddings",
        create_embeddings,
    )


def create_workspace(
    database_session: Session,
    owner_id: str = "user-a",
) -> Workspace:
    workspace = Workspace(
        owner_id=owner_id,
        name="Publishing workspace",
    )
    database_session.add(workspace)
    database_session.commit()
    database_session.refresh(workspace)
    return workspace


def principal(owner_id: str = "user-a") -> Principal:
    return Principal(
        owner_id=owner_id,
        rate_limit_key=f"owner:{owner_id}",
    )


def test_markdown_to_plain_text_removes_formatting():
    assert (
        markdown_to_plain_text(
            "# NVIDIA Thesis\n\n"
            "- AI demand\n"
            "- Read the [annual report](https://example.com)\n"
        )
        == "NVIDIA Thesis AI demand Read the annual report"
    )


def test_ingest_source_stores_markdown_and_indexes_plain_text(
    database_session: Session,
    stub_embeddings,
):
    workspace = create_workspace(database_session)

    source = ingest_source_text(
        database_session=database_session,
        workspace_id=workspace.id,
        title=" NVIDIA thesis ",
        raw_text="Original imported content",
        markdown_content="# NVIDIA Thesis\n\nRead the [report](https://example.com).",
        source_type="pasted_text",
    )
    chunk = database_session.query(Chunk).filter(Chunk.source_id == source.id).one()

    assert source.raw_text == "Original imported content"
    assert source.markdown_content == (
        "# NVIDIA Thesis\n\nRead the [report](https://example.com)."
    )
    assert source.plain_text == "NVIDIA Thesis Read the report."
    assert chunk.content == source.plain_text


def test_pasted_source_markdown_is_embedded_as_plain_text(
    database_session: Session,
    stub_embeddings,
):
    workspace = create_workspace(database_session)
    pasted_markdown = (
        "# Pasted Thesis\n\n"
        "- AI infrastructure demand\n"
        "- Read the [annual report](https://example.com/report)\n"
    )

    source = ingest_source_text(
        database_session=database_session,
        workspace_id=workspace.id,
        title="Pasted thesis",
        raw_text=pasted_markdown,
        source_type="pasted_text",
    )
    chunk = database_session.query(Chunk).filter(Chunk.source_id == source.id).one()

    assert source.raw_text == pasted_markdown.strip()
    assert source.markdown_content == pasted_markdown.strip()
    assert source.plain_text == (
        "Pasted Thesis AI infrastructure demand Read the annual report"
    )
    assert chunk.content == source.plain_text


def test_markdown_upload_preserves_raw_markdown_and_embeds_plain_text(
    database_session: Session,
    stub_embeddings,
):
    workspace = create_workspace(database_session)
    markdown_content = (
        "# Upload Thesis\n\n"
        "- AI infrastructure demand\n"
        "- Read the [annual report](https://example.com/report)\n"
    )
    extracted_file = extract_text_from_file(
        filename="thesis.md",
        content=markdown_content.encode("utf-8"),
        content_type="text/markdown",
    )

    source = ingest_source_text(
        database_session=database_session,
        workspace_id=workspace.id,
        title="Upload thesis",
        raw_text=extracted_file.text,
        source_type=extracted_file.source_type,
    )
    chunk = database_session.query(Chunk).filter(Chunk.source_id == source.id).one()

    assert extracted_file.source_type == "markdown_upload"
    assert source.raw_text == markdown_content.strip()
    assert source.markdown_content == markdown_content.strip()
    assert source.plain_text == (
        "Upload Thesis AI infrastructure demand Read the annual report"
    )
    assert chunk.content == source.plain_text


def test_create_post_from_source_copies_markdown_into_independent_draft(
    database_session: Session,
    stub_embeddings,
):
    workspace = create_workspace(database_session)
    source = ingest_source_text(
        database_session=database_session,
        workspace_id=workspace.id,
        title="AI research notes",
        raw_text="Original notes",
        markdown_content="# AI Research\n\n- One finding",
        source_type="pasted_text",
    )

    post = create_source_post(
        workspace_id=workspace.id,
        source_id=source.id,
        post_input=CreatePostFromSourceRequest(visibility="workspace"),
        principal=principal(),
        database_session=database_session,
    )
    source.markdown_content = "# Updated Source"
    database_session.commit()
    database_session.refresh(post)

    assert post.source_id == source.id
    assert post.author_id == "user-a"
    assert post.status == "draft"
    assert post.visibility == "workspace"
    assert post.slug == "ai-research-notes"
    assert post.markdown_content == "# AI Research\n\n- One finding"
    assert post.excerpt == "AI Research One finding"


def test_publish_post_sets_published_at_and_list_is_owner_scoped(
    database_session: Session,
    stub_embeddings,
):
    workspace = create_workspace(database_session)
    source = ingest_source_text(
        database_session=database_session,
        workspace_id=workspace.id,
        title="Market update",
        raw_text="Original notes",
        source_type="pasted_text",
    )
    post = create_source_post(
        workspace_id=workspace.id,
        source_id=source.id,
        post_input=None,
        principal=principal(),
        database_session=database_session,
    )

    updated = update_post(
        workspace_id=workspace.id,
        post_id=post.id,
        post_input=PostUpdate(status="published", visibility="public"),
        principal=principal(),
        database_session=database_session,
    )
    posts = list_posts(
        workspace_id=workspace.id,
        principal=principal(),
        database_session=database_session,
    )

    assert updated.status == "published"
    assert updated.visibility == "public"
    assert updated.published_at is not None
    assert [item.id for item in posts] == [post.id]

    with pytest.raises(HTTPException) as error:
        list_posts(
            workspace_id=workspace.id,
            principal=principal("user-b"),
            database_session=database_session,
        )

    assert error.value.status_code == 404
    assert database_session.query(Post).count() == 1


def test_public_feed_only_lists_public_published_posts(
    database_session: Session,
    stub_embeddings,
):
    workspace = create_workspace(database_session)
    other_workspace = create_workspace(database_session, owner_id="user-b")
    source = ingest_source_text(
        database_session=database_session,
        workspace_id=workspace.id,
        title="Public market update",
        raw_text="Original notes",
        source_type="pasted_text",
    )
    other_source = ingest_source_text(
        database_session=database_session,
        workspace_id=other_workspace.id,
        title="Private market update",
        raw_text="Other notes",
        source_type="pasted_text",
    )
    public_post = create_source_post(
        workspace_id=workspace.id,
        source_id=source.id,
        post_input=None,
        principal=principal(),
        database_session=database_session,
    )
    private_post = create_source_post(
        workspace_id=other_workspace.id,
        source_id=other_source.id,
        post_input=None,
        principal=principal("user-b"),
        database_session=database_session,
    )

    update_post(
        workspace_id=workspace.id,
        post_id=public_post.id,
        post_input=PostUpdate(status="published", visibility="public"),
        principal=principal(),
        database_session=database_session,
    )
    update_post(
        workspace_id=other_workspace.id,
        post_id=private_post.id,
        post_input=PostUpdate(status="published", visibility="private"),
        principal=principal("user-b"),
        database_session=database_session,
    )

    feed_posts = list_public_feed_posts(database_session=database_session)

    assert [post.id for post in feed_posts] == [public_post.id]
    assert feed_posts[0].workspace_name == "Publishing workspace"


def test_delete_source_removes_chunks_and_unlinks_posts(
    database_session: Session,
    stub_embeddings,
):
    workspace = create_workspace(database_session)
    source = ingest_source_text(
        database_session=database_session,
        workspace_id=workspace.id,
        title="Delete me",
        raw_text="Original notes",
        source_type="pasted_text",
    )
    post = create_source_post(
        workspace_id=workspace.id,
        source_id=source.id,
        post_input=None,
        principal=principal(),
        database_session=database_session,
    )

    result = delete_source(
        workspace_id=workspace.id,
        source_id=source.id,
        principal=principal(),
        database_session=database_session,
    )
    database_session.refresh(post)

    assert result["deleted_chunks"] == 1
    assert database_session.get(Source, source.id) is None
    assert database_session.query(Chunk).filter(Chunk.source_id == source.id).count() == 0
    assert post.source_id is None


def test_owner_can_rename_source(
    database_session: Session,
    stub_embeddings,
):
    workspace = create_workspace(database_session)
    source = ingest_source_text(
        database_session=database_session,
        workspace_id=workspace.id,
        title="Draft name",
        raw_text="Original notes",
        source_type="pasted_text",
    )

    updated = update_source(
        workspace_id=workspace.id,
        source_id=source.id,
        source_input=SourceUpdate(title="Final source name"),
        principal=principal(),
        database_session=database_session,
    )

    assert updated.title == "Final source name"


def test_other_user_cannot_rename_source(
    database_session: Session,
    stub_embeddings,
):
    workspace = create_workspace(database_session, owner_id="user-a")
    source = ingest_source_text(
        database_session=database_session,
        workspace_id=workspace.id,
        title="Private notes",
        raw_text="Original notes",
        source_type="pasted_text",
    )

    with pytest.raises(HTTPException) as error:
        update_source(
            workspace_id=workspace.id,
            source_id=source.id,
            source_input=SourceUpdate(title="Other title"),
            principal=principal("user-b"),
            database_session=database_session,
        )

    assert error.value.status_code == 404


def test_other_user_cannot_create_post_from_source(
    database_session: Session,
    stub_embeddings,
):
    workspace = create_workspace(database_session, owner_id="user-a")
    source = ingest_source_text(
        database_session=database_session,
        workspace_id=workspace.id,
        title="Private notes",
        raw_text="Original notes",
        source_type="pasted_text",
    )

    with pytest.raises(HTTPException) as error:
        create_source_post(
            workspace_id=workspace.id,
            source_id=source.id,
            post_input=None,
            principal=principal("user-b"),
            database_session=database_session,
        )

    assert error.value.status_code == 404
    assert database_session.query(Source).count() == 1
    assert database_session.query(Post).count() == 0
