export function escapeCsvValue(value) {
  const normalizedValue = String(value || "").replace(/\r?\n|\r/g, " ").trim();
  return `"${normalizedValue.replace(/"/g, '""')}"`;
}

export function buildProspectsCsv(prospects) {
  const headers = [
    "Nome azienda",
    "Settore/Categoria",
    "Telefono",
    "Sito",
    "Google Maps",
    "Indirizzo",
    "Rating",
    "Fonte",
    "Target score",
    "Motivo target",
    "Oggetto email",
    "Email",
    "WhatsApp",
    "LinkedIn",
    "Follow-up",
    "Stato prospect",
  ];

  const rows = prospects.slice(0, 50).map((prospect) => [
    prospect.name,
    prospect.category,
    prospect.phone,
    prospect.website,
    prospect.maps_url,
    prospect.address,
    prospect.rating,
    prospect.source,
    prospect.target_score ? `${prospect.target_score}/10` : "",
    prospect.score_reason || prospect.fit_reason,
    prospect.email_subject,
    prospect.email_body || prospect.message,
    prospect.whatsapp_message,
    prospect.linkedin_message,
    prospect.follow_up_message,
    prospect.status,
  ]);

  return [
    headers.map(escapeCsvValue).join(","),
    ...rows.map((row) => row.map(escapeCsvValue).join(",")),
  ].join("\n");
}

export function downloadProspectsCsv(prospects) {
  const csv = buildProspectsCsv(prospects);
  const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  const date = new Date().toISOString().slice(0, 10);
  anchor.href = url;
  anchor.download = `ai-lead-factory-sales-pack-${date}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
