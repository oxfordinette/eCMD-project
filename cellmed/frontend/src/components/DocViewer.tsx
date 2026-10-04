import { useEffect, useRef, useState } from "react";
import { fichierUrl } from "../api";
import { useApp } from "../AppContext";
import { fmtDate } from "../format";
import type { DocumentDossier, DossierDetail } from "../types";

/**
 * Aperçu des documents.
 * - Document avec fichier stocké : vrai PDF (iframe) ou vraie image.
 * - Document de démonstration (sans fichier) : rendu du certificat à partir des données du dossier.
 */
function Apercu({ d, doc, zoom }: { d: DossierDetail; doc: DocumentDossier; zoom?: boolean }) {
  if (doc.a_fichier) {
    const url = fichierUrl("document", doc.id);
    if (doc.type === "pdf") return <iframe className="doc-real-frame" src={url} title={doc.nom} />;
    if (doc.type === "img") return <img className="doc-real-img" src={url} alt={doc.nom} />;
    return (
      <div style={{ color: "#64748b", fontSize: 13, textAlign: "center", padding: 40 }}>
        <div style={{ fontSize: 32, marginBottom: 12 }}>📝</div>
        Aperçu indisponible pour ce format.
        <br />
        Utilisez « Télécharger ».
      </div>
    );
  }
  if (doc.type === "img" || doc.type === "other") {
    const w = zoom ? 420 : 300;
    const h = zoom ? 500 : 360;
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
        <div
          style={{
            background: "#1e293b",
            borderRadius: 8,
            padding: 20,
            width: w,
            maxWidth: "100%",
            height: h,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexDirection: "column",
            gap: 10,
            color: "#94a3b8",
          }}
        >
          <div style={{ fontSize: 48 }}>{doc.type === "img" ? "🩻" : "📝"}</div>
          <div style={{ fontSize: 11, textAlign: "center" }}>
            {doc.nom}
            <br />
            <span style={{ fontSize: 10, color: "#64748b" }}>{doc.taille}</span>
          </div>
        </div>
      </div>
    );
  }
  const L = ({ k, v }: { k: string; v: string | null }) => (
    <div className="doc-cert-line">
      <span className="doc-cert-key">{k}</span>
      <span className="doc-cert-val">{v ?? "—"}</span>
    </div>
  );
  return (
    <div className="doc-canvas-inner">
      <div className="doc-canvas-pdf-header">
        <span>📄</span>
        <span>{doc.nom}</span>
      </div>
      <div className="doc-cert-title">CERTIFICAT MÉDICAL D'ARRÊT DE TRAVAIL</div>
      <div className="doc-cert-section">Informations assuré</div>
      <L k="Nom :" v={`${d.nom} ${d.prenom}`} />
      <L k="Date de naissance :" v={fmtDate(d.date_naissance)} />
      <L k="N° SS :" v={d.nss} />
      <div className="doc-cert-section">Arrêt prescrit</div>
      <L k="Du :" v={fmtDate(d.date_debut)} />
      <L k="Au :" v={fmtDate(d.date_fin)} />
      <L k="Type :" v={d.type_arret} />
      <div className="doc-cert-section">Diagnostic</div>
      <L k="Pathologie :" v={d.patho} />
      <L k="Code CIM-10 :" v={d.cim10} />
      <div className="doc-cert-section">Commentaires</div>
      <div style={{ fontSize: 11, color: "#374151", lineHeight: 1.6 }}>{d.commentaire}</div>
      <div
        style={{
          marginTop: 20,
          paddingTop: 12,
          borderTop: "1px solid #f1f5f9",
          display: "flex",
          justifyContent: "space-between",
          fontSize: 10,
          color: "#94a3b8",
        }}
      >
        <span>Document certifié conforme</span>
        <span>Signé électroniquement</span>
      </div>
    </div>
  );
}

