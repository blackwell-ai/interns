// M0.3: connect integrations to a person's account (spec §8 step 2).
//
// Two jobs, both keeping secrets server-side:
//   action=store-key  — store an API-key provider (apollo/storeleads/anthropic).
//   action=start      — begin the SECOND Google OAuth consent (gmail.send +
//                       gmail.readonly). Sign-in identity ≠ send authorization
//                       (build plan §7 item 4), hence this separate flow.
//   GET ?state=...&code=... — Google's redirect lands here; we exchange the
//                       code for a refresh token and store it. The client
//                       secret (GOOGLE_OAUTH_CLIENT_SECRET) exists ONLY in
//                       this function's env — never on a laptop.
//
// Required function env (set via `supabase secrets set`):
//   GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET
// Provided automatically: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY

import { createClient } from "jsr:@supabase/supabase-js@2";

const GMAIL_SCOPES = [
  "https://www.googleapis.com/auth/gmail.send",
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/userinfo.email",
].join(" ");

const admin = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);

async function userFromRequest(req: Request) {
  const jwt = (req.headers.get("Authorization") ?? "").replace("Bearer ", "");
  const { data, error } = await admin.auth.getUser(jwt);
  if (error || !data.user) throw new Response("unauthorized", { status: 401 });
  return data.user;
}

async function upsertConnection(
  userId: string,
  provider: string,
  account: string,
  kind: "oauth" | "api_key",
  secret: string,
  orgShared = false,
) {
  const { data: conn, error } = await admin
    .from("connections")
    .upsert(
      { user_id: userId, provider, account, kind, org_shared: orgShared, updated_at: new Date() },
      { onConflict: "user_id,provider,account" },
    )
    .select("id")
    .single();
  if (error) throw error;
  const { error: e2 } = await admin
    .from("connection_secrets")
    .upsert({ connection_id: conn.id, secret, updated_at: new Date() });
  if (e2) throw e2;
}

function selfUrl(req: Request): string {
  // Public URL of this function, for the OAuth redirect_uri.
  const u = new URL(req.url);
  return `${u.origin}${u.pathname}`;
}

Deno.serve(async (req) => {
  try {
    if (req.method === "GET") {
      // Google redirect: ?state=...&code=...
      const url = new URL(req.url);
      const state = url.searchParams.get("state") ?? "";
      const code = url.searchParams.get("code") ?? "";
      const { data: st } = await admin
        .from("oauth_states")
        .select("user_id, provider")
        .eq("state", state)
        .single();
      if (!st) return new Response("unknown or expired state", { status: 400 });
      await admin.from("oauth_states").delete().eq("state", state);

      const tokenResp = await fetch("https://oauth2.googleapis.com/token", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          code,
          client_id: Deno.env.get("GOOGLE_OAUTH_CLIENT_ID")!,
          client_secret: Deno.env.get("GOOGLE_OAUTH_CLIENT_SECRET")!,
          redirect_uri: selfUrl(req),
          grant_type: "authorization_code",
        }),
      });
      const tok = await tokenResp.json();
      if (!tok.refresh_token) {
        return new Response(
          `Google did not return a refresh token (${JSON.stringify(tok.error ?? tok)}). ` +
            "Remove the app's prior consent at myaccount.google.com/permissions and retry.",
          { status: 400 },
        );
      }
      // Which account was connected? (so the outreach agent can assert it's
      // the Dartmouth address, per brain/company/connections.md)
      const info = await fetch("https://www.googleapis.com/oauth2/v2/userinfo", {
        headers: { Authorization: `Bearer ${tok.access_token}` },
      }).then((r) => r.json());
      await upsertConnection(st.user_id, st.provider, info.email ?? "", "oauth", tok.refresh_token);
      return new Response(
        `Connected ${st.provider} for ${info.email}. You can close this tab.`,
        { headers: { "Content-Type": "text/plain" } },
      );
    }

    const user = await userFromRequest(req);
    const body = await req.json();

    if (body.action === "store-key") {
      await upsertConnection(
        user.id,
        body.provider,
        body.account ?? "",
        "api_key",
        body.secret,
        body.org_shared ?? false,
      );
      return Response.json({ ok: true });
    }

    if (body.action === "start") {
      const state = crypto.randomUUID();
      await admin
        .from("oauth_states")
        .insert({ state, user_id: user.id, provider: body.provider });
      const auth_url =
        "https://accounts.google.com/o/oauth2/v2/auth?" +
        new URLSearchParams({
          client_id: Deno.env.get("GOOGLE_OAUTH_CLIENT_ID")!,
          redirect_uri: selfUrl(req),
          response_type: "code",
          scope: GMAIL_SCOPES,
          access_type: "offline",
          prompt: "consent", // force a refresh token even on re-consent
          state,
        });
      return Response.json({ auth_url });
    }

    return new Response("unknown action", { status: 400 });
  } catch (e) {
    if (e instanceof Response) return e;
    console.error(e);
    return new Response("internal error", { status: 500 });
  }
});
