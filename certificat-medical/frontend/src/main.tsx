import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";
import Acces from "./acces/Acces";
import Formulaire from "./formulaire/Formulaire";
import "./styles.css";

function Confirmation() {
  const numero = (useLocation().state as { numero?: string } | null)?.numero;
  return (
    <div className="centered">
      <div style={{ maxWidth: 680 }}>
        <div className="success-icon">
          <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4.5 12.5l5 5L19.5 7" />
          </svg>
        </div>
        <h1 className="h1">Votre attestation a bien été transmise</h1>
        {numero && (
          <>
            <p className="lead" style={{ marginBottom: 0 }}>
              Référence de votre dossier :
            </p>
            <div className="numero">{numero}</div>
          </>
        )}
        {!numero && (
          <p className="lead" style={{ marginBottom: 0 }}>
            Vous allez recevoir un email de confirmation avec la référence de votre dossier.
          </p>
        )}
        <p className="lead">
          Votre dossier va être étudié par un gestionnaire. Vous serez informé(e) par email ou SMS si des pièces
          complémentaires sont nécessaires. Vous pouvez fermer cette page.
        </p>
      </div>
    </div>
  );
}

function SansLien() {
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
      </div>
      <div className="acces-right">
        <h2 className="h1">Accès par invitation</h2>
        <p className="lead">
          Pour remplir votre attestation, utilisez le lien personnel reçu par email ou SMS de la part de votre assureur.
        </p>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/acces/:token" element={<Acces />} />
        <Route path="/acces/:token/formulaire" element={<Formulaire />} />
        <Route path="/acces/:token/confirmation" element={<Confirmation />} />
        <Route path="*" element={<SansLien />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
