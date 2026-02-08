-- Migration to remove status_override column from orders table
-- This column is no longer needed - we just update the status column directly

-- Remove the column if it exists
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'orders' 
        AND column_name = 'status_override'
    ) THEN
        ALTER TABLE orders DROP COLUMN status_override;
        RAISE NOTICE 'Column status_override removed from orders table';
    ELSE
        RAISE NOTICE 'Column status_override does not exist in orders table';
    END IF;
END $$;
