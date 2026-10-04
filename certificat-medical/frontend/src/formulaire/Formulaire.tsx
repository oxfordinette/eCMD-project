import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError, session, type Brouillon, type EtatFormulaire, type Formulaire as TF, type Section } from "../api";
import { Erreurs, Pencil, Steps } from "../ui";
import {
  EtapeAdministratif,
  EtapeAntecedents,
  EtapeArret,
  EtapeDocuments,
  EtapeEvolution,
  EtapeSoins,
  type Maj,
} from "./etapes";

const RUBRIQUES = [
  "Administratif",
  "Arrêt de travail",
  "Antécédents & état",
  "Soins & traitements",
  "Evolution & reprise",
  "Documents justificatifs",
  "Récapitulatif",
];

const PAGES: Record<number, { titre: string; lead: string }> = {
  1: { titre: "Informations administratives", lead: "Vérifiez vos informations et complétez vos coordonnées." },
  2: { titre: "Informations sur l'arrêt de travail", lead: "Informations relatives au début et à la cause de votre arrêt." },
  3: { titre: "Antécédents et état de santé actuel", lead: "Renseignez vos antécédents et l'état de santé au moment de cette déclaration." },
  4: {
    titre: "Soins et traitements",
    lead: "Renseignez vos traitements, résultats de consultations spécialisées et hospitalisations ou interventions chirurgicales.",
  },
  5: {
    titre: "Évolution et reprise envisagée",
    lead: "Indiquez les perspectives de reprise, d'invalidité ou de retraite ainsi que vos observations.",
  },
  6: { titre: "Documents justificatifs", lead: "Joignez les documents justificatifs nécessaires au traitement de votre dossier." },
  7: { titre: "Récapitulatif", lead: "Vérifiez l'ensemble des informations avant de transmettre votre attestation." },
};

