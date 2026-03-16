const subscribers = new Map();

window.eventBus = window.eventBus || {
  on(eventName, listener) {
    if (!subscribers.has(eventName)) {
      subscribers.set(eventName, new Set());
    }

    subscribers.get(eventName).add(listener);
    return () => this.off(eventName, listener);
  },

  off(eventName, listener) {
    subscribers.get(eventName)?.delete(listener);
  },

  emit(eventName, payload) {
    subscribers.get(eventName)?.forEach((listener) => {
      try {
        listener(payload);
      } catch (error) {
        console.error(`event bus listener failed for ${eventName}`, error);
      }
    });
  },
};

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

  if (data.event) {
    window.eventBus.emit(data.event, data);
  }
};