export function DocViewer({ d, onRelance }: { d: DossierDetail; onRelance: (pieceId: number) => void }) {
  const { toast } = useApp();
  const [selId, setSelId] = useState<number | null>(d.documents[0]?.id ?? null);
  const [zoom, setZoom] = useState(false);
  const doc = d.documents.find((x) => x.id === selId) ?? null;

  const nbDocs = useRef(d.documents.length);
  useEffect(() => {
    if (d.documents.length > nbDocs.current) {
      // un document vient d'être ajouté : on l'affiche
      setSelId(d.documents[d.documents.length - 1].id);
    } else if (!d.documents.some((x) => x.id === selId)) {
      setSelId(d.documents[0]?.id ?? null);
    }
    nbDocs.current = d.documents.length;
  }, [d.documents, selId]);

  const pending = d.pieces_requises.filter((p) => p.statut === "attente");
  const showPending = d.status === "pieces" && d.pieces_statut !== "recues" && pending.length > 0;
  const telecharger = () => {
    if (!doc) return toast("⚠️", "Aucun document sélectionné");
    if (!doc.a_fichier) return toast("ℹ️", "Document de démonstration : aucun fichier à télécharger");
    window.open(fichierUrl("document", doc.id, true), "_blank");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" }}>
      <div className="doc-list">
        {d.documents.length === 0 && <div className="comments-empty">Aucun document.</div>}
        {d.documents.map((x) => (
          <div key={x.id} className={`doc-item ${x.id === selId ? "active" : ""}`} onClick={() => setSelId(x.id)}>
            <div className={`doc-ico ${x.type === "pdf" ? "ico-pdf" : x.type === "img" ? "ico-img" : "ico-doc"}`}>
              {x.type === "pdf" ? "📄" : x.type === "img" ? "🖼️" : "📝"}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="doc-name">{x.nom}</div>
              <div className="doc-size">{x.taille}</div>
            </div>
          </div>
        ))}
      </div>

      {showPending && (
        <div className="pieces-pending-box">
          <div className="pieces-pending-title">📎 Pièces en attente de réception</div>
          <div className="pieces-pending-list">
            {pending.map((p) => (
              <div className="pieces-pending-item" key={p.id}>
                <span className="pieces-pending-icon">📄</span>
                <span className="pieces-pending-name" title={p.nom}>
                  {p.nom}
                  {p.nb_relances > 0 && (
                    <span style={{ fontWeight: 500, color: "#94a3b8" }}> · {p.nb_relances} relance(s)</span>
                  )}
                </span>
                <button className="pieces-pending-relance" onClick={() => onRelance(p.id)}>
                  🔔 Relancer
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="doc-preview">
        <div className="doc-preview-toolbar">
          <span
            style={{
              flex: 1,
              fontWeight: 600,
              color: "#1e293b",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {doc?.nom ?? "Aucun document sélectionné"}
          </span>
          <button className="dpt-btn" onClick={() => (doc ? setZoom(true) : toast("⚠️", "Aucun document sélectionné"))}>
            ⤢ Agrandir
          </button>
          <button className="dpt-btn" onClick={telecharger}>
            ⬇ Télécharger
          </button>
        </div>
        <div className="doc-canvas">
          {doc ? (
            <Apercu d={d} doc={doc} />
          ) : (
            <div style={{ color: "#94a3b8", fontSize: 13, textAlign: "center", padding: 40 }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>📄</div>
              Sélectionnez un document
              <br />
              pour l'afficher
            </div>
          )}
        </div>
      </div>

      {zoom && doc && (
        <div className="doc-zoom-overlay open" onClick={(e) => e.target === e.currentTarget && setZoom(false)}>
          <div className="doc-zoom-panel">
            <div className="doc-zoom-toolbar">
              <span className="doc-zoom-title">{doc.nom}</span>
              <button className="doc-zoom-btn" onClick={telecharger}>
                ⬇ Télécharger
              </button>
              <button className="doc-zoom-close" onClick={() => setZoom(false)}>
                ✕
              </button>
            </div>
            <div className="doc-zoom-body">
              <Apercu d={d} doc={doc} zoom />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
