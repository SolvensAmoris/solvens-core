"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function OidcCallback() {
  const router = useRouter();
  const { configured, completeSignIn } = useAuth();
  const [error, setError] = useState("");

  useEffect(() => {
    if (!configured) {
      setError("OIDC is not configured for this dashboard.");
      return;
    }
    let active = true;
    completeSignIn()
      .then(() => {
        if (active) router.replace("/");
      })
      .catch((reason: unknown) => {
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
