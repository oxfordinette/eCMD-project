import { useEffect, useState } from "react";
import { api } from "../api";
import { useApp } from "../AppContext";
import { ConfirmModal } from "../components/ConfirmModal";
import { fmtDateTime, initialesCompte as initiales } from "../format";
import type { Role, UtilisateurComplet, UtilisateurIn } from "../types";

export const ROLES: Record<Role, { cls: string; label: string; color: string }> = {
  admin: { cls: "role-admin", label: "Admin", color: "#C53532" },
  manager: { cls: "role-manager", label: "Manager", color: "#0B4BFF" },
  medecin: { cls: "role-medecin", label: "Médecin conseil", color: "#0D9488" },
  gestionnaire: { cls: "role-gestionnaire", label: "Gestionnaire", color: "#64748b" },
};

export function nomComplet(u: UtilisateurComplet): string {
  return u.nom_affiche || `${u.prenom} ${u.nom}`.trim();
}

function derniereCo(iso: string | null): string {
  if (!iso) return "Jamais connecté";
  const d = new Date(iso);
  const auj = new Date();
  const hier = new Date(auj.getTime() - 86400000);
  const heure = d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Paris" });
  if (d.toDateString() === auj.toDateString()) return `Aujourd'hui ${heure}`;
  if (d.toDateString() === hier.toDateString()) return `Hier ${heure}`;
  return fmtDateTime(iso);
}

