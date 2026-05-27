// HTML 페이지 (index + school). Jinja2 templates를 template literal로 옮김.
// 정적 자산(CSS)은 inline. 로고는 jsDelivr CDN(GitHub raw)로 서빙.

import { CATEGORIES } from "./categories.ts";

const CDN_BASE = "https://cdn.jsdelivr.net/gh/JIM00N/campus-ical@main";

export type SchoolRow = {
  slug: string;
  name: string;
  name_en: string | null;
  logo_path: string | null;
  website: string | null;
  timezone: string;
};

export function logoUrl(path: string | null): string | null {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  if (path.startsWith("/")) return `${CDN_BASE}${path}`;
  return path;
}

function escape(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

const STYLE = `
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Pretendard", "Apple SD Gothic Neo", sans-serif;
  background: #f6f7fb; color: #1f2937; line-height: 1.55;
  min-height: 100vh; display: flex; flex-direction: column;
}
.topbar { background: white; border-bottom: 1px solid #e5e7eb; padding: 14px 24px; }
.brand { font-weight: 700; color: #111827; text-decoration: none; font-size: 18px; }
.main { flex: 1; max-width: 720px; margin: 0 auto; padding: 48px 24px; width: 100%; }
.hero h1 { font-size: 30px; margin-bottom: 8px; color: #111827; }
.hero p { color: #4b5563; }
.school-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px; margin-top: 32px;
}
.school-card {
  background: white; border: 1px solid #e5e7eb; border-radius: 14px;
  padding: 24px 16px; text-align: center; text-decoration: none; color: #111827;
  transition: transform 0.15s, box-shadow 0.15s;
  display: flex; flex-direction: column; align-items: center; gap: 12px;
}
.school-card:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(15,23,42,0.08); }
.school-card img { width: 64px; height: 64px; object-fit: contain; }
.school-card span { font-weight: 600; }
.logo-fallback {
  width: 64px; height: 64px; border-radius: 16px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white; font-weight: 700; font-size: 28px;
  display: flex; align-items: center; justify-content: center;
}
.school-detail {
  background: white; border: 1px solid #e5e7eb; border-radius: 16px;
  padding: 40px 28px; text-align: center;
}
.school-logo { width: 96px; height: 96px; object-fit: contain; margin: 0 auto 16px; display: block; }
.school-detail h1 { margin: 0 0 24px; font-size: 26px; }
.filter-toggle {
  display: inline-flex; background: #f3f4f6; padding: 4px; border-radius: 10px;
  margin-bottom: 16px; gap: 2px;
}
.filter-switch { cursor: pointer; }
.filter-switch input { position: absolute; opacity: 0; pointer-events: none; }
.filter-switch span {
  display: inline-block; padding: 8px 18px; border-radius: 8px;
  font-size: 14px; font-weight: 500; color: #6b7280;
  transition: background 0.15s, color 0.15s;
}
.filter-switch input:checked + span {
  background: white; color: #111827; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.categories {
  display: flex; flex-wrap: wrap; gap: 8px;
  justify-content: center; margin-bottom: 20px;
  transition: opacity 0.15s;
}
.categories.disabled { opacity: 0.35; pointer-events: none; }
.category-chip { cursor: pointer; }
.category-chip input { position: absolute; opacity: 0; pointer-events: none; }
.category-chip span {
  display: inline-block; padding: 8px 14px; border: 1px solid #d1d5db;
  border-radius: 999px; font-size: 13px; color: #4b5563; background: white;
  transition: all 0.15s;
}
.category-chip input:checked + span {
  background: #2563eb; border-color: #2563eb; color: white;
}
.category-chip:hover span { border-color: #9ca3af; }
.url-box { display: flex; gap: 8px; margin-bottom: 8px; }
.url-box input {
  flex: 1; padding: 12px 14px; border: 1px solid #d1d5db; border-radius: 10px;
  font-size: 14px; background: #f9fafb; color: #111827; min-width: 0;
}
.url-box button {
  padding: 12px 18px; background: #2563eb; color: white; border: none;
  border-radius: 10px; font-weight: 600; cursor: pointer; white-space: nowrap;
}
.url-box button:hover { background: #1d4ed8; }
.copy-status { height: 20px; font-size: 14px; color: #6b7280; margin: 4px 0 20px; }
.copy-status.ok { color: #059669; }
.subscribe-btn {
  display: inline-block; padding: 12px 24px; background: #111827; color: white;
  text-decoration: none; border-radius: 10px; font-weight: 600; margin-bottom: 24px;
}
.subscribe-btn:hover { background: #000; }
.how {
  text-align: left; background: #f3f4f6; border-radius: 10px;
  padding: 12px 16px; margin-top: 16px;
}
.how summary { cursor: pointer; font-weight: 600; }
.how ol { margin: 12px 0 0; padding-left: 20px; }
.how li { margin-bottom: 8px; }
.ad-slot { max-width: 720px; margin: 0 auto 24px; width: 100%; padding: 0 24px; }
.ad-placeholder {
  background: #eef2ff; border: 1px dashed #c7d2fe; border-radius: 10px;
  padding: 24px; text-align: center; color: #6366f1; font-size: 13px;
}
.side-ad { display: none; }
.ad-placeholder--vertical {
  width: 160px; height: 600px; padding: 0;
  display: flex; align-items: center; justify-content: center; line-height: 1.5;
}
@media (min-width: 1100px) {
  .side-ad { display: block; position: fixed; top: 96px; width: 160px; }
  .side-ad--left  { left:  max(24px, calc((100vw - 720px) / 2 - 200px)); }
  .side-ad--right { right: max(24px, calc((100vw - 720px) / 2 - 200px)); }
}
.footer { padding: 24px; text-align: center; color: #9ca3af; font-size: 13px; }
.empty { color: #9ca3af; }
`.trim();

type AdsCtx = { enabled: boolean; clientId: string; slotId: string };

function adsHeadScript(ads: AdsCtx): string {
  if (!ads.enabled) return "";
  return `<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${escape(ads.clientId)}" crossorigin="anonymous"></script>`;
}
function verticalAd(ads: AdsCtx, side: "left" | "right"): string {
  const slot = ads.enabled
    ? `<ins class="adsbygoogle" style="display:block;width:160px;height:600px;" data-ad-client="${escape(ads.clientId)}" data-ad-slot="${escape(ads.slotId)}" data-ad-format="vertical"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({});</script>`
    : `<div class="ad-placeholder ad-placeholder--vertical"><span>광고 영역<br>(160 × 600)</span></div>`;
  return `<aside class="side-ad side-ad--${side}">${slot}</aside>`;
}
function bottomAd(ads: AdsCtx): string {
  if (ads.enabled) {
    return `<aside class="ad-slot"><ins class="adsbygoogle" style="display:block" data-ad-client="${escape(ads.clientId)}" data-ad-slot="${escape(ads.slotId)}" data-ad-format="auto" data-full-width-responsive="true"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({});</script></aside>`;
  }
  return `<aside class="ad-slot ad-placeholder"><span>광고 영역 (Google AdSense)</span></aside>`;
}

function shell(title: string, body: string, ads: AdsCtx): string {
  return `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${escape(title)}</title>
<meta name="description" content="대학 학사일정을 개인 캘린더 앱에서 자동으로 받아볼 수 있는 iCal 구독 서비스">
<style>${STYLE}</style>
${adsHeadScript(ads)}
</head>
<body>
<header class="topbar"><a href="/" class="brand">학사일정 구독</a></header>
${verticalAd(ads, "left")}
${verticalAd(ads, "right")}
<main class="main">${body}</main>
${bottomAd(ads)}
<footer class="footer"><p>학사일정은 각 학교 공식 사이트에서 매일 자동으로 동기화됩니다. 일정이 변경되면 캘린더에도 반영됩니다.</p></footer>
</body>
</html>`;
}

function logoBlock(school: SchoolRow, cls: string): string {
  const url = logoUrl(school.logo_path);
  if (url) return `<img class="${cls}" src="${escape(url)}" alt="${escape(school.name)}">`;
  return `<div class="${cls} logo-fallback">${escape(school.name[0])}</div>`;
}

export function renderIndex(schools: SchoolRow[], ads: AdsCtx, basePath: string): string {
  const body = `
<section class="hero">
  <h1>학사일정을 캘린더 앱에서 자동으로</h1>
  <p>학교를 선택하고 URL을 캘린더 앱에 등록하면, 시험·휴학·등록기간 등 학사일정이 자동으로 동기화됩니다.</p>
</section>
<section class="school-grid">
${schools.length === 0 ? `<p class="empty">등록된 학교가 아직 없습니다.</p>` : schools.map(s => `<a class="school-card" href="${escape(basePath)}/s/${escape(s.slug)}">${logoBlock(s, "")}<span>${escape(s.name)}</span></a>`).join("\n")}
</section>`;
  return shell("학사일정 캘린더 구독", body, ads);
}

export function renderSchool(
  school: SchoolRow,
  icalUrl: string,
  webcalUrl: string,
  ads: AdsCtx,
): string {
  const chips = CATEGORIES.map(c => `<label class="category-chip"><input type="checkbox" data-cat value="${escape(c.slug)}" disabled><span>${escape(c.label)}</span></label>`).join("\n");
  const body = `
<section class="school-detail">
  ${logoBlock(school, "school-logo")}
  <h1>${escape(school.name)} 학사일정</h1>
  <div class="filter-toggle">
    <label class="filter-switch"><input type="radio" name="mode" value="all" checked><span>전체 받기</span></label>
    <label class="filter-switch"><input type="radio" name="mode" value="pick"><span>골라 받기</span></label>
  </div>
  <div class="categories disabled">${chips}</div>
  <div class="url-box">
    <input id="icalUrl" type="text" readonly value="${escape(icalUrl)}">
    <button id="copyBtn" type="button">URL 복사</button>
  </div>
  <p id="copyStatus" class="copy-status"></p>
  <a id="subscribeBtn" class="subscribe-btn" href="${escape(webcalUrl)}">캘린더 앱으로 바로 추가</a>
  <details class="how">
    <summary>캘린더 앱에 등록하는 방법</summary>
    <ol>
      <li><strong>Google 캘린더</strong>: 좌측 "다른 캘린더" → "URL로 추가" → 위 URL 붙여넣기</li>
      <li><strong>Apple 캘린더 (iPhone/Mac)</strong>: "캘린더 추가" → "구독 캘린더 추가" → 위 URL 붙여넣기</li>
      <li><strong>Outlook</strong>: 캘린더 → "캘린더 추가" → "웹에서 구독" → 위 URL 붙여넣기</li>
    </ol>
  </details>
</section>
<script>
(function () {
  const baseUrl = ${JSON.stringify(icalUrl)};
  const icalInput = document.getElementById('icalUrl');
  const subscribeBtn = document.getElementById('subscribeBtn');
  const categoriesBox = document.querySelector('.categories');
  const modeRadios = document.querySelectorAll('input[name="mode"]');
  const catBoxes = document.querySelectorAll('input[data-cat]');
  function selectedCats() { return [...catBoxes].filter(c => c.checked).map(c => c.value); }
  function refresh() {
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const disabled = mode !== 'pick';
    categoriesBox.classList.toggle('disabled', disabled);
    catBoxes.forEach(c => { c.disabled = disabled; if (disabled) c.checked = false; });
    let url = baseUrl;
    if (!disabled) {
      const cats = selectedCats();
      if (cats.length) url = baseUrl + '?categories=' + cats.join(',');
    }
    icalInput.value = url;
    subscribeBtn.href = url.replace(/^https?/, 'webcal');
  }
  modeRadios.forEach(r => r.addEventListener('change', refresh));
  catBoxes.forEach(c => c.addEventListener('change', refresh));
  document.getElementById('copyBtn').addEventListener('click', async () => {
    const status = document.getElementById('copyStatus');
    try { await navigator.clipboard.writeText(icalInput.value); }
    catch (err) { icalInput.select(); document.execCommand('copy'); }
    status.textContent = '✓ URL이 복사되었습니다';
    status.className = 'copy-status ok';
  });
})();
</script>`;
  return shell(`${school.name} 학사일정 구독`, body, ads);
}
