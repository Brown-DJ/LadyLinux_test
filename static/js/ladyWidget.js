/* =====================================================
   LADY LINUX - FLOATING MINI CONSOLE WIDGET
   ===================================================== */

/* Widget page guard: never show on full console page */
if (window.location.pathname === "/") {
  const widget = document.getElementById("lady-widget");
  if (widget) {
    widget.style.display = "none";
  }
}

/* Widget element bindings */
const launcher = document.getElementById("lady-launcher");
const consoleBox = document.getElementById("lady-console");
const closeBtn = document.getElementById("lady-close");
const input = document.getElementById("lady-input");
const output = document.getElementById("lady-response");

/* Widget toggle behavior */
if (launcher && consoleBox) {
  launcher.addEventListener("click", () => {
    consoleBox.style.display = consoleBox.style.display === "flex" ? "none" : "flex";
  });
}

if (closeBtn && consoleBox) {
  closeBtn.addEventListener("click", () => {
    consoleBox.style.display = "none";
  });
}

/* Widget chat behavior: reuse shared chat.js sendPrompt + parser pipeline */
if (input && output) {
  input.addEventListener("keydown", async (e) => {
    if (e.key !== "Enter") return;

    const prompt = input.value.trim();
    if (!prompt) return;

    input.value = "";

    const userMessage = document.createElement("div");
    userMessage.className = "lady-message lady-message-user";
    userMessage.textContent = `You: ${prompt}`;
    output.appendChild(userMessage);

    try {
      const sendPrompt = window.sendPrompt;
      if (typeof sendPrompt !== "function") {
        throw new Error("Chat transport unavailable");
      }

      const reply = await sendPrompt(prompt);

      if (typeof window.processAssistantReply === "function") {
        window.processAssistantReply(prompt, reply);
      }

      const replyMessage = document.createElement("div");
      replyMessage.className = "lady-message";
      replyMessage.textContent = `Lady Linux: ${reply}`;
      output.appendChild(replyMessage);
    } catch (err) {
      const errMessage = document.createElement("div");
      errMessage.className = "lady-message";
      errMessage.textContent = `Lady Linux: Request failed - ${err.message}`;
      output.appendChild(errMessage);
    }

    output.scrollTop = output.scrollHeight;
  });
}
