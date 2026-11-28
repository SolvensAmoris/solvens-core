"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth";

export default function OidcSilentCallback() {
  const { configured, completeSilentSignIn } = useAuth();
  const completion = useRef<Promise<void> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!configured) {
      setError("OIDC is not configured for this dashboard.");
      return;
    }
    if (!completion.current) completion.current = completeSilentSignIn();
    let active = true;
    completion.current.catch((reason: unknown) => {
      if (active) {
        setError(reason instanceof Error ? reason.message : "Silent OIDC callback failed");
      }
    });
    return () => {
      active = false;
    };
  }, [configured, completeSilentSignIn]);

  return (
    <main className="flex h-full items-center justify-center bg-[#0f0f13] text-white">
      <p className="max-w-md text-center text-sm text-[#8888aa]">
        {error || "Completing silent session renewal…"}
      </p>
    </main>
  );
}
