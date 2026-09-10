const form = document.querySelector("#chat-form");
const questionInput = document.querySelector("#question");
const messages = document.querySelector("#messages");
const sendButton = document.querySelector("#send");
const statusText = document.querySelector("#status");
const clearButton = document.querySelector("#clear");
const conversation = [];
let conversationState = null;

function browserSessionId() {
  try {
    const stored = typeof sessionStorage !== "undefined"
      ? sessionStorage.getItem("asteris-session-id")
      : null;
    if (stored) return stored;
    const generated = typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `local-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.setItem("asteris-session-id", generated);
    }
    return generated;
  } catch (_error) {
    return `local-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }
}

const sessionId = browserSessionId();

function sanitizeStudentText(value) {
  const lines = String(value || "").split(/\r?\n/);
  return lines.filter((line) => {
    const text = line.trim();
    if (/^(?:assistant\s+to=)?functions?\.[A-Za-z_][\w.]*/i.test(text)) return false;
    if (/^\{.*\}$/.test(text) && /"(?:query|credential|credential_name|program_id|course_id|tool_choice)"\s*:/i.test(text)) return false;
    if (/^(?:tool|function)[ _-]?(?:call|result|output)\s*:/i.test(text)) return false;
    return true;
  }).join("\n").replace(/\n{3,}/g, "\n\n").trim();
}

function renderSafeText(container, text) {
  text = sanitizeStudentText(text);
  text = text.replace(/^#{1,6}\s+/gm, "");
  const parts = text.split(/(\[[^\]\n]+\]\\?\(https?:\/\/[^\s)]+\)|https?:\/\/[^\s<>]+|\*\*[^*]+\*\*)/g);
  parts.forEach((part) => {
    const markdownLink = part.match(/^\[([^\]\n]+)\]\\?\((https?:\/\/[^\s)]+)\)$/);
    const bareLink = part.match(/^https?:\/\/[^\s<>]+$/);
    if (markdownLink || bareLink) {
      const anchor = document.createElement("a");
      anchor.href = markdownLink ? markdownLink[2] : part;
      anchor.textContent = markdownLink ? markdownLink[1] : part;
      anchor.target = "_blank";
      anchor.rel = "noopener noreferrer";
      container.appendChild(anchor);
    } else if (part.startsWith("**") && part.endsWith("**")) {
      const strong = document.createElement("strong");
      strong.textContent = part.slice(2, -2);
      container.appendChild(strong);
    } else {
      container.appendChild(document.createTextNode(part));
    }
  });
}

function verificationLabel(verification) {
  if (!verification) return "";
  if (!verification.exact_count_available || !verification.count) {
    return "✓ Verified against academic data";
  }
  const noun = verification.kind === "requirement" ? "requirement" : "fact";
  return `✓ ${verification.count} academic ${noun}${verification.count === 1 ? "" : "s"} checked`;
}

function addMessage(role, text, verification = null) {
  const article = document.createElement("article");
  article.className = `message ${role === "user" ? "user-message" : "advisor-message"}`;

  if (role === "assistant") {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "A";
    avatar.setAttribute("aria-hidden", "true");
    article.appendChild(avatar);
  }

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  const paragraph = document.createElement("p");
  renderSafeText(paragraph, text);
  bubble.appendChild(paragraph);

  const label = verificationLabel(verification);
  if (label) {
    const verification = document.createElement("div");
    verification.className = "verification";
    verification.textContent = label;
    bubble.appendChild(verification);
  }

  article.appendChild(bubble);
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

function payloadFor(question) {
  return {
    question,
    conversation: conversation.slice(-10),
    conversation_state: conversationState,
  };
}

async function askAdvisor(question) {
  addMessage("user", question);
  const priorConversation = conversation.slice();
  conversation.push({ role: "user", content: question });
  sendButton.disabled = true;
  clearButton.disabled = true;
  statusText.textContent = "Asteris is checking academic rules…";
  const waiting = addMessage("assistant", "Checking verified Asteris data…");
  waiting.classList.add("typing");

  try {
    const payload = payloadFor(question);
    payload.conversation = priorConversation.slice(-10);
    const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    const timeout = controller && typeof setTimeout !== "undefined"
      ? setTimeout(() => controller.abort(), 35000)
      : null;
    const response = await fetch("/advisor", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Session-ID": sessionId },
      body: JSON.stringify(payload),
      ...(controller ? { signal: controller.signal } : {}),
    });
    if (timeout && typeof clearTimeout !== "undefined") clearTimeout(timeout);
    const data = await response.json().catch(() => ({}));
    waiting.remove();
    if (!response.ok) throw new Error(data.detail || "The advisor could not answer.");
    conversationState = data.conversation_state || null;
    addMessage("assistant", data.answer, data.verification || null);
    conversation.push({ role: "assistant", content: data.answer });
    statusText.textContent = "Answer ready. Confirm important decisions with your institution.";
  } catch (error) {
    waiting.remove();
    const safeMessage = error.name === "AbortError"
      ? "The request took too long. Your conversation is still here; please try again."
      : (error.message || "Asteris is temporarily unavailable.");
    const message = addMessage("assistant", safeMessage);
    message.classList.add("error");
    statusText.textContent = "The request was not completed.";
  } finally {
    sendButton.disabled = false;
    clearButton.disabled = false;
    questionInput.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question || sendButton.disabled) return;
  questionInput.value = "";
  askAdvisor(question);
});

questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

document.querySelectorAll(".suggestions button").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.textContent;
    questionInput.focus();
  });
});

clearButton.addEventListener("click", () => {
  conversation.length = 0;
  conversationState = null;
  messages.querySelectorAll(".message:not(:first-child)").forEach((message) => message.remove());
  statusText.textContent = "New conversation started.";
  questionInput.focus();
});
