# GeoAgent

**Ask a question. Get a data-backed location recommendation.**

> "Where should I open a coffee shop in Kitchener?"

GeoAgent takes plain English questions about business locations and returns scored recommendations backed by real demographic, competition, traffic, and zoning data — not guesses.

## How It Works

A boss agent (orchestrator) receives your question and dispatches it to specialist agents that each handle one piece of the puzzle:

- **Demographics** — population, income, age distribution
- **Competition** — existing businesses in the area
- **Traffic** — roads, transit, foot traffic patterns
- **Zoning** — commercial viability and land use

These agents query a spatial database in parallel, and the orchestrator synthesizes their findings into a scored recommendation with a clear explanation.

## Tech Stack

| Layer | Tech |
|-------|------|
| LLM | Claude API |
| Agent orchestration | LangGraph |
| Backend | Django + Python |
| Spatial database | PostGIS |
| Frontend | React + Leaflet |

## Current Status

Building incrementally, phase by phase:

- [x] Terminal chatbot with Claude API
- [ ] Tool use with mock data
- [ ] Real data with PostGIS
- [ ] Django backend with streaming API
- [ ] React + map frontend
- [ ] Multi-agent orchestration with LangGraph
- [ ] Polish, comparison mode, and deployment
