import { useState } from "react";
import type { Pathologie, PathologieIn } from "../types";

export function PathologieModal({
  initial,
  groupes,
  categories,
  groupeParDefaut,
  onClose,
  onSave,
}: {
  initial?: Pathologie | null;
  groupes: string[];
  categories: string[];
  groupeParDefaut?: string;
  onClose: () => void;
  onSave: (p: PathologieIn) => Promise<void>;
}) {
  const edition = !!initial;
  const [p, setP] = useState<PathologieIn>({
    code: initial?.code ?? "",
    groupe: initial?.groupe ?? groupeParDefaut ?? groupes[0] ?? "",
    libelle: initial?.libelle ?? "",
    categorie: initial?.categorie ?? categories[0] ?? null,
    duree_std: initial?.duree_std ?? null,
    synonymes: initial?.synonymes ?? "",
    commentaire: initial?.commentaire ?? "",
  });
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const set =
    <K extends keyof PathologieIn>(k: K) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setP({ ...p, [k]: e.target.value });

  const enregistrer = async () => {
    if (!p.code.trim() || !p.libelle.trim() || !p.groupe) {
      setErreur("Le code CIM-10, le libellé et le groupe sont obligatoires.");
      return;
    }
    setEnvoi(true);
    setErreur(null);
    try {
      await onSave({
        ...p,
        code: p.code.trim().toUpperCase(),
        duree_std: p.duree_std === null || (p.duree_std as unknown) === "" ? null : Number(p.duree_std),
      });
    } catch (e) {
      setErreur((e as Error).message);
      setEnvoi(false);
    }
  };

  return (
    <div className="modal-overlay open" onClick={(e) => e.target === e.currentTarget && !envoi && onClose()}>
      <div className="modal modal-wide">
        <div className="modal-title">🧬 {edition ? "Modifier la pathologie" : "Ajouter une pathologie"}</div>
        <div className="modal-sub">
          Référentiel utilisé pour l'analyse des dossiers et les demandes de pièces complémentaires.
        </div>
        <div className="modal-grid">
          <div className="modal-field">
            <label>Code CIM-10</label>
            <input value={p.code} onChange={set("code")} placeholder="ex: M51.1" disabled={edition} />
          </div>
          <div className="modal-field">
            <label>Durée standard AT (jours)</label>
            <input
              type="number"
              min={0}
              value={p.duree_std ?? ""}
              onChange={set("duree_std")}
              placeholder="ex: 28"
            />
          </div>
          <div className="modal-field full">
            <label>Libellé officiel</label>
            <input value={p.libelle} onChange={set("libelle")} placeholder="ex: Lombosciatique L4-L5" />
          </div>
          <div className="modal-field">
            <label>Groupe</label>
            <select value={p.groupe} onChange={set("groupe")}>
              {groupes.map((g) => (
                <option key={g}>{g}</option>
              ))}
            </select>
          </div>
          <div className="modal-field">
            <label>Catégorie</label>
            <select value={p.categorie ?? ""} onChange={set("categorie")}>
              {categories.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </div>
          <div className="modal-field full">
            <label>Synonymes / termes associés</label>
            <input value={p.synonymes ?? ""} onChange={set("synonymes")} placeholder="Séparés par des virgules" />
          </div>
          <div className="modal-field full">
            <label>Commentaire médical</label>
            <textarea rows={3} value={p.commentaire ?? ""} onChange={set("commentaire")} />
          </div>
        </div>
        {erreur && <div className="modal-error">{erreur}</div>}
        <div className="modal-actions">
          <button className="modal-cancel" onClick={onClose} disabled={envoi}>
            Annuler
          </button>
          <button className="modal-confirm mc-blue" onClick={enregistrer} disabled={envoi}>
            {envoi ? "Enregistrement…" : "Enregistrer"}
          </button>
        </div>
      </div>
    </div>
  );
}
