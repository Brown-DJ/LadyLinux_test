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
    const response = await fetch("https://brown-dj.github.io/LadyLinux_test/templates/nav.html");
    const navMarkup = await response.text();

    const container = document.querySelector("[data-nav-target]");
    if (!container) return;

    container.innerHTML = navMarkup;

    // Get current page filename
    const currentPage = window.location.pathname.split("/").pop() || "index.html";

    // Highlight matching link
    container.querySelectorAll(".nav-link").forEach(link => {
        const href = link.getAttribute("href");
        if (href === currentPage || (currentPage === "" && href === "index.html")) {
            link.classList.add("active");
        }
    });
}
