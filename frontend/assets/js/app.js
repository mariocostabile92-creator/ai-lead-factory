import { runAssistant, sendChat } from "./api.js";

const form = document.querySelector("#assistant-form");
const result = document.querySelector("#result");
const button = form.querySelector("button");
const resultModule = document.querySelector("#module");
const resultTitle = document.querySelector("#title");
const resultSummary = document.querySelector("#summary");
const resultActions = document.querySelector("#actions");
const resultOutput = document.querySelector("#output");
const resultProspects = document.querySelector("#prospects");
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

function mergeChatContext(context) {
  if (!context) {
    return;
  }

  const merged = {
    business_name: context.business_name || currentBusinessContext?.business_name || "La tua attivita",
    sector: context.sector || currentBusinessContext?.sector || context.target || "",
    location: context.location || currentBusinessContext?.location || "",
    target: context.target || currentBusinessContext?.target || context.sector || "",
    details: context.details || currentBusinessContext?.details || "",
  };

  if (merged.sector || merged.target || merged.location) {
    currentBusinessContext = merged;
    sessionStorage.setItem(businessStorageKey, JSON.stringify(currentBusinessContext));
  }
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

async function copyText(text, button) {
  try {
    await navigator.clipboard.writeText(text);
    const previous = button.textContent;
    button.textContent = "Copiato";
    setTimeout(() => {
      button.textContent = previous;
    }, 1200);
  } catch (error) {
    alert("Non riesco a copiare automaticamente. Seleziona il testo e copialo manualmente.");
  }
}

function renderProspects(prospects) {
  if (!resultProspects) {
    return;
  }

  if (!prospects || !prospects.length) {
    resultProspects.innerHTML = "";
    resultProspects.classList.add("hidden");
    return;
  }

  resultProspects.innerHTML = "";
  const title = document.createElement("h3");
  title.textContent = "Prospect pronti da lavorare";
  resultProspects.appendChild(title);

  const table = document.createElement("div");
  table.className = "prospect-table";

  prospects.slice(0, 10).forEach((prospect) => {
    const row = document.createElement("article");
    row.className = "prospect-row";

    const header = document.createElement("div");
    header.className = "prospect-header";

    const name = document.createElement("h4");
    name.textContent = prospect.name || "Prospect";
    header.appendChild(name);

    const source = document.createElement("span");
    source.textContent = prospect.source || "Fonte";
    source.className = "prospect-source";
    header.appendChild(source);
    row.appendChild(header);

    const meta = document.createElement("div");
    meta.className = "prospect-meta";
    [
      prospect.phone,
      prospect.address,
      prospect.rating,
    ].filter(Boolean).forEach((value) => {
      const item = document.createElement("span");
      item.textContent = value;
      meta.appendChild(item);
    });
    row.appendChild(meta);

    const reason = document.createElement("p");
    reason.className = "prospect-reason";
    reason.textContent = prospect.fit_reason || "Da qualificare manualmente.";
    row.appendChild(reason);

    const message = document.createElement("p");
    message.className = "prospect-message";
    message.textContent = prospect.message || "";
    row.appendChild(message);

    const actions = document.createElement("div");
    actions.className = "prospect-actions";
    const primaryLink = prospect.website || prospect.maps_url;
    if (primaryLink) {
      const anchor = document.createElement("a");
      anchor.href = primaryLink;
      anchor.target = "_blank";
      anchor.rel = "noreferrer";
      anchor.textContent = prospect.website ? "Apri sito" : "Apri Maps";
      anchor.className = "result-link";
      actions.appendChild(anchor);
    }

    const copyButton = document.createElement("button");
    copyButton.type = "button";
    copyButton.className = "copy-button";
    copyButton.textContent = "Copia messaggio";
    copyButton.addEventListener("click", () => copyText(prospect.message || "", copyButton));
    actions.appendChild(copyButton);
    row.appendChild(actions);

    table.appendChild(row);
  });

  resultProspects.appendChild(table);
  resultProspects.classList.remove("hidden");
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
    renderProspects(data.prospects);
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
    mergeChatContext(data.context);
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
