import { useRef, useState } from "react";
import { api, type Brouillon, type Formulaire, type Piece } from "../api";
import { DateInput, Field, FileUp, InfoDocs, OuiNonField, Plus, Radios, Trash, aujourdhui } from "../ui";

export type Maj = <K extends keyof Omit<Brouillon, "documents">>(section: K, patch: Partial<Brouillon[K]>) => void;

interface Props {
  b: Brouillon;
  maj: Maj;
  f: Formulaire;
  pieces: Piece[];
}

const piecesEtape = (pieces: Piece[], etape: number) =>
  pieces.filter((p) => p.etape === etape && p.obligatoire).map((p) => p.libelle);

// ── 01 Administratif ─────────────────────────────────────────────────────

export function EtapeAdministratif({ b, maj, f }: Props) {
  const a = f.admin;
  const ad = b.administratif;
  const lecture = (label: string, v: string | null) => (
    <Field label={label}>
      <input className="input" value={v ?? "—"} readOnly />
    </Field>
  );
  return (
    <>
      <div className="card">
        <div className="row2">
          {lecture("Nom de l'entreprise", a.entreprise)}
          {lecture("Numéro de contrat", a.numero_contrat)}
        </div>
        {lecture("Nom de l'assureur", a.assureur)}
        <hr className="sep" />
        <div className="row2">
          {lecture("Nom", a.nom.toUpperCase())}
          {lecture("Prénom", a.prenom)}
        </div>
        <div className="row2">
          {lecture("Date de naissance", a.date_naissance.split("-").reverse().join("/"))}
          {lecture("Numéro de Sécurité sociale", a.nss_formate)}
        </div>
        <p className="help" style={{ marginTop: 0 }}>
          Ces informations proviennent de votre contrat. Une erreur ? <a href="mailto:">Contactez votre assureur</a>.
        </p>
      </div>
      <div className="card">
        <div className="row2">
          <Field label="Profession">
            <input className="input" value={ad.profession} onChange={(e) => maj("administratif", { profession: e.target.value })} />
          </Field>
          <Field label="Catégorie socioprofessionnelle">
            <select className="select" value={ad.college} onChange={(e) => maj("administratif", { college: e.target.value })}>
              <option value="">Sélectionnez une catégorie</option>
              <option>Cadre</option>
              <option>Non-cadre</option>
              <option>Agent de maîtrise</option>
            </select>
          </Field>
        </div>
        <Field label="Adresse">
          <input className="input" value={ad.adresse} onChange={(e) => maj("administratif", { adresse: e.target.value })} />
        </Field>
        <div className="row2">
          <Field label="Email">
            <input type="email" className="input" value={ad.email} onChange={(e) => maj("administratif", { email: e.target.value })} />
          </Field>
          <Field label="Téléphone">
            <input type="tel" className="input" value={ad.telephone} onChange={(e) => maj("administratif", { telephone: e.target.value })} />
          </Field>
        </div>
      </div>
    </>
  );
}

// ── 02 Arrêt de travail ──────────────────────────────────────────────────

function SelectPathologie({
  value,
  onChange,
  pathologies,
  placeholder,
}: {
  value?: string;
  onChange: (v: string) => void;
  pathologies: Formulaire["pathologies"];
  placeholder: string;
}) {
  const groupes = [...new Set(pathologies.map((p) => p.groupe))].sort();
  return (
    <select className={`select${value ? "" : " placeholder"}`} value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
      <option value="">{placeholder}</option>
      {groupes.map((g) => (
        <optgroup key={g} label={g}>
          {pathologies
            .filter((p) => p.groupe === g)
            .map((p) => (
              <option key={p.code} value={p.code}>
                {p.libelle}
              </option>
            ))}
        </optgroup>
      ))}
    </select>
  );
}

