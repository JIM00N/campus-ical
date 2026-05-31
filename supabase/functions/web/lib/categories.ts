// 학사일정 카테고리. Python 쪽 app/categories.py와 정의 동일.
// summary 텍스트를 keyword로 매칭 (공백 무시 normalize).
export type Category = { slug: string; label: string; keywords: string[] };

export const CATEGORIES: Category[] = [
  { slug: "tuition",      label: "등록금",          keywords: ["등록금"] },
  { slug: "registration", label: "수강신청",        keywords: ["수강신청", "예비수강"] },
  { slug: "exam",         label: "시험",            keywords: ["중간고사", "기말고사", "기말시험", "중간시험", "성적공시", "정정"] },
  { slug: "major-change", label: "전과·부복수전공",  keywords: ["전과", "부전공", "복수전공", "다전공", "융합전공", "조기졸업"] },
  { slug: "leave",        label: "휴학·복학",       keywords: ["휴학", "복학"] },
  { slug: "summer",       label: "계절학기",        keywords: ["계절학기", "계절수업"] },
  { slug: "withdrawal",   label: "자퇴",            keywords: ["자퇴"] },
  { slug: "graduation",   label: "학위수여식",      keywords: ["학위수여", "졸업식"] },
];

const BY_SLUG = new Map(CATEGORIES.map(c => [c.slug, c]));
const norm = (s: string) => s.replace(/\s+/g, "");

export function eventCategories(summary: string): Set<string> {
  const s = norm(summary);
  const matched = new Set<string>();
  for (const c of CATEGORIES) {
    if (c.keywords.some(k => s.includes(norm(k)))) matched.add(c.slug);
  }
  return matched;
}

export function parseCategoryParam(raw: string | null): Set<string> {
  if (!raw) return new Set();
  return new Set(
    raw.split(",").map(s => s.trim()).filter(s => s && BY_SLUG.has(s))
  );
}

export function filterByCategories<T extends { summary: string }>(
  events: T[],
  wanted: Set<string>,
): T[] {
  if (wanted.size === 0) return events;
  return events.filter(e => {
    const cats = eventCategories(e.summary);
    for (const w of wanted) if (cats.has(w)) return true;
    return false;
  });
}

export function categoryLabels(slugs: Set<string>): string[] {
  const out: string[] = [];
  for (const c of CATEGORIES) if (slugs.has(c.slug)) out.push(c.label);
  return out;
}
