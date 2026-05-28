// iCal 직접 생성. Python ical_generator.py와 동일한 결과 형식.
// VEVENT는 DATE 값(allday) 기준이고 DTEND는 exclusive.

type School = { slug: string; name: string; timezone: string };
type Event = { summary: string; dtstart: string; dtend: string };

function fmtDate(s: string): string {
  // "2026-05-09" → "20260509"
  return s.replaceAll("-", "");
}

function addDays(s: string, n: number): string {
  const d = new Date(s + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

// 여러 날에 걸친 일정을 시작일/종료일 두 개의 하루짜리 마커로 분리한다.
// DTEND는 exclusive라 실제 마지막 날은 dtend - 1일.
// 하루짜리 일정은 그대로 둔다.
export function toEndpointEvents(events: Event[]): Event[] {
  const out: Event[] = [];
  for (const ev of events) {
    const lastDay = addDays(ev.dtend, -1);
    if (lastDay <= ev.dtstart) {
      out.push(ev);
      continue;
    }
    out.push({ summary: `${ev.summary} (시작)`, dtstart: ev.dtstart, dtend: addDays(ev.dtstart, 1) });
    out.push({ summary: `${ev.summary} (종료)`, dtstart: lastDay, dtend: ev.dtend });
  }
  return out;
}

function fmtUtc(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    d.getUTCFullYear() +
    pad(d.getUTCMonth() + 1) +
    pad(d.getUTCDate()) +
    "T" +
    pad(d.getUTCHours()) +
    pad(d.getUTCMinutes()) +
    pad(d.getUTCSeconds()) +
    "Z"
  );
}

function fold(line: string): string {
  // iCal 사양: 75옥텟 초과 시 CRLF + space로 fold. 한글은 다 fold되니 일단 단순.
  if (line.length <= 75) return line;
  const parts: string[] = [];
  for (let i = 0; i < line.length; i += 73) {
    parts.push((i === 0 ? "" : " ") + line.slice(i, i + 73));
  }
  return parts.join("\r\n");
}

function escapeText(s: string): string {
  return s.replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\n/g, "\\n");
}

async function sha1Hex(s: string): Promise<string> {
  const buf = new TextEncoder().encode(s);
  const digest = await crypto.subtle.digest("SHA-1", buf);
  return Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2, "0")).join("");
}

export async function buildCalendar(
  school: School,
  events: Event[],
  calendarName?: string,
): Promise<string> {
  const lines: string[] = [];
  const out = (l: string) => lines.push(fold(l));

  out("BEGIN:VCALENDAR");
  out("VERSION:2.0");
  out(`PRODID:-//ical-db//${school.slug}//KR`);
  out("CALSCALE:GREGORIAN");
  out("METHOD:PUBLISH");
  out(`X-WR-CALNAME:${escapeText(`${calendarName ?? school.name} 학사일정`)}`);
  out(`X-WR-TIMEZONE:${school.timezone}`);

  const stamp = fmtUtc(new Date());

  for (const ev of events) {
    const uidRaw = `${school.slug}|${ev.summary}|${ev.dtstart}|${ev.dtend}`;
    const uid = (await sha1Hex(uidRaw)) + "@ical-db";
    out("BEGIN:VEVENT");
    out(`UID:${uid}`);
    out(`SUMMARY:${escapeText(ev.summary)}`);
    out(`DTSTART;VALUE=DATE:${fmtDate(ev.dtstart)}`);
    out(`DTEND;VALUE=DATE:${fmtDate(ev.dtend)}`);
    out(`DTSTAMP:${stamp}`);
    out("END:VEVENT");
  }

  out("END:VCALENDAR");
  return lines.join("\r\n") + "\r\n";
}
