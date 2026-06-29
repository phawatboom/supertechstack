from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_database_session
from app.models.post import Post, PostVersion, WorkspacePostImport, WorkspacePostSave
from app.models.source import Source
from app.models.workspace import Workspace
from app.rate_limit import enforce_rate_limit
from app.schemas.post import (
    CreatePostFromSourceRequest,
    ImportedPostResponse,
    ImportPostRequest,
    PublicFeedPostResponse,
    PublicPostResponse,
    PostResponse,
    PostUpdate,
    SavedPostResponse,
    SavePostRequest,
)
from app.security import Principal, get_owned_workspace, optional_principal
from app.services.content_representations import normalize_markdown_content
from app.services.post_publishing import (
    create_post_from_source,
    create_post_version_if_needed,
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


def _can_read_post(
    post: Post,
    workspace_owner_id: str,
    principal: Principal | None,
) -> bool:
    if post.status == "published" and post.visibility in {"public", "unlisted"}:
        return True

    return principal is not None and workspace_owner_id == principal.owner_id


def _get_readable_post_row(
    post_id: int,
    principal: Principal | None,
    database_session: Session,
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

    if not _can_read_post(post, workspace_owner_id, principal):
        raise HTTPException(status_code=404, detail="Post not found")

    return post, workspace_name, workspace_owner_id, source_title


def _latest_available_post_version(
    post_id: int,
    database_session: Session,
) -> PostVersion:
    version = (
        database_session.query(PostVersion)
        .filter(
            PostVersion.post_id == post_id,
            PostVersion.is_available.is_(True),
        )
        .order_by(PostVersion.version_number.desc())
        .first()
    )

    if version is None:
        raise HTTPException(
            status_code=409,
            detail="Post has no importable published version",
        )

    return version


def _saved_post_response(
    save: WorkspacePostSave,
    post: Post,
) -> SavedPostResponse:
    return SavedPostResponse(
        workspace_id=save.workspace_id,
        post_id=save.post_id,
        saved_by=save.saved_by,
        created_at=save.created_at,
        title=post.title,
        visibility=post.visibility,
        status=post.status,
    )


def _imported_post_response(
    imported_post: WorkspacePostImport,
    version: PostVersion,
) -> ImportedPostResponse:
    return ImportedPostResponse(
        workspace_id=imported_post.workspace_id,
        post_version_id=imported_post.post_version_id,
        imported_by=imported_post.imported_by,
        imported_at=imported_post.imported_at,
        post_id=version.post_id,
        version_number=version.version_number,
        title=version.title,
    )


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
    post, workspace_name, _, source_title = _get_readable_post_row(
        post_id,
        principal,
        database_session,
    )

    return PublicPostResponse.model_validate(
        {
            **post.__dict__,
            "workspace_name": workspace_name,
            "source_title": source_title,
        }
    )


@router.post(
    "/workspaces/{workspace_id}/saved-posts",
    response_model=SavedPostResponse,
)
def save_post_to_workspace(
    workspace_id: int,
    save_input: SavePostRequest,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)
    post, _, _, _ = _get_readable_post_row(
        save_input.post_id,
        principal,
        database_session,
    )
    existing_save = database_session.get(
        WorkspacePostSave,
        {
            "workspace_id": workspace_id,
            "post_id": post.id,
        },
    )

    if existing_save is not None:
        return _saved_post_response(existing_save, post)

    save = WorkspacePostSave(
        workspace_id=workspace_id,
        post_id=post.id,
        saved_by=principal.owner_id,
    )
    database_session.add(save)

    try:
        database_session.commit()
        database_session.refresh(save)
    except IntegrityError:
        database_session.rollback()
        existing_save = database_session.get(
            WorkspacePostSave,
            {
                "workspace_id": workspace_id,
                "post_id": post.id,
            },
        )

        if existing_save is None:
            raise

        save = existing_save

    return _saved_post_response(save, post)


@router.get(
    "/workspaces/{workspace_id}/saved-posts",
    response_model=list[SavedPostResponse],
)
def list_saved_posts(
    workspace_id: int,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)
    rows = (
        database_session.query(WorkspacePostSave, Post)
        .join(Post, Post.id == WorkspacePostSave.post_id)
        .filter(WorkspacePostSave.workspace_id == workspace_id)
        .order_by(WorkspacePostSave.created_at.desc())
        .all()
    )

    return [_saved_post_response(save, post) for save, post in rows]


@router.post(
    "/workspaces/{workspace_id}/post-imports",
    response_model=ImportedPostResponse,
)
def import_post_to_workspace(
    workspace_id: int,
    import_input: ImportPostRequest,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)
    post, _, _, _ = _get_readable_post_row(
        import_input.post_id,
        principal,
        database_session,
    )
    version = _latest_available_post_version(post.id, database_session)
    existing_import = database_session.get(
        WorkspacePostImport,
        {
            "workspace_id": workspace_id,
            "post_version_id": version.id,
        },
    )

    if existing_import is not None:
        return _imported_post_response(existing_import, version)

    imported_post = WorkspacePostImport(
        workspace_id=workspace_id,
        post_version_id=version.id,
        imported_by=principal.owner_id,
    )
    database_session.add(imported_post)

    try:
        database_session.commit()
        database_session.refresh(imported_post)
    except IntegrityError:
        database_session.rollback()
        existing_import = database_session.get(
            WorkspacePostImport,
            {
                "workspace_id": workspace_id,
                "post_version_id": version.id,
            },
        )

        if existing_import is None:
            raise

        imported_post = existing_import

    return _imported_post_response(imported_post, version)


@router.get(
    "/workspaces/{workspace_id}/post-imports",
    response_model=list[ImportedPostResponse],
)
def list_imported_posts(
    workspace_id: int,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)
    rows = (
        database_session.query(WorkspacePostImport, PostVersion)
        .join(PostVersion, PostVersion.id == WorkspacePostImport.post_version_id)
        .filter(WorkspacePostImport.workspace_id == workspace_id)
        .order_by(WorkspacePostImport.imported_at.desc())
        .all()
    )

    return [
        _imported_post_response(imported_post, version)
        for imported_post, version in rows
    ]


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
        if post.status == "published":
            create_post_version_if_needed(database_session, post)

        database_session.commit()
        database_session.refresh(post)
    except Exception:
        database_session.rollback()
        raise

    return post
