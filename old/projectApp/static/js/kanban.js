(function(){
  // read config injected by template
  const CONF = window.KANBAN_CONF || {};
  const MOVE_URL = CONF.moveUrl || "";
  // prefer meta token, fallback to CONF.csrf
  const meta = document.querySelector('meta[name="csrf-token"]');
  const CSRF = meta ? meta.getAttribute('content') : (CONF.csrf || "");

  let dragged = null;

  function updateEmptyState(listEl) {
    const empty = listEl.querySelector('[data-empty]');
    const hasCards = listEl.querySelector('.kanban-card') !== null;
    if (hasCards) {
      if (empty) empty.remove();
    } else {
      if (!empty) {
        const li = document.createElement('li');
        li.className = 'kanban-empty';
        li.setAttribute('data-empty','');
        li.textContent = 'No tasks';
        listEl.appendChild(li);
      }
    }
  }

  function getDragAfterElement(container, y) {
    const cards = [...container.querySelectorAll(".kanban-card:not(.dragging)")];
    return cards.reduce((closest, child) => {
      const box = child.getBoundingClientRect();
      const offset = y - box.top - box.height / 2;
      if (offset < 0 && offset > closest.offset) {
        return { offset, element: child };
      } else {
        return closest;
      }
    }, { offset: Number.NEGATIVE_INFINITY }).element || null;
  }

  const kanban = {
    dragStart(e) {
      dragged = e.currentTarget; // li.kanban-card
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", dragged.dataset.taskId);
      requestAnimationFrame(()=> dragged.classList.add("dragging"));
    },
    dragEnd(e) {
      if (dragged) dragged.classList.remove("dragging");
      dragged = null;
    },
    dragOver(e) {
      e.preventDefault();
      const list = e.currentTarget.querySelector("[data-list]");
      const afterElement = getDragAfterElement(list, e.clientY);
      if (!dragged) return;
      if (afterElement == null) {
        list.appendChild(dragged);
      } else {
        list.insertBefore(dragged, afterElement);
      }
    },
    drop(e) {
      e.preventDefault();
      if (!dragged) return;

      const col = e.currentTarget; // section.col
      const toStatus = col.dataset.colStatus;
      const list = col.querySelector('[data-list]');
      const sourceList = dragged.parentElement;

      // neighbor after which we inserted (previous sibling only if it's a card)
      const prev = dragged.previousElementSibling;
      const afterId = (prev && prev.classList.contains('kanban-card')) ? prev.dataset.taskId : null;

      // keep placeholders correct
      updateEmptyState(sourceList);
      updateEmptyState(list);

      if (!MOVE_URL) {
        console.error("Kanban: MOVE_URL missing");
        return;
      }

      const payload = {
        task_id: parseInt(dragged.dataset.taskId, 10),
        to_status: toStatus,
        after_id: afterId ? parseInt(afterId, 10) : null
      };

      fetch(MOVE_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": CSRF
        },
        body: JSON.stringify(payload)
      }).then(async (res) => {
        if (!res.ok) {
          const txt = await res.text();
          throw new Error(`Save failed (${res.status}): ${txt}`);
        }
        return res.json();
      }).then((data) => {
        if (!data.ok) throw new Error("Server returned ok=false");
      }).catch(err => {
        console.error(err);
        alert("Could not save move. Please refresh. (" + err.message + ")");
      });
    }
  };

  // expose to inline handlers in the template
  window.kanban = kanban;
})();