export function EtapeArret({ b, maj, f, pieces }: Props) {
  const a = b.arret;
  const autres = a.autres_pathologies ?? [];
  const setAutres = (v: string[]) => maj("arret", { autres_pathologies: v });
  return (
    <div className="card">
      <Field label="Date des premiers symptômes" required>
        <DateInput value={a.date_symptomes} max={aujourdhui()} onChange={(v) => maj("arret", { date_symptomes: v })} />
      </Field>
      <Field label="Date de début de l'arrêt de travail initial" required>
        <DateInput value={a.date_debut} onChange={(v) => maj("arret", { date_debut: v })} />
      </Field>
      <Field label="Date de fin prévisionnelle de l'arrêt" optional="(si connue)">
        <DateInput value={a.date_fin} onChange={(v) => maj("arret", { date_fin: v })} />
      </Field>
      <hr className="sep" />
      <Field label="Cause de l'arrêt de travail" required>
        <Radios
          value={a.cause}
          onChange={(v) => maj("arret", { cause: v })}
          options={[
            ["accident", "Accident"],
            ["maladie", "Maladie"],
            ["grossesse", "État de grossesse"],
          ]}
        />
      </Field>
      {a.cause === "accident" && (
        <>
          <Field label="Type d'accident" required>
            <Radios
              value={a.type_accident}
              onChange={(v) => maj("arret", { type_accident: v })}
              options={[
                ["travail", "Accident de travail"],
                ["vie_privee", "Accident de la vie privé"],
              ]}
            />
          </Field>
          <OuiNonField label="Celui-ci a-t-il été causé par un tiers ?" value={a.tiers} onChange={(v) => maj("arret", { tiers: v })} />
        </>
      )}
      {a.cause === "maladie" && (
        <OuiNonField label="S'agit-il d'une maladie professionnelle ?" value={a.maladie_pro} onChange={(v) => maj("arret", { maladie_pro: v })} />
      )}
      <hr className="sep" />
      <Field label="Pathologie à l'origine de l'arrêt de travail actuel" required>
        <SelectPathologie
          value={a.pathologie_code}
          onChange={(v) => maj("arret", { pathologie_code: v })}
          pathologies={f.pathologies}
          placeholder="Sélectionnez la pathologie"
        />
      </Field>
      <OuiNonField
        label="Avez-vous précedemment eu un arrêt de travail pour la même pathologie ?"
        value={a.arret_anterieur}
        onChange={(v) => maj("arret", { arret_anterieur: v })}
      />
      {autres.map((code, i) => (
        <div className="numbered" key={i}>
          <div className="numbered-n">{i + 1}</div>
          <div className="numbered-body">
            <label className="label">Autre pathologie à l'origine de l'arrêt de travail</label>
            <SelectPathologie
              value={code}
              onChange={(v) => setAutres(autres.map((x, k) => (k === i ? v : x)))}
              pathologies={f.pathologies.filter((p) => p.code !== a.pathologie_code)}
              placeholder="Sélectionner la pathologie"
            />
          </div>
          <button className="btn-trash" title="Retirer" onClick={() => setAutres(autres.filter((_, k) => k !== i))}>
            <Trash />
          </button>
        </div>
      ))}
      <button className="btn-link" onClick={() => setAutres([...autres, ""])}>
        <Plus /> Ajouter une pathologie
      </button>
      <InfoDocs libelles={piecesEtape(pieces, 2)} />
    </div>
  );
}

// ── 03 Antécédents & état ────────────────────────────────────────────────

export function EtapeAntecedents({ b, maj }: Props) {
  const a = b.antecedents;
  return (
    <div className="card">
      <OuiNonField label="Aviez-vous une pathologie avant cet arrêt ?" value={a.patho_avant} onChange={(v) => maj("antecedents", { patho_avant: v })}>
        <Field label="Pathologie antérieure" required>
          <input className="input" value={a.patho_anterieure ?? ""} placeholder="Précisez la pathologie" onChange={(e) => maj("antecedents", { patho_anterieure: e.target.value })} />
        </Field>
      </OuiNonField>
      <hr className="sep" />
      <OuiNonField
        label="Une autre pathologie consécutive est-elle apparue après le début de l'arrêt ?"
        value={a.patho_consecutive}
        onChange={(v) => maj("antecedents", { patho_consecutive: v })}
      >
        <Field label="Pathologie consécutive" required>
          <input className="input" value={a.patho_consecutive_detail ?? ""} placeholder="Précisez la pathologie" onChange={(e) => maj("antecedents", { patho_consecutive_detail: e.target.value })} />
        </Field>
      </OuiNonField>
      <hr className="sep" />
      <OuiNonField
        label="Bénéficiez-vous d'une prise en charge à 100 % pour raison médicale par un organisme de sécurité sociale (ALD) ?"
        value={a.ald}
        onChange={(v) => maj("antecedents", { ald: v })}
      />
      <hr className="sep" />
      <Field label="État de santé actuel" required>
        <textarea
          className="textarea"
          placeholder="Décrivez votre état de santé au moment de cette déclaration"
          value={a.etat_sante ?? ""}
          onChange={(e) => maj("antecedents", { etat_sante: e.target.value })}
        />
      </Field>
    </div>
  );
}

// ── 04 Soins & traitements ───────────────────────────────────────────────

