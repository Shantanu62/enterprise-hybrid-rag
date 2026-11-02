
-- Migration: 001_add_password_hash
-- Purpose: Add secure password hash storage for custom authentication.

BEGIN;

ALTER TABLE users
ADD COLUMN IF NOT EXISTS password_hash TEXT;

COMMENT ON COLUMN users.password_hash IS
'Argon2 password hash. Never store plaintext passwords.';

COMMIT;
