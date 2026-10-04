import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { useApp } from "../AppContext";
import { ActionModal, type TypeAction } from "../components/ActionModals";
import { Commentaires } from "../components/Commentaires";
import { DocViewer } from "../components/DocViewer";
import { Historique, Parcours } from "../components/Timeline";
import { UploadZone } from "../components/UploadZone";
import { fmtDate, val } from "../format";
import { STATUT_CONFIG, StatusBadge, urgenceClass } from "../statuts";
import type { ActionPayload, DossierDetail as TDossier, Referentiels } from "../types";

const TOASTS: Record<TypeAction, [string, string]> = {
  validate: ["✅", "Dossier validé et clôturé avec succès"],
  pieces: ["📎", "Demande de pièces envoyée à l'assuré"],
  avis: ["🩺", "Demande d'avis médical envoyée"],
  expertise: ["🔬", "Dossier transmis pour expertise médicale"],
};

function Field({
  label,
  value,
  className = "",
  span,
  pre,
}: {
  label: string;
  value: string;
  className?: string;
  span?: string;
  pre?: boolean;
}) {
  return (
    <div className="field" style={span ? { gridColumn: span } : undefined}>
      <label>{label}</label>
      <div
        className={`field-val ${className}`}
        style={pre ? { minHeight: 60, whiteSpace: "pre-wrap" } : undefined}
      >
        {value}
      </div>
    </div>
  );
}

function Card({ icon, title, children }: { icon: string; title: string; children: React.ReactNode }) {
  return (
    <div className="form-card">
      <div className="fc-header">
        <span className="fc-icon">{icon}</span>
        <span className="fc-title">{title}</span>
      </div>
      <div className="fc-body">{children}</div>
    </div>
  );
}

