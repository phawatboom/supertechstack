from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.schemas.news import NewsSearchResult, canonicalize_news_url


class NewsSearchProviderError(RuntimeError):
    """Raised when a news provider cannot complete a search."""


class NewsSearchProviderTimeout(NewsSearchProviderError):
    """Raised when a news provider exceeds its timeout budget."""


class NewsSearchProvider(Protocol):
    provider_name: str

    def search(
        self,
        query: str,
        *,
        max_results: int,
    ) -> list[NewsSearchResult]:
        """Return normalized news search results for a query."""


@dataclass(frozen=True)
class RawNewsSearchResult:
    title: str
    url: str
    snippet: str | None = None
    publisher: str | None = None
    published_at: datetime | None = None
    external_id: str | None = None


def normalize_news_search_results(
    provider_name: str,
    raw_results: Iterable[RawNewsSearchResult],
    *,
    max_results: int,
) -> list[NewsSearchResult]:
    if max_results < 1:
        raise ValueError("max_results must be at least 1")

    normalized_results: list[NewsSearchResult] = []
    seen_urls: set[str] = set()

    for raw_result in raw_results:
        canonical_url = canonicalize_news_url(raw_result.url)

        if canonical_url in seen_urls:
            continue

        seen_urls.add(canonical_url)
        normalized_results.append(
            NewsSearchResult(
                title=raw_result.title,
                url=raw_result.url,
                canonical_url=canonical_url,
                snippet=raw_result.snippet,
                publisher=raw_result.publisher,
                published_at=raw_result.published_at,
                provider=provider_name,
                external_id=raw_result.external_id,
            )
        )

        if len(normalized_results) >= max_results:
            break

    return normalized_results


class StaticNewsSearchProvider:
    provider_name = "static"

    def __init__(self, results: Sequence[RawNewsSearchResult]):
        self._results = list(results)

    def search(
        self,
        query: str,
        *,
        max_results: int,
    ) -> list[NewsSearchResult]:
        query = query.strip()

        if not query:
            raise ValueError("query cannot be blank")

        return normalize_news_search_results(
            self.provider_name,
            self._results,
            max_results=max_results,
        )
