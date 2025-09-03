-- Telegram Subscription Bot Database Schema
-- Purpose: Manage monthly subscriptions for Telegram group access ($10 USD or 500 Stars)
-- 
-- Design Decisions:
-- 1. Using UUID for primary keys for better security and distributed systems compatibility
-- 2. telegram_id as bigint to handle Telegram's large user IDs
-- 3. Simple status tracking with check constraints for data integrity
-- 4. JSONB for activity log details to allow flexible logging without schema changes
-- 5. Indexes on frequently queried columns for performance
-- 6. RLS policies for security - users can only access their own data

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing objects if they exist (for clean migrations)
DROP TABLE IF EXISTS activity_log CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;

-- ============================================
-- 1. USERS TABLE
-- ============================================
-- Core user table for subscription management
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    subscription_status TEXT NOT NULL DEFAULT 'expired' 
        CHECK (subscription_status IN ('active', 'expired', 'whitelisted')),
    payment_method TEXT 
        CHECK (payment_method IN ('card', 'stars', 'whitelisted')),
    next_payment_date DATE,
    airwallex_payment_id TEXT,
    stars_transaction_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add comments for documentation
COMMENT ON TABLE users IS 'Core user table for managing Telegram bot subscriptions';
COMMENT ON COLUMN users.telegram_id IS 'Unique Telegram user ID';
COMMENT ON COLUMN users.subscription_status IS 'Current subscription status: active, expired, or whitelisted';
COMMENT ON COLUMN users.payment_method IS 'Payment method used: card (Airwallex), stars (Telegram), or whitelisted';
COMMENT ON COLUMN users.next_payment_date IS 'Date when the next payment is due (NULL for whitelisted users)';
COMMENT ON COLUMN users.airwallex_payment_id IS 'Payment ID from Airwallex for card payments';
COMMENT ON COLUMN users.stars_transaction_id IS 'Transaction ID from Telegram Stars payments';

-- ============================================
-- 2. ACTIVITY LOG TABLE
-- ============================================
-- Log all user actions for audit and analytics
CREATE TABLE activity_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT NOT NULL,
    action TEXT NOT NULL CHECK (action IN (
        'subscription_started',
        'subscription_renewed',
        'subscription_expired',
        'subscription_cancelled',
        'payment_successful',
        'payment_failed',
        'user_joined_group',
        'user_removed_from_group',
        'user_whitelisted',
        'user_created',
        'user_updated'
    )),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    details JSONB,
    
    -- Add foreign key reference to users table
    CONSTRAINT fk_activity_user 
        FOREIGN KEY (telegram_id) 
        REFERENCES users(telegram_id) 
        ON DELETE CASCADE
);

-- Add comments for documentation
COMMENT ON TABLE activity_log IS 'Audit log of all user actions and subscription events';
COMMENT ON COLUMN activity_log.action IS 'Type of action performed';
COMMENT ON COLUMN activity_log.details IS 'Additional context about the action in JSON format';

-- ============================================
-- 3. INDEXES FOR PERFORMANCE
-- ============================================
-- Following Supabase best practices: index columns used in RLS policies and frequent queries

-- Index for quick user lookups by telegram_id (already unique, but explicit for documentation)
CREATE INDEX idx_users_telegram_id ON users USING btree (telegram_id);

-- Index for filtering by subscription status (e.g., finding all active users)
CREATE INDEX idx_users_subscription_status ON users USING btree (subscription_status);

-- Index for scheduled tasks checking payment dates
CREATE INDEX idx_users_next_payment_date ON users USING btree (next_payment_date) 
    WHERE next_payment_date IS NOT NULL;

-- Composite index for status + date queries (e.g., active subscriptions expiring soon)
CREATE INDEX idx_users_status_payment_date ON users USING btree (subscription_status, next_payment_date) 
    WHERE subscription_status = 'active';

-- Index for activity log queries by telegram_id
CREATE INDEX idx_activity_log_telegram_id ON activity_log USING btree (telegram_id);

-- Index for activity log queries by action type
CREATE INDEX idx_activity_log_action ON activity_log USING btree (action);

