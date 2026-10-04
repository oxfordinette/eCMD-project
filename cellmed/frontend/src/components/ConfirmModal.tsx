import { useState } from "react";

export function ConfirmModal({
  titre,
  message,
  libelle = "Confirmer",
  danger = true,
  onConfirm,
  onClose,
}: {
  titre: string;
  message: string;
  libelle?: string;
  danger?: boolean;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}) {
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  return (
    <div className="modal-overlay open" onClick={(e) => e.target === e.currentTarget && !envoi && onClose()}>
      <div className="modal" style={{ maxWidth: 420 }}>
        <div className="modal-title">{titre}</div>
        <div className="modal-sub">{message}</div>
        {erreur && <div className="modal-error">{erreur}</div>}
        <div className="modal-actions">
          <button className="modal-cancel" onClick={onClose} disabled={envoi}>
            Annuler
          </button>
          <button
            className={`modal-confirm ${danger ? "mc-red" : "mc-blue"}`}
            disabled={envoi}
            onClick={async () => {
              setEnvoi(true);
              try {
                await onConfirm();
              } catch (e) {
                setErreur((e as Error).message);
                setEnvoi(false);
              }
            }}
          >
            {envoi ? "…" : libelle}
          </button>
        </div>
      </div>
    </div>
  );
}
