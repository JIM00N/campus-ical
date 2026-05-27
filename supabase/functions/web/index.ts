// iCal feed endpoint. 정적 페이지(학교 목록 / 학교 상세)는 Cloudflare Pages로
// 이전됐고, 이 함수는 캘린더 앱이 fetch하는 .ics 파일만 담당한다.
// (캘린더 앱은 Supabase HTML quirk 영향 없음 — text/calendar 응답이라 별 문제 없음)
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

import { filterByCategories, parseCategoryParam, categoryLabels } from "./lib/categories.ts";
import { buildCalendar } from "./lib/ical.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const sb = createClient(SUPABASE_URL, SERVICE_KEY);

const jsonResp = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });

Deno.serve(async (req) => {
  const url = new URL(req.url);

  // /functions/v1/web 또는 /web prefix stripping.
  let path = url.pathname;
  for (const prefix of ["/functions/v1/web", "/web"]) {
    if (path === prefix) { path = "/"; break; }
    if (path.startsWith(prefix + "/")) { path = path.slice(prefix.length); break; }
  }

  try {
    if (path === "/healthz") return jsonResp({ ok: true });

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
      const calName = wanted.size > 0
        ? `${school.name} (${categoryLabels(wanted).join(", ")})`
        : school.name;
      const body = await buildCalendar(school, filtered, calName);

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
