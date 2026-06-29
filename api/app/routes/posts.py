from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_database_session
from app.models.post import Post
from app.models.source import Source
from app.models.workspace import Workspace
from app.rate_limit import enforce_rate_limit
from app.schemas.post import (
    CreatePostFromSourceRequest,
    PublicFeedPostResponse,
    PublicPostResponse,
    PostResponse,
    PostUpdate,
)
from app.security import Principal, get_owned_workspace, optional_principal
from app.services.content_representations import normalize_markdown_content
from app.services.post_publishing import (
    create_post_from_source,
    create_unique_slug,
    publish_post_if_needed,
)

router = APIRouter(tags=["posts"])


def _get_workspace_post(
    workspace_id: int,
    post_id: int,
    database_session: Session,
) -> Post:
    post = (
        database_session.query(Post)
        .filter(Post.workspace_id == workspace_id, Post.id == post_id)
        .first()
    )

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    return post


@router.get(
    "/feed/public",
    response_model=list[PublicFeedPostResponse],
)
def list_public_feed_posts(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    database_session: Session = Depends(get_database_session),
):
    rows = (
        database_session.query(Post, Workspace.name)
        .join(Workspace, Workspace.id == Post.workspace_id)
        .filter(Post.status == "published", Post.visibility == "public")
        .order_by(Post.published_at.desc(), Post.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        PublicFeedPostResponse.model_validate(
            {
                **post.__dict__,
                "workspace_name": workspace_name,
            }
        )
        for post, workspace_name in rows
    ]


@router.get(
    "/posts/{post_id}",
    response_model=PublicPostResponse,
)
def get_public_post(
    post_id: int,
    principal: Principal | None = Depends(optional_principal),
    database_session: Session = Depends(get_database_session),
):
    row = (
        database_session.query(Post, Workspace.name, Workspace.owner_id, Source.title)
        .join(Workspace, Workspace.id == Post.workspace_id)
        .outerjoin(Source, Source.id == Post.source_id)
        .filter(Post.id == post_id)
        .first()
    )

    if row is None:
        raise HTTPException(status_code=404, detail="Post not found")

    post, workspace_name, workspace_owner_id, source_title = row
    is_publicly_readable = (
        post.status == "published"
        and post.visibility in {"public", "unlisted"}
    )
    is_owner = (
        principal is not None
        and workspace_owner_id == principal.owner_id
    )

    if not is_publicly_readable and not is_owner:
        raise HTTPException(status_code=404, detail="Post not found")

    return PublicPostResponse.model_validate(
        {
            **post.__dict__,
            "workspace_name": workspace_name,
            "source_title": source_title,
        }
    )


@router.post(
    "/workspaces/{workspace_id}/sources/{source_id}/posts",
    response_model=PostResponse,
)
def create_source_post(
    workspace_id: int,
    source_id: int,
    post_input: CreatePostFromSourceRequest | None = None,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)
    source = (
        database_session.query(Source)
        .filter(Source.workspace_id == workspace_id, Source.id == source_id)
        .first()
    )

    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    post_input = post_input or CreatePostFromSourceRequest()

    try:
        return create_post_from_source(
            database_session=database_session,
            source=source,
            author_id=principal.owner_id,
            title=post_input.title,
            excerpt=post_input.excerpt,
            cover_image_url=post_input.cover_image_url,
            visibility=post_input.visibility,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/workspaces/{workspace_id}/posts",
    response_model=list[PostResponse],
)
def list_posts(
    workspace_id: int,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)
    return (
        database_session.query(Post)
        .filter(Post.workspace_id == workspace_id)
        .order_by(Post.created_at.desc())
        .all()
    )


@router.patch(
    "/workspaces/{workspace_id}/posts/{post_id}",
    response_model=PostResponse,
)
def update_post(
    workspace_id: int,
    post_id: int,
    post_input: PostUpdate,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)
    post = _get_workspace_post(workspace_id, post_id, database_session)

    if post_input.title is not None:
        post.title = post_input.title
        post.slug = create_unique_slug(
            database_session,
            workspace_id,
            post_input.title,
            exclude_post_id=post.id,
        )

    if post_input.markdown_content is not None:
        post.markdown_content = normalize_markdown_content(
            post_input.markdown_content
        )

    if "excerpt" in post_input.model_fields_set:
        post.excerpt = post_input.excerpt

    if "cover_image_url" in post_input.model_fields_set:
        post.cover_image_url = post_input.cover_image_url

    if post_input.visibility is not None:
        post.visibility = post_input.visibility

    if post_input.status is not None:
        post.status = post_input.status
        publish_post_if_needed(post, post_input.status)

    try:
        database_session.commit()
        database_session.refresh(post)
    except Exception:
        database_session.rollback()
        raise

    return post