export function EtapeSoins({ b, maj, pieces }: Props) {
  const s = b.soins;
  const trt = s.traitements?.length ? s.traitements : [{ nom: "", posologie: "" }];
  const setTrt = (v: { nom: string; posologie: string }[]) => maj("soins", { traitements: v });
  const infos = piecesEtape(pieces, 4);
  return (
    <div className="card">
      {trt.map((t, i) => (
        <div className="numbered" key={i}>
          <div className="numbered-n">{i + 1}</div>
          <div className="numbered-body row2">
            <div>
              <label className="label">
                Nom du traitement <span className="opt">(en cours ou prévu)</span>
              </label>
              <input className="input" placeholder="Ex : Paracétamol" value={t.nom} onChange={(e) => setTrt(trt.map((x, k) => (k === i ? { ...x, nom: e.target.value } : x)))} />
            </div>
            <div>
              <label className="label">Posologie</label>
              <input className="input" placeholder="Ex : 500mg - 3 fois par jour, si douleur" value={t.posologie} onChange={(e) => setTrt(trt.map((x, k) => (k === i ? { ...x, posologie: e.target.value } : x)))} />
            </div>
          </div>
          {trt.length > 1 && (
            <button className="btn-trash" title="Retirer" onClick={() => setTrt(trt.filter((_, k) => k !== i))}>
              <Trash />
            </button>
          )}
        </div>
      ))}
      <button className="btn btn-outline" onClick={() => setTrt([...trt, { nom: "", posologie: "" }])}>
        <Plus /> Ajouter un traitement
      </button>
      <hr className="sep" />
      <OuiNonField label="Avez-vous été suivi par un ou plusieurs spécialistes ?" value={s.specialistes} onChange={(v) => maj("soins", { specialistes: v })}>
        <Field label="Date de la dernière consultation" required>
          <DateInput value={s.specialiste_date} max={aujourdhui()} onChange={(v) => maj("soins", { specialiste_date: v })} />
        </Field>
        <Field label="Motif de la dernière consultation" required>
          <textarea className="textarea" placeholder="Veuillez préciser le motif de la consultation..." value={s.specialiste_motif ?? ""} onChange={(e) => maj("soins", { specialiste_motif: e.target.value })} />
        </Field>
      </OuiNonField>
      {s.specialistes === "oui" && <InfoDocs libelles={infos.filter((l) => l.includes("spécialiste"))} />}
      <hr className="sep" />
      <OuiNonField label="Avez-vous subi une hospitalisation ou une intervention chirurgicale ?" value={s.hospitalisation} onChange={(v) => maj("soins", { hospitalisation: v })}>
        <Field label="Date de l'hospitalisation" required>
          <DateInput value={s.hospitalisation_date} onChange={(v) => maj("soins", { hospitalisation_date: v })} />
        </Field>
        <Field label="Type d'hospitalisation" required>
          <input className="input" placeholder="Veuillez préciser le type d'hospitalisation" value={s.hospitalisation_type ?? ""} onChange={(e) => maj("soins", { hospitalisation_type: e.target.value })} />
        </Field>
      </OuiNonField>
      {s.hospitalisation === "oui" && <InfoDocs libelles={infos.filter((l) => l.toLowerCase().includes("hospitalisation"))} />}
    </div>
  );
}

// ── 05 Évolution & reprise ───────────────────────────────────────────────

