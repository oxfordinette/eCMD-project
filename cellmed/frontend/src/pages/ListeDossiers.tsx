import { useEffect, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { DossierTable } from "../components/DossierTable";
import { STATUT_CONFIG } from "../statuts";
import type { DossierResume, Statut } from "../types";

export default function ListeDossiers() {
  const { statut } = useParams<{ statut: Statut }>();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [urgence, setUrgence] = useState("");
  const [type, setType] = useState("");
  const [piecesStatut, setPiecesStatut] = useState("");
  const [items, setItems] = useState<DossierResume[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);

  // Réinitialise les filtres quand on change de statut
  useEffect(() => {
    setQ("");
    setUrgence("");
    setType("");
    setPiecesStatut("");
  }, [statut]);

  useEffect(() => {
    if (!statut) return;
    setLoading(true);
    const t = window.setTimeout(() => {
      api
        .dossiers({ status: statut, q, urgence, type, pieces_statut: statut === "pieces" ? piecesStatut : "" })
        .then((r) => {
          setItems(r.items);
          setTotal(r.total);
          setErreur(null);
        })
        .catch((e: Error) => setErreur(e.message))
        .finally(() => setLoading(false));
    }, 200);
    return () => window.clearTimeout(t);
  }, [statut, q, urgence, type, piecesStatut]);

  if (!statut || !STATUT_CONFIG[statut]) return <Navigate to="/" replace />;
  const cfg = STATUT_CONFIG[statut];

  return (
    <div className="page">
      <div className="view-banner" style={{ background: cfg.banner }}>
        <div className="vb-tag">{cfg.tag}</div>
        <div className="vb-h1">{cfg.label}</div>
        <div className="vb-desc">{cfg.desc}</div>
      </div>
      <div className="section-head">
        <div>
          <div className="sh-title">{cfg.label}</div>
          <div className="sh-sub">
            {total} dossier{total !== 1 ? "s" : ""}
          </div>
        </div>
        <div className="sh-actions">
          <button className="btn-back" onClick={() => navigate("/")}>
            ← Retour
          </button>
        </div>
      </div>
      <div className="filter-bar">
        <div className="search-wrap">
          <span className="search-ico">🔍</span>
          <input
            type="text"
            placeholder="Rechercher un assuré, dossier…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <select className="filter-select" value={urgence} onChange={(e) => setUrgence(e.target.value)}>
          <option value="">Toutes urgences</option>
          <option value="Haute">Haute</option>
          <option value="Moyenne">Moyenne</option>
          <option value="Basse">Basse</option>
        </select>
        <select className="filter-select" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">Tous types</option>
          <option value="Initial">Initial</option>
          <option value="Suivi">Suivi</option>
        </select>
        {statut === "pieces" && (
          <select className="filter-select" value={piecesStatut} onChange={(e) => setPiecesStatut(e.target.value)}>
            <option value="">Tous sous-statuts</option>
            <option value="attente">Attente pièces</option>
            <option value="recues">Pièces reçues</option>
          </select>
        )}
      </div>
      {erreur ? <div className="error-box">Erreur : {erreur}</div> : <DossierTable items={items} loading={loading} />}
    </div>
  );
}
