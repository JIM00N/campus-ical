-- Track per-school cumulative "URL 복사" count for the public 누적 복사 stat.
-- The Edge Function POST /copy/{slug} handler calls increment_school_copy(school_id)
-- when a visitor clicks the "URL 복사" button on a school page. /stats sums these.
--
-- Unlike fetch_count (origin .ics fetches, edge-cached), this counts explicit user
-- copy actions in the browser, so it tracks real interest more directly.

ALTER TABLE schools
  ADD COLUMN IF NOT EXISTS copy_count BIGINT NOT NULL DEFAULT 0;

-- Atomic increment. SECURITY DEFINER so it runs with the table owner's rights
-- regardless of which role (service_role / anon) calls it.
CREATE OR REPLACE FUNCTION increment_school_copy(s_id INT)
RETURNS void
LANGUAGE sql
SECURITY DEFINER
AS $$
  UPDATE schools SET copy_count = copy_count + 1 WHERE id = s_id;
$$;

GRANT EXECUTE ON FUNCTION increment_school_copy(INT) TO anon, authenticated, service_role;
