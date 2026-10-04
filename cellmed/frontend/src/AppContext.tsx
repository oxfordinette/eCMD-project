import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { api } from "./api";
import type { Compteurs, Utilisateur } from "./types";

interface Ctx {
  user: Utilisateur | null;
  refreshUser: () => void;
  compteurs: Compteurs | null;
  refreshCompteurs: () => void;
  toast: (icon: string, msg: string) => void;
}

const AppCtx = createContext<Ctx | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Utilisateur | null>(null);
  const [compteurs, setCompteurs] = useState<Compteurs | null>(null);
  const [toastState, setToastState] = useState<{ icon: string; msg: string; show: boolean }>({
    icon: "",
    msg: "",
    show: false,
  });
  const timer = useRef<number>();

  const refreshCompteurs = useCallback(() => {
    api.compteurs().then(setCompteurs).catch(() => setCompteurs(null));
  }, []);

  const toast = useCallback((icon: string, msg: string) => {
    setToastState({ icon, msg, show: true });
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setToastState((t) => ({ ...t, show: false })), 3000);
  }, []);

  const refreshUser = useCallback(() => {
    api.me().then(setUser).catch(() => setUser(null));
  }, []);

  useEffect(() => {
    refreshUser();
    refreshCompteurs();
  }, [refreshUser, refreshCompteurs]);

  return (
    <AppCtx.Provider value={{ user, refreshUser, compteurs, refreshCompteurs, toast }}>
      {children}
      <div className={`toast ${toastState.show ? "show" : ""}`}>
        <span className="toast-icon">{toastState.icon}</span>
        <span>{toastState.msg}</span>
      </div>
    </AppCtx.Provider>
  );
}

export function useApp(): Ctx {
  const c = useContext(AppCtx);
  if (!c) throw new Error("useApp hors AppProvider");
  return c;
}
