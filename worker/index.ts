// campus-cal.com Worker entry.
//
// 라우팅:
// - /calendar/{slug}.ics → Supabase Edge Function으로 proxy.
//   학생에게 supabase.co 도메인을 노출하지 않으려고 가운데 한 단계 끼움.
//   Cloudflare CDN이 응답을 캐시하므로 매번 Supabase까지 가지 않는다.
// - 그 외 path → docs/ 정적 자산 (학교 목록 / 학교 페이지 / CSS / JS).

const SUPABASE_FUNCTION_URL = "https://rhjovcmtvzhqublrqxic.supabase.co/functions/v1/web";

export interface Env {
  ASSETS: Fetcher;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname.startsWith("/calendar/")) {
      const upstream = `${SUPABASE_FUNCTION_URL}${url.pathname}${url.search}`;
      const upstreamResp = await fetch(upstream, {
        method: request.method,
        headers: request.headers,
      });
      return new Response(upstreamResp.body, {
        status: upstreamResp.status,
        statusText: upstreamResp.statusText,
        headers: upstreamResp.headers,
      });
    }

    return env.ASSETS.fetch(request);
  },
};
