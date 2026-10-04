import { useRef, useState } from "react";

const ACCEPT = ".pdf,.jpg,.jpeg,.png,.doc,.docx";
const MAX_MO = 10;

/** Zone de dépôt (clic ou glisser-déposer) + nom optionnel du document. */
export function UploadZone({
  onUpload,
  placeholderNom = "Nom du document (optionnel)",
  accent = "teal",
}: {
  onUpload: (fichier: File, nom?: string) => Promise<void>;
  placeholderNom?: string;
  accent?: "teal" | "blue";
}) {
  const input = useRef<HTMLInputElement>(null);
  const [nom, setNom] = useState("");
  const [survol, setSurvol] = useState(false);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const envoyer = async (f: File | undefined) => {
    if (!f || envoi) return;
    setErreur(null);
    if (f.size > MAX_MO * 1048576) {
      setErreur(`Fichier trop volumineux (max ${MAX_MO} Mo)`);
      return;
    }
    setEnvoi(true);
    try {
      await onUpload(f, nom.trim() || undefined);
      setNom("");
    } catch (e) {
      setErreur((e as Error).message);
    } finally {
      setEnvoi(false);
      if (input.current) input.current.value = "";
    }
  };

  return (
    <div>
      <div
        className={`patho-upload-zone${survol ? " drag" : ""}${accent === "blue" ? " upload-blue" : ""}`}
        onClick={() => input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setSurvol(true);
        }}
        onDragLeave={() => setSurvol(false)}
        onDrop={(e) => {
          e.preventDefault();
          setSurvol(false);
          envoyer(e.dataTransfer.files[0]);
        }}
      >
        <div className="patho-upload-icon">{envoi ? "⏳" : "📄"}</div>
        <div className="patho-upload-text">
          {envoi ? (
            "Envoi en cours…"
          ) : (
            <>
              <strong>Cliquez pour parcourir</strong> ou glissez un fichier ici
            </>
          )}
        </div>
        <div style={{ fontSize: 10.5, color: "#94a3b8", marginTop: 4 }}>PDF, images, Word — max {MAX_MO} Mo</div>
      </div>
      <input
        ref={input}
        type="file"
        style={{ display: "none" }}
        accept={ACCEPT}
        onChange={(e) => envoyer(e.target.files?.[0])}
      />
      <div style={{ marginTop: 8 }}>
        <input
          type="text"
          className="upload-label-input"
          placeholder={placeholderNom}
          value={nom}
          onChange={(e) => setNom(e.target.value)}
        />
      </div>
      {erreur && <div className="upload-error">{erreur}</div>}
    </div>
  );
}
