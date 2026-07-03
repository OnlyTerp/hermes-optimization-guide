# Hermes Config Wizard

Static single-page wizard that emits a ready-to-drop `config.yaml` from 8 answers. **Runs entirely in the browser** — nothing is uploaded. Output shape mirrors [`templates/config/`](../../templates/config/) and is verified against the real Hermes schema (Part 19, v0.18).

## Local use

```bash
# After cloning the guide:
cd docs/wizard
python3 -m http.server 8080
# then open http://127.0.0.1:8080
```

Or just open [`docs/wizard/index.html`](./index.html) directly — it works from `file://`.

## Deployment

Served automatically via GitHub Pages once enabled on this repo. See [ROADMAP.md](../../ROADMAP.md) for Pages setup status.

## Extending

Everything lives in one `index.html`. Each form field maps to a case in `generate()`; question 1 (persona) pre-fills the rest of the form from `PERSONA_PRESETS`. To add a new persona / option:

1. Add the `<input>` under the right `<fieldset>` (and, for a persona, a preset object in `PERSONA_PRESETS`).
2. Read it in `generate()` via `val()` / `on()` / `select()`.
3. Append YAML `lines.push(...)` blocks where it fits.

No frameworks, no build step, on purpose.
