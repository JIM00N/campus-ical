// 학교 페이지의 카테고리 토글 + URL 복사 동작.
// data-cat checkbox와 #icalUrl input은 모든 학교 페이지에서 동일한 구조라서
// 같은 스크립트를 재사용한다.
(function () {
  var icalInput = document.getElementById('icalUrl');
  if (!icalInput) return;

  var baseUrl = icalInput.value;
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
  });
})();
