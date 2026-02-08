-- Migration: Add unified attachments column and migrate data
-- This script adds the new 'attachments' column and migrates existing data

-- Add attachments column to email_templates
ALTER TABLE email_templates 
ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]'::jsonb;

-- Add attachments column to marketing_email_templates
ALTER TABLE marketing_email_templates 
ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]'::jsonb;

-- Note: Data migration should be done via Python script (migrate_to_unified_attachments.py)
-- to properly convert the separate fields into the unified format

-- After migration, you can drop the old columns:
-- ALTER TABLE email_templates DROP COLUMN IF EXISTS template_files;
-- ALTER TABLE email_templates DROP COLUMN IF EXISTS template_images;
-- ALTER TABLE email_templates DROP COLUMN IF EXISTS template_videos;
-- ALTER TABLE marketing_email_templates DROP COLUMN IF EXISTS template_files;
-- ALTER TABLE marketing_email_templates DROP COLUMN IF EXISTS template_images;
-- ALTER TABLE marketing_email_templates DROP COLUMN IF EXISTS template_videos;
