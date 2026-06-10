// M0.4: exchange a person's session for a fresh provider token (spec §8 step 3).
//
// For OAuth providers (gmail): POST the stored refresh token to Google and
// return a short-lived access token. For API-key providers (apollo,
// storeleads, anthropic): return the stored key. Either way, long-lived
// secrets never leave Supabase — the laptop only ever holds a short-lived
// token or uses the key transiently in memory.
//
// Org-shared connections (e.g. a team Apollo key) are visible to all members:
// we look up the caller's own connection first, then fall back to org_shared.

import { createClient } from "jsr:@supabase/supabase-js@2";

const admin = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);

Deno.serve(async (req) => {
  try {
    const jwt = (req.headers.get("Authorization") ?? "").replace("Bearer ", "");
    const { data: userData, error: authErr } = await admin.auth.getUser(jwt);
    if (authErr || !userData.user) return new Response("unauthorized", { status: 401 });
    const { provider } = await req.json();

    const { data: conns } = await admin
      .from("connections")
      .select("id, user_id, kind, org_shared")
      .eq("provider", provider)
      .or(`user_id.eq.${userData.user.id},org_shared.eq.true`);
    // Prefer the caller's own connection over an org-shared one.
    const conn =
      conns?.find((c) => c.user_id === userData.user!.id) ?? conns?.find((c) => c.org_shared);
    if (!conn) return new Response("no connection", { status: 404 });

    const { data: sec } = await admin
      .from("connection_secrets")
      .select("secret")
      .eq("connection_id", conn.id)
      .single();
    if (!sec) return new Response("no secret stored", { status: 404 });

    if (conn.kind === "api_key") {
      return Response.json({ token: sec.secret });
    }

    // OAuth: refresh-token grant against Google.
    const r = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: Deno.env.get("GOOGLE_OAUTH_CLIENT_ID")!,
        client_secret: Deno.env.get("GOOGLE_OAUTH_CLIENT_SECRET")!,
        refresh_token: sec.secret,
        grant_type: "refresh_token",
      }),
    });
    const tok = await r.json();
    if (!tok.access_token) {
      console.error("refresh failed", tok.error);
      return new Response("refresh failed - reconnect the provider", { status: 502 });
    }
    return Response.json({ token: tok.access_token, expires_in: tok.expires_in });
  } catch (e) {
    console.error(e);
    return new Response("internal error", { status: 500 });
  }
});
