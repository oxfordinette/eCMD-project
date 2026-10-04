import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, fichierUrl } from "../api";
import { useApp } from "../AppContext";
import { ConfirmModal } from "../components/ConfirmModal";
import { PathologieModal } from "../components/PathologieModal";
import { UploadZone } from "../components/UploadZone";
import type { Pathologie, PathologieDocument, Referentiels } from "../types";
import { catClass } from "./Pathologies";

export default function PathologieDetail() {
  const { code = "" } = useParams();
  const navigate = useNavigate();
  const { toast } = useApp();
  const [p, setP] = useState<Pathologie | null>(null);
  const [refs, setRefs] = useState<Referentiels | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [edition, setEdition] = useState(false);
  const [aSupprimer, setASupprimer] = useState<PathologieDocument | null>(null);

  useEffect(() => {
    setP(null);
    api.pathologie(code).then(setP).catch((e: Error) => setErreur(e.message));
    api.referentiels().then(setRefs).catch(() => setRefs(null));
  }, [code]);

  if (erreur) return <div className="error-box">Erreur : {erreur}</div>;
  if (!p) return <div className="loading">Chargement…</div>;

  const retour = () => navigate(`/pathologies?groupe=${encodeURIComponent(p.groupe)}`);

  return (
    <div className="patho-detail-layout">
      <div className="patho-detail-main">
        <div
          className="view-banner"
          style={{ borderRadius: 10, marginBottom: 24, padding: "20px 24px 18px" }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <button
              className="btn-back"
              onClick={retour}
              style={{ background: "rgba(255,255,255,.15)", borderColor: "rgba(255,255,255,.3)", color: "#fff" }}
            >
              ← Retour
            </button>
            <div>
              <div className="vb-tag">Administration · {p.categorie ?? "Pathologie"}</div>
              <div className="vb-h1" style={{ fontSize: 20 }}>
                {p.code} — {p.libelle}
              </div>
            </div>
            <button className="patho-edit-btn" onClick={() => setEdition(true)} disabled={!refs}>
              ✏️ Modifier
            </button>
          </div>
        </div>

        <div className="patho-info-grid">
          <div className="patho-field">
            <div className="patho-field-label">Code CIM-10</div>
            <div className="patho-field-value" style={{ fontFamily: "monospace", fontSize: 18, color: "var(--navy)" }}>
              {p.code}
            </div>
          </div>
          <div className="patho-field">
            <div className="patho-field-label">Catégorie</div>
            <div className="patho-field-value">
              <span className={`patho-cat-badge ${catClass(p.categorie)}`}>{p.categorie ?? "—"}</span>
            </div>
          </div>
          <div className="patho-field full">
            <div className="patho-field-label">Libellé officiel</div>
            <div className="patho-field-value" style={{ fontSize: 16 }}>
              {p.libelle}
            </div>
          </div>
          <div className="patho-field">
            <div className="patho-field-label">Groupe</div>
            <div className="patho-field-value">{p.groupe}</div>
          </div>
          <div className="patho-field">
            <div className="patho-field-label">Durée standard AT (jours)</div>
            <div className="patho-field-value" style={{ fontSize: 22, color: "var(--teal)" }}>
              {p.duree_std ?? "—"} <span style={{ fontSize: 14, fontWeight: 500, color: "#64748b" }}>jours</span>
            </div>
          </div>
        </div>
        <div className="patho-field" style={{ marginBottom: 20 }}>
          <div className="patho-field-label" style={{ marginBottom: 8 }}>
            Synonymes / Termes associés
          </div>
          <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.7 }}>{p.synonymes || "—"}</div>
        </div>
        <div className="patho-field" style={{ marginBottom: 20 }}>
          <div className="patho-field-label" style={{ marginBottom: 8 }}>
            Commentaire médical
          </div>
          <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
            {p.commentaire || "—"}
          </div>
        </div>
      </div>

      <div className="patho-detail-side">
        <div style={{ padding: "14px 16px", borderBottom: "1px solid #e2e8f0", background: "#f8fafc", flexShrink: 0 }}>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: 1,
              color: "#94a3b8",
              marginBottom: 2,
            }}
          >
            Documents complémentaires
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#1e293b" }}>
            {p.documents.length} document{p.documents.length !== 1 ? "s" : ""}
          </div>
        </div>
        <div className="patho-doc-list">
          {p.documents.length === 0 ? (
            <div style={{ textAlign: "center", padding: "32px 16px", color: "#94a3b8", fontSize: 12.5 }}>
              Aucun document associé
            </div>
          ) : (
            p.documents.map((d) => (
              <div className="patho-doc-item" key={d.id}>
                <div
                  className={`patho-doc-icon ${d.type === "pdf" ? "patho-doc-pdf" : d.type === "img" ? "patho-doc-img" : "patho-doc-other"}`}
                >
                  {d.type === "pdf" ? "📄" : d.type === "img" ? "🖼️" : "📎"}
                </div>
                <div className="patho-doc-info">
                  <div className="patho-doc-name" title={d.nom}>
                    {d.a_fichier ? (
                      <a href={fichierUrl("pathologie-document", d.id)} target="_blank" rel="noreferrer">
                        {d.nom}
                      </a>
                    ) : (
                      d.nom
                    )}
                  </div>
                  <div className="patho-doc-size">
                    {d.taille}
                    {!d.a_fichier && " · document type (sans fichier)"}
                  </div>
                </div>
                <span className="patho-doc-del" title="Supprimer" onClick={() => setASupprimer(d)}>
                  ✕
                </span>
              </div>
            ))
          )}
        </div>
        <div className="patho-add-doc">
          <div className="patho-add-doc-title">Ajouter un document</div>
          <UploadZone
            onUpload={async (fichier, nom) => {
              setP(await api.ajouterDocumentPathologie(p.code, fichier, nom));
              toast("📄", `Document "${nom ?? fichier.name}" ajouté`);
            }}
          />
        </div>
      </div>

      {edition && refs && (
        <PathologieModal
          initial={p}
          groupes={refs.groupes}
          categories={refs.categories}
          onClose={() => setEdition(false)}
          onSave={async (maj) => {
            setP(await api.modifierPathologie(p.code, maj));
            setEdition(false);
            toast("✅", "Pathologie mise à jour");
          }}
        />
      )}
      {aSupprimer && (
        <ConfirmModal
          titre="🗑️ Supprimer le document"
          message={`Supprimer « ${aSupprimer.nom} » de cette pathologie ? Il ne sera plus proposé dans les demandes de pièces.`}
          libelle="Supprimer"
          onClose={() => setASupprimer(null)}
          onConfirm={async () => {
            setP(await api.supprimerDocumentPathologie(p.code, aSupprimer.id));
            setASupprimer(null);
            toast("🗑️", "Document supprimé");
          }}
        />
      )}
    </div>
  );
}
