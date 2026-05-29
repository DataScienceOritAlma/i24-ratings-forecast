# i24 Ratings Forecast

**Predict the rating of a TV program *before* it airs** — a decision-support tool for the Israeli news channel i24, built end-to-end: data engineering, a benchmarked ML model, a 3-tier web product, and a GenAI/agent layer on top.

> Forecasting horizon: weeks-to-months ahead, for strategic planning (schedule, revenue, work plans). *"The whole organization depends on these numbers."* — i24 research manager.

🔗 **Live demo (Streamlit):** https://i24-ratings-orit.streamlit.app · **API docs:** https://i24-ratings-api.onrender.com/docs

---

## Highlights

- **Benchmarked 19 models** across 7 families (linear, trees, gradient-boosting, ensembles, neural nets, stacking, classical time-series). Winner: **HistGradientBoosting**.
- **Production model:** target = *panel-adjusted* rating (the real business KPI). **MAE ≈ 0.30, R² ≈ 0.62** on a strict chronological hold-out.
- **Found & fixed a critical feature bug** (event tags were silently dropped in the retrain pipeline) → **+9.7% MAE improvement**; security-event signal is the 3rd most important feature.
- **Rigorous about what *doesn't* work:** an LLM-scored event-severity feature was tested and **rejected** — it hurt MAE (0.30→0.41) due to a duration confound (semantic intensity ≠ per-broadcast impact). Documented as the project's drift ceiling.
- **GenAI / agent layer:** natural-language forecast explanations, an LLM chatbot that answers free-text Hebrew questions by calling the model, and an autonomous news-reading agent that proposes security events from an RSS feed.

---

## Architecture

```
                ┌─────────────────────────┐
   Next.js  →   │  FastAPI  →  HistGBM     │  →  Supabase (Postgres)
  (Vercel)      │  /predict /ask  + LLM    │      programs · broadcasts
                └─────────────────────────┘      predictions · subs (RLS)
                          │
                          └── Groq LLM (explain · chatbot · event classify)
```

- **Frontend** — Next.js (RTL/Hebrew, Tailwind) on Vercel: marketing page, auth, prediction dashboard, chat, history, analytics.
- **Backend** — FastAPI on Render: `/predict`, `/ask` (LLM-parsed), `/health`, Stripe subscriptions. Loads the model + history at startup.
- **Data** — Supabase Postgres with Row-Level Security; auto-retraining monthly via GitHub Actions.
- **LLM** — Groq (OpenAI-compatible), plain HTTPS; graceful degradation when no key is configured.

A self-contained **Streamlit** app (the original prototype) is also deployed for a quick, no-login demo.

---

## The ML approach

- **Data:** 10,039 broadcasts · 2025-05-25 → 2026-04-18 · 179 unique programs · 34 features (15 raw + 19 engineered).
- **No leakage:** chronological 80/20 split; lag features computed only from history preceding each broadcast.
- **Target = adjusted rating** (`rating / panel_reception`) — comparable across time, the metric the business actually plans on.
- **Key features:** program & slot lag means, hour, program status, and **security-event flags** (holidays were tested and dropped — ~0 contribution).

| Model | MAE | R² |
|---|---|---|
| 🏆 HistGradientBoosting | ~0.30 | ~0.62 |
| LightGBM | ~0.31 | ~0.61 |
| GradientBoosting | ~0.30 | ~0.60 |

Naive global-mean baseline ≈ 0.42 MAE → the model is a large improvement, and 19-model benchmarking confirmed the ceiling is **event drift**, not model choice.

---

## GenAI / agent layer

| Module | What it does |
|---|---|
| `explain.py` | Plain-Hebrew explanation of each forecast, grounded **only** in the model's real numbers (no hallucinated facts). |
| `chat_agent.py` | An **agent**: free-text Hebrew question → LLM parses intent → the real model predicts → LLM answers. |
| `event_classifier.py` + `news_agent.py` | Reads a news RSS feed, classifies real-time security events, and proposes additions to the curated events file (human-in-the-loop). |
| `llm_client.py` | Shared Groq client (retry/backoff, JSON mode). |

---

## Run locally

**Backend (FastAPI):**
```bash
cd backend && pip install -r requirements.txt
uvicorn main:app --reload          # → http://localhost:8000/docs
```

**Frontend (Next.js):**
```bash
cd frontend && npm install && npm run dev   # → http://localhost:3000
```

**Streamlit prototype:**
```bash
pip install -r requirements.txt && streamlit run app.py
```

Configuration via `.env` (see `.env.example`): `DATABASE_URL` (Supabase), `GROQ_API_KEY` (optional, enables the LLM layer), Stripe keys (optional).

---

## Repo map

- `model_train_all.py`, `train_and_save_model.py`, `retrain_from_supabase.py` — modeling & monthly auto-retrain.
- `backend/`, `frontend/` — the production 3-tier app.
- `llm_client.py`, `explain.py`, `chat_agent.py`, `event_classifier.py`, `news_agent.py` — the GenAI/agent layer.
- `eda_script.py`, `EDA_REPORT.md` — exploratory analysis.
- `PRD.md`, `PRODUCT_SPEC.md`, `SCHEMA.md` — product & data design.
- `WORK_LOG.md` — full step-by-step build log.

---

*Built as a professional portfolio project for a data-scientist role. Documentation is primarily in Hebrew; this README is in English for a broader audience.*
