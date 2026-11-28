"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function OidcCallback() {
  const router = useRouter();
  const { configured } = useAuth();
  const [error, setError] = useState("");

  useEffect(() => {
    if (!configured) {
      setError("OIDC is not configured for this dashboard.");
      return;
    }
    let active = true;
    import("oidc-client-ts").then(async ({ UserManager, WebStorageStateStore, InMemoryWebStorage }) => {
      const authority = process.env.NEXT_PUBLIC_OIDC_AUTHORITY;
      const clientId = process.env.NEXT_PUBLIC_OIDC_CLIENT_ID;
      const apiScope = process.env.NEXT_PUBLIC_OIDC_API_SCOPE;
      if (!authority || !clientId || !apiScope) throw new Error("Missing OIDC configuration");
      const userManager = new UserManager({
        authority,
        client_id: clientId,
        redirect_uri: process.env.NEXT_PUBLIC_OIDC_REDIRECT_URI || `${window.location.origin}/auth/callback`,
        post_logout_redirect_uri: process.env.NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI || window.location.origin,
        response_type: "code",
        scope: `openid profile email ${apiScope}`,
        loadUserInfo: false,
        stateStore: new WebStorageStateStore({ store: window.sessionStorage }),
        userStore: new WebStorageStateStore({ store: new InMemoryWebStorage() }),
      });
      await userManager.signinRedirectCallback();
      if (active) router.replace("/");
    }).catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : "OIDC callback failed");
    });
    return () => {
      active = false;
    };
  }, [configured, router]);

  return (
    <main className="flex h-full items-center justify-center bg-[#0f0f13] text-white">
      <div className="max-w-md text-center">
        <p className="text-sm text-[#8888aa]">{error || "Completing secure sign-in…"}</p>
      </div>
    </main>
  );
}
