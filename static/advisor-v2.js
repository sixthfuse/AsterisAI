const form = document.querySelector("#chat-form");
const input = document.querySelector("#question");
const messages = document.querySelector("#messages");
const send = document.querySelector("#send");
const clear = document.querySelector("#clear");
const status = document.querySelector("#status");

function makeSessionId() {
  return crypto.randomUUID ? crypto.randomUUID() : `v2-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

let sessionId = makeSessionId();
let runtimeBuild = "unknown";

fetch("/advisor-v2/diagnostics", { cache: "no-store" })
  .then((response) => response.ok ? response.json() : null)
  .then((data) => {
    if (!data) return;
    runtimeBuild = data.build_fingerprint || "unknown";
    status.textContent = `V2 build ${runtimeBuild} · ready`;
  })
  .catch(() => {});

function addMessage(role, text, diagnostics) {
  const article = document.createElement("article");
  article.className = role;
  const body = document.createElement("p");
  body.textContent = text;
  article.appendChild(body);
  if (diagnostics) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "Developer trace";
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(diagnostics, null, 2);
    details.append(summary, pre);
    article.appendChild(details);
  }
  messages.appendChild(article);
  article.scrollIntoView({ behavior: "smooth", block: "end" });
  return article;
}

async function ask(question) {
  addMessage("user", question);
  send.disabled = true;
  clear.disabled = true;
  status.textContent = "Checking structured academic data…";
  const waiting = addMessage("assistant waiting", "Working…");
  try {
    const requestId = `browser-${makeSessionId()}`;
    const response = await fetch("/advisor-v2", {
      method: "POST",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        "X-Session-ID": sessionId,
        "X-Request-ID": requestId,
      },
      body: JSON.stringify({ question }),
    });
    const data = await response.json().catch(() => ({}));
    waiting.remove();
    if (!response.ok) throw new Error(data.detail || "The v2 advisor could not answer.");
    addMessage("assistant", data.answer, data.observability);
    const build = data.observability?.runtime?.build_fingerprint || runtimeBuild;
    status.textContent = `V2 build ${build} · turn ${data.conversation_state.turn_index} · ${data.verification.status}`;
  } catch (error) {
    waiting.remove();
    addMessage("assistant error", error.message || "The v2 advisor is unavailable.");
    status.textContent = "Request failed.";
  } finally {
    send.disabled = false;
    clear.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question || send.disabled) return;
  input.value = "";
  ask(question);
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

clear.addEventListener("click", () => {
  sessionId = makeSessionId();
  messages.querySelectorAll("article:not(:first-child)").forEach((node) => node.remove());
  status.textContent = "New isolated session started.";
  input.focus();
});
