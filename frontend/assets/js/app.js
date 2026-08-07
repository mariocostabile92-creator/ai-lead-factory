import { loadChatHistory, loadRecentLeads, runAssistant, sendChat } from "./api.js";

const form = document.querySelector("#assistant-form");
const result = document.querySelector("#result");
const button = form.querySelector("button");
const resultModule = document.querySelector("#module");
const resultTitle = document.querySelector("#title");
const resultSummary = document.querySelector("#summary");
const resultActions = document.querySelector("#actions");
const resultOutput = document.querySelector("#output");
const chatForm = document.querySelector("#chat-form");
const chatInput = document.querySelector("#chat-input");
const chatSend = document.querySelector("#chat-send");
const chatMessages = document.querySelector("#chat-messages");
const chatSuggestions = document.querySelector("#chat-suggestions");
const recentLeads = document.querySelector("#recent-leads");
const conversationStorageKey = "aiLeadFactoryConversationId";
let currentConversationId = localStorage.getItem(conversationStorageKey) || "";

function getBusinessContext() {
  return {
    business_name: document.querySelector("#business-name").value.trim(),
    sector: document.querySelector("#sector").value.trim(),
    location: document.querySelector("#location").value.trim(),
    details: document.querySelector("#details").value.trim(),
  };
}

function addChatBubble(role, text) {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = text;
  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function renderChatMessage(role, text, extraClass = "") {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${role} ${extraClass}`.trim();
  bubble.textContent = text;
  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function updateSuggestions(suggestions) {
  chatSuggestions.innerHTML = "";
  suggestions.forEach((suggestion) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "chat-chip";
    button.textContent = suggestion;
    button.addEventListener("click", () => {
      chatInput.value = suggestion;
      chatInput.focus();
    });
    chatSuggestions.appendChild(button);
  });
}

function renderRecentLeads(items) {
  if (!items.length) {
    recentLeads.innerHTML = `
      <article class="panel recent-card">
        <span class="card-label">In attesa</span>
        <h3>Nessun lead ancora salvato</h3>
        <p>Genera il primo pacchetto e vedrai comparire qui i dettagli dell'attivita salvata.</p>
      </article>
    `;
    return;
  }

  recentLeads.innerHTML = "";
  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "panel recent-card";

    const badge = document.createElement("span");
    badge.className = "card-label";
    badge.textContent = item.module;

    const title = document.createElement("h3");
    title.textContent = item.business_name;

    const details = document.createElement("p");
    details.textContent = `${item.sector} - ${item.location}`;

    const summary = document.createElement("p");
    summary.textContent = item.title;

    card.appendChild(badge);
    card.appendChild(title);
    card.appendChild(details);
    card.appendChild(summary);
    recentLeads.appendChild(card);
  });
}

async function refreshRecentLeads() {
  try {
    const items = await loadRecentLeads();
    renderRecentLeads(items);
  } catch (error) {
    renderRecentLeads([]);
  }
}

async function restoreChatHistory() {
  if (!currentConversationId) {
    return;
  }

  try {
    const history = await loadChatHistory(currentConversationId);
    chatMessages.innerHTML = "";
    history.messages.forEach((message) => {
      if (message.role === "assistant" && message.content.includes("CTA: ")) {
        const [replyText, ctaText] = message.content.split("\n\nCTA: ");
        renderChatMessage("bot", replyText.trim());
        if (ctaText) {
          renderChatMessage("cta", ctaText.trim(), "cta");
        }
        return;
      }

      renderChatMessage(message.role === "assistant" ? "bot" : "user", message.content);
    });
  } catch (error) {
    chatMessages.innerHTML = "";
  }
}

function attachPromptButtons() {
  document.querySelectorAll("[data-chat-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      chatInput.value = button.dataset.chatPrompt || "";
      chatInput.focus();
    });
  });
}

attachPromptButtons();
refreshRecentLeads();
restoreChatHistory();

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  button.disabled = true;
  button.textContent = "Sto lavorando...";

  const payload = { goal: document.querySelector("#goal").value.trim(), business: getBusinessContext() };

  try {
    const data = await runAssistant(payload);
    resultModule.textContent = data.module;
    resultTitle.textContent = data.title;
    resultSummary.textContent = data.summary;
    resultActions.innerHTML = "";
    data.actions.forEach((action) => {
      const item = document.createElement("li");
      item.textContent = action;
      resultActions.appendChild(item);
    });
    resultOutput.textContent = data.output;
    result.classList.remove("hidden");
    refreshRecentLeads();
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Avvia il lavoro";
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) {
    return;
  }

  addChatBubble("user", message);
  chatInput.value = "";
  chatSend.disabled = true;
  chatSend.textContent = "Sto pensando...";

  try {
    const data = await sendChat({
      message,
      business: getBusinessContext(),
      conversation_id: currentConversationId || null,
    });
    currentConversationId = data.conversation_id;
    localStorage.setItem(conversationStorageKey, currentConversationId);
    renderChatMessage("bot", data.reply);
    renderChatMessage("cta", data.cta, "cta");
    updateSuggestions(data.suggestions);
  } catch (error) {
    renderChatMessage("bot", error.message);
  } finally {
    chatSend.disabled = false;
    chatSend.textContent = "Invia";
    chatInput.focus();
  }
});
