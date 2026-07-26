# Sarvam × Disha — build story + deck

Standalone static site. It does not modify or depend on the Disha product in `web/`.

- `index.html` — the founder build story ("Four hours. Two languages. One voice built for India.")
- `deck/index.html` — the Sarvam Epoch build deck, mapped to the judging rubric
- `styles.css` — stylesheet for the blog (the deck is self-contained)

Live:

- Story — https://sarvam-blog.pages.dev/
- Deck — https://sarvam-blog.pages.dev/deck/

Preview locally:

```bash
cd sarvam-blog
python3 -m http.server 4173
# story: http://localhost:4173/   ·   deck: http://localhost:4173/deck/
```

Deploys to Cloudflare Pages (project `sarvam-blog`) on any push to `main` that
touches `sarvam-blog/**` — see `.github/workflows/deploy-blog.yml`. The whole
folder is the artefact; there is no build step.
