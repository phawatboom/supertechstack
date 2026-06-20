ALTER TABLE sources
ADD COLUMN IF NOT EXISTS original_filename VARCHAR(255);

ALTER TABLE sources
ADD COLUMN IF NOT EXISTS mime_type VARCHAR(100);

ALTER TABLE sources
ADD COLUMN IF NOT EXISTS file_size INTEGER;

ALTER TABLE sources
ADD COLUMN IF NOT EXISTS extraction_status VARCHAR(30)
NOT NULL DEFAULT 'completed';

ALTER TABLE sources
ALTER COLUMN source_type SET DEFAULT 'pasted_text';

UPDATE sources
SET source_type = 'pasted_text'
WHERE source_type IS NULL;

ALTER TABLE sources
ALTER COLUMN source_type SET NOT NULL;
