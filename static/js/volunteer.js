// Volunteer portal JS — sorting and UX enhancements

document.addEventListener('DOMContentLoaded', function () {

  // Highlight active sidebar link
  const path = window.location.pathname;
  document.querySelectorAll('.sidebar-link').forEach(function (link) {
    const href = link.getAttribute('href');
    if (href && path.startsWith(href) && href !== '/portal/') {
      link.classList.add('active');
    } else if (href === '/portal/' && path === '/portal/') {
      link.classList.add('active');
    }
  });

  // Sortable table columns
  document.querySelectorAll('.data-table th.sortable').forEach(function (th) {
    th.addEventListener('click', function () {
      const table = th.closest('table');
      const tbody = table.querySelector('tbody');
      const rows  = Array.from(tbody.querySelectorAll('tr'));
      const col   = Array.from(th.parentElement.children).indexOf(th);
      const asc   = th.dataset.sortDir !== 'asc';
      th.dataset.sortDir = asc ? 'asc' : 'desc';

      rows.sort(function (a, b) {
        const aText = (a.children[col]?.textContent || '').trim().toLowerCase();
        const bText = (b.children[col]?.textContent || '').trim().toLowerCase();
        const aNum  = parseFloat(aText);
        const bNum  = parseFloat(bText);
        if (!isNaN(aNum) && !isNaN(bNum)) return asc ? aNum - bNum : bNum - aNum;
        return asc ? aText.localeCompare(bText) : bText.localeCompare(aText);
      });

      rows.forEach(function (row) { tbody.appendChild(row); });

      // Update sort indicators
      th.closest('tr').querySelectorAll('th').forEach(function (h) {
        h.textContent = h.textContent.replace(' ↑', '').replace(' ↓', '');
        delete h.dataset.sortDir;
      });
      th.textContent += asc ? ' ↑' : ' ↓';
      th.dataset.sortDir = asc ? 'asc' : 'desc';
    });
  });

  // Auto-set today's date for any date input lacking a value
  document.querySelectorAll('input[type="date"]').forEach(function (input) {
    if (!input.value) {
      input.value = new Date().toISOString().split('T')[0];
    }
  });

});
