# South County Week

Every public event in Boca Raton, Delray Beach and Boynton Beach, FL, for the next two weeks.
Put together by Justin Himmelbaum and refreshed every Sunday.

Open it: https://justinhimmelbaum-glitch.github.io/south-county-week/

On a phone, add it to your home screen (iPhone: Safari > Share > Add to Home Screen;
Android: Chrome menu > Install app) and it opens like an app.

## How it's built
- `index.html` is the app. Its events are inside the page, so it works as one file.
- `kit/` holds what the weekly refresh uses: `build.py` (merges event files, removes duplicates,
  writes `index.html` from `template.html`), `sources.json` (which event sources work and how),
  `agent_brief.md` (instructions for the research sweep), and the Facebook Events helpers.
- `sw.js` and `manifest.webmanifest` make it installable and let it open without signal.

The Himmelbaum Group | Keller Williams Realty Boca Raton
