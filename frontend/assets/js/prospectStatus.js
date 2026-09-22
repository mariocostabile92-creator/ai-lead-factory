const statusStorageKey = "aiLeadFactoryProspectStatus";

export const prospectStatuses = ["Da contattare", "Contattato", "Risposto"];

function readStatusMap() {
  try {
    return JSON.parse(sessionStorage.getItem(statusStorageKey) || "{}");
  } catch (_error) {
    return {};
  }
}

function writeStatusMap(statusMap) {
  sessionStorage.setItem(statusStorageKey, JSON.stringify(statusMap));
}

export function prospectKey(prospect) {
  return [
    prospect.name || "prospect",
    prospect.phone || "",
    prospect.website || "",
    prospect.maps_url || "",
    prospect.address || "",
  ].join("|");
}

export function getProspectStatus(prospect) {
  const statusMap = readStatusMap();
  return statusMap[prospectKey(prospect)] || prospect.status || prospectStatuses[0];
}

export function setProspectStatus(prospect, status) {
  const statusMap = readStatusMap();
  statusMap[prospectKey(prospect)] = status;
  writeStatusMap(statusMap);
}
