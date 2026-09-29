(function () {
  // 移动端目录展开
  var toggle = document.getElementById('navToggle');
  var nav = document.getElementById('topNav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      nav.classList.toggle('open');
    });
  }

  // 侧栏目录高亮（滚动监听）
  var links = Array.prototype.slice.call(document.querySelectorAll('.toc a'));
  if (links.length && 'IntersectionObserver' in window) {
    var map = {};
    var targets = [];
    links.forEach(function (a) {
      var el = document.querySelector(a.getAttribute('href'));
      if (el) { map[el.id] = a; targets.push(el); }
    });
    var visible = {};
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        visible[e.target.id] = e.isIntersecting;
      });
      links.forEach(function (a) { a.classList.remove('active'); });
      for (var i = 0; i < targets.length; i++) {
        if (visible[targets[i].id]) { map[targets[i].id].classList.add('active'); break; }
      }
    }, { rootMargin: '-80px 0px -70% 0px' });
    targets.forEach(function (t) { io.observe(t); });
  }
})();
