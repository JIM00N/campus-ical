// 단일 Edge Function이 학교 목록 / 학교 상세 / iCal 피드 / healthz를 라우팅.
// PostgREST(supabase-js) + service_role key로 RLS 우회.
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

import { filterByCategories, parseCategoryParam, categoryLabels } from "./lib/categories.ts";
import { buildCalendar } from "./lib/ical.ts";
import { renderIndex, renderSchool, type SchoolRow } from "./lib/html.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const ADSENSE_CLIENT_ID = Deno.env.get("ADSENSE_CLIENT_ID") ?? "";
const ADSENSE_SLOT_ID = Deno.env.get("ADSENSE_SLOT_ID") ?? "";

const sb = createClient(SUPABASE_URL, SERVICE_KEY);

const ADS = {
  enabled: !!(ADSENSE_CLIENT_ID && ADSENSE_SLOT_ID),
  clientId: ADSENSE_CLIENT_ID,
  slotId: ADSENSE_SLOT_ID,
};

const SCHOOL_COLS = "id, slug, name, name_en, logo_path, website, timezone";

// BOM(0xEF 0xBB 0xBF)을 body 첫 byte로 박아야 macOS Safari/Chrome이 응답을
// 한국어 encoding으로 자동 추론하지 않음 (Content-Type charset=utf-8만으로는 부족).
const BOM = "﻿";
const htmlResp = (body: string, status = 200) =>
  new Response(BOM + body, {
    status,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "X-Content-Type-Options": "nosniff",
    },
  });
const jsonResp = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
const notFound = (msg = "Not Found") => htmlResp(`<h1>${msg}</h1>`, 404);

Deno.serve(async (req) => {
  const url = new URL(req.url);

  // /functions/v1/web 또는 /web prefix stripping.
  let path = url.pathname;
  let basePath = "";
  for (const prefix of ["/functions/v1/web", "/web"]) {
    if (path === prefix) { basePath = prefix; path = "/"; break; }
    if (path.startsWith(prefix + "/")) { basePath = prefix; path = path.slice(prefix.length); break; }
  }

  try {
    if (path === "/healthz") return jsonResp({ ok: true });

    // /
    if (path === "/" || path === "") {
      const { data, error } = await sb
        .from("schools").select(SCHOOL_COLS).order("name");
      if (error) throw error;
      return htmlResp(renderIndex((data ?? []) as SchoolRow[], ADS, basePath));
    }

    // /s/{slug}
    const schoolMatch = path.match(/^\/s\/([a-z0-9-]+)\/?$/);
    if (schoolMatch) {
      const { data, error } = await sb
        .from("schools").select(SCHOOL_COLS).eq("slug", schoolMatch[1]).maybeSingle();
      if (error) throw error;
      if (!data) return notFound("학교를 찾을 수 없습니다");
      const icalUrl = `${url.origin}${basePath}/calendar/${data.slug}.ics`;
      const webcalUrl = icalUrl.replace(/^https?/, "webcal");
      return htmlResp(renderSchool(data as SchoolRow, icalUrl, webcalUrl, ADS));
    }

    // /calendar/{slug}.ics
    const icalMatch = path.match(/^\/calendar\/([a-z0-9-]+)\.ics$/);
    if (icalMatch) {
      const { data: school, error: e1 } = await sb
        .from("schools").select("id, slug, name, timezone")
        .eq("slug", icalMatch[1]).maybeSingle();
      if (e1) throw e1;
      if (!school) return notFound("학교를 찾을 수 없습니다");

      const { data: rows, error: e2 } = await sb
        .from("events").select("summary, dtstart, dtend")
        .eq("school_id", school.id).order("dtstart");
      if (e2) throw e2;

      const wanted = parseCategoryParam(url.searchParams.get("categories"));
      const filtered = filterByCategories((rows ?? []) as Array<{ summary: string; dtstart: string; dtend: string }>, wanted);
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

    return notFound();
  } catch (err) {
    console.error("Unhandled error:", err);
    return jsonResp({ error: String(err) }, 500);
  }
});