export function EtapeEvolution({ b, maj, f, pieces }: Props) {
  const e = b.evolution;
  return (
    <div className="card">
      <OuiNonField label="Avez-vous repris votre activité ?" value={e.reprise} onChange={(v) => maj("evolution", { reprise: v })}>
        <Field label="À temps partiel ou plein ?" required>
          <Radios
            value={e.reprise_temps}
            onChange={(v) => maj("evolution", { reprise_temps: v })}
            options={[
              ["partiel", "Temps partiel"],
              ["plein", "Temps plein"],
            ]}
          />
        </Field>
        <Field label="Date de reprise effective" required>
          <DateInput value={e.reprise_date} onChange={(v) => maj("evolution", { reprise_date: v })} />
        </Field>
      </OuiNonField>
      <hr className="sep" />
      <OuiNonField label="Êtes-vous en invalidité ?" value={e.invalidite} onChange={(v) => maj("evolution", { invalidite: v })}>
        <Field label="Date de début d'invalidité" required>
          <DateInput value={e.invalidite_date} onChange={(v) => maj("evolution", { invalidite_date: v })} />
        </Field>
        <Field label="Catégorie d'invalidité" required>
          <select
            className={`select${e.invalidite_categorie ? "" : " placeholder"}`}
            style={{ maxWidth: 484 }}
            value={e.invalidite_categorie ?? ""}
            onChange={(ev) => maj("evolution", { invalidite_categorie: ev.target.value })}
          >
            <option value="">Sélectionnez une catégorie</option>
            {Object.entries(f.categories_invalidite).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </Field>
      </OuiNonField>
      <hr className="sep" />
      <OuiNonField label="Êtes-vous en incapacité permanente ?" value={e.incapacite} onChange={(v) => maj("evolution", { incapacite: v })}>
        <Field label="Date de début d'incapacité permanente" required>
          <DateInput value={e.incapacite_date} onChange={(v) => maj("evolution", { incapacite_date: v })} />
        </Field>
        <Field label="Taux d'incapacité permanente" required>
          <div className="percent">
            <input
              className="input"
              type="number"
              min={1}
              max={100}
              placeholder="0"
              value={e.incapacite_taux ?? ""}
              onChange={(ev) => maj("evolution", { incapacite_taux: ev.target.value })}
            />
            <span>%</span>
          </div>
        </Field>
      </OuiNonField>
      <hr className="sep" />
      <OuiNonField label="Êtes-vous à la retraite ?" value={e.retraite} onChange={(v) => maj("evolution", { retraite: v })}>
        <Field label="Date de début de retraite" required>
          <DateInput value={e.retraite_date} onChange={(v) => maj("evolution", { retraite_date: v })} />
        </Field>
      </OuiNonField>
      <hr className="sep" />
      <Field label="Observations complémentaires">
        <textarea
          className="textarea"
          placeholder="Toutes informations complémentaires utiles au traitement de votre dossier..."
          value={e.observations ?? ""}
          onChange={(ev) => maj("evolution", { observations: ev.target.value })}
        />
      </Field>
      <InfoDocs libelles={piecesEtape(pieces, 5)} />
    </div>
  );
}

// ── 06 Documents justificatifs ───────────────────────────────────────────

function ZoneDepot({ onFile, disabled }: { onFile: (f: File) => void; disabled?: boolean }) {
  const ref = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  return (
    <>
      <div
        className={`drop${over ? " over" : ""}`}
        role="button"
        tabIndex={0}
        aria-disabled={disabled}
        onClick={() => !disabled && ref.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && ref.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          [...e.dataTransfer.files].forEach(onFile);
        }}
      >
        <FileUp />
        <div>
          {disabled ? (
            "Envoi en cours…"
          ) : (
            <>
              <b>Glissez-déposez vos fichiers ici</b> ou cliquez pour sélectionner
            </>
          )}
        </div>
        <div className="hint">Formats acceptés : JPEG, PNG, PDF</div>
        <div className="hint">
          <b>Taille max : 10 Mo</b>
        </div>
      </div>
      <input
        ref={ref}
        type="file"
        multiple
        accept=".pdf,.jpg,.jpeg,.png"
        style={{ display: "none" }}
        onChange={(e) => {
          [...(e.target.files ?? [])].forEach(onFile);
          e.target.value = "";
        }}
      />
    </>
  );
}

export function EtapeDocuments({
  b,
  pieces,
  token,
  onEtat,
  erreurs,
}: Props & { token: string; onEtat: (e: Awaited<ReturnType<typeof api.deposer>>) => void; erreurs: string[] }) {
  const [envoi, setEnvoi] = useState<string | null>(null);
  const [erreur, setErreur] = useState<Record<string, string>>({});

  const deposer = async (categorie: string, fichier: File) => {
    if (fichier.size > 10 * 1048576) {
      setErreur({ ...erreur, [categorie]: `${fichier.name} : fichier trop volumineux (max 10 Mo)` });
      return;
    }
    setEnvoi(categorie);
    setErreur({ ...erreur, [categorie]: "" });
    try {
      onEtat(await api.deposer(token, categorie, fichier));
    } catch (e) {
      setErreur({ ...erreur, [categorie]: `${fichier.name} : ${(e as Error).message}` });
    } finally {
      setEnvoi(null);
    }
  };

  return (
    <div className="card">
      {pieces.map((p, i) => {
        const docs = b.documents.filter((d) => d.categorie === p.categorie);
        const manquant = p.obligatoire && erreurs.includes(p.libelle) && !docs.length;
        return (
          <div key={p.categorie}>
            {i > 0 && <div style={{ height: 34 }} />}
            <Field label={p.libelle} required={p.obligatoire} error={erreur[p.categorie] || (manquant ? "Ce document est requis." : null)}>
              <ZoneDepot onFile={(f) => deposer(p.categorie, f)} disabled={envoi === p.categorie} />
              {docs.length > 0 && (
                <div className="files">
                  {docs.map((d) => (
                    <div className="file" key={d.fichier_id}>
                      <span aria-hidden>{d.type === "img" ? "🖼️" : "📄"}</span>
                      <a href={api.urlDocument(token, d.fichier_id)} target="_blank" rel="noreferrer">
                        {d.nom}
                      </a>
                      <span className="size">{d.taille}</span>
                      <button
                        title="Retirer"
                        onClick={async () => onEtat(await api.retirer(token, d.fichier_id))}
                      >
                        <Trash />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </Field>
          </div>
        );
      })}
    </div>
  );
}
