# Deploying the waitlist site

The site in this folder is plain static HTML, CSS, and SVG. No build step, no server. It runs by opening `index.html`, and it goes public with any static host. Verified rendering in a headless browser at desktop and mobile, no console errors.

The only reason this is not already live is that a host needs an account in your name. Pick one, it is a minute of your time, then I deploy and operate it:

- Fastest, free: drag the `site/` folder onto Netlify Drop (app.netlify.com/drop). Live on a free subdomain in seconds, no card.
- One command, free tier: from `site/`, `npx vercel` (needs you logged into Vercel once).
- Free, in-repo: GitHub Pages pointed at this folder, if you want it under a repo you control.

A custom domain is optional and can come later. The free subdomain is enough to start collecting waitlist signups and to share the launch post.

## When it is live, the one wiring change

The waitlist form currently confirms locally. To capture real emails, point the form `action` in `index.html` at the Klaviyo list subscribe endpoint (or a Formspree endpoint as a stopgap). I do this the moment the Klaviyo key exists. Nothing else changes.
