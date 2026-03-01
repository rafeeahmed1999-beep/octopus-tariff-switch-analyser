# ⚡ Octopus Energy — Customer Tariff Switch Analyser

A Streamlit web app that simulates how Octopus Energy might identify customers who would benefit from switching to a variable tariff — built as a portfolio project for a Marketing Data Analyst role application.

**[Live demo →](https://your-app-name.streamlit.app)** *(replace with your Streamlit URL after deployment)*

---

## What this is

This tool analyses a synthetic cohort of 1,000 UK energy customers, segments them by usage behaviour, and recommends whether each customer should switch from a Standard tariff to either **Agile** or **Tracker** — along with an estimated annual saving.

It is built entirely on **synthetic data** to demonstrate realistic analytical usability without using any real customer records. The data generation logic is designed to reflect genuine UK household usage patterns and 2024 tariff structures.

---

## Why I built it

Octopus Energy's product range — particularly Agile and Tracker — is built on the insight that not all customers benefit equally from variable pricing. A customer who shifts their dishwasher to 2am benefits from Agile. One who uses most of their electricity during the 4–7pm peak window does not.

This project demonstrates the kind of segmentation thinking a marketing analyst at Octopus would apply when planning a tariff migration campaign: **who to target, with which message, and what the expected financial outcome is**.

---

## The four customer segments

| Segment | Profile | Best tariff |
|---|---|---|
| **Low & Stable** | Low consumption, flat usage across the day | Usually Standard or Tracker |
| **High & Stable** | High consumption, no strong time-of-use pattern | Tracker (benefits from wholesale dips) |
| **Peak Heavy** | Spikes during 16:00–19:00 (commuters, 9-to-5 workers) | Standard — Agile would cost more |
| **Off-Peak Opportunist** | Shifts load to nights/weekends (EV owners, home workers) | Agile — captures cheap overnight rates |

---

## Features

- **Segment Overview** — cohort composition, recommended tariff breakdown by segment, summary statistics
- **Savings Estimator** — annual cost comparison across Standard, Agile, and Tracker; saving distributions by segment
- **Usage vs Price Volatility** — scatter of volatility exposure vs saving potential; typical Agile daily price curve; peak/off-peak usage profiles
- **Customer Report** — full filterable table with CSV download for campaign planning

---

## How the data is generated

All customer data is procedurally generated using NumPy with a fixed random seed (reproducible). Each customer is assigned:

- A segment drawn from weighted probabilities reflecting realistic UK household distributions
- A base daily consumption scaled with randomness to avoid uniformity
- Peak and off-peak usage multipliers that reflect their segment's behavioural profile
- Representative 2024 UK tariff rates (Standard ~25p/kWh; Agile peak ~35–55p, off-peak ~8–16p; Tracker ~20–28p)
- An annual cost calculated for each tariff using the customer's usage-time split
- A volatility exposure score representing how much of their usage falls in high-price windows

No real Octopus Energy customer data is used or implied.

---

## Tech stack

| Tool | Use |
|---|---|
| Python 3.10+ | Core language |
| Streamlit | Web app framework |
| Plotly | Interactive charts |
| pandas / numpy | Data generation and manipulation |

---

## Running locally

```bash
# Clone the repo
git clone https://github.com/your-username/octopus-tariff-switch-analyser.git
cd octopus-tariff-switch-analyser

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub (must be public)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Click **New app** → select this repo → set main file to `app.py`
5. Click **Deploy** — takes ~2 minutes

Streamlit Community Cloud is free for public repos.

---

## Project context

This app is part of a larger energy market analytics portfolio built in Python:

| Module | Description |
|---|---|
| Module 1 | ETL pipeline pulling real UK wholesale prices from Elexon BMRS API |
| Module 2 | Comparative forecasting — multivariate regression vs ARIMA on half-hourly imbalance prices |
| Module 3 | Causal inference — measuring the structural impact of GB's last coal plant closure (Sep 2024) using BSTS |
| Module 4 | Interactive Plotly dashboards (market overview, forecast tracker, intervention analysis) |
| **This app** | Customer tariff switching analysis — the marketing-facing layer of the pipeline |

---

## Author

Built by [Your Name] as part of a Marketing Data Analyst portfolio.  
[LinkedIn](https://linkedin.com/in/your-profile) · [GitHub](https://github.com/your-username)
