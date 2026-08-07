import { runAssistant, sendChat } from "./api.js";

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

function attachPromptButtons() {
  document.querySelectorAll("[data-chat-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      chatInput.value = button.dataset.chatPrompt || "";
      chatInput.focus();
    });
  });
}

attachPromptButtons();

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
    });
    addChatBubble("bot", data.reply);
    updateSuggestions(data.suggestions);
  } catch (error) {
    addChatBubble("bot", error.message);
  } finally {
    chatSend.disabled = false;
    chatSend.textContent = "Invia";
    chatInput.focus();
  }
});
