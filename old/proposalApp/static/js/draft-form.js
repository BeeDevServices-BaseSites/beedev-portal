// static/js/draft-form.js
(function () {
  function ready(fn){ if (document.readyState !== 'loading') fn(); else document.addEventListener('DOMContentLoaded', fn); }

  ready(function () {
    // -------- Primary contact autofill ----------
    const companySelect = document.getElementById('id_company');
    const endpointInput = document.getElementById('company-ajax-endpoint');
    const nameInput     = document.getElementById('id_contact_name');
    const emailInput    = document.getElementById('id_contact_email');

    async function loadPrimaryContact(companyId) {
      if (!endpointInput || !companyId) return;
      const base = endpointInput.value;   // e.g. /companies/ajax-primary/0/
      const url  = base.replace(/0\/?$/, String(companyId) + '/');
      try {
        const resp = await fetch(url, {headers: {'X-Requested-With':'XMLHttpRequest'}});
        if (!resp.ok) return;
        const data = await resp.json();   // {name, email}
        if (data && typeof data === 'object') {
          if (nameInput && !nameInput.value)  nameInput.value  = (data.name || '').trim();
          if (emailInput && !emailInput.value) emailInput.value = (data.email || '').trim().toLowerCase();
        }
      } catch (_) {/* silent */}
    }

    if (companySelect) {
      companySelect.addEventListener('change', function () {
        if (this.value) loadPrimaryContact(this.value);
      });
      if (companySelect.value) loadPrimaryContact(companySelect.value); // prefill
    }

    // -------- Dynamic notes (formset grow) ----------
    const container   = document.getElementById('notes-container');
    const addBtn      = document.getElementById('add-note-btn');
    const tmpl        = document.getElementById('note-empty-template');
    const totalInput  = document.querySelector('input[name="notes-TOTAL_FORMS"]');
    const maxInput    = document.querySelector('input[name="notes-MAX_NUM_FORMS"]');

    function addNote() {
      if (!tmpl || !container || !totalInput) return;
      const max = maxInput ? parseInt(maxInput.value || '1000', 10) : 1000;
      let index = parseInt(totalInput.value || '0', 10);
      if (index >= max) return;

      const html = tmpl.innerHTML.replaceAll('__prefix__', String(index));
      const wrapper = document.createElement('div');
      wrapper.innerHTML = html;
      container.appendChild(wrapper.firstElementChild);
      totalInput.value = String(index + 1);
    }

    if (addBtn) addBtn.addEventListener('click', addNote);
  });
})();
