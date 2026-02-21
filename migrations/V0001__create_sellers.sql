CREATE TABLE IF NOT EXISTS sellers (
    id SERIAL PRIMARY KEY,
    is_verified_seller BOOLEAN NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sellers_id ON sellers (id);
