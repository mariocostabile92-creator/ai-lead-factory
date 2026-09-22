import { runAssistant, sendChat } from "./api.js";
import { downloadProspectsCsv } from "./csv.js";
import { getProspectStatus, prospectStatuses, setProspectStatus } from "./prospectStatus.js";

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

function valueOrUnavailable(value) {
  return value || "Non disponibile";
}

function prospectsWithCurrentStatuses(prospects) {
  return prospects.map((prospect) => ({
    ...prospect,
    status: getProspectStatus(prospect),
  }));
}

function countProspectScores(prospects) {
  return prospects.reduce(
    (counts, prospect) => {
      const score = Number(prospect.target_score || 0);
      if (score >= 8) {
        counts.strong += 1;
      } else if (score >= 6) {
        counts.medium += 1;
      } else {
        counts.review += 1;
      }
      return counts;
    },
    { strong: 0, medium: 0, review: 0 },
  );
}

function appendInfo(container, label, value, link = "") {
  const item = document.createElement("div");
  item.className = "sales-pack-info";

  const labelElement = document.createElement("span");
  labelElement.textContent = label;
  item.appendChild(labelElement);

  if (link) {
    const anchor = document.createElement("a");
    anchor.href = link;
    anchor.target = "_blank";
    anchor.rel = "noreferrer";
    anchor.textContent = valueOrUnavailable(value);
    item.appendChild(anchor);
  } else {
    const strong = document.createElement("strong");
    strong.textContent = valueOrUnavailable(value);
    item.appendChild(strong);
  }

  container.appendChild(item);
}

function createCopyButton(text, label = "Copia") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "copy-button";
  button.textContent = label;
  button.addEventListener("click", () => copyText(text || "", button));
  return button;
}

function renderMessageBlock(title, text, extraAction = null) {
  const block = document.createElement("article");
  block.className = "message-pack";

  const header = document.createElement("div");
  header.className = "message-pack-header";
  const heading = document.createElement("h5");
  heading.textContent = title;
  header.appendChild(heading);
  header.appendChild(createCopyButton(text));
  if (extraAction) {
    header.appendChild(extraAction);
  }
  block.appendChild(header);

  const body = document.createElement("p");
  body.textContent = text || "Non disponibile";
  block.appendChild(body);
  return block;
}

