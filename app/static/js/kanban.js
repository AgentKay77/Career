// Drag-and-drop Kanban for actions board. No external deps — plain HTML5 DnD.
// Status change is POSTed via fetch; server returns the updated card HTML
// which we drop into the destination column.

(function () {
  const board = document.getElementById("kanban");
  if (!board) return;

  let dragging = null;

  board.addEventListener("dragstart", (e) => {
    const card = e.target.closest(".kanban-card");
    if (!card) return;
    dragging = card;
    card.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", card.dataset.id);
  });

  board.addEventListener("dragend", () => {
    if (dragging) {
      dragging.classList.remove("dragging");
      dragging = null;
    }
    board.querySelectorAll(".dragging-over").forEach((c) => c.classList.remove("dragging-over"));
  });

  board.querySelectorAll(".kanban-col").forEach((col) => {
    col.addEventListener("dragover", (e) => {
      e.preventDefault();
      col.classList.add("dragging-over");
    });
    col.addEventListener("dragleave", () => col.classList.remove("dragging-over"));
    col.addEventListener("drop", async (e) => {
      e.preventDefault();
      col.classList.remove("dragging-over");
      const id = e.dataTransfer.getData("text/plain") || (dragging && dragging.dataset.id);
      const newStatus = col.dataset.status;
      if (!id || !newStatus) return;
      const card = board.querySelector(`.kanban-card[data-id="${id}"]`);
      if (!card) return;
      const oldStatus = card.dataset.status;
      if (oldStatus === newStatus) return;

      col.appendChild(card);
      card.dataset.status = newStatus;

      const fd = new FormData();
      fd.set("csrf_token", CSRF_TOKEN);
      fd.set("status", newStatus);
      try {
        const resp = await fetch(CHANGE_STATUS_URL(id), {
          method: "POST",
          body: fd,
          headers: { "HX-Request": "true" },
        });
        if (resp.ok) {
          const html = await resp.text();
          const tmp = document.createElement("div");
          tmp.innerHTML = html.trim();
          const fresh = tmp.firstElementChild;
          if (fresh) card.replaceWith(fresh);
        }
      } catch (err) {
        console.error(err);
        // roll back DOM placement on error
        document.getElementById(`col-${oldStatus}`)?.appendChild(card);
        card.dataset.status = oldStatus;
      }
    });
  });
})();
