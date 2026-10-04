import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type FiltresListe } from "../api";
import { useApp } from "../AppContext";
import { DossierTable } from "../components/DossierTable";
import type { DossierResume } from "../types";

const VIDE = {
  id: "",
  nom: "",
  prenom: "",
  nss: "",
  societe: "",
  sinistre: "",
  patho: "",
  status: "",
  type: "",
  urgence: "",
  debut_min: "",
  fin_max: "",
};
type Criteres = typeof VIDE;

export default function Recherche() {
  const navigate = useNavigate();
  const { toast } = useApp();
  const [c, setC] = useState<Criteres>(VIDE);
  const [resultats, setResultats] = useState<DossierResume[] | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const set = (k: keyof Criteres) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setC({ ...c, [k]: e.target.value });

  const lancer = async () => {
    if (!Object.values(c).some((v) => v.trim())) {
      toast("⚠️", "Renseignez au moins un critère de recherche");
      return;
    }
    setLoading(true);
    try {
      const r = await api.dossiers({ ...(c as FiltresListe), limit: 500 });
      setResultats(r.items);
      setTotal(r.total);
    } catch (e) {
      toast("⚠️", (e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const champ = (label: string, k: keyof Criteres, placeholder: string, type = "text") => (
    <div className="field">
      <label>{label}</label>
      <input
        type={type}
        className="field-val editable"
        placeholder={placeholder}
        value={c[k]}
        onChange={set(k)}
        onKeyDown={(e) => e.key === "Enter" && lancer()}
      />
    </div>
  );

  return (
    <div className="page rs-wrap">
      <div className="view-banner" style={{ background: "linear-gradient(135deg,#1e293b 0%,#334155 100%)" }}>
        <div className="vb-tag">CELLMED · OUTILS</div>
        <div className="vb-h1">Recherche avancée</div>
        <div className="vb-desc">
          Combinez plusieurs critères pour retrouver un dossier précis parmi l'ensemble des dossiers CMD.
        </div>
      </div>
      <div className="section-head">
        <div>
          <div className="sh-title">Critères de recherche</div>
          <div className="sh-sub">Renseignez un ou plusieurs champs puis lancez la recherche.</div>
        </div>
        <div className="sh-actions">
          <button className="btn-back" onClick={() => navigate("/")}>
            ← Retour
          </button>
        </div>
      </div>

      <div className="form-card">
        <div className="fc-header">
          <span className="fc-icon">🔍</span>
          <span className="fc-title">CRITÈRES</span>
        </div>
        <div className="fc-body">
          <div className="form-grid cols3">
            {champ("N° dossier", "id", "ex: MQC-2024-00142")}
            {champ("Nom", "nom", "Nom de l'assuré")}
            {champ("Prénom", "prenom", "Prénom de l'assuré")}
            {champ("N° sécurité sociale", "nss", "ex: 2810312075042")}
            {champ("Société", "societe", "Nom de la société")}
            {champ("N° dossier sinistre", "sinistre", "ex: SIN-2024-08741")}
            {champ("Pathologie / Code CIM-10", "patho", "ex: Lombosciatique, M51.1")}
            <div className="field">
              <label>Statut</label>
              <select className="field-val editable" value={c.status} onChange={set("status")}>
                <option value="">Tous statuts</option>
                <option value="valider">À valider</option>
                <option value="pieces">Attente pièces</option>
                <option value="expertise">Attente expertise</option>
                <option value="avis-medical">Attente avis médical</option>
                <option value="clotures">Clôturé</option>
              </select>
            </div>
            <div className="field">
              <label>Type de certificat</label>
              <select className="field-val editable" value={c.type} onChange={set("type")}>
                <option value="">Tous types</option>
                <option value="Initial">Initial</option>
                <option value="Suivi">Suivi</option>
              </select>
            </div>
            <div className="field">
              <label>Urgence</label>
              <select className="field-val editable" value={c.urgence} onChange={set("urgence")}>
                <option value="">Toutes urgences</option>
                <option value="Haute">Haute</option>
                <option value="Moyenne">Moyenne</option>
                <option value="Basse">Basse</option>
              </select>
            </div>
            {champ("Date début arrêt (à partir du)", "debut_min", "", "date")}
            {champ("Date fin arrêt (jusqu'au)", "fin_max", "", "date")}
          </div>
          <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
            <button className="btn btn-primary" onClick={lancer} disabled={loading}>
              🔍 {loading ? "Recherche…" : "Lancer la recherche"}
            </button>
            <button
              className="btn btn-outline"
              onClick={() => {
                setC(VIDE);
                setResultats(null);
              }}
            >
              Réinitialiser
            </button>
          </div>
        </div>
      </div>

      <div className="section-head" style={{ paddingTop: 4 }}>
        <div>
          <div className="sh-title">Résultats</div>
          <div className="sh-sub">
            {resultats === null
              ? "Renseignez des critères puis lancez la recherche."
              : `${total} résultat${total !== 1 ? "s" : ""} trouvé${total !== 1 ? "s" : ""}`}
          </div>
        </div>
      </div>
      {resultats !== null && <DossierTable items={resultats} loading={loading} />}
    </div>
  );
}
