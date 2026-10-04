/** Client de l'API « portail assuré » (backend partagé eCMD). */

export type OuiNon = "oui" | "non" | "";

export interface Brouillon {
  administratif: { profession: string; college: string; adresse: string; email: string; telephone: string };
  arret: {
    date_symptomes?: string;
    date_debut?: string;
    date_fin?: string;
    cause?: "accident" | "maladie" | "grossesse";
    type_accident?: "travail" | "vie_privee";
    tiers?: OuiNon;
    maladie_pro?: OuiNon;
    pathologie_code?: string;
    arret_anterieur?: OuiNon;
    autres_pathologies?: string[];
  };
  antecedents: {
    patho_avant?: OuiNon;
    patho_anterieure?: string;
    patho_consecutive?: OuiNon;
    patho_consecutive_detail?: string;
    ald?: OuiNon;
    etat_sante?: string;
  };
  soins: {
    traitements?: { nom: string; posologie: string }[];
    specialistes?: OuiNon;
    specialiste_date?: string;
    specialiste_motif?: string;
    hospitalisation?: OuiNon;
    hospitalisation_date?: string;
    hospitalisation_type?: string;
  };
  evolution: {
    reprise?: OuiNon;
    reprise_temps?: "partiel" | "plein";
    reprise_date?: string;
    invalidite?: OuiNon;
    invalidite_date?: string;
    invalidite_categorie?: string;
    incapacite?: OuiNon;
    incapacite_date?: string;
    incapacite_taux?: string;
    retraite?: OuiNon;
    retraite_date?: string;
    observations?: string;
  };
  documents: DocumentDepose[];
}

export interface DocumentDepose {
  fichier_id: number;
  categorie: string;
  nom: string;
  taille: string;
  type: string;
}

export interface Piece {
  categorie: string;
  libelle: string;
  etape: number;
  obligatoire: boolean;
}

export interface EtatFormulaire {
  brouillon: Brouillon;
  etape: number;
  pieces_requises: Piece[];
  erreurs: Record<string, string[]>;
}

export interface Formulaire extends EtatFormulaire {
  admin: {
    entreprise: string | null;
    numero_contrat: string | null;
    assureur: string | null;
    nom: string;
    prenom: string;
    date_naissance: string;
    nss: string | null;
    nss_formate: string | null;
    type_certificat: string;
  };
  pathologies: { code: string; libelle: string; groupe: string }[];
  categories_invalidite: Record<string, string>;
}

export interface Section {
  numero: string;
  titre: string;
  etape: number;
  lignes: { label: string; valeur: string | string[] }[];
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: unknown,
  ) {
    super(message);
  }
}

const cle = (token: string) => `cm-session-${token}`;

export const session = {
  get: (token: string) => {
    try {
      return sessionStorage.getItem(cle(token));
    } catch {
      return null;
    }
  },
  set: (token: string, s: string) => {
    try {
      sessionStorage.setItem(cle(token), s);
    } catch {
      /* stockage indisponible */
    }
  },
  clear: (token: string) => {
    try {
      sessionStorage.removeItem(cle(token));
    } catch {
      /* stockage indisponible */
    }
  },
};

async function req<T>(token: string, path: string, init: RequestInit = {}, auth = false): Promise<T> {
  const headers: Record<string, string> = {};
  if (!(init.body instanceof FormData)) headers["Content-Type"] = "application/json";
  if (auth) headers["Authorization"] = `Bearer ${session.get(token) ?? ""}`;
  const res = await fetch(`/api/portail/${encodeURIComponent(token)}${path}`, { ...init, headers });
  if (!res.ok) {
    let msg = "Une erreur est survenue. Merci de réessayer.";
    let detail: unknown;
    try {
      const body = await res.json();
      detail = body.detail;
      if (typeof body.detail === "string") msg = body.detail;
      else if (body.detail?.message) msg = body.detail.message;
    } catch {
      /* corps non JSON */
    }
    throw new ApiError(msg, res.status, detail);
  }
  return res.json() as Promise<T>;
}

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const api = {
  etat: (t: string) =>
    req<{ statut: string; langue: string; soumise: boolean; numero_dossier: string | null }>(t, ""),
  langue: (t: string, langue: string) => req(t, "/langue", json("PUT", { langue })),
  identite: (t: string, date_naissance: string) =>
    req<{ sms: string | null; email: string | null }>(t, "/identite", json("POST", { date_naissance })),
  code: (t: string, canal: "sms" | "email") =>
    req<{ canal: string; destination: string; expire_min: number; code_dev: string | null }>(
      t,
      "/code",
      json("POST", { canal }),
    ),
  verifier: (t: string, code: string) =>
    req<{ session: string; expire_at: string }>(t, "/verifier", json("POST", { code })),

  formulaire: (t: string) => req<Formulaire>(t, "/formulaire", {}, true),
  enregistrer: (t: string, brouillon: Brouillon, etape: number) =>
    req<EtatFormulaire>(t, "/formulaire", json("PUT", { brouillon, etape }), true),
  deposer: (t: string, categorie: string, fichier: File) => {
    const fd = new FormData();
    fd.append("categorie", categorie);
    fd.append("fichier", fichier);
    return req<EtatFormulaire>(t, "/documents", { method: "POST", body: fd }, true);
  },
  retirer: (t: string, fichierId: number) =>
    req<EtatFormulaire>(t, `/documents/${fichierId}`, { method: "DELETE" }, true),
  urlDocument: (t: string, fichierId: number) =>
    `/api/portail/${encodeURIComponent(t)}/documents/${fichierId}?session=${encodeURIComponent(session.get(t) ?? "")}`,
  recapitulatif: (t: string) =>
    req<{ sections: Section[]; erreurs: Record<string, string[]> }>(t, "/recapitulatif", {}, true),
  soumettre: (t: string) => req<{ numero_dossier: string }>(t, "/soumettre", { method: "POST" }, true),
};
