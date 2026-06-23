import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DATASET_PATH = Path(__file__).with_name("dataset.json")


def search(
    api_url: str,
    access_token: str,
    workspace_id: str,
    question: str,
    limit: int,
) -> list[dict]:
    request = Request(
        f"{api_url.rstrip('/')}/workspaces/{workspace_id}/search",
        data=json.dumps({"query": question, "limit": limit}).encode(),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urlopen(request, timeout=60) as response:
        return json.load(response)


def reciprocal_rank(
    results: list[dict],
    expected_titles: set[str],
) -> float:
    for rank, result in enumerate(results, start=1):
        if result["source_title"] in expected_titles:
            return 1 / rank
    return 0.0


def main() -> int:
    api_url = os.getenv("EVAL_API_URL", "http://localhost:8000")
    access_token = os.getenv("EVAL_ACCESS_TOKEN", "")
    workspace_id = os.getenv("EVAL_WORKSPACE_ID", "")
    limit = int(os.getenv("EVAL_RETRIEVAL_LIMIT", "5"))

    if not access_token or not workspace_id:
        print(
            "Set EVAL_ACCESS_TOKEN and EVAL_WORKSPACE_ID before running.",
            file=sys.stderr,
        )
        return 2

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    hits = 0
    reciprocal_ranks = []

    try:
        for case in dataset:
            results = search(
                api_url,
                access_token,
                workspace_id,
                case["question"],
                limit,
            )
            expected = set(case["expected_source_titles"])
            rank_score = reciprocal_rank(results, expected)
            hit = rank_score > 0
            hits += int(hit)
            reciprocal_ranks.append(rank_score)
            print(
                f"{case['id']}: {'PASS' if hit else 'FAIL'} "
                f"top={results[0]['source_title'] if results else 'none'}"
            )
    except (HTTPError, URLError, TimeoutError) as error:
        print(f"Evaluation request failed: {error}", file=sys.stderr)
        return 1

    total = len(dataset)
    recall_at_k = hits / total if total else 0
    mean_reciprocal_rank = (
        sum(reciprocal_ranks) / total if total else 0
    )

    print(f"\nCases: {total}")
    print(f"Recall@{limit}: {recall_at_k:.1%}")
    print(f"MRR: {mean_reciprocal_rank:.3f}")
    return 0 if hits == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
