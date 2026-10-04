import { useEffect, useState } from "react";
import { api } from "../api";
import type { ActionPayload, DossierDetail, Pathologie, Referentiels } from "../types";

export type TypeAction = "validate" | "pieces" | "expertise" | "avis";

interface Props {
  type: TypeAction;
  dossier: DossierDetail;
  refs: Referentiels;
  onClose: () => void;
  onConfirm: (payload: ActionPayload) => Promise<void>;
}

export function ActionModal({ type, dossier, refs, onClose, onConfirm }: Props) {
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  // Valider
  const [decision, setDecision] = useState(refs.decisions[0] ?? "");
  const [duree, setDuree] = useState<string>(String(dossier.analyse_duree_estimee ?? dossier.duree ?? ""));
  const [commentaireVal, setCommentaireVal] = useState("");
  // Pièces
  const [patho, setPatho] = useState<Pathologie | null>(null);
  const [pathoCharge, setPathoCharge] = useState(false);
  const [docSel, setDocSel] = useState("");
  const [autreDoc, setAutreDoc] = useState("");
  const [pieces, setPieces] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const [delai, setDelai] = useState(14);
  // Expertise / avis
  const [medecinId, setMedecinId] = useState<number>(refs.medecins[0]?.id ?? 0);
  const [typeExp, setTypeExp] = useState(refs.types_expertise[0] ?? "");
  const [motif, setMotif] = useState("");
  const [delaiAvis, setDelaiAvis] = useState(refs.delais_avis[1] ?? refs.delais_avis[0] ?? "");

  useEffect(() => {
    if (type !== "pieces" || !dossier.cim10) {
      setPathoCharge(true);
      return;
    }
    api
      .pathologie(dossier.cim10)
      .then(setPatho)
      .catch(() => setPatho(null))
      .finally(() => setPathoCharge(true));
  }, [type, dossier.cim10]);

  const ajouterPiece = (nom: string) => {
    const n = nom.trim();
    if (n && !pieces.includes(n)) setPieces([...pieces, n]);
  };

  const confirmer = async () => {
    setErreur(null);
    let payload: ActionPayload;
    if (type === "validate") {
      payload = {
        type,
        decision,
        duree_validee: duree === "" ? null : Number(duree),
        commentaire: commentaireVal || undefined,
      };
    } else if (type === "pieces") {
      if (!pieces.length) {
        setErreur("Ajoutez au moins une pièce à demander.");
        return;
      }
      payload = { type, pieces, message: message || undefined, delai_jours: delai };
    } else if (type === "expertise") {
      payload = { type, medecin_id: medecinId, type_expertise: typeExp, motif: motif || undefined };
    } else {
      payload = { type, medecin_id: medecinId, motif: motif || undefined, delai: delaiAvis };
    }
    setEnvoi(true);
    try {
      await onConfirm(payload);
    } catch (e) {
      setErreur((e as Error).message);
      setEnvoi(false);
    }
  };

  const selectMedecin = (
    <div className="modal-field">
      <label>Médecin conseil</label>
      <select value={medecinId} onChange={(e) => setMedecinId(Number(e.target.value))}>
        {refs.medecins.map((m) => (
          <option key={m.id} value={m.id}>
            {m.nom} — {m.specialite}
          </option>
        ))}
      </select>
    </div>
  );

  const footer = (label: string, cls: string) => (
    <>
      {erreur && <div className="modal-error">{erreur}</div>}
      <div className="modal-actions">
        <button className="modal-cancel" onClick={onClose} disabled={envoi}>
          Annuler
        </button>
        <button className={`modal-confirm ${cls}`} onClick={confirmer} disabled={envoi}>
          {envoi ? "Envoi…" : label}
        </button>
      </div>
    </>
  );

  return (
    <div className="modal-overlay open" onClick={(e) => e.target === e.currentTarget && !envoi && onClose()}>
      <div className="modal">
        {type === "validate" && (
          <>
            <div className="modal-title">✅ Valider le dossier</div>
            <div className="modal-sub">
              Confirmez la validation du dossier. Une notification sera envoyée à l'assuré et au gestionnaire
              prévoyance.
            </div>
            <div className="modal-field">
              <label>Décision médicale</label>
              <select value={decision} onChange={(e) => setDecision(e.target.value)}>
                {refs.decisions.map((d) => (
                  <option key={d}>{d}</option>
                ))}
              </select>
            </div>
            <div className="modal-field">
              <label>Durée validée CellMed (jours)</label>
              <input type="number" min={0} value={duree} onChange={(e) => setDuree(e.target.value)} placeholder="ex: 21" />
            </div>
            <div className="modal-field">
              <label>Commentaire de clôture (optionnel)</label>
              <textarea
                rows={3}
                value={commentaireVal}
                onChange={(e) => setCommentaireVal(e.target.value)}
                placeholder="Observations pour le dossier…"
              />
            </div>
            {footer("Confirmer la validation", "mc-green")}
          </>
        )}

        {type === "pieces" && (
          <>
            <div className="modal-title">📎 Demander des pièces complémentaires</div>
            <div className="modal-sub">
              Précisez les documents manquants. L'assuré recevra une notification par e-mail et SMS.
            </div>
            <div className="modal-field">
              <label>Documents liés à la pathologie</label>
              <div style={{ display: "flex", gap: 8 }}>
                <select
                  style={{ flex: 1 }}
                  value={docSel}
                  disabled={!patho?.documents.length}
                  onChange={(e) => setDocSel(e.target.value)}
                >
                  {!pathoCharge ? (
                    <option>Chargement…</option>
                  ) : patho?.documents.length ? (
                    <>
                      <option value="">— Sélectionner un document —</option>
                      {patho.documents.map((d) => (
                        <option key={d.id} value={d.nom}>
                          {d.nom} {d.taille ? `(${d.taille})` : ""}
                        </option>
                      ))}
                    </>
                  ) : (
                    <option value="">Aucun document référencé pour cette pathologie</option>
                  )}
                </select>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ flexShrink: 0 }}
                  onClick={() => {
                    ajouterPiece(docSel);
                    setDocSel("");
                  }}
                >
                  ＋ Ajouter
                </button>
              </div>
              <div className="pieces-doc-hint">
                {patho
                  ? `Documents issus du référentiel pathologie : ${patho.libelle} (${patho.code})`
                  : pathoCharge
                    ? `${dossier.patho ?? ""} (${dossier.cim10 ?? "—"}) — aucun document type associé dans le référentiel.`
                    : ""}
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                <input
                  type="text"
                  placeholder="Autre document (saisie libre)"
                  value={autreDoc}
                  onChange={(e) => setAutreDoc(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      ajouterPiece(autreDoc);
                      setAutreDoc("");
                    }
                  }}
                />
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ flexShrink: 0 }}
                  onClick={() => {
                    ajouterPiece(autreDoc);
                    setAutreDoc("");
                  }}
                >
                  ＋ Ajouter
                </button>
              </div>
              <div className="pieces-doc-chips">
                {pieces.length === 0 ? (
                  <span className="pieces-doc-empty">Aucun document sélectionné.</span>
                ) : (
                  pieces.map((p) => (
                    <span className="pieces-doc-chip" key={p}>
                      📄 {p}
                      <span
                        className="pieces-doc-chip-del"
                        title="Retirer"
                        onClick={() => setPieces(pieces.filter((x) => x !== p))}
                      >
                        ✕
                      </span>
                    </span>
                  ))
                )}
              </div>
            </div>
            <div className="modal-field">
              <label>Message personnalisé (optionnel)</label>
              <textarea
                rows={3}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Message à transmettre à l'assuré…"
              />
            </div>
            <div className="modal-field">
              <label>Délai de réponse</label>
              <select value={delai} onChange={(e) => setDelai(Number(e.target.value))}>
                {refs.delais_pieces.map((j) => (
                  <option key={j} value={j}>
                    {j} jours
                  </option>
                ))}
              </select>
            </div>
            {footer("Envoyer la demande", "mc-orange")}
          </>
        )}

        {type === "expertise" && (
          <>
            <div className="modal-title">🔬 Demander une expertise</div>
            <div className="modal-sub">
              Le dossier sera transmis au médecin conseil pour une expertise médicale indépendante.
            </div>
            {selectMedecin}
            <div className="modal-field">
              <label>Type d'expertise</label>
              <select value={typeExp} onChange={(e) => setTypeExp(e.target.value)}>
                {refs.types_expertise.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </div>
            <div className="modal-field">
              <label>Motif de la demande</label>
              <textarea
                rows={3}
                value={motif}
                onChange={(e) => setMotif(e.target.value)}
                placeholder="Précisez le motif de la demande d'expertise…"
              />
            </div>
            {footer("Transmettre au médecin", "mc-purple")}
          </>
        )}

        {type === "avis" && (
          <>
            <div className="modal-title">🩺 Demander un avis médical</div>
            <div className="modal-sub">
              Le dossier sera soumis au médecin conseil pour avis médical avant toute décision.
            </div>
            {selectMedecin}
            <div className="modal-field">
              <label>Motif de la demande d'avis</label>
              <textarea
                rows={3}
                value={motif}
                onChange={(e) => setMotif(e.target.value)}
                placeholder="Précisez le motif de la demande d'avis médical…"
              />
            </div>
            <div className="modal-field">
              <label>Délai souhaité</label>
              <select value={delaiAvis} onChange={(e) => setDelaiAvis(e.target.value)}>
                {refs.delais_avis.map((d) => (
                  <option key={d}>{d}</option>
                ))}
              </select>
            </div>
            {footer("Envoyer la demande", "mc-teal")}
          </>
        )}
      </div>
    </div>
  );
}
