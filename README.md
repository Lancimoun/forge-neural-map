# FORGE · Neural Map — The mind of Maxima

[![CI](https://github.com/Lancimoun/forge-neural-map/actions/workflows/ci.yml/badge.svg)](https://github.com/Lancimoun/forge-neural-map/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> An explorable 3D **universe of an AI's mind**, narrated by the AI herself.

**▶ Live demo:** https://forge-neural-map-production.up.railway.app  *(sound on)*

![The mind of Maxima](og.png)

I took **Maxima** — a production AI agent built at [FORGE](https://forge-landing-production.up.railway.app) — and rendered her entire codebase as an explorable galaxy. Then I made *her* your guide through it.

## What it is
- **2,778 stars · 7,295 connections · 157 systems** — every function and file in her code, mapped from a real knowledge graph.
- **Five scales of exploration:** fly the galaxy → warp into a star → orbit its planets → drop to a planet's surface → zoom out to a universe of sibling galaxies (Memory, Voice, Reasoning, Soul, Dreams).
- **Maxima narrates it** — a cinematic, voiced guide (Web Speech) that welcomes you and explains what each part of her is.
- **The Neural Web** — toggle the real 7,295 connections and watch her mind light up as a firing brain.
- Hidden discoveries, a codex, comets, a black hole at the core, **free-flight** (WASD), a cinematic record mode, an evolving procedural score, saved progress, and deep-link sharing.

## How it's built
- **Vanilla three.js (r128)** + custom **GLSL vertex shaders** for the live orbital animation — no game engine.
- A pure-Python bake (`bake.py`) turns a code knowledge-graph into a compact `nodes.json`: a spiral-galaxy layout with community detection and per-node orbital parameters.
- **UnrealBloom** + **ACES** filmic tone-mapping for the cinematic look.
- Procedural ambient score + narration via the **Web Audio** & **Web Speech** APIs.
- Shipped as a static site (nginx) on **Railway**.

> Note: the raw `graph.json` (the source knowledge-graph of the private codebase) isn't included — `nodes.json` is the baked, public-facing output that powers the demo.

## Run it
```bash
docker build -t neural-map .
docker run -p 8080:8080 -e PORT=8080 neural-map
```
…or serve the folder statically and open `index.html`.

## Stack
`three.js` · `GLSL` · `Web Audio API` · `Web Speech API` · `Python` · `Docker` · `nginx` · `Railway`

---
Built by **[Lance](https://github.com/Lancimoun)** · part of **FORGE** — building AI you can watch think.
