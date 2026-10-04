import { useEffect, useRef, useState } from "react";
import { fmtDateTime, initiales } from "../format";
import type { Commentaire } from "../types";

function cssRole(role: string | null): string {
  const r = (role ?? "").toLowerCase();
  if (r.includes("système") || r.includes("systeme")) return "is-system";
  if (r.includes("assuré") || r.includes("assure")) return "is-assure";
  return "";
}

export function Commentaires({
  commentaires,
  onSend,
}: {
  commentaires: Commentaire[];
  onSend: (texte: string) => Promise<void>;
}) {
  const [texte, setTexte] = useState("");
  const [envoi, setEnvoi] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [commentaires.length]);

  const envoyer = async () => {
    const t = texte.trim();
    if (!t || envoi) return;
    setEnvoi(true);
    try {
      await onSend(t);
      setTexte("");
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <div className="comments-panel">
      <div className="comments-list" ref={listRef}>
        {commentaires.length === 0 ? (
          <div className="comments-empty">
            Aucun commentaire pour le moment.
            <br />
            Soyez le premier à échanger sur ce dossier.
          </div>
        ) : (
          commentaires.map((c) => (
            <div className={`comment-item ${cssRole(c.role)}`} key={c.id}>
              <div className="comment-head">
                <div className="comment-avatar">{initiales(c.auteur)}</div>
                <div className="comment-author">{c.auteur}</div>
                {c.role && <div className="comment-role">{c.role}</div>}
                <div className="comment-date">{fmtDateTime(c.date)}</div>
              </div>
              <div className="comment-bubble" style={{ whiteSpace: "pre-wrap" }}>
                {c.texte}
              </div>
            </div>
          ))
        )}
      </div>
      <div className="comment-input-zone">
        <div className="comment-input-row">
          <textarea
            placeholder="Écrire un commentaire…"
            value={texte}
            onChange={(e) => setTexte(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                envoyer();
              }
            }}
          />
          <button className="comment-send-btn" onClick={envoyer} disabled={envoi || !texte.trim()}>
            Envoyer
          </button>
        </div>
      </div>
    </div>
  );
}
