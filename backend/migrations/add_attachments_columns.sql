-- Migration: Add unified attachments column to email_templates and marketing_email_templates
-- Run this script to add the attachments column to both tables

-- Add attachments column to email_templates
ALTER TABLE email_templates 
ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]'::jsonb;

-- Add attachments column to marketing_email_templates
ALTER TABLE marketing_email_templates 
ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]'::jsonb;

-- Verify columns were added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name IN ('email_templates', 'marketing_email_templates') 
AND column_name = 'attachments';
