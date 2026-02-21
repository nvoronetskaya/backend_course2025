CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT NOT NULL,
    images_qty INTEGER NOT NULL,
    category INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_items_id ON items (id);
