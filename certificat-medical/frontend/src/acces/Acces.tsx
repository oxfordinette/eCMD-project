import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError, session } from "../api";
import { Field, Steps } from "../ui";

const ETAPES = ["Language", "Vérification d'identité", "Code de vérification", "Vérification du code"];

const Phone = () => (
  <svg width="68" height="94" viewBox="0 0 68 94" fill="none" stroke="currentColor" strokeWidth="5" aria-hidden>
    <rect x="3" y="3" width="62" height="88" rx="9" />
    <circle cx="34" cy="74" r="2.5" fill="currentColor" stroke="none" />
  </svg>
);
const Mail = () => (
  <svg width="96" height="76" viewBox="0 0 96 76" fill="none" stroke="currentColor" strokeWidth="5" strokeLinejoin="round" aria-hidden>
    <rect x="3" y="3" width="90" height="70" rx="8" />
    <path d="M5 8l43 32L91 8" />
  </svg>
);
const Refresh = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden>
    <path d="M4 12a8 8 0 108-8M4 4v5h5" />
  </svg>
);

function FlagFR() {
  return (
    <span className="flag">
      <span style={{ flex: 1, background: "#1e40d6" }} />
      <span style={{ flex: 1, background: "#fff" }} />
      <span style={{ flex: 1, background: "#d62e2e" }} />
    </span>
  );
}
function FlagEN() {
  return (
    <span className="flag" style={{ background: "#1e3a8a", position: "relative" }}>
      <span style={{ position: "absolute", inset: "8px 0", background: "#fff" }} />
      <span style={{ position: "absolute", inset: "9px 0", background: "#d62e2e" }} />
      <span style={{ position: "absolute", top: 0, bottom: 0, left: 12, width: 6, background: "#fff" }} />
      <span style={{ position: "absolute", top: 0, bottom: 0, left: 13, width: 4, background: "#d62e2e" }} />
    </span>
  );
}

