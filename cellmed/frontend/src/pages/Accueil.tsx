import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useApp } from "../AppContext";
import { fmtDate } from "../format";
import { StatusBadge, Urgence } from "../statuts";
import type { DossierResume, Statut } from "../types";

const CARTES: { s: Statut; cls: string; icon: string; iconCls: string; countCls: string; label: string; sub: string }[] = [
  { s: "valider", cls: "card-valider", icon: "📋", iconCls: "icon-red", countCls: "count-red", label: "Dossiers à valider", sub: "Formulaires soumis, en attente de décision" },
  { s: "pieces", cls: "card-pieces", icon: "📎", iconCls: "icon-orange", countCls: "count-orange", label: "Attente pièces complémentaires", sub: "Documents manquants demandés à l'assuré" },
  { s: "expertise", cls: "card-expertise", icon: "🔬", iconCls: "icon-purple", countCls: "count-purple", label: "Attente d'expertise médicale", sub: "Avis expert médical en attente" },
  { s: "avis-medical", cls: "card-avis", icon: "🩺", iconCls: "icon-teal", countCls: "count-teal", label: "Attente avis médical", sub: "Dossiers soumis à l'avis du médecin conseil" },
  { s: "clotures", cls: "card-clotures", icon: "✅", iconCls: "icon-green", countCls: "count-green", label: "Dossiers clôturés", sub: "Décisions rendues" },
];

export default function Accueil() {
  const { user, compteurs, refreshCompteurs } = useApp();
  const [recents, setRecents] = useState<DossierResume[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    refreshCompteurs();
    api
      .dossiers({ limit: 6, tri: "recent" })
      .then((r) => setRecents(r.items))
      .catch((e: Error) => setErreur(e.message));
  }, [refreshCompteurs]);

  return (
    <div className="page">
      <div className="view-banner">
        <div className="vb-tag">CellMed · Tableau de bord</div>
        <div className="vb-h1">Bonjour, {user?.nom ?? ""} 👋</div>
        <div className="vb-desc">Voici l'état en temps réel des dossiers CMD sous votre responsabilité.</div>
      </div>

      <div className="dash-grid">
        {CARTES.map((c) => (
          <div key={c.s} className={`dash-card ${c.cls}`} onClick={() => navigate(`/dossiers/${c.s}`)}>
            <div className={`dc-icon ${c.iconCls}`}>{c.icon}</div>
            <div className={`dc-count ${c.countCls}`}>{compteurs ? compteurs[c.s] ?? 0 : "…"}</div>
            <div className="dc-label">{c.label}</div>
            <div className="dc-sub">{c.sub}</div>
            <div className="dc-arrow">→</div>
          </div>
        ))}
      </div>

      <div className="section-head">
        <div>
          <div className="sh-title">Derniers dossiers traités</div>
          <div className="sh-sub">Activité récente sur vos dossiers</div>
        </div>
      </div>
      <div className="table-wrap" style={{ margin: "0 36px 36px" }}>
        <table>
          <thead>
            <tr>
              <th>Dossier</th>
              <th>Assuré</th>
              <th>Pathologie</th>
              <th>Statut</th>
              <th>Date soumission</th>
              <th>Urgence</th>
            </tr>
          </thead>
          <tbody>
            {erreur ? (
              <tr>
                <td colSpan={6} className="error-box">
                  Impossible de charger les dossiers : {erreur}
                </td>
              </tr>
            ) : !recents ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", padding: 30, color: "#94a3b8" }}>
                  Chargement…
                </td>
              </tr>
            ) : (
              recents.map((d) => (
                <tr key={d.id} onClick={() => navigate(`/dossier/${d.id}`)}>
                  <td>
                    <div className="td-id">{d.id}</div>
                  </td>
                  <td>
                    <div className="td-name">
                      {d.nom}, {d.prenom}
                    </div>
                  </td>
                  <td>{d.patho}</td>
                  <td>
                    <StatusBadge d={d} />
                  </td>
                  <td>{fmtDate(d.date_soumission)}</td>
                  <td>
                    <Urgence u={d.urgence} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
