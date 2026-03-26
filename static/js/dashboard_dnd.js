/* =====================================================
   LADY LINUX - DASHBOARD DRAG AND DROP
   Depends on: SortableJS (loaded before this script)
   ===================================================== */

(function initDashboardDnD() {
  const STORAGE_KEY = "lady-dashboard-order";
  const container = document.getElementById("dashboard-sortable");
  if (!container || typeof Sortable === "undefined") return;

  // Restore saved order before first paint
  function restoreOrder() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return;
    try {
      const order = JSON.parse(saved); // e.g. ["metric-cards", "ai-console", ...]
      order.forEach((widgetId) => {
        const el = container.querySelector(`[data-widget-id="${widgetId}"]`);
        if (el) container.appendChild(el); // move to end in order
      });
    } catch (e) {
      console.warn("DnD: could not restore order", e);
    }
  }

  restoreOrder();

  // Initialize SortableJS
  Sortable.create(container, {
    animation: 180,
    handle: ".ll-drag-handle",
    ghostClass: "ll-drag-ghost",
    chosenClass: "ll-drag-chosen",
    dragClass: "ll-dragging",
    onEnd() {
      const order = [...container.querySelectorAll("[data-widget-id]")]
        .map((el) => el.getAttribute("data-widget-id"));
      localStorage.setItem(STORAGE_KEY, JSON.stringify(order));
    },
  });
})();
