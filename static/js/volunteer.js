/**
 * volunteer.js — Medina County SPCA Volunteer Portal
 */

(function () {
  'use strict';

  /* ------------------------------------------------------------------
     Auto-set today's date on any input.js-today
     ------------------------------------------------------------------ */
  function setTodayDates() {
    var today = new Date();
    var yyyy = today.getFullYear();
    var mm = String(today.getMonth() + 1).padStart(2, '0');
    var dd = String(today.getDate()).padStart(2, '0');
    var isoDate = yyyy + '-' + mm + '-' + dd;

    document.querySelectorAll('input.js-today').forEach(function (el) {
      if (!el.value) {
        el.value = isoDate;
      }
    });
  }

  /* ------------------------------------------------------------------
     Sortable table columns
     Click a <th data-sort> to sort the tbody rows.
     Toggles asc/desc on successive clicks.
     ------------------------------------------------------------------ */
  function initSortableTables() {
    document.querySelectorAll('table.sortable').forEach(function (table) {
      var headers = table.querySelectorAll('th[data-sort]');
      headers.forEach(function (th, colIndex) {
        th.addEventListener('click', function () {
          var ascending = !th.classList.contains('sorted-asc');

          // Reset other headers
          headers.forEach(function (h) {
            h.classList.remove('sorted-asc', 'sorted-desc');
          });
          th.classList.add(ascending ? 'sorted-asc' : 'sorted-desc');

          var tbody = table.querySelector('tbody');
          if (!tbody) return;

          var rows = Array.from(tbody.querySelectorAll('tr'));
          rows.sort(function (a, b) {
            var aText = (a.cells[colIndex] ? a.cells[colIndex].textContent : '').trim().toLowerCase();
            var bText = (b.cells[colIndex] ? b.cells[colIndex].textContent : '').trim().toLowerCase();

            // Numeric sort if both look like numbers
            var aNum = parseFloat(aText);
            var bNum = parseFloat(bText);
            if (!isNaN(aNum) && !isNaN(bNum)) {
              return ascending ? aNum - bNum : bNum - aNum;
            }

            // String sort
            if (aText < bText) return ascending ? -1 : 1;
            if (aText > bText) return ascending ? 1 : -1;
            return 0;
          });

          rows.forEach(function (row) {
            tbody.appendChild(row);
          });
        });
      });
    });
  }

  /* ------------------------------------------------------------------
     Recipient count preview on group email page
     (The inline script in group_email.html handles the primary update;
      this is a fallback initialiser in case that script is absent.)
     ------------------------------------------------------------------ */
  function initEmailRecipientPreview() {
    var select = document.querySelector('[name="recipient_filter"]');
    var preview = document.getElementById('recipient-count-text');
    if (!select || !preview || preview.textContent.trim() !== '') return;

    // Try to read counts from data attributes if present
    var countAll = parseInt(document.getElementById('count-all') && document.getElementById('count-all').textContent, 10) || 0;
    var countActive = parseInt(document.getElementById('count-active') && document.getElementById('count-active').textContent, 10) || 0;
    var countInactive = parseInt(document.getElementById('count-inactive') && document.getElementById('count-inactive').textContent, 10) || 0;

    var counts = { all: countAll, active: countActive, inactive: countInactive };

    function update() {
      var val = select.value;
      var count = counts[val] !== undefined ? counts[val] : '?';
      preview.textContent = count + ' volunteer' + (count !== 1 ? 's' : '') + ' will receive this email.';
    }

    select.addEventListener('change', update);
    update();
  }

  /* ------------------------------------------------------------------
     Flash-message auto-dismiss (optional: fade out after 6 seconds)
     ------------------------------------------------------------------ */
  function initMessageAutoDismiss() {
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (el) {
      setTimeout(function () {
        el.style.transition = 'opacity 0.6s ease';
        el.style.opacity = '0';
        setTimeout(function () {
          if (el.parentNode) el.parentNode.removeChild(el);
        }, 600);
      }, 6000);
    });
  }

  /* ------------------------------------------------------------------
     Init
     ------------------------------------------------------------------ */
  document.addEventListener('DOMContentLoaded', function () {
    setTodayDates();
    initSortableTables();
    initEmailRecipientPreview();
    initMessageAutoDismiss();
  });

})();
