-- Migration: Drop product_variants and product_templates tables
-- Run this script to remove the unused tables from the database

-- Drop product_variants table (CASCADE to drop dependent objects like indexes, constraints)
DROP TABLE IF EXISTS product_variants CASCADE;

-- Drop product_templates table (CASCADE to drop dependent objects like indexes, constraints)
DROP TABLE IF EXISTS product_templates CASCADE;

-- Verify tables are dropped
-- SELECT table_name FROM information_schema.tables 
-- WHERE table_schema = 'public' 
-- AND table_name IN ('product_variants', 'product_templates');
