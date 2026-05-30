-- Baseline schema.
--
-- schools/events 테이블은 원래 SQLAlchemy(app/models.py → scripts/seed_schools.py의
-- Base.metadata.create_all)가 생성해서, 마이그레이션으로 캡처된 적이 없었다.
-- Supabase Branching은 빈 Preview DB에 supabase/migrations/ 파일만 순서대로 실행하므로,
-- 이 베이스라인이 없으면 이후 ALTER가 "relation schools does not exist"로 실패한다.
--
-- 전부 IF NOT EXISTS라서 운영 DB(테이블 이미 존재)에선 완전한 no-op이다.
-- DROP/DELETE/TRUNCATE/파괴적 ALTER 없음 → 기존 데이터 불변.

CREATE TABLE IF NOT EXISTS schools (
  id          SERIAL PRIMARY KEY,
  slug        VARCHAR(50)  NOT NULL UNIQUE,
  name        VARCHAR(255) NOT NULL,
  name_en     VARCHAR(255),
  logo_path   VARCHAR(500),
  website     VARCHAR(500),
  crawler_key VARCHAR(50)  NOT NULL,
  timezone    VARCHAR(50)  NOT NULL DEFAULT 'Asia/Seoul',
  created_at  TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS events (
  id           SERIAL PRIMARY KEY,
  school_id    INTEGER NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  summary      VARCHAR(500) NOT NULL,
  dtstart      DATE NOT NULL,
  dtend        DATE NOT NULL,
  description  TEXT,
  last_seen_at TIMESTAMP DEFAULT now(),
  CONSTRAINT uq_event_identity UNIQUE (school_id, summary, dtstart, dtend)
);

CREATE INDEX IF NOT EXISTS idx_events_school_dt ON events (school_id, dtstart);
