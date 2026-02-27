/* =====================================================
   LADY LINUX – MAIN CONTROLLER
   ===================================================== */

document.addEventListener("DOMContentLoaded", async () => {

    try {
        // 1. Load theme system FIRST (affects UI)
        await initThemes();

        // 2. Load navigation
       await loadNavigation();

        // 3. Initialize AI / Chat system
        initChat();

    } catch (err) {
        console.error("Initialization error:", err);
    }

});

/* =====================================================
   NAVIGATION LOADER
   ===================================================== */



async function loadNavigation() {
    const response = await fetch("/static/nav.html"); // ✅ LOCAL
    const navMarkup = await response.text();

    const container = document.querySelector("[data-nav-target]");
    if (!container) return;

    container.innerHTML = navMarkup;
}