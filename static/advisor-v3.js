const form = document.querySelector("#chat-form");
const input = document.querySelector("#question");
const messages = document.querySelector("#messages");
const send = document.querySelector("#send");
const clear = document.querySelector("#clear");
const status = document.querySelector("#status");

function makeSessionId() {
  return crypto.randomUUID ? crypto.randomUUID() : `v3-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

let sessionId = makeSessionId();
let runtimeBuild = "unknown";

fetch("/advisor-v3/diagnostics", { cache: "no-store" })
  .then((response) => response.ok ? response.json() : null)
  .then((data) => {
    if (!data) return;
    runtimeBuild = data.build_fingerprint || "unknown";
    status.textContent = `V3 build ${runtimeBuild} · ready`;
  })
  .catch(() => {});

function addMessage(role, text, trace) {
  const article = document.createElement("article");
  article.className = role;
  const body = document.createElement("p");
  body.textContent = text;
  article.appendChild(body);
  if (trace) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "Developer trace";
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(trace, null, 2);
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
  status.textContent = "Planning and checking academic evidence…";
  const waiting = addMessage("assistant waiting", "Working…");
  try {
    const response = await fetch("/advisor-v3", {
      method: "POST",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        "X-Session-ID": sessionId,
        "X-Request-ID": `browser-${makeSessionId()}`,
      },
      body: JSON.stringify({ question }),
    });
    const data = await response.json().catch(() => ({}));
    waiting.remove();
    if (!response.ok) throw new Error(data.detail || "The v3 advisor could not answer.");
    addMessage("assistant", data.answer, data.developer_trace);
    const build = data.developer_trace?.build_fingerprint || runtimeBuild;
    status.textContent = `V3 build ${build} · turn ${data.conversation_state.turn_index} · ${data.verification.status}`;
  } catch (error) {
    waiting.remove();
    addMessage("assistant error", error.message || "The v3 advisor is unavailable.");
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
  status.textContent = "New isolated v3 session started.";
  input.focus();
});