export default function Acces() {
  const { token = "" } = useParams();
  const navigate = useNavigate();
  const [etape, setEtape] = useState(0); // 0 = chargement
  const [langue, setLangue] = useState("fr");
  const [dob, setDob] = useState("");
  const [canaux, setCanaux] = useState<{ sms: string | null; email: string | null }>({ sms: null, email: null });
  const [canal, setCanal] = useState<"sms" | "email" | null>(null);
  const [envoi, setEnvoi] = useState<{ destination: string; code_dev: string | null } | null>(null);
  const [code, setCode] = useState<string[]>(Array(6).fill(""));
  const [erreur, setErreur] = useState<string | null>(null);
  const [fatal, setFatal] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inputs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    api
      .etat(token)
      .then((e) => {
        if (e.soumise) {
          navigate(`/acces/${token}/confirmation`, { replace: true, state: { numero: e.numero_dossier } });
          return;
        }
        setLangue(e.langue);
        setEtape(1);
      })
      .catch((e: Error) => setFatal(e.message));
  }, [token, navigate]);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setErreur(null);
    try {
      await fn();
    } catch (e) {
      setErreur(e instanceof ApiError ? e.message : "Une erreur est survenue. Merci de réessayer.");
    } finally {
      setBusy(false);
    }
  };

  const valider = () =>
    run(async () => {
      await api.langue(token, langue);
      setEtape(2);
    });
  const verifierIdentite = () =>
    run(async () => {
      const c = await api.identite(token, dob);
      setCanaux(c);
      setCanal(c.sms ? (c.email ? null : "sms") : "email");
      setEtape(3);
    });
  const envoyerCode = (c: "sms" | "email") =>
    run(async () => {
      const r = await api.code(token, c);
      setCanal(c);
      setEnvoi(r);
      setCode(Array(6).fill(""));
      setEtape(4);
      setTimeout(() => inputs.current[0]?.focus(), 50);
    });
  const verifierCode = () =>
    run(async () => {
      const r = await api.verifier(token, code.join(""));
      session.set(token, r.session);
      navigate(`/acces/${token}/formulaire`);
    });

  const saisir = (i: number, v: string) => {
    const chiffres = v.replace(/\D/g, "");
    if (chiffres.length > 1) {
      // collage d'un code complet
      const next = Array(6)
        .fill("")
        .map((_, k) => chiffres[k] ?? "");
      setCode(next);
      inputs.current[Math.min(chiffres.length, 5)]?.focus();
      return;
    }
    const next = [...code];
    next[i] = chiffres;
    setCode(next);
    if (chiffres && i < 5) inputs.current[i + 1]?.focus();
  };

  if (fatal) {
    return (
      <div className="acces">
        <div className="acces-left">
          <h1 className="acces-title">Portail d'attestation d'arrêt de travail</h1>
        </div>
        <div className="acces-right">
          <h2 className="h1">Lien invalide</h2>
          <p className="lead">{fatal}</p>
        </div>
      </div>
    );
  }

  const autreCanal = canal === "sms" ? (canaux.email ? "email" : null) : canaux.sms ? "sms" : null;

  return (
    <div className="acces">
      <div className="acces-left">
        <h1 className="acces-title">
          Portail
          <br />
          d'attestation
          <br />
          d'arrêt de travail
        </h1>
        <Steps items={ETAPES} current={etape} done={(i) => i < etape} />
      </div>

      <div className="acces-right">
        {etape === 0 && <div className="spinner">Chargement…</div>}

        {etape === 1 && (
          <>
            <div className="kicker">1/4</div>
            <h2 className="h1">Bienvenue</h2>
            <p className="lead">
              Pour accéder à votre espace, vous devrez vérifier votre identité en saisissant votre date de naissance,
              puis confirmer votre accès via un code de vérification envoyé par SMS ou e-mail.
            </p>
            <div className="card">
              <Field label="Choisissez votre langue">
                <div className="lang">
                  {langue === "en" ? <FlagEN /> : <FlagFR />}
                  <select className="select" value={langue} onChange={(e) => setLangue(e.target.value)}>
                    <option value="fr">Français</option>
                    <option value="en">English</option>
                  </select>
                </div>
              </Field>
            </div>
            <div className="actions end">
              <button className="btn btn-primary" onClick={valider} disabled={busy}>
                Valider
              </button>
            </div>
          </>
        )}

        {etape === 2 && (
          <>
            <div className="kicker">2/4</div>
            <h2 className="h1">Vérification de votre identité</h2>
            <p className="lead">Saisissez votre date de naissance.</p>
            <div className="card">
              <Field label="Date de naissance" required error={erreur}>
                <input
                  type="date"
                  className="input"
                  value={dob}
                  max={new Date().toISOString().slice(0, 10)}
                  onChange={(e) => setDob(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && dob && verifierIdentite()}
                />
              </Field>
            </div>
            <p className="help">
              Vos informations ne correspondent pas ? <a href="mailto:">Contactez votre assureur</a> pour les corriger.
            </p>
            <div className="actions">
              <button className="btn btn-secondary" onClick={() => setEtape(1)}>
                Retour
              </button>
              <button className="btn btn-primary" onClick={verifierIdentite} disabled={!dob || busy}>
                Continuer
              </button>
            </div>
          </>
        )}

        {etape === 3 && (
          <>
            <div className="kicker">3/4</div>
            <h2 className="h1">Comment recevoir votre code ?</h2>
            <p className="lead">Choisissez le canal sur lequel vous souhaitez recevoir votre code unique à 6 chiffres.</p>
            <div className="card">
              <div className="canaux">
                <button
                  className={`canal${canal === "sms" ? " selected" : ""}`}
                  disabled={!canaux.sms}
                  onClick={() => setCanal("sms")}
                  aria-pressed={canal === "sms"}
                >
                  <Phone />
                  <span className="canal-title">SMS</span>
                  <span className="canal-dest">{canaux.sms ?? "Aucun numéro enregistré"}</span>
                </button>
                <button
                  className={`canal${canal === "email" ? " selected" : ""}`}
                  disabled={!canaux.email}
                  onClick={() => setCanal("email")}
                  aria-pressed={canal === "email"}
                >
                  <Mail />
                  <span className="canal-title">Email</span>
                  <span className="canal-dest">{canaux.email ?? "Aucun email enregistré"}</span>
                </button>
              </div>
              {erreur && <div className="field-error">{erreur}</div>}
            </div>
            <p className="help">
              Vous ne reconnaissez pas ces coordonnées ? <a href="mailto:">Contactez votre assureur</a> pour les mettre
              à jour.
            </p>
            <div className="actions">
              <button className="btn btn-secondary" onClick={() => setEtape(2)}>
                Retour
              </button>
              <button className="btn btn-primary" onClick={() => canal && envoyerCode(canal)} disabled={!canal || busy}>
                Envoyer le code
              </button>
            </div>
          </>
        )}

        {etape === 4 && envoi && (
          <>
            <div className="kicker">4/4</div>
            <h2 className="h1">Saisir votre code</h2>
            <p className="lead">
              Un code a été envoyé par <b style={{ color: "var(--text)" }}>{canal === "sms" ? "SMS" : "email"}</b>{" "}
              {canal === "sms" ? "au numéro" : "à l'adresse"} <b style={{ color: "var(--text)" }}>{envoi.destination}</b>
            </p>
            {envoi.code_dev && (
              <div className="demo-code">
                Mode démonstration (aucun envoi réel) : votre code est <b>{envoi.code_dev}</b>
              </div>
            )}
            <div className="card">
              <Field label="Code de vérification">
                <div className={`otp${erreur ? " error" : ""}`}>
                  {code.map((c, i) => (
                    <input
                      key={i}
                      ref={(el) => (inputs.current[i] = el)}
                      inputMode="numeric"
                      autoComplete={i === 0 ? "one-time-code" : "off"}
                      maxLength={6}
                      value={c}
                      aria-label={`Chiffre ${i + 1}`}
                      onChange={(e) => saisir(i, e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Backspace" && !code[i] && i > 0) inputs.current[i - 1]?.focus();
                        if (e.key === "Enter" && code.every(Boolean)) verifierCode();
                      }}
                    />
                  ))}
                </div>
              </Field>
              {erreur && <div className="field-error" style={{ marginTop: -20, marginBottom: 20 }}>{erreur}</div>}
              <button
                className="btn btn-secondary btn-block"
                disabled={busy}
                onClick={() => envoyerCode(autreCanal ?? canal!)}
              >
                <Refresh /> Renvoyer un code par {(autreCanal ?? canal) === "sms" ? "SMS" : "email"}
              </button>
            </div>
            <div className="actions">
              <button className="btn btn-secondary" onClick={() => setEtape(3)}>
                Retour
              </button>
              <button className="btn btn-primary" onClick={verifierCode} disabled={!code.every(Boolean) || busy}>
                Accéder à mon espace
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
