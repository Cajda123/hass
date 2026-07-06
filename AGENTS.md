# Codex / agent rules for this repository

Tento projekt řídí reálné energetické zařízení v domě. Změny mohou ovlivnit baterii, měniče, wallboxy, bojlery a zatížení fází. Chovej se konzervativně.

## Hard rules

- Never delete files unless explicitly requested.
- Never rewrite the whole repository blindly.
- Never modify secrets, credentials, tokens, certificates or production runtime files.
- Never add real passwords, API keys, tokens, private IP secrets or credentials into git.
- Never change entity IDs without listing every affected reference.
- Never change MQTT topics without listing every affected producer and consumer.
- Never change Node-RED flow structure in bulk unless the user explicitly asks for a refactor.
- Never assume that an unknown load is safe to switch.
- Prefer documentation/report output when unsure.

## Preferred workflow

1. Read relevant files first.
2. Summarize what currently exists.
3. Propose a small change.
4. Make the smallest possible patch.
5. Document EMS behavior changes in `docs/decision_logic.md`.
6. Mention any required manual Home Assistant or Node-RED reload/restart.

## Repository roles

- `homeassistant/` contains Home Assistant YAML, helpers, template sensors, scripts and dashboard definitions.
- `nodered/` contains Node-RED flows and the main EMS decision logic.
- `docs/` contains architecture and behavior documentation.
- Future `esphome/` should contain ESPHome configs.
- Future `esp32/` should contain custom firmware projects.

## Style rules

- Internal entity IDs should stay stable and preferably English with `ems_` prefix.
- Czech user-facing names are OK in dashboards and UI.
- Keep changes small and reviewable.
- Prefer explicit names over clever abbreviations.
- Keep safety limits visible and configurable via helpers where possible.
- Do not hide important behavior in undocumented magic constants.

## EMS safety priorities

1. Do not overload phases, inverters or grid input.
2. Do not drain the house battery below configured minimum SOC except by explicit manual override.
3. Do not start large loads if current measurements are unavailable or stale.
4. Prefer PV surplus before grid import.
5. Use cheap grid tariff only according to documented rules.
6. When in doubt, fail safe: stop controllable loads rather than start them.

## Review checklist for any EMS logic change

- Which entities does this change read?
- Which entities/scripts/switches does this change write?
- What happens if a sensor is unavailable/unknown/stale?
- What happens if both cars are connected?
- What happens when tariff changes?
- What happens when SOC is below minimum?
- What happens if PV forecast is wrong?
- Is the behavior visible on the dashboard or in logs?
