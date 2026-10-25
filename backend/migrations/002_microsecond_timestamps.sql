-- Preserve sub-second order for rapid successive artifact/annotation versions.
-- Back up existing records before applying to a previously created database.
-- Existing second-resolution timestamps retain their values with .000000.
ALTER TABLE seals MODIFY COLUMN created_at DATETIME(6) NOT NULL;
ALTER TABLE artifacts MODIFY COLUMN created_at DATETIME(6) NOT NULL;
ALTER TABLE events MODIFY COLUMN created_at DATETIME(6) NOT NULL;
