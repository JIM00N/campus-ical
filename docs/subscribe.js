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
