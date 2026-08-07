export async function runAssistant(payload) {
  const response = await fetch("/api/assistant/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Errore durante l'elaborazione.");
  }

  return response.json();
}

export async function sendChat(payload) {
  const response = await fetch("/api/chat/respond", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Errore durante la chat.");
  }

  return response.json();
}

export async function loadRecentLeads() {
  const response = await fetch("/api/leads/recent");

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Errore nel caricamento dei lead recenti.");
  }

  return response.json();
}

export async function loadChatHistory(conversationId) {
  const response = await fetch(`/api/chat/history/${conversationId}`);

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Errore nel caricamento della cronologia.");
  }

  return response.json();
}