function renderSalesPack(details, prospect) {
  const pack = document.createElement("div");
  pack.className = "sales-pack";

  const prospectSection = document.createElement("section");
  prospectSection.className = "sales-pack-section";
  prospectSection.innerHTML = "<h4>Prospect</h4>";
  appendInfo(prospectSection, "Nome", prospect.name);
  appendInfo(prospectSection, "Categoria", prospect.category);
  appendInfo(prospectSection, "Fonte", prospect.source);
  appendInfo(prospectSection, "Rating", prospect.rating);
  pack.appendChild(prospectSection);

  const targetSection = document.createElement("section");
  targetSection.className = "sales-pack-section";
  targetSection.innerHTML = "<h4>Perché è un buon target</h4>";
  const score = document.createElement("strong");
  score.className = "score-line";
  score.textContent = `Buon target: ${prospect.target_score || "?"}/10`;
  targetSection.appendChild(score);
  const reason = document.createElement("p");
  reason.textContent = prospect.score_reason || prospect.fit_reason || "Da qualificare manualmente.";
  targetSection.appendChild(reason);
  const contactReason = document.createElement("p");
  contactReason.textContent = prospect.contact_reason || "Da contattare dopo verifica manuale.";
  targetSection.appendChild(contactReason);
  pack.appendChild(targetSection);

  const contactSection = document.createElement("section");
  contactSection.className = "sales-pack-section";
  contactSection.innerHTML = "<h4>Contatti</h4>";
  appendInfo(contactSection, "Telefono", prospect.phone);
  appendInfo(contactSection, "Sito", prospect.website, prospect.website);
  appendInfo(contactSection, "Google Maps", prospect.maps_url, prospect.maps_url);
  appendInfo(contactSection, "Indirizzo", prospect.address);
  pack.appendChild(contactSection);

  const emailText = `Oggetto: ${prospect.email_subject || ""}\n\n${prospect.email_body || prospect.message || ""}`.trim();
  const subjectButton = createCopyButton(prospect.email_subject || "", "Copia oggetto");
  pack.appendChild(renderMessageBlock("Email", emailText, subjectButton));
  pack.appendChild(renderMessageBlock("WhatsApp", prospect.whatsapp_message));
  pack.appendChild(renderMessageBlock("LinkedIn", prospect.linkedin_message));
  pack.appendChild(renderMessageBlock("Follow-up", prospect.follow_up_message));

  const nextAction = document.createElement("section");
  nextAction.className = "sales-pack-section next-action";
  nextAction.innerHTML = "<h4>Prossima azione</h4>";
  const actionText = document.createElement("p");
  actionText.textContent = "Verifica il prospect, copia il messaggio più adatto e aggiorna lo stato dopo il primo contatto.";
  nextAction.appendChild(actionText);
  pack.appendChild(nextAction);

  details.appendChild(pack);
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

  const enrichedProspects = prospectsWithCurrentStatuses(prospects);
  const counts = countProspectScores(enrichedProspects);
  resultProspects.innerHTML = "";
  const header = document.createElement("div");
  header.className = "prospects-header";

  const titleBlock = document.createElement("div");
  const title = document.createElement("h3");
  title.textContent = `${enrichedProspects.length} prospect trovati`;
  titleBlock.appendChild(title);

  const subtitle = document.createElement("p");
  subtitle.textContent = `${Math.min(enrichedProspects.length, 50)} contatti esportabili con Sales Pack completo.`;
  titleBlock.appendChild(subtitle);
  header.appendChild(titleBlock);

  const exportButton = document.createElement("button");
  exportButton.type = "button";
  exportButton.className = "export-button";
  exportButton.textContent = "Scarica CSV";
  exportButton.addEventListener("click", () => downloadProspectsCsv(prospectsWithCurrentStatuses(prospects)));
  header.appendChild(exportButton);

  resultProspects.appendChild(header);

  const summary = document.createElement("div");
  summary.className = "prospect-summary";
  [
    ["Target forti", counts.strong],
    ["Target medi", counts.medium],
    ["Da valutare", counts.review],
  ].forEach(([label, value]) => {
    const item = document.createElement("div");
    item.innerHTML = `<strong>${value}</strong><span>${label}</span>`;
    summary.appendChild(item);
  });
  resultProspects.appendChild(summary);

  const table = document.createElement("div");
  table.className = "prospect-table";

  enrichedProspects.slice(0, 10).forEach((prospect) => {
    const row = document.createElement("article");
    row.className = "prospect-row";

    const header = document.createElement("div");
    header.className = "prospect-header";

    const name = document.createElement("h4");
    name.textContent = prospect.name || "Prospect";
    header.appendChild(name);

    const source = document.createElement("span");
    source.textContent = `${prospect.target_score || "?"}/10`;
    source.className = "prospect-source score-badge";
    header.appendChild(source);
    row.appendChild(header);

    const meta = document.createElement("div");
    meta.className = "prospect-meta";
    [
      prospect.score_label,
      prospect.category,
      prospect.phone,
      prospect.website ? "Sito disponibile" : "",
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

    const statusLabel = document.createElement("label");
    statusLabel.className = "status-control";
    statusLabel.textContent = "Stato";
    const statusSelect = document.createElement("select");
    prospectStatuses.forEach((status) => {
      const option = document.createElement("option");
      option.value = status;
      option.textContent = status;
      option.selected = status === prospect.status;
      statusSelect.appendChild(option);
    });
    statusSelect.addEventListener("change", () => {
      setProspectStatus(prospect, statusSelect.value);
      prospect.status = statusSelect.value;
    });
    statusLabel.appendChild(statusSelect);
    row.appendChild(statusLabel);

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

    actions.appendChild(createCopyButton(prospect.email_body || prospect.message || "", "Copia email"));
    row.appendChild(actions);

    const details = document.createElement("details");
    details.className = "sales-pack-details";
    const summary = document.createElement("summary");
    summary.textContent = "Apri Sales Pack";
    details.appendChild(summary);
    renderSalesPack(details, prospect);
    row.appendChild(details);

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
    resultOutput.classList.add("hidden");
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