export default function DossierDetail() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { toast, refreshCompteurs } = useApp();
  const [d, setD] = useState<TDossier | null>(null);
  const [refs, setRefs] = useState<Referentiels | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [onglet, setOnglet] = useState<"docs" | "commentaires" | "historique">("docs");
  const [modal, setModal] = useState<TypeAction | null>(null);
  const [notes, setNotes] = useState("");
  const [dureeEstimee, setDureeEstimee] = useState("");
  const [saving, setSaving] = useState(false);

  const charger = useCallback(
    (dossier: TDossier) => {
      setD(dossier);
      setNotes(dossier.analyse_compte_rendu ?? "");
      setDureeEstimee(String(dossier.analyse_duree_estimee ?? dossier.duree ?? ""));
    },
    [setD],
  );

  useEffect(() => {
    setD(null);
    setErreur(null);
    setOnglet("docs");
    api.dossier(id).then(charger).catch((e: Error) => setErreur(e.message));
    api.referentiels().then(setRefs).catch(() => setRefs(null));
  }, [id, charger]);

  if (erreur) return <div className="error-box">Erreur : {erreur}</div>;
  if (!d) return <div className="loading">Chargement du dossier…</div>;

  const cfg = STATUT_CONFIG[d.status];
  const cloture = d.status === "clotures";

  const executer = async (payload: ActionPayload) => {
    const maj = await api.action(d.id, payload);
    charger(maj);
    setModal(null);
    refreshCompteurs();
    const [icon, msg] = TOASTS[payload.type];
    toast(icon, msg);
  };

  const enregistrerAnalyse = async () => {
    setSaving(true);
    try {
      charger(await api.analyse(d.id, notes, dureeEstimee === "" ? null : Number(dureeEstimee)));
      toast("💾", "Analyse enregistrée");
    } catch (e) {
      toast("⚠️", (e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const urgBadge = d.urgence === "Haute" ? "badge-red" : d.urgence === "Moyenne" ? "badge-orange" : "badge-gray";

  return (
    <div className="detail-layout">
      {/* Colonne principale */}
      <div className="detail-main">
        <div className="view-banner" style={{ padding: "20px 24px 16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <button
              className="btn-back"
              onClick={() => navigate(`/dossiers/${d.status}`)}
              style={{ background: "rgba(255,255,255,.15)", borderColor: "rgba(255,255,255,.3)", color: "#fff" }}
            >
              ← Retour
            </button>
            <div>
              <div className="vb-tag">Dossier CMD · {cfg.label}</div>
              <div className="vb-h1" style={{ fontSize: 20 }}>
                {d.id} — {d.nom}, {d.prenom}
              </div>
            </div>
            <div style={{ marginLeft: "auto" }}>
              <StatusBadge d={d} />{" "}
              <span className={`badge ${urgBadge}`} style={{ marginLeft: 6 }}>
                <span className={`urgency-dot urg-${urgenceClass(d.urgence)}`} />
                {d.urgence}
              </span>
            </div>
          </div>
        </div>

        <div style={{ padding: "20px 24px 0" }}>
          <Parcours d={d} />

          <Card icon="👤" title="Identité de l'assuré">
            <div className="form-grid cols3">
              <Field label="Nom" value={d.nom} />
              <Field label="Prénom" value={d.prenom} />
              <Field label="Date de naissance" value={fmtDate(d.date_naissance)} />
              <Field label="N° Sécurité Sociale" value={val(d.nss)} />
              <Field label="Société" value={val(d.societe)} />
              <Field label="N° Dossier sinistre" value={val(d.dossier_sinistre)} />
              <Field label="Profession" value={val(d.profession)} />
              <Field label="Collège" value={val(d.college)} />
              <Field label="Téléphone" value={val(d.telephone)} />
              <Field label="Email" value={val(d.email)} />
              <Field label="Adresse" value={val(d.adresse)} span="span 2" />
            </div>
          </Card>

          <Card icon="📑" title="Contrat de l'assuré">
            <div className="form-grid cols3">
              <Field label="N° Mercer" value={val(d.numero_mercer)} />
              <Field label="Partition" value={val(d.partition)} />
              <Field label="Assureur" value={val(d.assureur)} />
            </div>
          </Card>

          <Card icon="📋" title="Arrêt de travail déclaré">
            <div className="form-grid">
              <Field label="Date début arrêt" value={fmtDate(d.date_debut)} className="highlight" />
              <Field label="Date fin prévisionnelle" value={fmtDate(d.date_fin)} className="highlight" />
              <Field label="Type d'arrêt" value={val(d.type_arret)} />
              <Field label="Type de certificat" value={val(d.type_cert)} />
              <Field label="Durée estimée (jours)" value={d.duree != null ? `${d.duree} jours` : "—"} />
              <Field label="Temps partiel" value={val(d.temps_partiel)} />
            </div>
          </Card>

          <Card icon="🩺" title="Pathologie & informations médicales">
            <div className="form-grid">
              <Field label="Pathologie principale" value={val(d.patho)} />
              <Field label="Code CIM-10" value={val(d.cim10)} />
              <hr className="field-divider" />
              <Field label="État de santé" value={val(d.commentaire)} span="1/-1" pre />
              <Field label="Traitement en cours" value={val(d.traitement)} span="1/-1" pre />
              <hr className="field-divider" />
              <Field label="Hospitalisation / intervention chirurgicale" value={val(d.hospitalisation)} />
              <Field label="Précédent arrêt de travail pour la même pathologie" value={val(d.arret_anterieur)} />
              <Field label="Pathologie antérieure" value={val(d.patho_anterieure)} />
              <Field label="Pathologie consécutive" value={val(d.patho_consecutive)} />
              <Field label="Prise en charge ALD" value={val(d.ald)} />
            </div>
          </Card>

          {d.declaration && (
            <Card icon="📝" title="Déclaration de l'assuré (portail Certificat médical)">
              {d.declaration
                .filter((sec) => sec.etape >= 2 && sec.etape <= 5)
                .map((sec) => (
                  <div className="decl-section" key={sec.numero}>
                    <div className="decl-title">
                      <span>{sec.numero}</span> {sec.titre}
                    </div>
                    {sec.lignes.map((l) => (
                      <div className="decl-row" key={l.label}>
                        <div className="decl-label">{l.label}</div>
                        <div className={`decl-val${l.valeur === "--" ? " vide" : ""}`}>
                          {Array.isArray(l.valeur) ? l.valeur.map((x) => <div key={x}>• {x}</div>) : l.valeur}
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
            </Card>
          )}

          <Card icon="✏️" title="Analyse du gestionnaire">
            <div className="form-grid cols1">
              <div className="field">
                <label>Compte-rendu</label>
                <textarea
                  className="field-val editable"
                  rows={4}
                  placeholder="Saisir vos observations…"
                  value={notes}
                  disabled={cloture}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </div>
              <div className="field">
                <label>Durée estimée arrêt de travail (jours)</label>
                <input
                  type="number"
                  min={0}
                  className="field-val editable"
                  style={{ maxWidth: 160 }}
                  placeholder="ex: 21"
                  value={dureeEstimee}
                  disabled={cloture}
                  onChange={(e) => setDureeEstimee(e.target.value)}
                />
              </div>
              <div className="field">
                <label>Ajouter un document (ex : CR d'expertise)</label>
                <UploadZone
                  placeholderNom="Nom du document (optionnel, ex: CR d'expertise)"
                  onUpload={async (fichier, nom) => {
                    charger(await api.ajouterDocumentDossier(d.id, fichier, nom));
                    setOnglet("docs");
                    toast("📄", `Document "${nom ?? fichier.name}" ajouté au dossier`);
                  }}
                />
              </div>
              {!cloture && (
                <div className="analyse-actions">
                  <button className="btn btn-primary" onClick={enregistrerAnalyse} disabled={saving}>
                    {saving ? "Enregistrement…" : "💾 Enregistrer l'analyse"}
                  </button>
                </div>
              )}
            </div>
          </Card>

          <Card icon="🕐" title="Historique du dossier">
            <Historique evenements={d.evenements} />
          </Card>
        </div>
      </div>

      {/* Colonne latérale : documents / commentaires / historique + actions */}
      <div className="detail-sidebar">
        <div className="doc-tabs">
          <div className={`doc-tab ${onglet === "docs" ? "active" : ""}`} onClick={() => setOnglet("docs")}>
            Documents ({d.documents.length})
          </div>
          <div
            className={`doc-tab ${onglet === "commentaires" ? "active" : ""}`}
            onClick={() => setOnglet("commentaires")}
          >
            Commentaires ({d.commentaires.length})
          </div>
          <div className={`doc-tab ${onglet === "historique" ? "active" : ""}`} onClick={() => setOnglet("historique")}>
            Historique dossier
          </div>
        </div>

        {onglet === "docs" && (
          <DocViewer
            d={d}
            onRelance={async (pieceId) => {
              try {
                const maj = await api.relancer(d.id, pieceId);
                const p = maj.pieces_requises.find((x) => x.id === pieceId);
                charger(maj);
                toast("🔔", `Relance envoyée pour "${p?.nom ?? "la pièce"}"`);
              } catch (e) {
                toast("⚠️", (e as Error).message);
              }
            }}
          />
        )}
        {onglet === "commentaires" && (
          <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
            <Commentaires
              commentaires={d.commentaires}
              onSend={async (texte) => {
                try {
                  charger(await api.commenter(d.id, texte));
                  toast("💬", "Commentaire ajouté");
                } catch (e) {
                  toast("⚠️", (e as Error).message);
                  throw e;
                }
              }}
            />
          </div>
        )}
        {onglet === "historique" && (
          <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
            <Historique evenements={d.evenements} />
          </div>
        )}

        <div className="action-panel">
          <div className="ap-title">Actions disponibles</div>
          {cloture ? (
            <div className="closed-note">
              <b>Dossier clôturé.</b>
              {d.decision && (
                <>
                  <br />
                  Décision : {d.decision}
                  {d.duree_validee != null && ` — ${d.duree_validee} jours validés`}
                </>
              )}
            </div>
          ) : (
            <div className="ap-actions">
              <button className="ap-btn ap-btn-validate" disabled={!refs} onClick={() => setModal("validate")}>
                <span className="ap-btn-icon">✅</span> Valider le dossier
              </button>
              <button className="ap-btn ap-btn-pieces" disabled={!refs} onClick={() => setModal("pieces")}>
                <span className="ap-btn-icon">📎</span> Demander des pièces complémentaires
              </button>
              <button className="ap-btn ap-btn-avis" disabled={!refs} onClick={() => setModal("avis")}>
                <span className="ap-btn-icon">🩺</span> Demander un avis médical
              </button>
              <button className="ap-btn ap-btn-expertise" disabled={!refs} onClick={() => setModal("expertise")}>
                <span className="ap-btn-icon">🔬</span> Demander une expertise
              </button>
            </div>
          )}
        </div>
      </div>

      {modal && refs && (
        <ActionModal type={modal} dossier={d} refs={refs} onClose={() => setModal(null)} onConfirm={executer} />
      )}
    </div>
  );
}