-- Index for time-based activity queries
CREATE INDEX idx_activity_log_timestamp ON activity_log USING btree (timestamp DESC);

-- ============================================
-- 4. ROW LEVEL SECURITY (RLS)
-- ============================================
-- Enable RLS on both tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;

-- Users table policies
-- Note: We're not using auth.uid() since this is a Telegram bot, not a web app
-- The bot will use service role key for full access
-- These policies are for potential future web dashboard or user API access

-- Policy: Users can view their own data (for future user-facing features)
-- Using wrapped SELECT for performance optimization as per Supabase best practices
CREATE POLICY "users_select_own" ON users
    FOR SELECT
    TO authenticated
    USING (
        telegram_id = COALESCE(
            (SELECT (current_setting('request.jwt.claims', true)::json->>'telegram_id')::BIGINT),
            -1  -- Impossible telegram_id to prevent null matches
        )
    );

-- Policy: Service role has full access (for bot operations)
CREATE POLICY "service_role_users_all" ON users
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Activity log policies
-- Users can view their own activity logs
CREATE POLICY "activity_log_select_own" ON activity_log
    FOR SELECT
    TO authenticated
    USING (
        telegram_id = COALESCE(
            (SELECT (current_setting('request.jwt.claims', true)::json->>'telegram_id')::BIGINT),
            -1
        )
    );

-- Service role has full access to activity logs
CREATE POLICY "service_role_activity_all" ON activity_log
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Public read-only policy for anonymous health checks (optional)
-- Uncomment if you want to allow anonymous status checks
-- CREATE POLICY "anon_can_check_health" ON users
--     FOR SELECT
--     TO anon
--     USING (false);  -- Effectively denies all access, but allows table structure queries

-- ============================================
-- 5. TRIGGERS AND FUNCTIONS
-- ============================================

