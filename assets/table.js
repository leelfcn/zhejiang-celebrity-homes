(function () {
  var SPOTS = window.SPOTS || [];
  var tbody = document.querySelector('#spotTable tbody');
  var q = document.getElementById('q');
  var fCity = document.getElementById('f-city');
  var fTicket = document.getElementById('f-ticket');
  var fMon = document.getElementById('f-mon');
  var fBook = document.getElementById('f-book');
  var count = document.getElementById('count');
  var emptyTip = document.getElementById('emptyTip');
  var table = document.getElementById('spotTable');
  if (!tbody) return;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function match(s) {
    var kw = (q.value || '').trim().toLowerCase();
    if (kw) {
      var hay = [s.name, s.city, s.addr, s.figure, s.ticket, s.traffic, s.hours].join(' ').toLowerCase();
      if (hay.indexOf(kw) === -1) return false;
    }
    if (fCity.value && s.city !== fCity.value) return false;
    if (fTicket.value === 'free' && !s.free) return false;
    if (fTicket.value === 'paid' && s.free) return false;
    if (fMon.value === 'closed' && !s.monday_closed) return false;
    if (fMon.value === 'open' && s.monday_status !== 'open') return false;
    if (fMon.value === 'unknown' && s.monday_status !== 'unknown') return false;
    if (fBook.value === 'yes' && !s.booking) return false;
    if (fBook.value === 'no' && s.booking) return false;
    return true;
  }

  function render() {
    var rows = SPOTS.filter(match);
    tbody.innerHTML = rows.map(function (s) {
      var ticket = s.free
        ? '<span class="badge free">免费</span>'
        : esc(s.ticket || '待核实');
      var mon = s.monday_status === 'closed'
        ? '<span class="badge warn">' + esc(s.monday) + '</span>'
        : (s.monday_status === 'unknown'
          ? '<span class="muted">' + esc(s.monday || '待核实') + '</span>'
          : esc(s.monday));
      return '<tr>' +
        '<td data-label="地市">' + esc(s.city) + '</td>' +
        '<td data-label="名称"><a href="' + s.url + '">' + esc(s.name) + '</a>' +
        (s.booking_level === 2
          ? ' <span class="badge info">须提前预约</span>'
          : (s.booking_level === 1 ? ' <span class="badge soft">凭证/预约</span>' : '')) + '</td>' +
        '<td data-label="门票">' + ticket + '</td>' +
        '<td data-label="开放时间">' + esc(s.hours) + '</td>' +
        '<td data-label="周一">' + mon + '</td>' +
        '<td data-label="时长">' + esc(s.duration) + '</td>' +
        '<td data-label="交通要点">' + esc(s.traffic || s.addr) + '</td>' +
        '</tr>';
    }).join('');
    count.textContent = '共 ' + rows.length + ' / ' + SPOTS.length + ' 处';
    emptyTip.hidden = rows.length !== 0;
    if (table) table.parentElement.classList.toggle('dim', rows.length === 0);
  }

  [q, fCity, fTicket, fMon, fBook].forEach(function (el) {
    if (!el) return;
    el.addEventListener('input', render);
    el.addEventListener('change', render);
  });

  var lucky = document.getElementById('lucky');
  if (lucky) {
    lucky.addEventListener('click', function () {
      var pool = SPOTS.filter(match);
      if (!pool.length) pool = SPOTS;
      var pick = pool[Math.floor(Math.random() * pool.length)];
      window.location.href = pick.url;
    });
  }

  render();
})();
