export type Statut = "valider" | "pieces" | "expertise" | "avis-medical" | "clotures";

export interface DossierResume {
  id: string;
  status: Statut;
  pieces_statut: "attente" | "recues" | null;
  urgence: "Haute" | "Moyenne" | "Basse";
  type: "Initial" | "Suivi";
  nom: string;
  prenom: string;
  date_naissance: string | null;
  societe: string | null;
  patho: string | null;
  cim10: string | null;
  date_soumission: string | null;
}

export interface DocumentDossier {
  id: number;
  nom: string;
  type: "pdf" | "img" | "other";
  taille: string | null;
  a_fichier: boolean;
}

export interface Evenement {
  id: number;
  date: string;
  action: string;
  auteur: string;
  categorie: string;
}

export interface Commentaire {
  id: number;
  date: string;
  auteur: string;
  role: string | null;
  texte: string;
}

export interface PieceRequise {
  id: number;
  nom: string;
  statut: "attente" | "recue";
  nb_relances: number;
  date_limite: string | null;
}

export interface DossierDetail extends DossierResume {
  parcours: Statut[];
  nss: string | null;
  profession: string | null;
  college: string | null;
  telephone: string | null;
  email: string | null;
  adresse: string | null;
  dossier_sinistre: string | null;
  numero_mercer: string | null;
  partition: string | null;
  entreprise: string | null;
  assureur: string | null;
  date_debut: string | null;
  date_fin: string | null;
  type_arret: string | null;
  type_cert: string | null;
  duree: number | null;
  temps_partiel: string | null;
  commentaire: string | null;
  traitement: string | null;
  hospitalisation: string | null;
  arret_anterieur: string | null;
  patho_anterieure: string | null;
  patho_consecutive: string | null;
  ald: string | null;
  analyse_compte_rendu: string | null;
  analyse_duree_estimee: number | null;
  decision: string | null;
  duree_validee: number | null;
  documents: DocumentDossier[];
  evenements: Evenement[];
  commentaires: Commentaire[];
  pieces_requises: PieceRequise[];
  declaration: DeclarationSection[] | null;
}

export interface DeclarationSection {
  numero: string;
  titre: string;
  etape: number;
  lignes: { label: string; valeur: string | string[] }[];
}


export interface Medecin {
  id: number;
  nom: string;
  specialite: string;
}

export interface Referentiels {
  decisions: string[];
  types_expertise: string[];
  delais_pieces: number[];
  delais_avis: string[];
  medecins: Medecin[];
  groupes: string[];
  categories: string[];
}

export interface PathologieDocument {
  id: number;
  nom: string;
  type: "pdf" | "img" | "other";
  taille: string | null;
  a_fichier: boolean;
}

export interface PathologieResume {
  code: string;
  groupe: string;
  libelle: string;
  categorie: string | null;
  duree_std: number | null;
  synonymes: string | null;
  nb_documents: number;
}

export interface Pathologie extends Omit<PathologieResume, "nb_documents"> {
  commentaire: string | null;
  documents: PathologieDocument[];
}

export type PathologieIn = Omit<Pathologie, "documents">;

export interface Utilisateur {
  id: number | null;
  nom: string;
  role: string;
  initiales: string;
  email: string | null;
}

export type Role = "admin" | "manager" | "medecin" | "gestionnaire";

export interface UtilisateurComplet {
  id: number;
  nom: string;
  prenom: string;
  nom_affiche: string | null;
  titre: string | null;
  email: string;
  telephone: string | null;
  role: Role;
  statut: "actif" | "inactif";
  langue: "fr" | "en";
  fuseau: string;
  notif_valider: boolean;
  notif_pieces: boolean;
  notif_expertise: boolean;
  notif_resume: boolean;
  derniere_connexion: string | null;
}

export interface UtilisateurIn {
  nom: string;
  prenom: string;
  email: string;
  role: Role;
  statut: "actif" | "inactif";
}

export interface Statistiques {
  total: number;
  en_cours: number;
  duree_moyenne: number;
  urgence_haute: number;
  duree_traitement_moyenne: number;
  par_statut: Record<Statut, number>;
  par_urgence: Record<string, number>;
  top_pathologies: [string, number][];
}

export type Compteurs = Record<Statut, number>;

export type ActionPayload =
  | { type: "validate"; decision: string; duree_validee: number | null; commentaire?: string }
  | { type: "pieces"; pieces: string[]; message?: string; delai_jours: number }
  | { type: "expertise"; medecin_id: number; type_expertise: string; motif?: string }
  | { type: "avis"; medecin_id: number; motif?: string; delai?: string };