-- Function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at column on users table
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to log user status changes automatically
CREATE OR REPLACE FUNCTION log_subscription_status_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Only log if subscription_status actually changed
    IF OLD.subscription_status IS DISTINCT FROM NEW.subscription_status THEN
        INSERT INTO activity_log (telegram_id, action, details)
        VALUES (
            NEW.telegram_id,
            CASE 
                WHEN NEW.subscription_status = 'active' AND OLD.subscription_status = 'expired' 
                    THEN 'subscription_started'
                WHEN NEW.subscription_status = 'active' AND OLD.subscription_status = 'active' 
                    THEN 'subscription_renewed'
                WHEN NEW.subscription_status = 'expired' 
                    THEN 'subscription_expired'
                WHEN NEW.subscription_status = 'whitelisted' 
                    THEN 'user_whitelisted'
                ELSE 'user_updated'
            END,
            jsonb_build_object(
                'old_status', OLD.subscription_status,
                'new_status', NEW.subscription_status,
                'payment_method', NEW.payment_method,
                'next_payment_date', NEW.next_payment_date
            )
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to log subscription status changes
CREATE TRIGGER log_user_subscription_changes
    AFTER UPDATE ON users
    FOR EACH ROW
    WHEN (OLD.subscription_status IS DISTINCT FROM NEW.subscription_status)
    EXECUTE FUNCTION log_subscription_status_change();

-- Function to log new user creation
CREATE OR REPLACE FUNCTION log_user_creation()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO activity_log (telegram_id, action, details)
    VALUES (
        NEW.telegram_id,
        'user_created',
        jsonb_build_object(
            'username', NEW.username,
            'subscription_status', NEW.subscription_status,
            'payment_method', NEW.payment_method
        )
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to log new user creation
CREATE TRIGGER log_new_user
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION log_user_creation();

-- ============================================
-- 6. HELPER FUNCTIONS FOR COMMON OPERATIONS
-- ============================================

-- Function to check if a subscription is expired
CREATE OR REPLACE FUNCTION is_subscription_expired(check_date DATE)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN check_date < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to extend subscription by one month
CREATE OR REPLACE FUNCTION extend_subscription(
    p_telegram_id BIGINT,
    p_payment_method TEXT,
    p_transaction_id TEXT DEFAULT NULL
)
RETURNS TABLE (
    success BOOLEAN,
    new_expiry_date DATE,
    message TEXT
) AS $$
DECLARE
    v_user_record RECORD;
    v_new_date DATE;
BEGIN
    -- Get current user data
    SELECT * INTO v_user_record 
    FROM users 
    WHERE telegram_id = p_telegram_id
    FOR UPDATE;  -- Lock the row to prevent concurrent updates
    
    IF NOT FOUND THEN
        RETURN QUERY SELECT 
            FALSE, 
            NULL::DATE, 
            'User not found'::TEXT;
        RETURN;
    END IF;
    
    -- Calculate new expiry date
    IF v_user_record.next_payment_date IS NULL OR v_user_record.next_payment_date < CURRENT_DATE THEN
        -- If no date or expired, start from today
        v_new_date := CURRENT_DATE + INTERVAL '1 month';
    ELSE
        -- If still active, extend from current expiry
        v_new_date := v_user_record.next_payment_date + INTERVAL '1 month';
    END IF;
    
    -- Update user record
    UPDATE users SET
        subscription_status = 'active',
        payment_method = p_payment_method,
        next_payment_date = v_new_date,
        airwallex_payment_id = CASE 
            WHEN p_payment_method = 'card' THEN p_transaction_id 
            ELSE airwallex_payment_id 
        END,
        stars_transaction_id = CASE 
            WHEN p_payment_method = 'stars' THEN p_transaction_id 
            ELSE stars_transaction_id 
        END
    WHERE telegram_id = p_telegram_id;
    
    -- Log the payment
    INSERT INTO activity_log (telegram_id, action, details)
    VALUES (
        p_telegram_id,
        'payment_successful',
        jsonb_build_object(
            'payment_method', p_payment_method,
            'transaction_id', p_transaction_id,
            'new_expiry_date', v_new_date
        )
    );
    
    RETURN QUERY SELECT 
        TRUE, 
        v_new_date, 
        'Subscription extended successfully'::TEXT;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to expire subscriptions (for scheduled jobs)
CREATE OR REPLACE FUNCTION expire_overdue_subscriptions()
RETURNS TABLE (
    expired_count INTEGER,
    expired_users BIGINT[]
) AS $$
DECLARE
    v_expired_users BIGINT[];
BEGIN
    -- Update all overdue subscriptions
    UPDATE users 
    SET subscription_status = 'expired'
    WHERE subscription_status = 'active'
        AND next_payment_date < CURRENT_DATE
        AND payment_method != 'whitelisted'
    RETURNING telegram_id INTO v_expired_users;
    
    -- Return results
    RETURN QUERY SELECT 
        array_length(v_expired_users, 1)::INTEGER,
        v_expired_users;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- 7. INITIAL DATA AND PERMISSIONS
-- ============================================

-- Grant necessary permissions to authenticated users
GRANT SELECT ON users TO authenticated;
GRANT SELECT ON activity_log TO authenticated;

-- Grant full permissions to service role (bot backend)
GRANT ALL ON users TO service_role;
GRANT ALL ON activity_log TO service_role;

-- ============================================
-- 8. VALIDATION CONSTRAINTS
-- ============================================

-- Ensure whitelisted users don't have payment dates
ALTER TABLE users ADD CONSTRAINT check_whitelisted_no_payment_date
    CHECK (
        (subscription_status = 'whitelisted' AND next_payment_date IS NULL)
        OR subscription_status != 'whitelisted'
    );

-- Ensure active subscriptions have payment method
ALTER TABLE users ADD CONSTRAINT check_active_has_payment_method
    CHECK (
        subscription_status != 'active' 
        OR payment_method IS NOT NULL
    );

-- ============================================
-- Migration completed successfully!
-- 
-- To apply this schema:
-- 1. Run this SQL in Supabase SQL Editor
-- 2. Verify tables and policies in Table Editor
-- 3. Test RLS policies with different roles
-- 
-- Key features implemented:
-- ✓ Simple, efficient schema for subscription management
-- ✓ Automatic timestamp updates
-- ✓ Activity logging with triggers
-- ✓ Row Level Security for data protection
-- ✓ Performance indexes on critical columns
-- ✓ Helper functions for common operations
-- ✓ Data integrity constraints
-- ============================================