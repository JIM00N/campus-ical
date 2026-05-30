-- Track per-school cumulative ICS fetch count for the public "누적 동기화" stat.
-- The Edge Function /calendar/{slug}.ics handler calls increment_school_fetch(school_id)
-- after a successful response. /stats sums these.
--
-- Note: ICS responses are cached at the edge (Cloudflare CDN + Cache-Control: max-age=3600),
-- so this counter reflects origin fetches (cache misses), not every device poll.
-- Treat it as a "popularity" floor, not exact subscriber count.

ALTER TABLE schools
  ADD COLUMN IF NOT EXISTS fetch_count BIGINT NOT NULL DEFAULT 0;

-- Atomic increment. SECURITY DEFINER so it runs with the table owner's rights
-- regardless of which role (service_role / anon) calls it.
CREATE OR REPLACE FUNCTION increment_school_fetch(s_id INT)
RETURNS void
LANGUAGE sql
SECURITY DEFINER
AS $$
  UPDATE schools SET fetch_count = fetch_count + 1 WHERE id = s_id;
$$;

GRANT EXECUTE ON FUNCTION increment_school_fetch(INT) TO anon, authenticated, service_role;
