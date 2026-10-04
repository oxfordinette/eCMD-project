import { useNavigate } from "react-router-dom";

export default function Bientot({ titre, tag, desc }: { titre: string; tag: string; desc: string }) {
  const navigate = useNavigate();
  return (
    <div className="page">
      <div className="view-banner">
        <div className="vb-tag">{tag}</div>
        <div className="vb-h1">{titre}</div>
        <div className="vb-desc">{desc}</div>
      </div>
      <div className="coming-soon">
        <div>🚧</div>
        Cette page arrive dans une prochaine itération du portail CellMed.
        <br />
        <br />
        <button className="btn btn-outline" onClick={() => navigate("/")}>
          ← Retour au tableau de bord
        </button>
      </div>
    </div>
  );
}
