import type {
  ActionPayload,
  Compteurs,
  DossierDetail,
  DossierResume,
  Pathologie,
  PathologieIn,
  PathologieResume,
  Referentiels,
  Statistiques,
  Utilisateur,
  UtilisateurComplet,
  UtilisateurIn,
} from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isForm = init?.body instanceof FormData;
  const res = await fetch(BASE + path, {
    ...init,
    headers: isForm ? init?.headers : { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail =
        typeof body.detail === "string"
          ? body.detail
          : Array.isArray(body.detail)
            ? body.detail.map((e: { msg: string }) => e.msg).join(", ")
            : JSON.stringify(body.detail);
    } catch {
      /* corps non JSON */
    }
    throw new Error(detail || `Erreur ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

function upload(fichier: File, nom?: string): RequestInit {
  const fd = new FormData();
  fd.append("fichier", fichier);
  if (nom) fd.append("nom", nom);
  return { method: "POST", body: fd };
}

export interface FiltresListe {
  status?: string;
  q?: string;
  urgence?: string;
  type?: string;
  pieces_statut?: string;
  limit?: number;
  tri?: "soumission" | "recent";
  // recherche avancée
  id?: string;
  nom?: string;
  prenom?: string;
  nss?: string;
  societe?: string;
  sinistre?: string;
  patho?: string;
  debut_min?: string;
  fin_max?: string;
}

function qs(f: object): string {
  const p = new URLSearchParams();
  Object.entries(f).forEach(([k, v]) => v !== undefined && v !== null && v !== "" && p.set(k, String(v)));
  return p.toString();
}

const enc = encodeURIComponent;

export const fichierUrl = (cible: "document" | "pathologie-document", id: number, telecharger = false) =>
  `${BASE}/api/fichiers/${cible}/${id}${telecharger ? "?telecharger=true" : ""}`;

export const api = {
  me: () => request<Utilisateur>("/api/me"),
  compteurs: () => request<Compteurs>("/api/dossiers/compteurs"),
  dossiers: (f: FiltresListe = {}) => request<{ total: number; items: DossierResume[] }>(`/api/dossiers?${qs(f)}`),
  dossier: (id: string) => request<DossierDetail>(`/api/dossiers/${enc(id)}`),
  action: (id: string, payload: ActionPayload) =>
    request<DossierDetail>(`/api/dossiers/${enc(id)}/actions`, json("POST", payload)),
  commenter: (id: string, texte: string) =>
    request<DossierDetail>(`/api/dossiers/${enc(id)}/commentaires`, json("POST", { texte })),
  analyse: (id: string, compte_rendu: string, duree_estimee: number | null) =>
    request<DossierDetail>(`/api/dossiers/${enc(id)}/analyse`, json("PUT", { compte_rendu, duree_estimee })),
  relancer: (id: string, pieceId: number) =>
    request<DossierDetail>(`/api/dossiers/${enc(id)}/pieces/${pieceId}/relance`, { method: "POST" }),
  ajouterDocumentDossier: (id: string, fichier: File, nom?: string) =>
    request<DossierDetail>(`/api/dossiers/${enc(id)}/documents`, upload(fichier, nom)),

  referentiels: () => request<Referentiels>("/api/referentiels"),
  statistiques: () => request<Statistiques>("/api/statistiques"),

  pathologies: (f: { q?: string; groupe?: string; categorie?: string } = {}) =>
    request<PathologieResume[]>(`/api/pathologies?${qs(f)}`),
  groupesPathologies: () => request<{ groupe: string; nb: number }[]>("/api/pathologies/groupes"),
  pathologie: (code: string) => request<Pathologie>(`/api/pathologies/${enc(code)}`),
  creerPathologie: (p: PathologieIn) => request<Pathologie>("/api/pathologies", json("POST", p)),
  modifierPathologie: (code: string, p: PathologieIn) =>
    request<Pathologie>(`/api/pathologies/${enc(code)}`, json("PUT", p)),
  ajouterDocumentPathologie: (code: string, fichier: File, nom?: string) =>
    request<Pathologie>(`/api/pathologies/${enc(code)}/documents`, upload(fichier, nom)),
  supprimerDocumentPathologie: (code: string, docId: number) =>
    request<Pathologie>(`/api/pathologies/${enc(code)}/documents/${docId}`, { method: "DELETE" }),

  utilisateurs: (f: { q?: string; role?: string } = {}) => request<UtilisateurComplet[]>(`/api/utilisateurs?${qs(f)}`),
  creerUtilisateur: (u: UtilisateurIn) => request<UtilisateurComplet>("/api/utilisateurs", json("POST", u)),
  modifierUtilisateur: (id: number, u: UtilisateurIn) =>
    request<UtilisateurComplet>(`/api/utilisateurs/${id}`, json("PUT", u)),
  supprimerUtilisateur: (id: number) => request<void>(`/api/utilisateurs/${id}`, { method: "DELETE" }),

  profil: () => request<UtilisateurComplet>("/api/profil"),
  modifierProfil: (p: { nom_affiche: string; email: string; telephone: string | null; langue: string; fuseau: string }) =>
    request<UtilisateurComplet>("/api/profil", json("PUT", p)),
  preferences: (p: Partial<Pick<UtilisateurComplet, "notif_valider" | "notif_pieces" | "notif_expertise" | "notif_resume">>) =>
    request<UtilisateurComplet>("/api/profil/preferences", json("PATCH", p)),
};
