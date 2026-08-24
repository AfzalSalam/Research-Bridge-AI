import { client } from "@/lib/api/generated/client.gen";
import { supabase } from "@/lib/supabase/client";

let isConfigured = false;

export function configureApiClient() {
  if (isConfigured) return;
  
  client.setConfig({ baseUrl: "/backend" });

  client.interceptors.request.use(async (request) => {
    // Inject Supabase session token into headers
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      request.headers.set("Authorization", `Bearer ${session.access_token}`);
    }
    return request;
  });

  isConfigured = true;
}
