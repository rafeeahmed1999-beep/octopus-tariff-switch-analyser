# Octopus Energy: Customer Tariff Switch Analyser

A Streamlit web app that simulates how Octopus Energy might identify which customers would benefit from switching to a variable tariff, and which are already on the right deal.

**[Live demo](https://octopus-tariff-switch-analyser.streamlit.app)**

---

## Overview

This tool analyses a synthetic cohort of UK energy customers, segments them by usage behaviour, and recommends whether each customer should switch from a Standard tariff to either Agile or Tracker, along with an estimated annual saving.

It demonstrates the kind of segmentation analysis a marketing team would run ahead of a tariff migration campaign: who to target, with which message, and what the expected financial outcome is.

---

## The three tariffs

**Standard:** a fixed unit rate (~24-26p/kWh) regardless of when you use power. Predictable bills but no opportunity to benefit from cheaper off-peak electricity. The most common tariff in the UK.

**Agile Octopus:** half-hourly prices that follow the wholesale electricity market. Cheap overnight (sometimes negative) and expensive during the 4-7pm evening peak. Rewards customers who can shift flexible loads (EV charging, dishwashers, washing machines) away from peak hours.

**Tracker:** a daily rate that tracks the wholesale market plus a supplier margin. Less volatile than Agile, changing once per day rather than every 30 minutes. A middle ground for customers who want some wholesale benefit without actively managing when they use power.

---

## The four customer segments

| Segment | Profile | Likely recommendation |
|---|---|---|
| Low & Stable | Low consumption, flat usage across the day | Tracker or Standard |
| High & Stable | High consumption, no strong time-of-use pattern | Tracker |
| Peak Heavy | Spikes during 16:00-19:00 | Stay on Standard |
| Off-Peak Opportunist | Shifts load to nights and weekends | Agile |

The key insight the app demonstrates: high volatility exposure does not mean Agile is a good fit. Peak Heavy customers have the most exposure to volatile prices, but that exposure works against them on Agile. Off-Peak Opportunists have lower exposure but the highest savings.

---

## What data is real vs synthetic

### Real: from the Octopus public API

Agile Octopus half-hourly unit rates (p/kWh inc. VAT) are pulled from the Octopus public API on load. No API key is required. From the real price data, three inputs are derived for the cost model:

- `agile_peak_p`: average Agile rate during 16:00-19:00 (p/kWh)
- `agile_offpk_p`: average Agile rate outside 16:00-19:00 (p/kWh)
- `agile_avg_p`: overall average across all half-hour slots (p/kWh)

These values change when you switch region, which is why tariff recommendations shift by geography.

### Synthetic: researched and modelled by the author

All customer records are generated using a consumption model built from domain knowledge of UK household energy use and retail energy pricing structures. The specific formulas and parameter values are not from Octopus's internal data or documentation.

**Consumption model**

Each customer's electricity use is modelled per half-hour slot using three values:

- `base`: kWh per slot before any scaling. Set so that annual consumption lands in a realistic 2,500-4,500 kWh/yr range across all segments.
- `pm` (peak multiplier): scales `base` during the 6 peak slots (16:00-19:00). A value of 3.50 means the customer uses 3.5x their base rate during those hours.
- `om` (off-peak multiplier): scales `base` across the remaining 42 slots per day.

Annual kWh = (6 x base x pm + 42 x base x om) x 365

The Off-Peak Opportunist has a lower `base` than other segments by design. They are not high consumers; they are efficient households that time-shift their loads. Their `om` of 1.10 reflects modest load-shifting rather than higher total usage, keeping their annual kWh comparable to other segments so cost differences reflect tariff fit rather than volume.

**Tariff cost formulas**

| Tariff | Formula | Notes |
|---|---|---|
| Standard | annual_kwh x U(24, 26) / 100 | Rate range from Ofgem Oct 2024 price cap |
| Agile (blended) | annual_kwh x (peak_frac x agile_peak_p + (1 - peak_frac) x agile_offpk_p) / 100 | Uses real API prices; peak_frac from synthetic usage model |
| Tracker | annual_kwh x agile_avg_p x U(1.15, 1.25) / 100 | 15-25% margin reflects supplier hedging cost, estimated from domain knowledge |

The Tracker margin represents the supplier's cost of hedging wholesale exposure for a daily variable product. This figure is estimated from general knowledge of retail energy pricing and is not taken from Octopus's published Tracker terms, which vary over time.

**Segment weights and volatility exposure ranges**

Population weights (Low 25%, High Stable 30%, Peak Heavy 28%, Opportunist 17%) and the volatility exposure score ranges per segment are author-estimated based on general knowledge of UK household energy behaviour. They are not derived from Octopus customer data.

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

## Author

Built by Rafee Ahmed as part of a Marketing Data Analyst portfolio.
