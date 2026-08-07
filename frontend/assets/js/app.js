import { runAssistant, sendChat } from "./api.js";

const form = document.querySelector("#assistant-form");
const result = document.querySelector("#result");
const button = form.querySelector("button");
const resultModule = document.querySelector("#module");
const resultTitle = document.querySelector("#title");
const resultSummary = document.querySelector("#summary");
const resultActions = document.querySelector("#actions");
const resultOutput = document.querySelector("#output");
const resultResearch = document.querySelector("#research");
const resultLinks = document.querySelector("#links");
const chatForm = document.querySelector("#chat-form");
const chatInput = document.querySelector("#chat-input");
const chatSend = document.querySelector("#chat-send");
const chatMessages = document.querySelector("#chat-messages");
const chatSuggestions = document.querySelector("#chat-suggestions");
const recentLeads = document.querySelector("#recent-leads");
const conversationStorageKey = "aiLeadFactoryConversationId";
const businessStorageKey = "aiLeadFactoryBusinessContext";
localStorage.removeItem(conversationStorageKey);
localStorage.removeItem(businessStorageKey);
let currentConversationId = "";
let currentBusinessContext = JSON.parse(sessionStorage.getItem(businessStorageKey) || "null");

function resetChatForBusiness(business) {
  currentConversationId = "";
  currentBusinessContext = business;
  sessionStorage.setItem(businessStorageKey, JSON.stringify(currentBusinessContext));
  chatMessages.innerHTML = "";
  renderChatMessage("bot", `Ok, riparto da questo contesto: ${business.business_name}, ${business.sector}, zona ${business.location}, target ${business.target}. Dimmi se vuoi cercare prospect, scrivere messaggi o qualificare una lista.`);
  updateSuggestions([
    "Cerca aziende target reali",
    "Scrivi email per questi target",
    "Crea messaggio LinkedIn",
  ]);
}

function getBusinessContext() {
  const business_name = document.querySelector("#business-name").value.trim();
  const sector = document.querySelector("#sector").value.trim();
  const location = document.querySelector("#location").value.trim();
  const target = document.querySelector("#target").value.trim();
  const details = document.querySelector("#details").value.trim();

  if (!business_name && !sector && !location && !target && !details) {
    return null;
  }

  if (!business_name || !sector || !location || !target) {
    return null;
  }

  return {
    business_name,
    sector,
    location,
    target,
    details,
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
  const normalizedSuggestions = [...suggestions];
  if (!normalizedSuggestions.some((suggestion) => suggestion.toLowerCase().includes("ricerca"))) {
    normalizedSuggestions.push("Cerca aziende target reali");
  }

  chatSuggestions.innerHTML = "";
  normalizedSuggestions.slice(0, 4).forEach((suggestion) => {
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

function renderResearch(items) {
  if (!resultResearch) {
    return;
  }

  if (!items || !items.length) {
    resultResearch.innerHTML = "";
    resultResearch.classList.add("hidden");
    return;
  }

  resultResearch.innerHTML = "";
  const title = document.createElement("h3");
  title.textContent = "Ricerca reale";
  resultResearch.appendChild(title);

  const list = document.createElement("ul");
  items.forEach((item) => {
    const entry = document.createElement("li");
    entry.textContent = item;
    list.appendChild(entry);
  });
  resultResearch.appendChild(list);
  resultResearch.classList.remove("hidden");
}

function renderLinks(links) {
  if (!resultLinks) {
    return;
  }

  if (!links || !links.length) {
    resultLinks.innerHTML = "";
    resultLinks.classList.add("hidden");
    return;
  }

  resultLinks.innerHTML = "";
  const title = document.createElement("h3");
  title.textContent = "Link pronti";
  resultLinks.appendChild(title);

  const list = document.createElement("div");
  list.className = "link-list";
  links.forEach((link) => {
    const anchor = document.createElement("a");
    anchor.href = link;
    anchor.target = "_blank";
    anchor.rel = "noreferrer";
    anchor.textContent = "Apri ricerca";
    anchor.className = "result-link";
    list.appendChild(anchor);
  });
  resultLinks.appendChild(list);
  resultLinks.classList.remove("hidden");
}

function renderChatLinks(links) {
  if (!links || !links.length) {
    return;
  }

  const bubble = document.createElement("div");
  bubble.className = "chat-bubble cta";

  const label = document.createElement("strong");
  label.textContent = "Link utili:";
  bubble.appendChild(label);

  const list = document.createElement("div");
  list.className = "link-list chat-link-list";
  links.forEach((link) => {
    const anchor = document.createElement("a");
    anchor.href = link;
    anchor.target = "_blank";
    anchor.rel = "noreferrer";
    anchor.textContent = "Apri";
    anchor.className = "result-link";
    list.appendChild(anchor);
  });
  bubble.appendChild(list);
  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function renderDraft(title, draft) {
  if (!draft) {
    return;
  }

  const bubble = document.createElement("div");
  bubble.className = "chat-bubble bot";

  const heading = document.createElement("strong");
  heading.textContent = title || "Bozza pronta";
  bubble.appendChild(heading);

  const body = document.createElement("pre");
  body.textContent = draft;
  body.className = "chat-draft";
  bubble.appendChild(body);

  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function renderRecentLeads(items) {
  recentLeads.innerHTML = `
    <article class="panel recent-card">
      <span class="card-label">Privacy</span>
      <h3>Nessun dato pubblico salvato</h3>
      <p>Ogni visitatore lavora nella propria sessione. Senza login non mostriamo lead o chat di altre persone.</p>
    </article>
  `;
}

async function refreshRecentLeads() {
  renderRecentLeads([]);
}

async function restoreChatHistory() {
  currentConversationId = "";
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
  const business = getBusinessContext();
  if (!business) {
    alert("Compila nome attività, settore, zona e target da cercare.");
    return;
  }

  button.disabled = true;
  button.textContent = "Sto lavorando...";

  const payload = { goal: document.querySelector("#goal").value.trim(), business };

  try {
    const data = await runAssistant(payload);
    resetChatForBusiness(payload.business);
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
    renderResearch(data.research);
    renderLinks(data.search_links);
    result.classList.remove("hidden");
    refreshRecentLeads();
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Cerca prospect e crea messaggi";
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
    const business = getBusinessContext() || currentBusinessContext;
    if (!business) {
      renderChatMessage("bot", "Se vuoi, scrivimi comunque cosa ti serve: la chat può partire anche senza i dati aziendali. Se vuoi un risultato più preciso, compila i campi sopra.");
    }
    const data = await sendChat({
      message,
      business,
      conversation_id: currentConversationId || null,
    });
    currentConversationId = data.conversation_id;
    renderChatMessage("bot", data.reply);
    renderChatMessage("cta", data.cta, "cta");
    if (data.follow_up_question) {
      renderChatMessage("bot", data.follow_up_question);
    }
    if (data.research && data.research.length) {
      renderChatMessage("cta", `Ricerca: ${data.research.join(" | ")}`, "cta");
    }
    renderChatLinks(data.search_links);
    renderDraft(data.draft_title, data.draft);
    updateSuggestions(data.suggestions);
  } catch (error) {
    renderChatMessage("bot", error.message);
  } finally {
    chatSend.disabled = false;
    chatSend.textContent = "Invia";
    chatInput.focus();
  }
});
