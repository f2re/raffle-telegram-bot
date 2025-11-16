-- Manual SQL fix for TON enum support
-- Run this with: psql <your_database_url> -f fix_ton_enum.sql

-- Check current enum values
SELECT 'Current currencytype values:' AS message;
SELECT e.enumlabel
FROM pg_enum e
JOIN pg_type t ON e.enumtypid = t.oid
WHERE t.typname = 'currencytype'
ORDER BY e.enumsortorder;

-- Add 'ton' value if it doesn't exist
-- Note: This must be run outside a transaction block
DO $$
BEGIN
    -- Check if 'ton' already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum e
        JOIN pg_type t ON e.enumtypid = t.oid
        WHERE t.typname = 'currencytype' AND e.enumlabel = 'ton'
    ) THEN
        -- Cannot run ALTER TYPE ADD VALUE inside a block, so raise a notice
        RAISE NOTICE 'The ton value needs to be added. Run the ALTER TYPE command below manually:';
        RAISE NOTICE 'ALTER TYPE currencytype ADD VALUE ''ton'';';
    ELSE
        RAISE NOTICE 'The ton value already exists!';
    END IF;
END $$;

-- If the above shows you need to add 'ton', uncomment and run this line:
-- ALTER TYPE currencytype ADD VALUE 'ton';

-- Verify the fix
SELECT 'Updated currencytype values:' AS message;
SELECT e.enumlabel
FROM pg_enum e
JOIN pg_type t ON e.enumtypid = t.oid
WHERE t.typname = 'currencytype'
ORDER BY e.enumsortorder;
