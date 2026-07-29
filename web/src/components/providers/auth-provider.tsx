"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { api, getToken, setToken as persistToken } from "@/lib/api";
import type { DocumentRow, User } from "@/lib/types";

export type UsageInfo = {
  questions_last_hour: number;
  questions_limit: number;
  uploads_last_hour: number;
  uploads_limit: number;
  documents_owned: number;
  documents_limit: number;
};

type AuthContextValue = {
  booting: boolean;
  token: string | null;
  user: User | null;
  isAdmin: boolean;
  usage: UsageInfo | null;
  usageLabel: string;
  docs: DocumentRow[];
  readyDocs: DocumentRow[];
  afterAuth: (access: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<User | null>;
  refreshDocs: () => Promise<DocumentRow[]>;
  refreshUsage: () => Promise<void>;
  setDocs: React.Dispatch<React.SetStateAction<DocumentRow[]>>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [booting, setBooting] = useState(true);
  const [token, setTok] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const [docs, setDocs] = useState<DocumentRow[]>([]);

  // Read via ref, not the `token` state, so these callbacks (and afterAuth/the
  // mount effect below that depends on it) keep a stable identity across
  // renders — afterAuth itself calls setTok() partway through, and a `[token]`
  // dependency here previously made afterAuth's own identity change mid-call,
  // re-triggering the mount effect and running the whole login sequence twice
  // (confirmed: every endpoint afterAuth calls was hit exactly twice on login).
  const tokenRef = useRef<string | null>(null);
  tokenRef.current = token;

  const refreshDocs = useCallback(async (t?: string | null) => {
    const access = t ?? tokenRef.current;
    if (!access) return [] as DocumentRow[];
    const list = await api<DocumentRow[]>("/documents", { token: access });
    setDocs(list);
    return list;
  }, []);

  const refreshUsage = useCallback(async (t?: string | null) => {
    const access = t ?? tokenRef.current;
    if (!access) return;
    try {
      const u = await api<UsageInfo>("/account/usage", { token: access });
      setUsage(u);
    } catch {
      setUsage(null);
    }
  }, []);

  const afterAuth = useCallback(
    async (access: string) => {
      persistToken(access);
      setTok(access);
      const me = await api<User>("/auth/me", { token: access });
      setUser(me);
      await refreshDocs(access);
      await refreshUsage(access);
      try {
        await api("/admin/stats", { token: access });
        setIsAdmin(true);
      } catch {
        setIsAdmin(false);
      }
      setBooting(false);
    },
    [refreshDocs, refreshUsage]
  );

  useEffect(() => {
    const existing = getToken();
    if (!existing) {
      setBooting(false);
      return;
    }
    afterAuth(existing).catch(() => {
      persistToken(null);
      setTok(null);
      setUser(null);
      setBooting(false);
    });
  }, [afterAuth]);

  const logout = useCallback(async () => {
    try {
      if (token) await api("/auth/logout", { method: "POST", token });
    } catch {
      /* ignore */
    }
    persistToken(null);
    setTok(null);
    setUser(null);
    setDocs([]);
    setUsage(null);
    setIsAdmin(false);
  }, [token]);

  const refreshUser = useCallback(async () => {
    if (!token) return null;
    const me = await api<User>("/auth/me", { token });
    setUser(me);
    return me;
  }, [token]);

  const readyDocs = useMemo(
    () => docs.filter((d) => (d.status || "").toUpperCase() === "READY"),
    [docs]
  );

  const usageLabel = usage
    ? `Questions ${usage.questions_last_hour}/${usage.questions_limit} · Uploads ${usage.uploads_last_hour}/${usage.uploads_limit} · Docs ${usage.documents_owned}/${usage.documents_limit}`
    : "";

  const value = useMemo(
    () => ({
      booting,
      token,
      user,
      isAdmin,
      usage,
      usageLabel,
      docs,
      readyDocs,
      afterAuth,
      logout,
      refreshUser,
      refreshDocs,
      refreshUsage,
      setDocs,
    }),
    [
      booting,
      token,
      user,
      isAdmin,
      usage,
      usageLabel,
      docs,
      readyDocs,
      afterAuth,
      logout,
      refreshUser,
      refreshDocs,
      refreshUsage,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
