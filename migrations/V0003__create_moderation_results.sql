CREATE TABLE IF NOT EXISTS moderation_results (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    status VARCHAR NOT NULL,
    is_violation BOOLEAN,
    probability FLOAT,
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    processed_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_moderation_results_id ON moderation_results (id);
CREATE INDEX IF NOT EXISTS ix_moderation_results_item_id ON moderation_results (item_id);
