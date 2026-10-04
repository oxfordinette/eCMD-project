import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useApp } from "../AppContext";
import { fmtDateTime, initialesCompte as initiales } from "../format";
import type { UtilisateurComplet } from "../types";
import { ROLES, nomComplet } from "./Utilisateurs";

type Notif = "notif_valider" | "notif_pieces" | "notif_expertise" | "notif_resume";

const NOTIFS: { k: Notif; label: string; desc: string }[] = [
  {
    k: "notif_valider",
    label: "Nouveaux dossiers à valider",
    desc: "Recevoir une notification lorsqu'un dossier nécessite votre décision.",
  },
  {
    k: "notif_pieces",
    label: "Pièces complémentaires reçues",
    desc: "Être alerté dès que l'assuré transmet les documents demandés.",
  },
  {
    k: "notif_expertise",
    label: "Retours d'expertise médicale",
    desc: "Être notifié à la réception d'un rapport d'expertise.",
  },
  {
    k: "notif_resume",
    label: "Résumé hebdomadaire par email",
    desc: "Recevoir chaque lundi un récapitulatif de l'activité de la semaine.",
  },
];

export default function Parametres() {
  const navigate = useNavigate();
  const { toast, refreshUser } = useApp();
  const [u, setU] = useState<UtilisateurComplet | null>(null);
  const [form, setForm] = useState({ nom_affiche: "", telephone: "", langue: "fr", fuseau: "Europe/Paris" });
  const [saving, setSaving] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    api
      .profil()
      .then((p) => {
        setU(p);
        setForm({
          nom_affiche: nomComplet(p),
          telephone: p.telephone ?? "",
          langue: p.langue,
          fuseau: p.fuseau,
        });
      })
      .catch((e: Error) => setErreur(e.message));
  }, []);

  if (erreur) return <div className="error-box">Erreur : {erreur}</div>;
  if (!u) return <div className="loading">Chargement…</div>;

  const enregistrer = async () => {
    if (!form.nom_affiche.trim()) return toast("⚠️", "Le nom affiché ne peut pas être vide");
    setSaving(true);
    try {
      setU(
        await api.modifierProfil({
          nom_affiche: form.nom_affiche.trim(),
          email: u.email,
          telephone: form.telephone.trim() || null,
          langue: form.langue,
          fuseau: form.fuseau,
        }),
      );
      refreshUser();
      toast("✅", "Profil mis à jour avec succès");
    } catch (e) {
      toast("⚠️", (e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const basculer = async (k: Notif, v: boolean) => {
    setU({ ...u, [k]: v });
    try {
      setU(await api.preferences({ [k]: v }));
      toast("🔔", "Préférence enregistrée");
    } catch (e) {
      setU({ ...u, [k]: !v });
      toast("⚠️", (e as Error).message);
    }
  };

  const nom = nomComplet(u);

  return (
    <div className="page settings-wrap">
      <div className="view-banner">
        <div className="vb-tag">Mon compte</div>
        <div className="vb-h1">Paramètres</div>
        <div className="vb-desc">Gérez vos informations personnelles, vos préférences et la sécurité de votre compte.</div>
      </div>
      <div className="section-head">
        <div>
          <div className="sh-title">Préférences du compte</div>
          <div className="sh-sub">Ces réglages sont enregistrés sur votre compte.</div>
        </div>
        <div className="sh-actions">
          <button className="btn-back" onClick={() => navigate("/")}>
            ← Retour
          </button>
        </div>
      </div>

      <div className="form-card">
        <div className="fc-header">
          <span className="fc-icon">👤</span>
          <span className="fc-title">Profil</span>
        </div>
        <div className="fc-body">
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
            <div
              className="h-avatar"
              style={{ width: 56, height: 56, fontSize: 18, background: "var(--navy)", borderColor: "var(--navy)" }}
            >
              {initiales(nom)}
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#1e293b" }}>{nom}</div>
              <div style={{ fontSize: 12, color: "#64748b" }}>{u.titre ?? ROLES[u.role]?.label}</div>
            </div>
          </div>
          <div className="form-grid cols3">
            <div className="field">
              <label>Nom affiché</label>
              <input
                className="field-val editable"
                value={form.nom_affiche}
                onChange={(e) => setForm({ ...form, nom_affiche: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Email professionnel</label>
              <div className="field-val" style={{ background: "#f1f5f9", color: "#64748b" }} title="Identifiant du compte">
                {u.email}
              </div>
            </div>
            <div className="field">
              <label>Téléphone</label>
              <input
                className="field-val editable"
                value={form.telephone}
                onChange={(e) => setForm({ ...form, telephone: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Rôle</label>
              <div className="field-val" style={{ background: "#f1f5f9", color: "#64748b" }}>
                {ROLES[u.role]?.label ?? u.role}
              </div>
            </div>
            <div className="field">
              <label>Langue</label>
              <select
                className="field-val editable"
                value={form.langue}
                onChange={(e) => setForm({ ...form, langue: e.target.value })}
              >
                <option value="fr">Français</option>
                <option value="en">English</option>
              </select>
            </div>
            <div className="field">
              <label>Fuseau horaire</label>
              <select
                className="field-val editable"
                value={form.fuseau}
                onChange={(e) => setForm({ ...form, fuseau: e.target.value })}
              >
                <option value="Europe/Paris">Europe/Paris</option>
                <option value="Europe/London">Europe/London</option>
              </select>
            </div>
          </div>
          <div style={{ marginTop: 14 }}>
            <button className="btn btn-primary" onClick={enregistrer} disabled={saving}>
              {saving ? "Enregistrement…" : "Enregistrer les modifications"}
            </button>
          </div>
        </div>
      </div>

      <div className="form-card">
        <div className="fc-header">
          <span className="fc-icon">🔔</span>
          <span className="fc-title">Notifications</span>
        </div>
        <div className="fc-body">
          {NOTIFS.map((n, i) => (
            <div
              className="settings-pref-row"
              key={n.k}
              style={i === NOTIFS.length - 1 ? { borderBottom: "none" } : undefined}
            >
              <div>
                <div className="settings-pref-label">{n.label}</div>
                <div className="settings-pref-desc">{n.desc}</div>
              </div>
              <label className="settings-toggle">
                <input type="checkbox" checked={u[n.k]} onChange={(e) => basculer(n.k, e.target.checked)} />
                <span className="settings-toggle-slider" />
              </label>
            </div>
          ))}
        </div>
      </div>

      <div className="form-card">
        <div className="fc-header">
          <span className="fc-icon">🔒</span>
          <span className="fc-title">Sécurité</span>
        </div>
        <div className="fc-body">
          <div className="settings-note">
            🔐 Le mot de passe et l'authentification seront gérés par le <b>SSO de l'entreprise</b> : ils ne sont pas
            stockés dans CellMed.
            {u.derniere_connexion && (
              <>
                <br />
                Dernière connexion : {fmtDateTime(u.derniere_connexion)}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
