// iCal feed endpoint + 사이트 통계.
// 정적 페이지(학교 목록 / 학교 상세)는 Cloudflare Pages로 이전됐고,
// 이 함수는 (1) 캘린더 앱이 fetch하는 .ics 파일과 (2) 프론트가 호출하는 /stats만 담당한다.
// 캘린더 앱은 Supabase HTML quirk 영향 없음 — text/calendar 응답이라 별 문제 없음.
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

import { filterByCategories, parseCategoryParam, categoryLabels } from "./lib/categories.ts";
import { buildCalendar, toEndpointEvents } from "./lib/ical.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const sb = createClient(SUPABASE_URL, SERVICE_KEY);

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};

const jsonResp = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...CORS_HEADERS },
  });

Deno.serve(async (req) => {
  const url = new URL(req.url);

  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  }

  // /functions/v1/web 또는 /web prefix stripping.
  let path = url.pathname;
  for (const prefix of ["/functions/v1/web", "/web"]) {
    if (path === prefix) { path = "/"; break; }
    if (path.startsWith(prefix + "/")) { path = path.slice(prefix.length); break; }
  }

  try {
    if (path === "/healthz") return jsonResp({ ok: true });

    // /stats — 누적 통계: 학교 수 + 전체 URL 복사 횟수
    if (path === "/stats") {
      const { count: schoolsCount, error: e1 } = await sb
        .from("schools").select("id", { count: "exact", head: true });
      if (e1) throw e1;

      const { data: rows, error: e2 } = await sb
        .from("schools").select("copy_count");
      if (e2) throw e2;

      const copies = (rows ?? []).reduce(
        (acc: number, r: { copy_count: number | null }) =>
          acc + Number(r.copy_count ?? 0),
        0,
      );
      return jsonResp({ schools: schoolsCount ?? 0, copies });
    }

    // POST /copy/{slug} — URL 복사 버튼 클릭 1회 기록 (학교별 copy_count++).
    const copyMatch = path.match(/^\/copy\/([a-z0-9-]+)$/);
    if (copyMatch) {
      if (req.method !== "POST") {
        return jsonResp({ error: "method not allowed" }, 405);
      }
      const { data: school, error: e1 } = await sb
        .from("schools").select("id").eq("slug", copyMatch[1]).maybeSingle();
      if (e1) throw e1;
      if (!school) return jsonResp({ error: "school not found" }, 404);

      const { error: e2 } = await sb.rpc("increment_school_copy", {
        s_id: school.id,
      });
      if (e2) throw e2;
      return jsonResp({ ok: true });
    }

    // /calendar/{slug}.ics
    const icalMatch = path.match(/^\/calendar\/([a-z0-9-]+)\.ics$/);
    if (icalMatch) {
      const { data: school, error: e1 } = await sb
        .from("schools").select("id, slug, name, timezone")
        .eq("slug", icalMatch[1]).maybeSingle();
      if (e1) throw e1;
      if (!school) return jsonResp({ error: "school not found" }, 404);

      const { data: rows, error: e2 } = await sb
        .from("events").select("summary, dtstart, dtend")
        .eq("school_id", school.id).order("dtstart");
      if (e2) throw e2;

      const wanted = parseCategoryParam(url.searchParams.get("categories"));
      const filtered = filterByCategories(
        (rows ?? []) as Array<{ summary: string; dtstart: string; dtend: string }>,
        wanted,
      );
      const endpointsOnly = ["1", "true", "yes"].includes(
        (url.searchParams.get("endpoints") ?? "").toLowerCase(),
      );
      const events = endpointsOnly ? toEndpointEvents(filtered) : filtered;
      const calName = wanted.size > 0
        ? `${school.name} (${categoryLabels(wanted).join(", ")})`
        : school.name;
      const body = await buildCalendar(school, events, calName);

      // Fire-and-forget: 누적 fetch 카운터 증가 (/stats에서 합산).
      // 응답을 막지 않도록 await 하지 않음. RPC 실패해도 ICS 응답엔 영향 없음.
      sb.rpc("increment_school_fetch", { s_id: school.id })
        .then(({ error }) => {
          if (error) console.warn("increment_school_fetch failed:", error.message);
        });

      return new Response(body, {
        status: 200,
        headers: {
          "Content-Type": "text/calendar; charset=utf-8",
          "Content-Disposition": `inline; filename="${school.slug}.ics"`,
          "Cache-Control": "public, max-age=3600",
        },
      });
    }

    return jsonResp({ error: "not found" }, 404);
  } catch (err) {
    console.error("Unhandled error:", err);
    return jsonResp({ error: String(err) }, 500);
  }
});
