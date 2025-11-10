# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local) to your Gemini API key
3. Run the app:
   `npm run dev`

## Kai autonomous core

The repository now bundles a lightweight Python toolkit that mirrors the
"Copilot Integration and Autonomous Tooling" blueprint.  Run a full autonomous
cycle from the project root with:

```
python scripts/run_kai_autonomy.py
```

The script orchestrates the new `core/` package to fetch insights, synthesise
artefacts and evaluate them against the configured stability threshold.  Check
the printed report to follow Kai's unstoppable progreso.
