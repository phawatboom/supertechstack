CREATE TABLE IF NOT EXISTS answer_traces (
    id VARCHAR(36) PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id),
    report_id INTEGER REFERENCES reports(id),
    query TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'started',
    capture_content BOOLEAN NOT NULL DEFAULT TRUE,
    retrieved_chunks JSON,
    model_input JSON,
    model_output JSON,
    model_used VARCHAR(100),
    openai_response_id VARCHAR(255),
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    retrieval_ms INTEGER,
    generation_ms INTEGER,
    total_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITHOUT TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_answer_traces_workspace_id
ON answer_traces (workspace_id);

CREATE INDEX IF NOT EXISTS ix_answer_traces_created_at
ON answer_traces (created_at DESC);
