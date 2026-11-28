"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  InMemoryWebStorage,
  UserManager,
  WebStorageStateStore,
  type User,
} from "oidc-client-ts";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  configured: boolean;
  signIn: () => Promise<void>;
  completeSignIn: () => Promise<void>;
  completeSilentSignIn: () => Promise<void>;
  signOut: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
  apiFetch: (path: string, init?: RequestInit) => Promise<Response>;
};

const AuthContext = createContext<AuthContextValue | null>(null);
let manager: UserManager | null = null;

function oidcConfigured() {
  return Boolean(
    process.env.NEXT_PUBLIC_OIDC_AUTHORITY &&
      process.env.NEXT_PUBLIC_OIDC_CLIENT_ID &&
      process.env.NEXT_PUBLIC_OIDC_API_SCOPE
  );
}

function getManager(): UserManager {
  if (manager) return manager;
  if (typeof window === "undefined") {
    throw new Error("OIDC manager is only available in the browser");
  }
  const authority = process.env.NEXT_PUBLIC_OIDC_AUTHORITY;
  const clientId = process.env.NEXT_PUBLIC_OIDC_CLIENT_ID;
  const apiScope = process.env.NEXT_PUBLIC_OIDC_API_SCOPE;
  if (!authority || !clientId || !apiScope) {
    throw new Error("Dashboard OIDC environment is not configured");
  }
  const redirectUri =
    process.env.NEXT_PUBLIC_OIDC_REDIRECT_URI ||
    `${window.location.origin}/auth/callback`;
  const silentRedirectUri =
    process.env.NEXT_PUBLIC_OIDC_SILENT_REDIRECT_URI ||
    `${window.location.origin}/auth/silent-callback`;
  const extraScope = process.env.NEXT_PUBLIC_OIDC_EXTRA_SCOPE?.trim();
  manager = new UserManager({
    authority,
    client_id: clientId,
    redirect_uri: redirectUri,
    silent_redirect_uri: silentRedirectUri,
    post_logout_redirect_uri:
      process.env.NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI ||
      window.location.origin,
    response_type: "code",
    disablePKCE: false,
    scope: ["openid", "profile", "email", apiScope, extraScope]
      .filter(Boolean)
      .join(" "),
    loadUserInfo: false,
    automaticSilentRenew: false,
    // Tokens stay in memory. OIDC state uses sessionStorage across the redirect.
    stateStore: new WebStorageStateStore({ store: window.sessionStorage }),
    userStore: new WebStorageStateStore({ store: new InMemoryWebStorage() }),
  });
  return manager;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const configured = oidcConfigured();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!configured) {
      setLoading(false);
      return;
    }
    const oidc = getManager();
    const loaded = (next: User) => setUser(next);
    const unloaded = () => setUser(null);
    oidc.events.addUserLoaded(loaded);
    oidc.events.addUserUnloaded(unloaded);
    oidc.getUser()
      .then((current) => setUser(current))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
    return () => {
      oidc.events.removeUserLoaded(loaded);
      oidc.events.removeUserUnloaded(unloaded);
    };
  }, [configured]);

  const signIn = useCallback(async () => {
    await getManager().signinRedirect();
  }, []);

  const completeSignIn = useCallback(async () => {
    const signedIn = await getManager().signinRedirectCallback();
    setUser(signedIn);
  }, []);

  const completeSilentSignIn = useCallback(async () => {
    await getManager().signinSilentCallback();
  }, []);

  const signOut = useCallback(async () => {
    const oidc = getManager();
    const current = await oidc.getUser();
    setUser(null);
    await oidc.signoutRedirect({ id_token_hint: current?.id_token });
  }, []);

  const getAccessToken = useCallback(async (): Promise<string | null> => {
    const oidc = getManager();
    let current = await oidc.getUser();
    if (!current) return null;
    if (current.expired) {
      try {
        current = await oidc.signinSilent();
      } catch {
        await oidc.signinRedirect();
        return null;
      }
    }
    return current?.access_token || null;
  }, []);

  const apiFetch = useCallback(
    async (path: string, init: RequestInit = {}) => {
      const token = await getAccessToken();
      if (!token) {
        await signIn();
        throw new Error("Sign-in required");
      }
      const headers = new Headers(init.headers);
      headers.set("Authorization", `Bearer ${token}`);
      const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const apiBase = base.endsWith("/") ? base.slice(0, -1) : base;
      const response = await fetch(`${apiBase}${path}`, {
        ...init,
        headers,
      });
      if (response.status === 401) {
        setUser(null);
        await getManager().removeUser();
      }
      if (!response.ok) {
        throw new Error(`API request failed (${response.status})`);
      }
      return response;
    },
    [getAccessToken, signIn],
  );

  const value = useMemo(
    () => ({
      user,
      loading,
      configured,
      signIn,
      completeSignIn,
      completeSilentSignIn,
      signOut,
      getAccessToken,
      apiFetch,
    }),
    [
      user,
      loading,
      configured,
      signIn,
      completeSignIn,
      completeSilentSignIn,
      signOut,
      getAccessToken,
      apiFetch,
    ],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

export function AuthControls() {
  const { user, loading, configured, signIn, signOut } = useAuth();
  if (!configured) {
    return <span className="text-xs text-amber-300">OIDC not configured</span>;
  }
  if (loading) return <span className="text-xs text-[#8888aa]">Checking session…</span>;
  return user ? (
    <div className="flex items-center gap-3">
      <span className="max-w-40 truncate text-xs text-[#8888aa]">
        {String(user.profile.email || user.profile.sub || "Signed in")}
      </span>
      <button
        onClick={() => void signOut()}
        className="rounded border border-[#3a3a4a] px-3 py-1 text-xs hover:bg-[#2a2a3a]"
      >
        Sign out
      </button>
    </div>
  ) : (
    <button
      onClick={() => void signIn()}
      className="rounded bg-indigo-600 px-3 py-1 text-xs font-medium hover:bg-indigo-500"
    >
      Sign in
    </button>
  );
}
