-- Add 'ton' to currencytype enum if not exists
-- This fixes the error: invalid input value for enum currencytype: "TON"

DO $$
BEGIN
    -- Check if 'ton' already exists in the enum
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum e
        JOIN pg_type t ON e.enumtypid = t.oid
        WHERE t.typname = 'currencytype' AND e.enumlabel = 'ton'
    ) THEN
        -- Add 'ton' to the enum
        ALTER TYPE currencytype ADD VALUE 'ton';
        RAISE NOTICE 'Added ''ton'' to currencytype enum';
    ELSE
        RAISE NOTICE '''ton'' already exists in currencytype enum';
    END IF;
END $$;
