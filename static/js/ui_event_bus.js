const socket = new WebSocket("ws://localhost:8000/ws/ui");

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.event === "theme_change") {
    if (typeof window.applyTheme === "function" && data.theme) {
      window.applyTheme(data.theme, { remote: false });
    }

    const css = data.css || {};
    Object.keys(css).forEach((key) => {
      document.documentElement.style.setProperty(key, css[key]);
    });
  }
};
