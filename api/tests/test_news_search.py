from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.news import NewsSearchResult, canonicalize_news_url
from app.services.news_search import (
    DisabledNewsSearchProvider,
    RawNewsSearchResult,
    StaticNewsSearchProvider,
    discover_news_results,
    normalize_news_search_results,
)


def test_canonicalize_news_url_removes_tracking_and_fragment():
    canonical_url = canonicalize_news_url(
        "HTTPS://Example.com/article?utm_source=newsletter&b=2&a=1#comments"
    )

    assert canonical_url == "https://example.com/article?a=1&b=2"


def test_normalize_news_search_results_deduplicates_by_canonical_url():
    results = normalize_news_search_results(
        "fixture-provider",
        [
            RawNewsSearchResult(
                title="Original article",
                url="https://example.com/article?utm_source=x",
                snippet="First version",
                publisher="Example",
                published_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
                external_id="one",
            ),
            RawNewsSearchResult(
                title="Duplicate article",
                url="https://example.com/article",
                snippet="Second version",
                publisher="Example",
                external_id="two",
            ),
            RawNewsSearchResult(
                title="Different article",
                url="https://example.com/other",
            ),
        ],
        max_results=10,
    )

    assert len(results) == 2
    assert results[0].title == "Original article"
    assert results[0].canonical_url == "https://example.com/article"
    assert results[0].provider == "fixture-provider"
    assert results[1].canonical_url == "https://example.com/other"


def test_normalize_news_search_results_respects_max_results():
    results = normalize_news_search_results(
        "fixture-provider",
        [
            RawNewsSearchResult(title="One", url="https://example.com/one"),
            RawNewsSearchResult(title="Two", url="https://example.com/two"),
        ],
        max_results=1,
    )

    assert [result.title for result in results] == ["One"]


def test_normalize_news_search_results_rejects_invalid_limit():
    with pytest.raises(ValueError):
        normalize_news_search_results("fixture-provider", [], max_results=0)


def test_news_search_result_rejects_non_http_urls():
    with pytest.raises(ValidationError):
        NewsSearchResult(
            title="Invalid URL",
            url="ftp://example.com/article",
            canonical_url="ftp://example.com/article",
            provider="fixture-provider",
        )


def test_static_provider_returns_normalized_results():
    provider = StaticNewsSearchProvider(
        [
            RawNewsSearchResult(
                title="AI infrastructure update",
                url="https://example.com/ai?utm_campaign=test",
            )
        ]
    )

    results = provider.search("AI infrastructure", max_results=5)

    assert len(results) == 1
    assert results[0].canonical_url == "https://example.com/ai"
    assert results[0].provider == "static"


def test_static_provider_rejects_blank_query():
    provider = StaticNewsSearchProvider([])

    with pytest.raises(ValueError):
        provider.search("   ", max_results=5)


def test_discover_news_results_uses_provider_contract():
    provider = StaticNewsSearchProvider(
        [RawNewsSearchResult(title="One", url="https://example.com/one")]
    )

    results = discover_news_results(
        "  market regulation  ",
        max_results=5,
        provider=provider,
    )

    assert [result.title for result in results] == ["One"]


def test_disabled_provider_fails_explicitly():
    provider = DisabledNewsSearchProvider()

    with pytest.raises(RuntimeError, match="not configured"):
        provider.search("market regulation", max_results=5)
