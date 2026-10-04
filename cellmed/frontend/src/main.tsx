import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppProvider } from "./AppContext";
import Layout from "./components/Layout";
import Accueil from "./pages/Accueil";
import DossierDetail from "./pages/DossierDetail";
import ListeDossiers from "./pages/ListeDossiers";
import Parametres from "./pages/Parametres";
import PathologieDetail from "./pages/PathologieDetail";
import Pathologies from "./pages/Pathologies";
import Recherche from "./pages/Recherche";
import Statistiques from "./pages/Statistiques";
import Utilisateurs from "./pages/Utilisateurs";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Accueil />} />
            <Route path="dossiers/:statut" element={<ListeDossiers />} />
            <Route path="dossier/:id" element={<DossierDetail />} />
            <Route path="recherche" element={<Recherche />} />
            <Route path="statistiques" element={<Statistiques />} />
            <Route path="pathologies" element={<Pathologies />} />
            <Route path="pathologies/:code" element={<PathologieDetail />} />
            <Route path="utilisateurs" element={<Utilisateurs />} />
            <Route path="parametres" element={<Parametres />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </AppProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
