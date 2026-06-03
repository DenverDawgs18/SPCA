document.addEventListener('DOMContentLoaded', function () {

  /* ---- Mobile nav toggle ---- */
  const toggle   = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (toggle && navLinks) {
    toggle.addEventListener('click', function () {
      const open = navLinks.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open);
    });
  }

  /* ---- FAQ accordion ---- */
  document.querySelectorAll('.faq-question').forEach(function (q) {
    q.addEventListener('click', function () {
      q.closest('.faq-item').classList.toggle('open');
    });
  });

  /* ---- Active nav link ---- */
  var path = window.location.pathname;
  document.querySelectorAll('.nav-links a').forEach(function (a) {
    var href = a.getAttribute('href');
    if (!href) return;
    if (href !== '/' && path.startsWith(href)) a.classList.add('active');
    else if (href === '/' && path === '/') a.classList.add('active');
  });

  /* ---- Header shadow on scroll ---- */
  var header = document.querySelector('.site-header');
  if (header) {
    window.addEventListener('scroll', function () {
      header.classList.toggle('scrolled', window.scrollY > 20);
    }, { passive: true });
  }

  /* ---- Scroll reveal system ---- */
  if (!window.IntersectionObserver) return; // graceful degradation

  var revealObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.10, rootMargin: '0px 0px -36px 0px' });

  function observe(el) { revealObserver.observe(el); }

  // Section headers
  document.querySelectorAll('.section-header').forEach(function (el) {
    el.classList.add('reveal');
    observe(el);
  });

  // Grids: stagger each child
  var grids = [
    ['.animal-grid',    '.animal-card'],
    ['.action-cards',   '.action-card'],
    ['.steps',          '.step-card'],
    ['.impact-grid',    '.impact-item'],
    ['.donate-options', '.donate-card'],
    ['.team-grid',      '.team-card'],
  ];
  grids.forEach(function (pair) {
    document.querySelectorAll(pair[0]).forEach(function (grid) {
      var children = grid.querySelectorAll(pair[1]);
      children.forEach(function (child, i) {
        child.classList.add('reveal');
        var delay = Math.min(i, 4);
        if (delay > 0) child.classList.add('reveal-delay-' + delay);
        observe(child);
      });
    });
  });

  // About split: image slides from left, text from right
  document.querySelectorAll('.about-split').forEach(function (el) {
    var kids = el.children;
    if (kids[0]) { kids[0].classList.add('reveal-left'); observe(kids[0]); }
    if (kids[1]) { kids[1].classList.add('reveal-right'); observe(kids[1]); }
  });

  // Info blocks: left/right aware of .reverse modifier
  document.querySelectorAll('.info-block').forEach(function (el) {
    var reversed = el.classList.contains('reverse');
    var kids = el.children;
    var firstClass  = reversed ? 'reveal-right' : 'reveal-left';
    var secondClass = reversed ? 'reveal-left'  : 'reveal-right';
    if (kids[0]) { kids[0].classList.add(firstClass);  observe(kids[0]); }
    if (kids[1]) { kids[1].classList.add(secondClass); observe(kids[1]); }
  });

  // Contact grid
  document.querySelectorAll('.contact-grid > *').forEach(function (el, i) {
    el.classList.add('reveal');
    if (i > 0) el.classList.add('reveal-delay-' + Math.min(i, 4));
    observe(el);
  });

  /* ---- Counter animation ---- */
  function animateCounter(el) {
    var raw    = el.textContent.trim();
    var num    = parseFloat(raw.replace(/[^0-9.]/g, ''));
    if (isNaN(num) || num === 0) return;
    var prefix = raw.match(/^[^0-9]*/)[0];
    var suffix = raw.match(/[^0-9.]*$/)[0];
    var isInt  = Number.isInteger(num);
    var dur    = 1600;
    var t0     = performance.now();

    function tick(now) {
      var p    = Math.min((now - t0) / dur, 1);
      var ease = 1 - Math.pow(1 - p, 3); // ease-out cubic
      var val  = ease * num;
      el.textContent = prefix + (isInt ? Math.round(val).toLocaleString() : val.toFixed(0)) + suffix;
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  // Impact numbers: trigger on scroll
  var counterObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        counterObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  document.querySelectorAll('.impact-item .num').forEach(function (el) {
    counterObserver.observe(el);
  });

  // Hero stats: count up after the entrance animation finishes
  var heroStats = document.querySelectorAll('.hero-stat .num');
  if (heroStats.length) {
    setTimeout(function () {
      heroStats.forEach(animateCounter);
    }, 750);
  }

});
