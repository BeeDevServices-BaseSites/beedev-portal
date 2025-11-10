(function() {
  const addBtn = document.getElementById('add-note');
  if (!addBtn) return;
  addBtn.addEventListener('click', function() {
    const totalEl = document.getElementById('id_notes-TOTAL_FORMS');
    const total = parseInt(totalEl.value, 10);
    const container = document.querySelector('fieldset.card'); // notes fieldset
    // Build from an empty form template:
    const tmpl = `{{ notes_fs.empty_form.as_p|escapejs }}`.replace(/__prefix__/g, total);
    const wrapper = document.createElement('div');
    wrapper.className = 'note-row';
    wrapper.innerHTML = tmpl;
    // Insert before actions
    const actions = document.querySelector('.actions');
    container.insertBefore(wrapper, actions);
    totalEl.value = total + 1;
  });
})();