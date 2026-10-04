const TZ = "Europe/Paris";

/** "2024-07-15" -> "15/07/2024" */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

/** ISO datetime -> "15/07/2024 13:02" (heure de Paris) */
export function fmtDateTime(iso: string): string {
  const dt = new Date(iso);
  const date = dt.toLocaleDateString("fr-FR", { timeZone: TZ });
  const heure = dt.toLocaleTimeString("fr-FR", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
  return `${date} ${heure}`;
}

export function initiales(nom: string): string {
  const parts = nom.replace(/^Dr\.?\s*/, "").trim().split(/\s+/);
  if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function val(v: string | number | null | undefined): string {
  return v === null || v === undefined || v === "" ? "—" : String(v);
}

/** Initiales d'un compte (titre inclus) : "Dr. Martin" -> "DM", comme l'en-tête. */
export function initialesCompte(nom: string): string {
  const parts = nom.replace(/[^\p{L}\p{N}\s-]/gu, "").trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
