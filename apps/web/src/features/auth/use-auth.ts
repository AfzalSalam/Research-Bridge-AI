import { useEffect, useState } from "react";
import { User, Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase/client";

const isE2E = process.env.NEXT_PUBLIC_E2E_TEST === "true";

export function useAuth() {
  const [user, setUser] = useState<User | null>(
    isE2E ? ({ id: "e2e-user", email: "e2e@example.com" } as User) : null,
  );
  const [session, setSession] = useState<Session | null>(
    isE2E ? ({ access_token: "e2e-token" } as Session) : null,
  );
  const [loading, setLoading] = useState(!isE2E);

  useEffect(() => {
    if (isE2E) return;

    const isDemo = typeof window !== "undefined" && localStorage.getItem("demo_mode") === "true";
    if (isDemo) {
      setUser({ id: "demo-user", email: "demo@researchbridge.ai" } as User);
      setSession({ access_token: "demo-token" } as Session);
      setLoading(false);
      return;
    }

    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session);
        setUser(session?.user ?? null);
        setLoading(false);
      }
    );

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  return { user, session, loading };
}
