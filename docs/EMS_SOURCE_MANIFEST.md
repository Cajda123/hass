# EMS source manifest

**Canonical EMS version:** v28.6  
**Prepared:** 2026-09-12  
**Based on repository HEAD before v28.6:** `c900958d17234d6a49f5f64f3d7c52932fdf1da1`

This file lists the source-of-truth runtime files Codex should inspect before editing EMS.

## Handoff state

The repository HEAD before the handoff patch is `c900958d17234d6a49f5f64f3d7c52932fdf1da1`.

If the three mutable runtime files still have these baseline blobs:

- `nodered/flows.json` -> `a8e38895ac1f82eb00abe713a12017cd9a895bc5`
- `homeassistant/ems_base.yaml` -> `afbe1eec4571134a9961e2df711fbd0ca3c37f97`
- `homeassistant/03_ems_notifications.yaml` -> `213123e234449ec8179df3f523b84c2477e9a8b5`

then v28.6 has **not yet been committed into the runtime files**. Run:

`python3 tools/patch_ems_v28_6_hard_deny_20min.py .`

The guarded patcher refuses to touch any unexpected baseline.

## Runtime control files after applying v28.6

| Path | Role | Expected Git blob SHA after v28.6 |
|---|---|---|
| `nodered/flows.json` | Main deterministic EMS logic | `1390d47c4aa18983288d3bffd3850746afecc370` |
| `homeassistant/ems_base.yaml` | HA helpers/templates/scripts/entities | `27401d42ea9d3b93a19ea319fcdcab2720785e9d` |
| `homeassistant/02_ems_heating.yaml` | Heating/DHW package, unchanged by v28.6 | `79ce076da38bd18d2aae0efa1b8f1af12fca3ef6` |
| `homeassistant/03_ems_notifications.yaml` | EV consent/questions/audit | `c2e88f5d0aae20d7e21923faab83ba1ab887e582` |
| `homeassistant/ems_ai.yaml` | AI/commentary routing | `3472574a364c38d5a61fce84a922296af011f2c5` |
| `nodered/ems_ai_commentator_flow.json` | Separate AI commentator flow | `c765618f313e285f6a00dc1ca8e39b9387e923a0` |

## UI files

These are part of the repository and may expose EMS controls, but v28.6 does not rewrite them:

| Path | Git blob SHA at v28.6 preparation |
|---|---|
| `homeassistant/dashboard_family.yaml` | `8b14963904e5331ce0fb5ed123d0a9f99b02c877` |
| `homeassistant/dashboard_technic.yaml` | `23a329d90884f584fcf6b3fc40b434bb5a0b3945` |

## Permanent context

- `AGENTS.md` – safety/workflow rules for Codex.
- `docs/EMS_CURRENT_STATE.md` – current architecture and behavior.
- `docs/EMS_INCIDENT_2026-09-11_EV_GRID_AFTER_DENY.md` – root cause and regression rule for the v28.6 EV fix.
- `docs/architecture.md` – broader architecture.
- `docs/decision_logic.md` – historical/design decision logic.
- `docs/entities.md` – entity map.
- `docs/force_modes_and_probe_logic.md` – force-mode background.

## Verification rule

If a runtime file's blob SHA differs from this manifest, do not assume the documentation is still exact. Read the changed runtime file first, summarize the diff, then update `EMS_CURRENT_STATE.md` and this manifest as part of the same change.
