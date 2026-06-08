/* Volunteer portal JS */

(function () {
  "use strict";

  // Auto-set today's date on date inputs with data-today attribute
  function initDateDefaults() {
    var today = new Date().toISOString().slice(0, 10);
    document.querySelectorAll('input[data-today]').forEach(function (inp) {
      if (!inp.value) inp.value = today;
    });
  }

  // Recipient count preview on group email page
  function initRecipientCount() {
    var select = document.getElementById('id_recipient_filter');
    var preview = document.getElementById('recipient-count-preview');
    if (!select || !preview) return;

    function fetchCount() {
      var url = preview.dataset.url + '?filter=' + encodeURIComponent(select.value);
      fetch(url)
        .then(function (r) { return r.json(); })
        .then(function (data) {
          preview.textContent = 'Estimated recipients: ' + data.count;
        })
        .catch(function () {
          preview.textContent = '';
        });
    }

    select.addEventListener('change', fetchCount);
    fetchCount(); // run on load
  }

  // Dismissible alerts
  function initAlertDismiss() {
    document.querySelectorAll('.alert-dismiss').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var el = btn.closest('.alert, li');
        if (el) el.remove();
      });
    });
  }

  // Sortable tables — click any column header to toggle asc/desc
  function initSortableTables() {
    document.querySelectorAll('.data-table.sortable thead th').forEach(function (th, colIdx) {
      th.style.cursor = 'pointer';
      th.title = 'Click to sort';
      var ascending = true;

      th.addEventListener('click', function () {
        var table = th.closest('table');
        var tbody = table.querySelector('tbody');
        if (!tbody) return;

        var rows = Array.from(tbody.querySelectorAll('tr'));
        rows.sort(function (a, b) {
          var aText = (a.cells[colIdx] ? a.cells[colIdx].textContent : '').trim();
          var bText = (b.cells[colIdx] ? b.cells[colIdx].textContent : '').trim();
          var aNum = parseFloat(aText);
          var bNum = parseFloat(bText);
          if (!isNaN(aNum) && !isNaN(bNum)) {
            return ascending ? aNum - bNum : bNum - aNum;
          }
          return ascending ? aText.localeCompare(bText) : bText.localeCompare(aText);
        });

        rows.forEach(function (row) { tbody.appendChild(row); });
        ascending = !ascending;

        table.querySelectorAll('thead th').forEach(function (t) { delete t.dataset.sort; });
        th.dataset.sort = ascending ? 'desc' : 'asc';
      });
    });
  }

  // Confirm before submit on forms with data-confirm attribute
  function initConfirmForms() {
    document.querySelectorAll('form[data-confirm]').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        if (!window.confirm(form.dataset.confirm)) {
          e.preventDefault();
        }
      });
    });
  }

  // Kiosk: focus the volunteer select on load
  function initKioskSelect() {
    var sel = document.getElementById('id_volunteer');
    if (sel && document.querySelector('.kiosk-page')) {
      sel.focus();
    }
  }

  // Scroll active sidebar link into view on mobile
  function initSidebarScroll() {
    var active = document.querySelector('.sidebar-nav a.active');
    if (active && window.innerWidth <= 768) {
      active.scrollIntoView({ block: 'nearest', inline: 'center' });
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    initDateDefaults();
    initRecipientCount();
    initAlertDismiss();
    initSortableTables();
    initConfirmForms();
    initKioskSelect();
    initSidebarScroll();
  });
})();
