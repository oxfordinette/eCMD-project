import { fmtDateTime } from "../format";
import { COULEUR_EVENEMENT, STATUTS, STATUT_CONFIG } from "../statuts";
import type { DossierDetail, Evenement } from "../types";

export function Historique({ evenements }: { evenements: Evenement[] }) {
  if (!evenements.length) return <div className="comments-empty">Aucun événement.</div>;
  return (
    <>
      {evenements.map((h, i) => (
        <div className="hist-item" key={h.id}>
          <div className="hist-dot-col">
            <div className="hist-dot" style={{ background: COULEUR_EVENEMENT[h.categorie] ?? "#64748b" }} />
            {i < evenements.length - 1 && <div className="hist-line" />}
          </div>
          <div className="hist-content">
            <div style={{ fontSize: 12.5, color: "#1e293b", fontWeight: 600 }}>{h.action}</div>
            <div style={{ fontSize: 11, color: "#94a3b8" }}>
              {fmtDateTime(h.date)} · {h.auteur}
            </div>
          </div>
        </div>
      ))}
    </>
  );
}

/** Frise horizontale : étapes du workflow parcourues par le dossier. */
export function Parcours({ d }: { d: DossierDetail }) {
  const visited = d.parcours?.length ? d.parcours : [d.status];
  const currentIdx = STATUTS.indexOf(d.status);
  return (
    <div className="parcours-card">
      <div className="parcours-title">Parcours du dossier</div>
      <div className="parcours-row">
        {STATUTS.map((step, i) => {
          const cfg = STATUT_CONFIG[step];
          const isCurrent = step === d.status;
          const isVisited = visited.includes(step);
          const state = isCurrent ? "pc-current" : isVisited ? "pc-done" : "pc-skipped";
          const style = { "--pc-color": cfg.couleur } as React.CSSProperties;
          const next = STATUTS[i + 1];
          const filled = next && isVisited && visited.includes(next) && i < currentIdx;
          return (
            <span key={step} style={{ display: "contents" }}>
              <div className={`parcours-step ${state}`} style={style}>
                <div className="parcours-step-dot">{isVisited || isCurrent ? cfg.icone : "·"}</div>
                <div className="parcours-step-label">{cfg.etape}</div>
              </div>
              {next && <div className={`parcours-connector ${filled ? "pc-filled" : ""}`} style={style} />}
            </span>
          );
        })}
      </div>
    </div>
  );
}
