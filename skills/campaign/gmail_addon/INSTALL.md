# Installing Reply Assist (per founder, ~3 minutes)

Each founder installs it once, in their own Google account. There is no GCP project, no
sharing, and no ownership transfer. Making the script inside your own account is what
avoids all the cross-org problems.

You need one thing from whoever set up the backend: the **shared secret** (the value of
`ADDON_SHARED_SECRET` on the Railway `slack_wiz` service). Everyone uses the same value.

## Steps

1. Sign into **your own founder Google account** (the one you send outreach from).
2. Go to **script.google.com** and click **New project**.
3. Left sidebar → **gear (Project Settings)** → tick **"Show appsscript.json manifest
   file in editor."**
4. Back in the editor:
   - Open `Code.gs`, select all, delete, and paste in the contents of this folder's
     `Code.gs`.
   - Open `appsscript.json`, select all, delete, and paste in this folder's
     `appsscript.json`.
5. Still in **Project Settings → Script properties**, add one property:
   - name: `ADDON_SHARED_SECRET`
   - value: the shared secret (same value for everyone). No trailing spaces.
6. **Deploy → Test deployments → Install** → Done.
7. Reload Gmail. The **Reply Assist** panel appears on the right (click its icon in the
   far-right vertical strip). Open a prospect reply → **Draft a reply**.

## Notes

- The backend URL is already baked into `Code.gs` and `appsscript.json`. If it ever
  changes, update it in both.
- Only the founder accounts the backend knows about will work; anyone else gets a
  clear "not authorized" and nothing sends.
- If Draft returns `401 invalid credential`, the Script Property secret does not match
  the Railway `ADDON_SHARED_SECRET`. Re-check both, byte for byte.
- If Draft returns `403 not authorized`, you are signed into an account the backend does
  not recognize as a founder.

## If we outgrow this

For one-click install across the team (no code pasting, auto-updates), the path is a
private **Google Workspace Marketplace** app. It needs a GCP project with the Marketplace
SDK and an OAuth consent screen configured once, and because the founders span two Google
orgs (dartmouth.edu and berkeley.edu), it would need to be published unlisted rather than
single-domain-private. Worth doing only if the number of installers grows well past the
three founders.