function Valeur({ v }: { v: string | string[] }) {
  if (Array.isArray(v)) {
    return (
      <div className="recap-value">
        <ul>
          {v.map((x) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
      </div>
    );
  }
  return <div className={`recap-value${v === "--" ? " vide" : ""}`} style={{ whiteSpace: "pre-wrap" }}>{v}</div>;
}

export default function Formulaire() {
  const { token = "" } = useParams();
  const navigate = useNavigate();
  const [f, setF] = useState<TF | null>(null);
  const [b, setB] = useState<Brouillon | null>(null);
  const [etat, setEtat] = useState<Pick<EtatFormulaire, "pieces_requises" | "erreurs"> | null>(null);
  const [etape, setEtape] = useState(1);
  const [maxEtape, setMaxEtape] = useState(1);
  const [erreursVisibles, setErreursVisibles] = useState<string[]>([]);
  const [recap, setRecap] = useState<Section[] | null>(null);
  const [certifie, setCertifie] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sauvegarde, setSauvegarde] = useState<"" | "en cours" | "ok" | "erreur">("");
  const [erreurGlobale, setErreurGlobale] = useState<string | null>(null);
  const timer = useRef<number>();
  const dernier = useRef<Brouillon | null>(null);

  const expire = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError && (e.status === 401 || e.status === 409)) {
        session.clear(token);
        navigate(`/acces/${token}`, { replace: true });
        return true;
      }
      return false;
    },
    [navigate, token],
  );

  useEffect(() => {
    if (!session.get(token)) {
      navigate(`/acces/${token}`, { replace: true });
      return;
    }
    api
      .formulaire(token)
      .then((r) => {
        const brouillon: Brouillon = {
          ...r.brouillon,
          arret: r.brouillon.arret ?? {},
          antecedents: r.brouillon.antecedents ?? {},
          soins: r.brouillon.soins ?? {},
          evolution: r.brouillon.evolution ?? {},
          documents: r.brouillon.documents ?? [],
        };
        setF(r);
        setB(brouillon);
        dernier.current = brouillon;
        setEtat({ pieces_requises: r.pieces_requises, erreurs: r.erreurs });
        setEtape(r.etape);
        setMaxEtape(r.etape);
      })
      .catch((e) => expire(e) || setErreurGlobale((e as Error).message));
  }, [token, navigate, expire]);

  const sauver = useCallback(
    async (brouillon: Brouillon, et: number) => {
      window.clearTimeout(timer.current);
      setSauvegarde("en cours");
      try {
        const r = await api.enregistrer(token, brouillon, et);
        setEtat({ pieces_requises: r.pieces_requises, erreurs: r.erreurs });
        setSauvegarde("ok");
        return r;
      } catch (e) {
        if (!expire(e)) setSauvegarde("erreur");
        throw e;
      }
    },
    [token, expire],
  );

  const maj: Maj = (section, patch) => {
    setB((prev) => {
      if (!prev) return prev;
      const next = { ...prev, [section]: { ...prev[section], ...patch } };
      dernier.current = next;
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => sauver(next, etape).catch(() => undefined), 800);
      return next;
    });
  };

  const allerA = async (cible: number) => {
    if (!b) return;
    setErreursVisibles([]);
    try {
      await sauver(dernier.current ?? b, cible);
    } catch {
      return;
    }
    setEtape(cible);
    setMaxEtape((m) => Math.max(m, cible));
    window.scrollTo({ top: 0 });
    if (cible === 7) {
      setRecap(null);
      api
        .recapitulatif(token)
        .then((r) => setRecap(r.sections))
        .catch((e) => expire(e) || setErreurGlobale((e as Error).message));
    }
  };

  const suivant = async () => {
    if (!b) return;
    setBusy(true);
    try {
      const r = await sauver(dernier.current ?? b, etape);
      const errs = r.erreurs[String(etape)] ?? [];
      if (errs.length) {
        setErreursVisibles(errs);
        return;
      }
      await allerA(etape + 1);
    } catch {
      /* déjà signalé */
    } finally {
      setBusy(false);
    }
  };

  const soumettre = async () => {
    setBusy(true);
    setErreurGlobale(null);
    try {
      const r = await api.soumettre(token);
      session.clear(token);
      navigate(`/acces/${token}/confirmation`, { replace: true, state: { numero: r.numero_dossier } });
    } catch (e) {
      if (expire(e)) return;
      const detail = (e as ApiError).detail as { erreurs?: Record<string, string[]> } | undefined;
      const premiere = detail?.erreurs ? Number(Object.keys(detail.erreurs)[0]) : null;
      setErreurGlobale(
        premiere ? `${(e as Error).message} : voir la rubrique ${RUBRIQUES[premiere - 1]}.` : (e as Error).message,
      );
    } finally {
      setBusy(false);
    }
  };

  if (erreurGlobale && !f) return <div className="spinner">{erreurGlobale}</div>;
  if (!f || !b || !etat) return <div className="spinner">Chargement de votre dossier…</div>;

  const page = PAGES[etape];
  const props = { b, maj, f, pieces: etat.pieces_requises };
  const fait = (i: number) => i < maxEtape && !(etat.erreurs[String(i)]?.length);

  return (
    <div className="form-layout">
      <aside className="form-side">
        <div className="side-title">RUBRIQUES</div>
        <Steps items={RUBRIQUES} current={etape} done={fait} light onSelect={(i) => allerA(i)} />
        <div className="saving" aria-live="polite">
          {sauvegarde === "en cours" && "Enregistrement…"}
          {sauvegarde === "ok" && "✓ Brouillon enregistré"}
          {sauvegarde === "erreur" && "⚠ Enregistrement impossible"}
        </div>
      </aside>

      <main className="form-main">
        <div className="kicker">{etape}/7</div>
        <h1 className="h1">{page.titre}</h1>
        <p className="lead">{page.lead}</p>

        {etape === 1 && <EtapeAdministratif {...props} />}
        {etape === 2 && <EtapeArret {...props} />}
        {etape === 3 && <EtapeAntecedents {...props} />}
        {etape === 4 && <EtapeSoins {...props} />}
        {etape === 5 && <EtapeEvolution {...props} />}
        {etape === 6 && (
          <EtapeDocuments
            {...props}
            token={token}
            erreurs={erreursVisibles}
            onEtat={(r) => {
              setB((prev) => (prev ? { ...prev, documents: r.brouillon.documents } : prev));
              if (dernier.current) dernier.current = { ...dernier.current, documents: r.brouillon.documents };
              setEtat({ pieces_requises: r.pieces_requises, erreurs: r.erreurs });
            }}
          />
        )}
        {etape === 7 &&
          (recap ? (
            <>
              {recap.map((s) => (
                <section className="recap" key={s.numero}>
                  <div className="recap-head">
                    <span className="recap-num">{s.numero}</span>
                    <span className="recap-title">{s.titre}</span>
                    <button className="recap-edit" onClick={() => allerA(s.etape)}>
                      <Pencil /> Modifier
                    </button>
                  </div>
                  {s.lignes.map((l) => (
                    <div className="recap-row" key={l.label}>
                      <div className="recap-label">{l.label}</div>
                      <Valeur v={l.valeur} />
                    </div>
                  ))}
                </section>
              ))}
              <label className="certify">
                <input type="checkbox" checked={certifie} onChange={(e) => setCertifie(e.target.checked)} />
                <span>
                  Je certifie sur l'honneur l'exactitude des informations déclarées et j'accepte qu'elles soient transmises à
                  mon assureur pour l'étude de mon dossier.
                </span>
              </label>
            </>
          ) : (
            <div className="spinner">Préparation du récapitulatif…</div>
          ))}

        {etape !== 6 && <Erreurs items={erreursVisibles} />}
        {etape === 6 && erreursVisibles.length > 0 && (
          <Erreurs items={erreursVisibles.map((e) => `Document requis : ${e}`)} />
        )}
        {erreurGlobale && <div className="errors">{erreurGlobale}</div>}

        <div className="actions">
          {etape > 1 ? (
            <button className="btn btn-secondary" onClick={() => allerA(etape - 1)} disabled={busy}>
              Retour
            </button>
          ) : (
            <span />
          )}
          {etape < 7 ? (
            <button className="btn btn-primary" onClick={suivant} disabled={busy}>
              Suivant
            </button>
          ) : (
            <button className="btn btn-primary" onClick={soumettre} disabled={!certifie || busy || !recap}>
              {busy ? "Transmission…" : "Transmettre mon attestation"}
            </button>
          )}
        </div>
      </main>
    </div>
  );
}
