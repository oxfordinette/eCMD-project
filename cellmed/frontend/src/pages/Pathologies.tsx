import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useApp } from "../AppContext";
import { PathologieModal } from "../components/PathologieModal";
import type { PathologieResume, Referentiels } from "../types";

export function catClass(cat: string | null): string {
  return (
    {
      "Ostéo-articulaire": "cat-osteo",
      Psychiatrique: "cat-psy",
      Cardiologique: "cat-cardio",
      Neurologique: "cat-neuro",
      "Gastro-entérologique": "cat-gastro",
    }[cat ?? ""] ?? "cat-other"
  );
}

export default function Pathologies() {
  const navigate = useNavigate();
  const { toast } = useApp();
  const [params, setParams] = useSearchParams();
  const vueListe = params.get("vue") === "liste" || params.has("groupe");
  const groupe = params.get("groupe") ?? "";

  const [groupes, setGroupes] = useState<{ groupe: string; nb: number }[]>([]);
  const [items, setItems] = useState<PathologieResume[]>([]);
  const [q, setQ] = useState("");
  const [categorie, setCategorie] = useState("");
  const [refs, setRefs] = useState<Referentiels | null>(null);
  const [modal, setModal] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.referentiels().then(setRefs).catch(() => setRefs(null));
    api.groupesPathologies().then(setGroupes).catch(() => setGroupes([]));
  }, []);

  useEffect(() => {
    setQ("");
    setCategorie("");
  }, [groupe, vueListe]);

  useEffect(() => {
    if (!vueListe) return;
    setLoading(true);
    const t = window.setTimeout(() => {
      api
        .pathologies({ q, groupe, categorie })
        .then(setItems)
        .catch((e: Error) => toast("⚠️", e.message))
        .finally(() => setLoading(false));
    }, 200);
    return () => window.clearTimeout(t);
  }, [vueListe, q, groupe, categorie, toast]);

  const total = groupes.reduce((n, g) => n + g.nb, 0);

  return (
    <div className="page">
      <div className="view-banner">
        <div className="vb-tag">Administration · Référentiel</div>
        <div className="vb-h1">Pathologies</div>
        <div className="vb-desc">
          Référentiel des pathologies reconnues — codes CIM-10, catégories, durées standard et documents associés.
        </div>
      </div>
      <div className="section-head">
        <div>
          <div className="sh-title">{vueListe ? "Liste des pathologies" : "Groupes de pathologies"}</div>
          <div className="sh-sub">
            {vueListe
              ? `${items.length} pathologie${items.length !== 1 ? "s" : ""}`
              : `${total} pathologie${total !== 1 ? "s" : ""} au total`}
          </div>
        </div>
        <div className="sh-actions">
          {vueListe && !groupe ? (
            <button className="btn btn-outline" onClick={() => setParams({})}>
              🧬 Afficher les groupes
            </button>
          ) : (
            <button className="btn btn-outline" onClick={() => setParams({ vue: "liste" })}>
              📋 Afficher toutes les pathologies
            </button>
          )}
          <button className="btn-add-patho" onClick={() => setModal(true)} disabled={!refs}>
            ＋ Ajouter une pathologie
          </button>
        </div>
      </div>

      {!vueListe ? (
        <div className="patho-groupes-grid">
          {groupes.map((g) => (
            <div className="patho-groupe-card" key={g.groupe} onClick={() => setParams({ groupe: g.groupe })}>
              <div className="patho-groupe-name">{g.groupe}</div>
              <div className="patho-groupe-count">
                <b>{g.nb}</b> pathologie{g.nb !== 1 ? "s" : ""}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <>
          <div style={{ margin: "0 36px 14px" }}>
            <button className="btn-back" onClick={() => setParams({})}>
              ← Retour aux groupes
            </button>
          </div>
          {groupe && (
            <div className="patho-groupe-chip show">
              <span>Groupe : {groupe}</span>
              <span className="patho-groupe-chip-close" onClick={() => setParams({ vue: "liste" })}>
                ✕
              </span>
            </div>
          )}
          <div className="filter-bar">
            <div className="search-wrap">
              <span className="search-ico">🔍</span>
              <input
                type="text"
                placeholder="Rechercher une pathologie, code CIM-10…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </div>
            <select className="filter-select" value={categorie} onChange={(e) => setCategorie(e.target.value)}>
              <option value="">Toutes catégories</option>
              {(refs?.categories ?? []).map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </div>
          <div className="patho-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Code CIM-10</th>
                  <th>Libellé</th>
                  <th>Catégorie</th>
                  <th>Durée std AT (j)</th>
                  <th>Documents</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center", padding: 40, color: "#94a3b8" }}>
                      Chargement…
                    </td>
                  </tr>
                ) : items.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center", padding: 40, color: "#94a3b8", fontSize: 13 }}>
                      Aucune pathologie trouvée
                    </td>
                  </tr>
                ) : (
                  items.map((p) => (
                    <tr key={p.code} onClick={() => navigate(`/pathologies/${encodeURIComponent(p.code)}`)}>
                      <td>
                        <span style={{ fontFamily: "monospace", fontSize: 12, fontWeight: 700, color: "var(--navy)" }}>
                          {p.code}
                        </span>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, color: "#1e293b" }}>{p.libelle}</div>
                        {p.synonymes && (
                          <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
                            {p.synonymes.split(",")[0].trim()}
                          </div>
                        )}
                      </td>
                      <td>
                        <span className={`patho-cat-badge ${catClass(p.categorie)}`}>{p.categorie ?? "—"}</span>
                      </td>
                      <td>
                        <span style={{ fontWeight: 700, color: "#1e293b" }}>{p.duree_std ?? "—"}</span>
                        <span style={{ fontSize: 11, color: "#94a3b8" }}> j</span>
                      </td>
                      <td>
                        <span className="patho-count-badge">
                          📄 {p.nb_documents} doc{p.nb_documents !== 1 ? "s" : ""}
                        </span>
                      </td>
                      <td style={{ textAlign: "right", color: "#cbd5e1", fontSize: 16 }}>→</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {modal && refs && (
        <PathologieModal
          groupes={refs.groupes}
          categories={refs.categories}
          groupeParDefaut={groupe || undefined}
          onClose={() => setModal(false)}
          onSave={async (p) => {
            const cree = await api.creerPathologie(p);
            setModal(false);
            toast("🧬", `Pathologie ${cree.code} ajoutée`);
            navigate(`/pathologies/${encodeURIComponent(cree.code)}`);
          }}
        />
      )}
    </div>
  );
}
