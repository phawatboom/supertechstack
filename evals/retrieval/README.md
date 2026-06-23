# Retrieval evaluation

This starter evaluation checks whether an expected source appears in the top
retrieval results and reports recall at K and mean reciprocal rank.

Use a workspace containing the matching evaluation sources, then run:

```powershell
$env:EVAL_API_URL="https://supertechstack-production.up.railway.app"
$env:EVAL_ACCESS_TOKEN="<Supabase access token or beta token>"
$env:EVAL_WORKSPACE_ID="2"
python evals/retrieval/run.py
```

Edit `dataset.json` so each question has manually reviewed expected source
titles. As the dataset matures, add expected chunk IDs and answer-level
faithfulness and citation checks.
