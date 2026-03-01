# Octopus Energy — Customer Tariff Switch Analyser

A Streamlit web app that simulates how Octopus Energy might identify which customers would benefit from switching to a variable tariff — and which are already on the right deal.

**[Live demo →](https://octopus-tariff-switch-analyser.streamlit.app)**

---

## What this is

This tool analyses a synthetic cohort of UK energy customers, segments them by usage behaviour, and recommends whether each customer should switch from a Standard tariff to either Agile or Tracker — along with an estimated annual saving. It is built as a portfolio project demonstrating the kind of segmentation analysis a Marketing Data Analyst at Octopus Energy would run ahead of a tariff migration campaign.

Agile half-hourly prices are fetched live from the [Octopus public API](https://developer.octopus.energy/rest/reference) — no API key required. Customer behaviour data is synthetic, generated to reflect realistic UK household usage archetypes.

---

## The three tariffs

**Standard** — a fixed unit rate (~24–26p/kWh) regardless of when you use power. Predictable bills but no opportunity to benefit from cheaper off-peak electricity. The most common tariff type in the UK.

**Agile Octopus** — half-hourly prices that follow the wholesale electricity market. Cheap overnight (sometimes negative), expensive during the 4–7pm evening peak. Rewards customers who can shift flexible loads — EV charging, dishwashers, washing machines — away from peak hours.

**Tracker** — a daily rate that tracks the wholesale market with a small margin added. Less volatile than Agile — changes once per day rather than every 30 minutes. A middle ground for customers who want some wholesale benefit without actively managing when they use power.

---

## The four customer segments

| Segment | Profile | Why they might not benefit from Agile |
|---|---|---|
| Low & Stable | Low consumption, flat usage across the day | Marginal saving — low volume limits upside |
| High & Stable | High consumption, no strong time-of-use pattern | Tracker often wins — stable but high volume |
| Peak Heavy | Spikes during 16:00–19:00 | Agile would cost *more* — peak hours are the most expensive slots |
| Off-Peak Opportunist | Shifts load to nights/weekends | Strong Agile candidate — captures cheap overnight rates |

The key insight the app demonstrates: **high volatility exposure does not mean Agile is a good fit**. Peak Heavy customers have the most exposure to volatile prices, but that exposure works against them on Agile. Off-Peak Opportunists have lower exposure but the highest savings.

---

## Features

- **Segment Overview** — cohort composition, recommended tariff by segment, summary table showing what percentage of each segment stays on Standard
- **Savings Estimator** — annual cost comparison across all three tariffs; saving distributions by segment
- **Usage vs Price Volatility** — scatter of exposure vs saving potential; real Agile daily price curve for the selected region; peak/off-peak usage profiles
- **Customer Report** — filterable table with CSV download for campaign planning

---

## How the data is generated

All customer data is procedurally generated using NumPy with a fixed random seed. Each customer is assigned a segment drawn from weighted probabilities, a base daily consumption with realistic variance, and peak/off-peak usage multipliers that reflect their segment's behavioural profile.

Annual costs are calculated for each tariff using the customer's usage-time split applied against the real Agile price profile fetched from the API. Standard tariff rates (~24–26p/kWh) reflect the UK price cap level as of late 2024. No real Octopus Energy customer data is used or implied.

---

## Tech stack

| Tool | Use |
|---|---|
| Python 3.10+ | Core language |
| Streamlit | Web app framework |
| Plotly | Interactive charts |
| pandas / numpy | Data generation and manipulation |
| requests | Octopus API calls |

---

## Running locally

```bash
git clone https://github.com/rafeeahmed1999-beep/octopus-tariff-switch-analyser.git
cd octopus-tariff-switch-analyser
pip install -r requirements.txt
streamlit run otsa_app.py
```

---

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub (must be public)
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click **Create app** → select this repo → set main file path to `otsa_app.py`
4. Click **Deploy**

---

## Project context

This app is part of a wider energy market analytics portfolio:

| Project | Description |
|---|---|
| [Energy Market Volatility](https://github.com/rafeeahmed1999-beep) | ETL pipeline on real Elexon BMRS data, ARIMA/regression forecasting, BSTS causal inference on the GB coal closure, and Plotly dashboards |
| **This app** | Marketing-facing layer — customer segmentation and tariff switching analysis |

---

## Author

Built by Rafee Ahmed as part of a Marketing Data Analyst portfolio.
