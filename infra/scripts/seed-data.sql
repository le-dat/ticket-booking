-- ==============================================================================
-- Seed Data Script for Milestone 6: High-Concurrency Benchmark & Smoke Test
-- Target Database: event_db
-- ==============================================================================

BEGIN;

-- 1. Seed Venue
INSERT INTO venues (id, name, address, capacity, created_at, updated_at)
VALUES (
    'c1b07384-d113-4ec6-a56f-958087920701',
    'National Convention Center',
    'Pham Hung Blvd, Me Tri, Nam Tu Liem, Hanoi',
    5000,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE 
SET name = EXCLUDED.name, address = EXCLUDED.address, updated_at = NOW();

-- 2. Seed Event
INSERT INTO events (id, venue_id, title, description, banner_url, status, created_at, updated_at)
VALUES (
    'c2b07384-d113-4ec6-a56f-958087920702',
    'c1b07384-d113-4ec6-a56f-958087920701',
    'High-Concurrency Tech Concert 2026',
    'Đại nhạc hội công nghệ quy mô lớn thử nghiệm tải hàng ngàn người giữ ghế đồng thời.',
    'https://images.unsplash.com/photo-1501386761578-eac5c94b800a',
    'PUBLISHED',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE 
SET title = EXCLUDED.title, status = EXCLUDED.status, updated_at = NOW();

-- 3. Seed Show (d3b07384-d113-4ec6-a56f-958087920782)
INSERT INTO shows (id, event_id, start_time, end_time, status, created_at, updated_at)
VALUES (
    'd3b07384-d113-4ec6-a56f-958087920782',
    'c2b07384-d113-4ec6-a56f-958087920702',
    NOW() + INTERVAL '7 days',
    NOW() + INTERVAL '7 days 3 hours',
    'OPEN_FOR_BOOKING',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE 
SET status = EXCLUDED.status, updated_at = NOW();

-- 4. Seed Target VIP Seat (e7b07384-d113-4ec6-a56f-958087920799)
INSERT INTO seats (id, show_id, seat_number, row_name, col_index, price, status, held_by_user_id, hold_expires_at, version, created_at, updated_at)
VALUES (
    'e7b07384-d113-4ec6-a56f-958087920799',
    'd3b07384-d113-4ec6-a56f-958087920782',
    'A01',
    'A',
    1,
    150000.00,
    'AVAILABLE',
    NULL,
    NULL,
    1,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO UPDATE 
SET status = 'AVAILABLE',
    held_by_user_id = NULL,
    hold_expires_at = NULL,
    version = 1,
    updated_at = NOW();

-- 5. Seed Remaining 49 Seats (Rows A..E, Columns 1..10)
DO $$
DECLARE
    row_chars text[] := ARRAY['A', 'B', 'C', 'D', 'E'];
    r_char text;
    col_idx int;
    seat_num text;
    s_price numeric(12, 2);
    seat_uuid uuid;
BEGIN
    FOREACH r_char IN ARRAY row_chars LOOP
        FOR col_idx IN 1..10 LOOP
            -- Skip the VIP A01 seat which was seeded explicitly above
            IF r_char = 'A' AND col_idx = 1 THEN
                CONTINUE;
            END IF;

            seat_num := r_char || LPAD(col_idx::text, 2, '0');

            -- Pricing tiers by row
            CASE r_char
                WHEN 'A' THEN s_price := 150000.00;
                WHEN 'B' THEN s_price := 120000.00;
                WHEN 'C' THEN s_price := 100000.00;
                WHEN 'D' THEN s_price := 80000.00;
                ELSE s_price := 50000.00;
            END CASE;

            -- Predictable UUID derivation based on row and col for idempotency
            seat_uuid := ('e7b07384-d113-4ec6-a56f-' || LPAD(to_hex((ascii(r_char) * 100 + col_idx)::int), 12, '0'))::uuid;

            INSERT INTO seats (id, show_id, seat_number, row_name, col_index, price, status, held_by_user_id, hold_expires_at, version, created_at, updated_at)
            VALUES (
                seat_uuid,
                'd3b07384-d113-4ec6-a56f-958087920782',
                seat_num,
                r_char,
                col_idx,
                s_price,
                'AVAILABLE',
                NULL,
                NULL,
                1,
                NOW(),
                NOW()
            )
            ON CONFLICT (id) DO UPDATE 
            SET status = 'AVAILABLE',
                held_by_user_id = NULL,
                hold_expires_at = NULL,
                version = 1,
                updated_at = NOW();
        END LOOP;
    END LOOP;
END $$;

COMMIT;
