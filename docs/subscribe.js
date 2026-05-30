// 모든 페이지 공통 인터랙션 + 학교 페이지 전용 로직.
// - 모든 페이지: .js-share-btn 클릭 처리(Web Share API + fallback)
// - index 페이지: #statsSchools / #statsCopies 가 있으면 /stats fetch
// - 학교 페이지: 카테고리/엔드포인트 토글, URL 복사(+ /copy/{slug} 기록), #howRoot 가이드 렌더
(function () {
  // ────────────────────────────────────────────────────────────
  // 1) 공유 버튼 — Web Share API 우선, 데스크톱은 URL 복사 fallback
  // ────────────────────────────────────────────────────────────
  function shareCurrentPage() {
    var data = {
      title: document.title,
      text: document.title + ' — 학사일정 자동 동기화',
      url: location.href
    };
    if (navigator.share) {
      navigator.share(data).catch(function () { /* 사용자 취소 — 무시 */ });
      return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(location.href).then(function () {
        alert('링크를 복사했습니다. 카톡이나 SNS에 붙여 공유해주세요!');
      });
    } else {
      prompt('아래 링크를 복사하세요:', location.href);
    }
  }
  var shareBtns = document.querySelectorAll('.js-share-btn');
  for (var s = 0; s < shareBtns.length; s++) {
    shareBtns[s].addEventListener('click', shareCurrentPage);
  }

  // ────────────────────────────────────────────────────────────
  // 2) 누적 통계 (index 페이지만)
  // ────────────────────────────────────────────────────────────
  var statsSchools = document.getElementById('statsSchools');
  var statsCopies = document.getElementById('statsCopies');
  if (statsSchools || statsCopies) {
    fetch('/stats', { method: 'GET' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        if (statsSchools && typeof data.schools === 'number') {
          statsSchools.textContent = data.schools.toLocaleString('ko-KR');
        }
        if (statsCopies && typeof data.copies === 'number') {
          statsCopies.textContent = data.copies.toLocaleString('ko-KR');
        }
        if (Array.isArray(data.ranking)) renderRanking(data.ranking);
      })
      .catch(function () { /* 조용히 실패 — 기본값 유지 */ });
  }

  // 학교별 인기 순위 — 도넛(conic-gradient) + 등수 리스트. 복사 0건이면 섹션 숨김 유지.
  function renderRanking(ranking) {
    var section = document.getElementById('rankingSection');
    var chart = document.getElementById('rankingChart');
    var list = document.getElementById('rankingList');
    if (!section || !chart || !list) return;
    var ranked = ranking.filter(function (r) { return r && r.copies > 0; });
    var total = ranked.reduce(function (a, r) { return a + r.copies; }, 0);
    if (total === 0) return;
    var palette = ['#2563eb', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'];
    var medals = ['🥇', '🥈', '🥉'];
    var acc = 0, stops = [], rows = '';
    for (var i = 0; i < ranked.length; i++) {
      var color = palette[i % palette.length];
      var start = (acc / total) * 100;
      acc += ranked[i].copies;
      var end = (acc / total) * 100;
      stops.push(color + ' ' + start.toFixed(2) + '% ' + end.toFixed(2) + '%');
      var pct = Math.round((ranked[i].copies / total) * 100);
      var rank = i < 3 ? medals[i] : (i + 1) + '위';
      rows += '<li>'
        + '<span class="ranking__rank">' + rank + '</span>'
        + '<span class="ranking__dot" style="background:' + color + '"></span>'
        + '<span class="ranking__name">' + escapeHtml(ranked[i].name) + '</span>'
        + '<span class="ranking__count">' + ranked[i].copies.toLocaleString('ko-KR') + '회 · ' + pct + '%</span>'
        + '</li>';
    }
    chart.style.background = 'conic-gradient(' + stops.join(', ') + ')';
    list.innerHTML = rows;
    var totalEl = document.getElementById('rankingTotal');
    if (totalEl) totalEl.textContent = total.toLocaleString('ko-KR');
    section.hidden = false;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // ────────────────────────────────────────────────────────────
  // 2.5) 업데이트 내역 — 간단 목록 + 클릭 시 상세 모달(이전/다음 글 이동)
  // ────────────────────────────────────────────────────────────
  var clListEl = document.getElementById('changelogList');
  if (clListEl) initChangelog(clListEl);

  function initChangelog(listEl) {
    // 목록엔 date+title만, 상세(모달)엔 body. 최신 글이 위(index 0).
    var entries = [
      {
        date: '2026-05-30',
        title: '구독 가이드 보강 · 공유/신청 버튼 추가',
        body: '<p>캘린더 앱마다 구독 추가 방법이 달라, 앱별 단계별 가이드를 새로 정리했습니다.</p>'
          + '<ul>'
          + '<li><strong>안드로이드</strong> — 구글 캘린더 <em>모바일 앱</em>에서는 구독 추가가 막혀 있습니다. PC나 폰 <em>브라우저</em>로 Google Calendar에 추가하면 앱에도 자동 동기화됩니다. 삼성 캘린더 연동도 안내합니다.</li>'
          + '<li><strong>아이폰·아이패드</strong> — “캘린더 앱으로 바로 추가” 버튼 한 번, 또는 설정 → 캘린더에서 구독 추가.</li>'
          + '<li><strong>맥</strong> — 캘린더 앱 → 파일 → 새로운 구독 캘린더.</li>'
          + '<li><strong>Outlook(웹)</strong> — 캘린더 추가 → 웹에서 구독.</li>'
          + '</ul>'
          + '<p>또한 “친구에게 공유하기”·“내 학교 신청하기” 버튼을 추가했습니다.</p>'
      },
      {
        date: '2026-05-30',
        title: 'URL 복사 횟수 통계 · 모바일 버튼 수정',
        body: '<p>메인에 학교별로 캘린더 주소가 몇 번 복사됐는지 집계한 ‘URL 복사 횟수’ 통계를 추가했습니다.</p>'
          + '<p>또한 모바일 화면에서 ‘학교 신청’·‘공유’ 버튼이 가려지던 문제를 수정했습니다.</p>'
      },
      {
        date: '2026-05-29',
        title: '지원 학교 6곳으로 확대 · 공식 로고 적용',
        body: '<p>서울대학교·고려대학교·한국체육대학교·한림대학교를 추가해 총 6개교를 지원합니다.</p>'
          + '<p>각 학교의 공식 로고도 적용했습니다.</p>'
      },
      {
        date: '2026-05-28',
        title: '카테고리 필터 · ‘시작·끝만 표시’ 토글',
        body: '<p>‘시험만’, ‘등록기간만’처럼 원하는 종류의 일정만 골라서 구독할 수 있는 카테고리 필터를 추가했습니다.</p>'
          + '<p>여러 날에 걸친 일정을 시작일·종료일 두 개의 하루짜리 표시로만 정리하는 ‘시작·끝만 표시’ 토글도 생겼습니다. 일정이 많아 캘린더가 복잡할 때 유용합니다.</p>'
      },
      {
        date: '2026-05-27',
        title: 'iCal 구독 서비스 오픈 (가천대·동서울대)',
        body: '<p>대학 학사일정을 개인 캘린더 앱에서 자동으로 받아보는 iCal 구독 서비스를 열었습니다.</p>'
          + '<p>가천대학교·동서울대학교부터 시작하며, 구글·애플·아웃룩 등 주요 캘린더 앱에서 구독할 수 있습니다.</p>'
      }
    ];

    var modal = document.getElementById('changelogModal');
    var mDate = document.getElementById('clModalDate');
    var mTitle = document.getElementById('clModalTitle');
    var mBody = document.getElementById('clModalBody');
    var mPrev = document.getElementById('clPrev');
    var mNext = document.getElementById('clNext');
    var lastFocus = null;

    // 목록은 최근 STEP개만 노출, '더보기'로 오래된 항목 펼침 (무한 증가 방지)
    var STEP = 4;
    var shown = Math.min(STEP, entries.length);
    var moreBtn = document.createElement('button');
    moreBtn.type = 'button';
    moreBtn.className = 'changelog-more';
    moreBtn.textContent = '더보기';
    if (listEl.parentNode) listEl.parentNode.insertBefore(moreBtn, listEl.nextSibling);

    function renderList() {
      var html = '';
      for (var i = 0; i < shown; i++) {
        html += '<li><button type="button" class="cl-item" data-i="' + i + '">'
          + '<time>' + entries[i].date + '</time>'
          + '<span class="cl-item__title"></span>'
          + '<span class="cl-item__arrow" aria-hidden="true">›</span>'
          + '</button></li>';
      }
      listEl.innerHTML = html;
      var titleEls = listEl.querySelectorAll('.cl-item__title');
      for (var t = 0; t < titleEls.length; t++) titleEls[t].textContent = entries[t].title;
      moreBtn.hidden = shown >= entries.length;
    }
    moreBtn.addEventListener('click', function () {
      shown = Math.min(shown + STEP, entries.length);
      renderList();
    });
    renderList();

    function setNav(btn, idx, label) {
      if (idx >= 0 && idx < entries.length) {
        btn.hidden = false;
        btn.setAttribute('data-i', idx);
        btn.innerHTML = '<span class="cl-nav__label">' + label + '</span><span class="cl-nav__title"></span>';
        btn.querySelector('.cl-nav__title').textContent = entries[idx].title;
      } else {
        btn.hidden = true;
      }
    }
    function openEntry(i) {
      if (!modal || i < 0 || i >= entries.length) return;
      var e = entries[i];
      mDate.textContent = e.date;
      mTitle.textContent = e.title;
      mBody.innerHTML = e.body;
      setNav(mPrev, i + 1, '← 이전 글'); // 이전 = 더 오래된 글
      setNav(mNext, i - 1, '다음 글 →'); // 다음 = 더 최신 글
      var firstOpen = modal.hidden;
      if (firstOpen) {
        lastFocus = document.activeElement;
        modal.hidden = false;
        document.body.style.overflow = 'hidden';
      }
      modal.querySelector('.cl-modal__panel').scrollTop = 0;
      modal.querySelector('.cl-modal__close').focus();
    }
    function closeModal() {
      if (!modal || modal.hidden) return;
      modal.hidden = true;
      document.body.style.overflow = '';
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    }

    listEl.addEventListener('click', function (ev) {
      var b = ev.target.closest('.cl-item');
      if (b) openEntry(Number(b.getAttribute('data-i')));
    });
    if (modal) {
      mPrev.addEventListener('click', function () { openEntry(Number(mPrev.getAttribute('data-i'))); });
      mNext.addEventListener('click', function () { openEntry(Number(mNext.getAttribute('data-i'))); });
      modal.addEventListener('click', function (ev) {
        if (ev.target.hasAttribute('data-close')) closeModal();
      });
      document.addEventListener('keydown', function (ev) {
        if (modal.hidden) return;
        if (ev.key === 'Escape') closeModal();
        else if (ev.key === 'ArrowLeft' && !mPrev.hidden) openEntry(Number(mPrev.getAttribute('data-i')));
        else if (ev.key === 'ArrowRight' && !mNext.hidden) openEntry(Number(mNext.getAttribute('data-i')));
      });
    }
  }

  // ────────────────────────────────────────────────────────────
  // 2.6) 전국 비교 (메인) — 모든 학교 .ics를 파싱해 방학·시험 순위
  // ────────────────────────────────────────────────────────────
  var compareSection = document.getElementById('compareSection');
  if (compareSection) renderCompare(compareSection);

  function renderCompare(section) {
    var cards = document.querySelectorAll('.school-card[href^="s/"]');
    var schools = [];
    for (var i = 0; i < cards.length; i++) {
      var m = cards[i].getAttribute('href').match(/s\/([a-z0-9-]+)\.html/);
      if (m) schools.push({ slug: m[1], name: (cards[i].textContent || '').trim() });
    }
    if (!schools.length) return;
    Promise.all(schools.map(function (s) {
      return fetch('/calendar/' + s.slug + '.ics')
        .then(function (r) { return r.ok ? r.text() : ''; })
        .then(function (t) { return { name: s.name, events: t ? parseIcs(t) : [] }; })
        .catch(function () { return { name: s.name, events: [] }; });
    })).then(function (all) {
      var today = startOfToday();
      var vac = [], exam = [];
      all.forEach(function (sc) {
        var v = sc.events.filter(function (e) { return /방학|휴가/.test(e.summary) && e.start >= today; })
          .sort(function (a, b) { return a.start - b.start; })[0];
        if (v) vac.push({ name: sc.name, date: v.start });
        var x = sc.events.filter(function (e) { return /시험|고사/.test(e.summary) && e.end > today; })
          .sort(function (a, b) { return a.start - b.start; })[0];
        if (x) exam.push({ name: sc.name, date: x.start });
      });
      vac.sort(function (a, b) { return a.date - b.date; });
      exam.sort(function (a, b) { return a.date - b.date; });
      var html = '';
      if (vac.length) html += compareCard('🏖️ 방학이 가장 빠른 학교', vac, today, 'date');
      if (exam.length) html += compareCard('📝 시험이 가장 임박한 학교', exam, today, 'dday');
      if (!html) return;
      section.innerHTML = '<h2 class="compare__heading">🏫 전국 비교</h2><div class="compare__grid">' + html + '</div>';
      section.hidden = false;
    }).catch(function () { /* 조용히 실패 */ });
  }
  function compareCard(title, items, today, mode) {
    var rows = '';
    for (var i = 0; i < items.length && i < 5; i++) {
      var rank = i < 3 ? ['🥇', '🥈', '🥉'][i] : (i + 1) + '';
      var val = mode === 'dday' ? ddayLabel(items[i].date, today) : fmtMD(items[i].date);
      rows += '<li><span class="compare__rank">' + rank + '</span>'
        + '<span class="compare__name">' + escapeHtml(items[i].name) + '</span>'
        + '<span class="compare__val">' + val + '</span></li>';
    }
    return '<div class="compare__card"><h3 class="compare__title">' + title + '</h3><ol class="compare__list">' + rows + '</ol></div>';
  }
  function ddayLabel(date, today) {
    var dd = Math.round((date - today) / 86400000);
    return dd > 0 ? 'D-' + dd : (dd === 0 ? 'D-DAY' : '진행중');
  }

  // ────────────────────────────────────────────────────────────
  // 3) 학교 페이지 전용 (#icalUrl 없으면 종료)
  // ────────────────────────────────────────────────────────────
  var icalInput = document.getElementById('icalUrl');
  if (!icalInput) return;

  var baseUrl = icalInput.value;
  var slugMatch = baseUrl.match(/\/calendar\/([a-z0-9-]+)\.ics/);
  var schoolSlug = slugMatch ? slugMatch[1] : null;
  var subscribeBtn = document.getElementById('subscribeBtn');
  var categoriesBox = document.querySelector('.categories');
  var modeRadios = document.querySelectorAll('input[name="mode"]');
  var catBoxes = document.querySelectorAll('input[data-cat]');
  var endpointsToggle = document.getElementById('endpointsToggle');
  var copyBtn = document.getElementById('copyBtn');
  var status = document.getElementById('copyStatus');

  function selectedCats() {
    var out = [];
    for (var i = 0; i < catBoxes.length; i++) {
      if (catBoxes[i].checked) out.push(catBoxes[i].value);
    }
    return out;
  }

  function refresh() {
    var mode = document.querySelector('input[name="mode"]:checked').value;
    var disabled = mode !== 'pick';
    categoriesBox.classList.toggle('disabled', disabled);
    for (var i = 0; i < catBoxes.length; i++) {
      catBoxes[i].disabled = disabled;
      if (disabled) catBoxes[i].checked = false;
    }
    var params = [];
    if (!disabled) {
      var cats = selectedCats();
      if (cats.length) params.push('categories=' + cats.join(','));
    }
    if (endpointsToggle && endpointsToggle.checked) params.push('endpoints=1');
    var url = params.length ? baseUrl + '?' + params.join('&') : baseUrl;
    icalInput.value = url;
    subscribeBtn.href = url.replace(/^https?/, 'webcal');
  }

  for (var i = 0; i < modeRadios.length; i++) modeRadios[i].addEventListener('change', refresh);
  for (var j = 0; j < catBoxes.length; j++) catBoxes[j].addEventListener('change', refresh);
  if (endpointsToggle) endpointsToggle.addEventListener('change', refresh);

  copyBtn.addEventListener('click', function () {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(icalInput.value).catch(function () {
        icalInput.select();
        document.execCommand('copy');
      });
    } else {
      icalInput.select();
      document.execCommand('copy');
    }
    status.textContent = '✓ URL이 복사되었습니다';
    status.className = 'copy-status ok';
    // 학교별 복사 횟수 기록 (fire-and-forget; 실패해도 무시).
    if (schoolSlug) {
      fetch('/copy/' + schoolSlug, { method: 'POST', keepalive: true })
        .catch(function () {});
    }
  });

  // ────────────────────────────────────────────────────────────
  // 3.5) 다가오는 일정 (학교 페이지) — .ics를 직접 파싱해 D-day 표시.
  //      Edge Function 변경 없이 프론트에서 처리.
  // ────────────────────────────────────────────────────────────
  var upcomingRoot = document.getElementById('upcomingRoot');
  if (upcomingRoot && schoolSlug) renderUpcoming(upcomingRoot, schoolSlug);

  function renderUpcoming(root, slug) {
    fetch('/calendar/' + slug + '.ics')
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (text) {
        if (!text) return;
        var today = startOfToday();
        var up = parseIcs(text)
          .filter(function (e) { return e.end > today; })   // 아직 안 끝난 일정
          .sort(function (a, b) { return a.start - b.start; })
          .slice(0, 5);
        if (!up.length) return;
        var html = '<h3 class="upcoming__title">📅 다가오는 일정</h3><ul class="upcoming__list">';
        for (var i = 0; i < up.length; i++) {
          var e = up[i];
          var dd = Math.round((e.start - today) / 86400000);
          var badge = 'D-' + dd, cls = '';
          if (dd === 0) { badge = 'D-DAY'; cls = ' upcoming__badge--today'; }
          else if (dd < 0) { badge = '진행중'; cls = ' upcoming__badge--now'; }
          html += '<li class="upcoming__item">'
            + '<span class="upcoming__badge' + cls + '">' + badge + '</span>'
            + '<span class="upcoming__name"></span>'
            + '<span class="upcoming__date">' + fmtRange(e.start, e.end) + '</span>'
            + '</li>';
        }
        html += '</ul>';
        root.className = 'upcoming';
        root.innerHTML = html;
        var names = root.querySelectorAll('.upcoming__name');
        for (var j = 0; j < names.length; j++) names[j].textContent = up[j].summary;
      })
      .catch(function () { /* 조용히 실패 */ });
  }

  function parseIcs(text) {
    var out = [];
    var blocks = text.split('BEGIN:VEVENT');
    for (var i = 1; i < blocks.length; i++) {
      var sm = blocks[i].match(/\nSUMMARY:(.*)/);
      var ds = blocks[i].match(/DTSTART[^:\n]*:(\d{8})/);
      var de = blocks[i].match(/DTEND[^:\n]*:(\d{8})/);
      if (!sm || !ds) continue;
      var start = ymd(ds[1]);
      out.push({
        summary: sm[1].replace(/\\([,;\\])/g, '$1').trim(),
        start: start,
        end: de ? ymd(de[1]) : start
      });
    }
    return out;
  }
  function ymd(s) { return new Date(+s.slice(0, 4), +s.slice(4, 6) - 1, +s.slice(6, 8)); }
  function startOfToday() { var n = new Date(); return new Date(n.getFullYear(), n.getMonth(), n.getDate()); }
  function fmtRange(start, end) {
    var last = new Date(end.getTime() - 86400000); // DTEND는 비포함 → 실제 마지막 날
    return last <= start ? fmtMD(start) : fmtMD(start) + ' ~ ' + fmtMD(last);
  }
  function fmtMD(d) { return (d.getMonth() + 1) + '월 ' + d.getDate() + '일'; }

  // ────────────────────────────────────────────────────────────
  // 4) 캘린더 앱 등록 가이드 (#howRoot 가 있을 때만)
  //    안드로이드(Google Calendar 모바일 앱 한계)를 가장 위에 강조.
  // ────────────────────────────────────────────────────────────
  var howRoot = document.getElementById('howRoot');
  if (howRoot) renderGuide(howRoot);

  function renderGuide(root) {
    root.innerHTML = [
      '<h3 class="how__title">📅 캘린더 앱에 등록하는 방법</h3>',

      '<details class="how-platform" open>',
      '<summary><span class="how-platform__name">🤖 Android</span><span class="how-platform__tag">가장 많이 막힘</span></summary>',
      '<p class="how-warn">⚠️ <strong>구글 캘린더 모바일 앱에서는 구독 추가가 안 됩니다.</strong> PC 또는 폰의 <em>브라우저</em>로 Google Calendar 웹사이트에서 추가해야 합니다. 한 번 추가하면 폰 앱에도 자동으로 동기화됩니다.</p>',
      '<ol>',
      '<li>위 URL을 <strong>복사</strong></li>',
      '<li>브라우저로 <a href="https://calendar.google.com" target="_blank" rel="noopener">calendar.google.com</a> 접속 (PC 또는 폰 브라우저 모두 가능)</li>',
      '<li>왼쪽 사이드바 <strong>"다른 캘린더"</strong> 옆 <strong>+</strong> 버튼 → <strong>"URL로 만들기"</strong></li>',
      '<li>복사한 URL 붙여넣고 <strong>"캘린더 추가"</strong></li>',
      '<li>잠시 뒤 폰의 구글 캘린더 앱에서도 일정이 보입니다 ✓</li>',
      '</ol>',
      '<p class="how-tip">💡 <strong>삼성 캘린더 사용자</strong>: 위 방식대로 구글 캘린더에 추가한 뒤, 삼성 캘린더 앱의 <strong>설정 → 동기화할 캘린더</strong>에서 해당 구글 캘린더 표시를 켜주세요.</p>',
      '</details>',

      '<details class="how-platform">',
      '<summary><span class="how-platform__name">🍎 iPhone / iPad</span></summary>',
      '<ol>',
      '<li><strong>가장 쉬운 방법</strong>: 위 <strong>"캘린더 앱으로 바로 추가"</strong> 버튼을 탭 → 팝업에서 <strong>"구독"</strong> 선택. 끝.</li>',
      '<li>안 되면: 설정 앱 → <strong>캘린더 → 계정 → 계정 추가 → 기타 → 구독 캘린더 추가</strong> → URL 붙여넣기 → 다음 → 저장</li>',
      '</ol>',
      '</details>',

      '<details class="how-platform">',
      '<summary><span class="how-platform__name">🖥 Mac (macOS 캘린더)</span></summary>',
      '<ol>',
      '<li>캘린더 앱 열기 → 상단 메뉴 <strong>파일 → 새로운 구독 캘린더…</strong></li>',
      '<li>위 URL 붙여넣고 <strong>"구독"</strong> → 위치는 iCloud 권장</li>',
      '</ol>',
      '</details>',

      '<details class="how-platform">',
      '<summary><span class="how-platform__name">📧 Outlook (웹)</span></summary>',
      '<ol>',
      '<li>Outlook 웹(outlook.com 또는 outlook.office.com) → 캘린더 화면</li>',
      '<li>왼쪽 사이드바 <strong>"캘린더 추가"</strong> → <strong>"웹에서 구독"</strong></li>',
      '<li>URL 붙여넣고 <strong>"가져오기"</strong></li>',
      '</ol>',
      '</details>'
    ].join('');
  }
})();
