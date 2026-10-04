import type { DossierResume, Statut } from "./types";

export const STATUTS: Statut[] = ["valider", "pieces", "expertise", "avis-medical", "clotures"];

export const STATUT_CONFIG: Record<
  Statut,
  { label: string; desc: string; tag: string; banner: string; badge: string; court: string; sidebar: string; couleur: string; icone: string; etape: string; cnt: string }
> = {
  valider: {
    label: "Dossiers à valider",
    desc: "Formulaires soumis par les assurés, en attente de décision médicale.",
    tag: "CELLMED · DÉCISION REQUISE",
    banner: "linear-gradient(135deg,#7f1d1d 0%,#b91c1c 100%)",
    badge: "badge-red",
    court: "À valider",
    sidebar: "À valider",
    couleur: "#C53532",
    icone: "📋",
    etape: "À valider",
    cnt: "cnt-red",
  },
  pieces: {
    label: "Attente pièces complémentaires",
    desc: "Dossiers en attente de documents manquants de la part de l'assuré.",
    tag: "CELLMED · EN ATTENTE",
    banner: "linear-gradient(135deg,#78350f 0%,#d97706 100%)",
    badge: "badge-orange",
    court: "Attente pièces",
    sidebar: "Attente pièces",
    couleur: "#D97706",
    icone: "📎",
    etape: "Pièces complémentaires",
    cnt: "cnt-orange",
  },
  expertise: {
    label: "Attente d'expertise médicale",
    desc: "Dossiers transmis au médecin conseil pour avis spécialisé.",
    tag: "CELLMED · EXPERTISE EN COURS",
    banner: "linear-gradient(135deg,#4c1d95 0%,#6d28d9 100%)",
    badge: "badge-purple",
    court: "Attente expertise",
    sidebar: "Attente expertise",
    couleur: "#6D28D9",
    icone: "🔬",
    etape: "Expertise médicale",
    cnt: "cnt-purple",
  },
  "avis-medical": {
    label: "Attente d'avis médical",
    desc: "Dossiers en attente de l'avis du médecin conseil.",
    tag: "CELLMED · AVIS EN COURS",
    banner: "linear-gradient(135deg,#0f4c40 0%,#0d9488 100%)",
    badge: "badge-teal",
    court: "Avis médical",
    sidebar: "Attente avis médical",
    couleur: "#0D9488",
    icone: "🩺",
    etape: "Avis médical",
    cnt: "cnt-teal",
  },
  clotures: {
    label: "Dossiers clôturés",
    desc: "Dossiers pour lesquels une décision finale a été rendue.",
    tag: "CELLMED · ARCHIVÉS",
    banner: "linear-gradient(135deg,#064e3b 0%,#14853d 100%)",
    badge: "badge-green",
    court: "Clôturé",
    sidebar: "Clôturés",
    couleur: "#14853D",
    icone: "✅",
    etape: "Clôturé",
    cnt: "cnt-gray",
  },
};

export const COULEUR_EVENEMENT: Record<string, string> = {
  systeme: "#64748b",
  assure: "#1d4ed8",
  valider: "#C53532",
  pieces: "#D97706",
  expertise: "#6D28D9",
  "avis-medical": "#0D9488",
  clotures: "#14853D",
};

export function StatusBadge({ d }: { d: Pick<DossierResume, "status" | "pieces_statut"> }) {
  if (d.status === "pieces") {
    return d.pieces_statut === "recues" ? (
      <span className="badge badge-green">Pièces reçues</span>
    ) : (
      <span className="badge badge-orange">Attente pièces</span>
    );
  }
  const c = STATUT_CONFIG[d.status];
  return <span className={`badge ${c?.badge ?? "badge-gray"}`}>{c?.court ?? d.status}</span>;
}

export function urgenceClass(u: string) {
  return u === "Haute" ? "high" : u === "Moyenne" ? "med" : "low";
}

export function Urgence({ u }: { u: string }) {
  return (
    <>
      <span className={`urgency-dot urg-${urgenceClass(u)}`} />
      {u}
    </>
  );
}
