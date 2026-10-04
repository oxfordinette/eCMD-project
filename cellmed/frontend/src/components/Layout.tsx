import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useApp } from "../AppContext";
import { STATUTS, STATUT_CONFIG } from "../statuts";

function SbItem({ to, children, end }: { to: string; children: React.ReactNode; end?: boolean }) {
  return (
    <NavLink to={to} end={end} className={({ isActive }) => `sb-item${isActive ? " active" : ""}`}>
      {children}
    </NavLink>
  );
}

export default function Layout() {
  const { user, compteurs, toast } = useApp();
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    document.getElementById("app-main")?.scrollTo(0, 0);
  }, [location.pathname]);

  useEffect(() => {
    const close = () => setMenuOpen(false);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);

  const go = (path: string) => {
    setMenuOpen(false);
    navigate(path);
  };

  return (
    <>
      <header id="app-header">
        <div className="h-logo">
          <div className="h-mark">M</div>
          <div className="h-name">CELLMED</div>
        </div>
        <span className="h-sub">Gestion des Dossiers CMD — Certificat Médical Dématérialisé</span>
        <div
          className="h-user"
          style={{ cursor: "pointer", position: "relative" }}
          title="Mon compte"
          onClick={(e) => {
            e.stopPropagation();
            setMenuOpen((o) => !o);
          }}
        >
          <div>
            {user?.nom ?? "…"}, {user?.role ?? ""}
          </div>
          <div className="h-avatar">{user?.initiales ?? ""}</div>
          {menuOpen && (
            <div className="h-user-menu" onClick={(e) => e.stopPropagation()}>
              <div className="h-user-menu-header">
                <div className="h-avatar" style={{ background: "var(--navy)", borderColor: "var(--navy)" }}>
                  {user?.initiales}
                </div>
                <div>
                  <div className="hum-name">{user?.nom}</div>
                  <div className="hum-role">{user?.role}</div>
                </div>
              </div>
              <div className="h-user-menu-sep" />
              <div className="h-user-menu-item" onClick={() => go("/parametres")}>
                <span>⚙️</span>
                <span>Paramètres</span>
              </div>
              <div className="h-user-menu-item" onClick={() => go("/utilisateurs")}>
                <span>👤</span>
                <span>Gestion des utilisateurs</span>
              </div>
              <div className="h-user-menu-sep" />
              <div
                className="h-user-menu-item hum-logout"
                onClick={() => {
                  setMenuOpen(false);
                  toast("👋", "Déconnexion : disponible avec le SSO");
                }}
              >
                <span>🚪</span>
                <span>Déconnexion</span>
              </div>
            </div>
          )}
        </div>
      </header>

      <nav id="app-sidebar">
        <div className="sb-group">
          <div className="sb-group-title">Tableau de bord</div>
          <SbItem to="/" end>
            <span>🏠</span>
            <span>Accueil</span>
          </SbItem>
        </div>
        <div className="sb-group">
          <div className="sb-group-title">Dossiers</div>
          {STATUTS.map((s) => (
            <SbItem key={s} to={`/dossiers/${s}`}>
              <span className="sb-dot" style={{ background: STATUT_CONFIG[s].couleur }} />
              <span>{STATUT_CONFIG[s].sidebar}</span>
              <span className={`sb-count ${STATUT_CONFIG[s].cnt}`}>{compteurs ? compteurs[s] ?? 0 : "…"}</span>
            </SbItem>
          ))}
        </div>
        <div className="sb-group">
          <div className="sb-group-title">Outils</div>
          <SbItem to="/recherche">
            <span>🔍</span>
            <span>Recherche avancée</span>
          </SbItem>
          <SbItem to="/statistiques">
            <span>📊</span>
            <span>Statistiques</span>
          </SbItem>
        </div>
        <div className="sb-group">
          <div className="sb-group-title">Administration</div>
          <SbItem to="/pathologies">
            <span>🧬</span>
            <span>Pathologies</span>
          </SbItem>
          <SbItem to="/utilisateurs">
            <span>👤</span>
            <span>Utilisateurs</span>
          </SbItem>
        </div>
      </nav>

      <main id="app-main">
        <Outlet />
      </main>
    </>
  );
}
