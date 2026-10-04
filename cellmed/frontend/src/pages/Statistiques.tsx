import { useEffect, useState } from "react";
import { api } from "../api";
import { STATUTS, STATUT_CONFIG } from "../statuts";
import type { Statistiques as TStats } from "../types";

const LIBELLE_STATUT: Record<string, string> = {
  valider: "À valider",
  pieces: "Attente pièces",
  expertise: "Attente expertise",
  "avis-medical": "Attente avis médical",
  clotures: "Clôturés",
};
const COULEUR_URGENCE: Record<string, string> = { Haute: "var(--red)", Moyenne: "var(--orange)", Basse: "#94a3b8" };

function Kpi({ label, value, sub }: { label: string; value: string | number; sub: string }) {
  return (
    <div className="stat-kpi-card">
      <div className="stat-kpi-label">{label}</div>
      <div className="stat-kpi-value">{value}</div>
      <div className="stat-kpi-sub">{sub}</div>
    </div>
  );
}

export default function Statistiques() {
  const [s, setS] = useState<TStats | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    api.statistiques().then(setS).catch((e: Error) => setErreur(e.message));
  }, []);

  const banner = (
    <div className="view-banner">
      <div className="vb-tag">Outils · Pilotage</div>
      <div className="vb-h1">Statistiques</div>
      <div className="vb-desc">
        Vue d'ensemble de l'activité des dossiers CMD — répartition par statut, pathologie et durée moyenne d'arrêt.
      </div>
    </div>
  );
  if (erreur) return <div className="page">{banner}<div className="error-box">Erreur : {erreur}</div></div>;
  if (!s) return <div className="page">{banner}<div className="loading">Chargement…</div></div>;

  // Camembert par statut (conic-gradient)
  const totalStatut = STATUTS.reduce((n, k) => n + (s.par_statut[k] ?? 0), 0) || 1;
  let curseur = 0;
  const parts = STATUTS.map((k) => {
    const part = ((s.par_statut[k] ?? 0) / totalStatut) * 360;
    const seg = `${STATUT_CONFIG[k].couleur} ${curseur}deg ${curseur + part}deg`;
    curseur += part;
    return seg;
  });

  const maxUrg = Math.max(1, ...Object.values(s.par_urgence));
  const maxPatho = Math.max(1, ...s.top_pathologies.map(([, n]) => n));

  return (
    <div className="page">
      {banner}
      <div className="stat-kpi-grid">
        <Kpi label="Dossiers totaux" value={s.total} sub="Tous statuts confondus" />
        <Kpi label="En cours de traitement" value={s.en_cours} sub="Hors dossiers clôturés" />
        <Kpi label="Durée moyenne d'arrêt" value={`${s.duree_moyenne} j`} sub="Sur l'ensemble des dossiers" />
        <Kpi label="Urgence haute" value={s.urgence_haute} sub="Dossiers à traiter en priorité" />
        <Kpi
          label="Durée moyenne de traitement"
          value={`${s.duree_traitement_moyenne} j`}
          sub="De la soumission à la dernière mise à jour"
        />
      </div>

      <div className="stat-charts-row">
        <div className="stat-chart-card">
          <div className="stat-chart-title">Répartition par statut</div>
          <div className="stat-pie-wrap">
            <div className="stat-pie" style={{ background: `conic-gradient(${parts.join(",")})` }} />
            <div className="stat-pie-legend">
              {STATUTS.map((k) => (
                <div className="stat-legend-item" key={k}>
                  <span className="stat-legend-dot" style={{ background: STATUT_CONFIG[k].couleur }} />
                  <span className="stat-legend-label">{LIBELLE_STATUT[k]}</span>
                  <span className="stat-legend-value">{s.par_statut[k] ?? 0}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="stat-chart-card">
          <div className="stat-chart-title">Répartition par urgence</div>
          {["Haute", "Moyenne", "Basse"].map((u) => {
            const v = s.par_urgence[u] ?? 0;
            return (
              <div className="stat-bar-row" key={u}>
                <div className="stat-bar-name">{u}</div>
                <div className="stat-bar-track">
                  <div
                    className="stat-bar-fill"
                    style={{ width: `${Math.round((v / maxUrg) * 100)}%`, background: COULEUR_URGENCE[u] }}
                  />
                </div>
                <div className="stat-bar-value">{v}</div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="stat-charts-row">
        <div className="stat-chart-card" style={{ gridColumn: "1/-1" }}>
          <div className="stat-chart-title">Pathologies les plus fréquentes</div>
          {s.top_pathologies.length === 0 ? (
            <div className="comments-empty">Aucune donnée.</div>
          ) : (
            <div className="stat-vbar-row">
              {s.top_pathologies.map(([nom, n]) => (
                <div className="stat-vbar-col" key={nom}>
                  <div className="stat-vbar-value">{n}</div>
                  <div className="stat-vbar-track">
                    <div
                      className="stat-vbar-fill"
                      style={{ height: `${Math.round((n / maxPatho) * 100)}%`, background: "var(--blue)" }}
                    />
                  </div>
                  <div className="stat-vbar-name" title={nom}>
                    {nom}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