function UserModal({
  initial,
  onClose,
  onSave,
}: {
  initial: UtilisateurComplet | null;
  onClose: () => void;
  onSave: (u: UtilisateurIn) => Promise<void>;
}) {
  const [u, setU] = useState<UtilisateurIn>({
    nom: initial?.nom ?? "",
    prenom: initial?.prenom ?? "",
    email: initial?.email ?? "",
    role: initial?.role ?? "gestionnaire",
    statut: initial?.statut ?? "actif",
  });
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const set = (k: keyof UtilisateurIn) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setU({ ...u, [k]: e.target.value });

  const enregistrer = async () => {
    if (!u.nom.trim() || !u.prenom.trim() || !u.email.trim()) {
      setErreur("Veuillez renseigner le nom, le prénom et l'email.");
      return;
    }
    setEnvoi(true);
    setErreur(null);
    try {
      await onSave({ ...u, nom: u.nom.trim(), prenom: u.prenom.trim(), email: u.email.trim() });
    } catch (e) {
      setErreur((e as Error).message);
      setEnvoi(false);
    }
  };

  return (
    <div className="modal-overlay open" onClick={(e) => e.target === e.currentTarget && !envoi && onClose()}>
      <div className="modal">
        <div className="modal-title">👤 {initial ? "Modifier un utilisateur" : "Ajouter un utilisateur"}</div>
        <div className="modal-sub">Renseignez les informations du compte et le rôle d'accès.</div>
        <div className="modal-field">
          <label>Nom</label>
          <input value={u.nom} onChange={set("nom")} placeholder="ex: Martin" />
        </div>
        <div className="modal-field">
          <label>Prénom</label>
          <input value={u.prenom} onChange={set("prenom")} placeholder="ex: Sophie" />
        </div>
        <div className="modal-field">
          <label>Email</label>
          <input type="email" value={u.email} onChange={set("email")} placeholder="ex: s.martin@cellmed.fr" />
        </div>
        <div className="modal-field">
          <label>Rôle</label>
          <select value={u.role} onChange={set("role")}>
            {(Object.keys(ROLES) as Role[]).map((r) => (
              <option key={r} value={r}>
                {ROLES[r].label}
              </option>
            ))}
          </select>
        </div>
        <div className="modal-field">
          <label>Statut</label>
          <select value={u.statut} onChange={set("statut")}>
            <option value="actif">Actif</option>
            <option value="inactif">Inactif</option>
          </select>
        </div>
        {erreur && <div className="modal-error">{erreur}</div>}
        <div className="modal-actions">
          <button className="modal-cancel" onClick={onClose} disabled={envoi}>
            Annuler
          </button>
          <button className="modal-confirm mc-blue" onClick={enregistrer} disabled={envoi}>
            {envoi ? "Enregistrement…" : "Enregistrer"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Utilisateurs() {
  const { toast, user } = useApp();
  const [items, setItems] = useState<UtilisateurComplet[]>([]);
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<{ u: UtilisateurComplet | null } | null>(null);
  const [aSupprimer, setASupprimer] = useState<UtilisateurComplet | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    setLoading(true);
    const t = window.setTimeout(() => {
      api
        .utilisateurs({ q, role })
        .then(setItems)
        .catch((e: Error) => toast("⚠️", e.message))
        .finally(() => setLoading(false));
    }, 200);
    return () => window.clearTimeout(t);
  }, [q, role, version, toast]);

  return (
    <div className="page">
      <div className="view-banner">
        <div className="vb-tag">Administration · Accès</div>
        <div className="vb-h1">Utilisateurs</div>
        <div className="vb-desc">Gestion des comptes et des rôles d'accès à CellMed.</div>
      </div>
      <div className="section-head">
        <div>
          <div className="sh-title">Liste des utilisateurs</div>
          <div className="sh-sub">
            {items.length} utilisateur{items.length !== 1 ? "s" : ""}
          </div>
        </div>
        <div className="sh-actions">
          <button className="btn-add-user" onClick={() => setModal({ u: null })}>
            ＋ Ajouter un utilisateur
          </button>
        </div>
      </div>
      <div className="filter-bar">
        <div className="search-wrap">
          <span className="search-ico">🔍</span>
          <input
            type="text"
            placeholder="Rechercher un utilisateur, un email…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <select className="filter-select" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="">Tous les rôles</option>
          {(Object.keys(ROLES) as Role[]).map((r) => (
            <option key={r} value={r}>
              {ROLES[r].label}
            </option>
          ))}
        </select>
      </div>
      <div className="user-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Utilisateur</th>
              <th>Email</th>
              <th>Rôle</th>
              <th>Statut</th>
              <th>Dernière connexion</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", padding: 40, color: "#94a3b8" }}>
                  Chargement…
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", padding: 40, color: "#94a3b8", fontSize: 13 }}>
                  Aucun utilisateur trouvé
                </td>
              </tr>
            ) : (
              items.map((u) => {
                const ri = ROLES[u.role] ?? ROLES.gestionnaire;
                const moi = user?.id === u.id;
                return (
                  <tr key={u.id} style={{ cursor: "default" }}>
                    <td>
                      <div className="user-cell">
                        <div className="user-avatar" style={{ background: ri.color }}>
                          {initiales(nomComplet(u))}
                        </div>
                        <div style={{ fontWeight: 600, color: "#1e293b", fontSize: 13 }}>
                          {nomComplet(u)}
                          {moi && <span style={{ color: "#94a3b8", fontWeight: 500 }}> (vous)</span>}
                        </div>
                      </div>
                    </td>
                    <td style={{ color: "#64748b", fontSize: 12.5 }}>{u.email}</td>
                    <td>
                      <span className={`role-badge ${ri.cls}`}>{ri.label}</span>
                    </td>
                    <td>
                      <span className="status-dot-wrap">
                        <span className={`status-dot ${u.statut === "actif" ? "status-active" : "status-inactive"}`} />
                        {u.statut === "actif" ? "Actif" : "Inactif"}
                      </span>
                    </td>
                    <td style={{ color: "#94a3b8", fontSize: 12 }}>{derniereCo(u.derniere_connexion)}</td>
                    <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                      <span className="user-action-link" onClick={() => setModal({ u })}>
                        Modifier
                      </span>
                      {!moi && (
                        <>
                          {" "}
                          &nbsp;·&nbsp;{" "}
                          <span className="user-action-link danger" onClick={() => setASupprimer(u)}>
                            Supprimer
                          </span>
                        </>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {modal && (
        <UserModal
          initial={modal.u}
          onClose={() => setModal(null)}
          onSave={async (data) => {
            if (modal.u) await api.modifierUtilisateur(modal.u.id, data);
            else await api.creerUtilisateur(data);
            setModal(null);
            setVersion((v) => v + 1);
            toast("✅", modal.u ? "Utilisateur modifié avec succès" : "Utilisateur ajouté avec succès");
          }}
        />
      )}
      {aSupprimer && (
        <ConfirmModal
          titre="🗑️ Supprimer l'utilisateur"
          message={`Supprimer le compte de ${nomComplet(aSupprimer)} (${aSupprimer.email}) ? Cette action est définitive.`}
          libelle="Supprimer"
          onClose={() => setASupprimer(null)}
          onConfirm={async () => {
            await api.supprimerUtilisateur(aSupprimer.id);
            setASupprimer(null);
            setVersion((v) => v + 1);
            toast("🗑️", "Utilisateur supprimé");
          }}
        />
      )}
    </div>
  );
}
