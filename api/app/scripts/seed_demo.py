from app.config import get_settings
from app.db.database import SessionLocal
from app.models.source import Source
from app.models.workspace import Workspace
from app.services.source_ingestion import ingest_source_text


DEMO_SOURCES = (
    (
        "REST API Development",
        """
Reliable REST APIs are organized around resources rather than remote
procedure names. Resource URLs should be stable nouns, while HTTP methods
communicate the requested operation. GET reads, POST creates or initiates
processing, PUT replaces, PATCH applies a partial change, and DELETE removes.

HTTP status codes form part of the API contract. Successful creation commonly
returns 201, validation failures return 422 or 400, missing resources return
404, authentication failures return 401, and authorization failures return
403. Error responses should have one stable shape that clients can parse.

Stateless requests, idempotency where appropriate, pagination, request
validation, explicit timeouts, and documented compatibility policies make an
API easier to operate. JSON over HTTP alone is not REST; the design also
depends on resource representations, protocol semantics, caching constraints,
and predictable links between resources.
""".strip(),
    ),
    (
        "API Reliability Checklist",
        """
Validate all external input at the API boundary and never rely on frontend
validation alone. Return actionable errors without exposing stack traces,
credentials, database details, or internal implementation information.

Attach a request identifier to logs and responses so failures can be traced
across services. Measure request latency, dependency latency, error rate, and
rate-limit events. Use health checks for process availability and readiness
checks for dependencies required to serve traffic.

Set explicit connection and request timeouts. Retry only transient failures,
use exponential backoff with jitter, and avoid retrying unsafe operations
without an idempotency strategy. Apply authentication, ownership filtering,
and rate limits on the backend.
""".strip(),
    ),
    (
        "API Versioning and Compatibility",
        """
Prefer additive and backward-compatible API evolution. Adding an optional
response field is usually safer than renaming or removing an existing field.
Consumers should ignore fields they do not understand.

Introduce a new version when a breaking change cannot be avoided. Publish a
migration guide, provide a deprecation period, monitor usage of the old
contract, and remove it only after clients have had a realistic migration
window.

Contract tests and representative client tests catch accidental breaking
changes. Database migrations should be compatible with both the old and new
application versions during a rolling deployment.
""".strip(),
    ),
)


def main() -> None:
    settings = get_settings()

    with SessionLocal() as database_session:
        workspace = (
            database_session.query(Workspace)
            .filter(Workspace.owner_id == settings.demo_owner_id)
            .order_by(Workspace.id)
            .first()
        )

        if workspace is None:
            workspace = Workspace(
                owner_id=settings.demo_owner_id,
                name="REST API Engineering",
                description=(
                    "A public, read-only research workspace demonstrating "
                    "semantic retrieval and source-grounded answers."
                ),
            )
            database_session.add(workspace)
            database_session.commit()
            database_session.refresh(workspace)

        existing_titles = {
            title
            for (title,) in (
                database_session.query(Source.title)
                .filter(Source.workspace_id == workspace.id)
                .all()
            )
        }

        for title, raw_text in DEMO_SOURCES:
            if title in existing_titles:
                continue

            ingest_source_text(
                database_session=database_session,
                workspace_id=workspace.id,
                title=title,
                raw_text=raw_text,
                source_type="demo_text",
            )

        print(f"Demo workspace ready: id={workspace.id}")


if __name__ == "__main__":
    main()
