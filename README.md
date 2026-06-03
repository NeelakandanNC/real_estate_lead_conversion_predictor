# EstateIQ — Real-estate Lead Scoring

Out of a calling list of thousands, only ~1–2% actually buy. This project scores
every inbound lead by their probability of buying, so the sales team follows up the
highest-value callers first. The whole thing is built on **survey-calibrated synthetic
data** (no private CRM needed to demonstrate it) and ships as a small website.

> Methodology demonstrator calibrated to the ANAROCK Homebuyer Sentiment Survey
> (H1-2022 → H1-2025). The production model swaps in the developer's own CRM data.

---

## What's the pipeline

```
ANAROCK surveys ─► priors.py ─► generate_synthetic_data.py ─► leads_synthetic.csv
                                                                     │
                                            preprocessing.py (encode + features + MI)
                                                                     │
                                                              leads_encoded.csv
                                                                     │
                                   modelling.py (LightGBM + calibration + lift)  ─► lead_scorer.pkl
                                                                     │
                                       export_web_model.py  ─►  web/model/model.json (trees + calibration)
                                                                     │
                                   web/  (HTML/CSS/JS + serverless /api/score) ─► scores a lead
```

The website scores leads with a **dependency-free JavaScript tree-walker** (a GBDT is just
tree lookups + a sum). We don't ship an ML runtime to production — `onnxruntime` blows past
Vercel's 250 MB function limit, so instead `export_web_model.py` dumps the LightGBM trees +
isotonic curve to `model.json` and `api/score.js` evaluates them directly. The JS output is
verified identical to Python (parity test in the export step). `export_onnx.py` remains as an
optional, portable ONNX artifact, but the site does not use it.

**Headline result:** ROC-AUC ≈ 0.76; calling the top 20% of the ranked list reaches
~50% of all buyers (2.5× better than random).

## Repo layout

```
ml/                 Python pipeline
  priors.py                 survey numbers (the only data source)
  generate_synthetic_data.py  -> leads_synthetic.csv  (200k leads, ~1.5% buyers)
  preprocessing.py            encode + engineer + MI/correlation selection
  modelling.py                LightGBM, calibration, lift curve  -> lead_scorer.pkl + figs/
  export_onnx.py              clean single model -> web/model/*.onnx + meta.json
  streamlit_app.py            quick manual test form (Python)
web/                Deployable website (this is what goes to Vercel)
  index.html, style.css, app.js   frontend
  api/score.js                serverless scoring (onnxruntime-node, no Python)
  model/                      lead_scorer.onnx + meta.json
  dev-server.mjs              run locally without the Vercel CLI
data_sources/       source PDFs + extracted text/images
docs/EXTRACTED_DATA.md        every survey number, with page-level provenance
```

## Run the Python side

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install numpy pandas scikit-learn lightgbm matplotlib onnx onnxmltools skl2onnx onnxruntime
# (macOS LightGBM also needs: brew install libomp)

cd ml
python generate_synthetic_data.py    # -> leads_synthetic.csv
python preprocessing.py              # -> leads_encoded.csv, feature_ranking.csv
python modelling.py                  # -> lead_scorer.pkl, figs/
python export_web_model.py           # -> web/model/model.json  (what the site uses)
python export_onnx.py                # optional: ml/lead_scorer.onnx (portable artifact)
```

## Run the website locally

```bash
cd web
node dev-server.mjs        # open http://localhost:3000   (no npm install needed)
```

## Deploy to Vercel

Point Vercel at this repo and set **Root Directory = `web`**, then deploy.

`web/vercel.json` declares the build explicitly (`builds` + `routes`), so Vercel skips
framework auto-detection and does: `public/` → static site, `api/score.js` → a Node
serverless function with `model/model.json` bundled. The function has **no npm
dependencies** (pure-JS tree-walker), so it stays tiny — no size-limit or runtime issues.
