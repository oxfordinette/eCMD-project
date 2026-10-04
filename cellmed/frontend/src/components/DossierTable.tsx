import { useNavigate } from "react-router-dom";
import { fmtDate } from "../format";
import { StatusBadge, Urgence } from "../statuts";
import type { DossierResume } from "../types";

/** Tableau complet (vue liste par statut). */
export function DossierTable({ items, loading }: { items: DossierResume[]; loading?: boolean }) {
  const navigate = useNavigate();
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Dossier</th>
            <th>Assuré</th>
            <th>Société</th>
            <th>Pathologie</th>
            <th>Type</th>
            <th>Date soumission</th>
            <th>Urgence</th>
            <th>Statut</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={8} style={{ textAlign: "center", padding: 40, color: "#94a3b8" }}>
                Chargement…
              </td>
            </tr>
          ) : items.length === 0 ? (
            <tr>
              <td colSpan={8} style={{ textAlign: "center", padding: 40, color: "#94a3b8" }}>
                Aucun dossier trouvé
              </td>
            </tr>
          ) : (
            items.map((d) => (
              <tr key={d.id} onClick={() => navigate(`/dossier/${d.id}`)}>
                <td>
                  <div className="td-id">{d.id}</div>
                </td>
                <td>
                  <div className="td-name">
                    {d.nom}, {d.prenom}
                  </div>
                  <div style={{ fontSize: 10.5, color: "#94a3b8" }}>{fmtDate(d.date_naissance)}</div>
                </td>
                <td>{d.societe}</td>
                <td>
                  {d.patho}
                  <br />
                  <span style={{ fontSize: 10.5, color: "#94a3b8" }}>{d.cim10}</span>
                </td>
                <td>
                  <span className="badge badge-blue">{d.type}</span>
                </td>
                <td>{fmtDate(d.date_soumission)}</td>
                <td>
                  <Urgence u={d.urgence} />
                </td>
                <td>
                  <StatusBadge d={d} />
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
