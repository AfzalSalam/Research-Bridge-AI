import { client } from "@/lib/api/generated/client.gen";
import { supabase } from "@/lib/supabase/client";

let isConfigured = false;

export async function getAccessToken(): Promise<string | null> {
  if (process.env.NEXT_PUBLIC_E2E_TEST === "true") return "e2e-token";
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

export function configureApiClient() {
  if (isConfigured) return;
  
  client.setConfig({ baseUrl: "/backend" });

  client.interceptors.request.use(async (request) => {
    const token = await getAccessToken();
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  });

  isConfigured = true;
}
