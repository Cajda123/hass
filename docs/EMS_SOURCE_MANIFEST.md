# EMS source manifest

**Canonical EMS version:** v28.6  
**Prepared:** 2026-09-12  
**v28.6 runtime commit:** `44b80f3541cac66c38b38f71bbba8538627830d0`

This file lists the source-of-truth runtime files Codex should inspect before editing EMS.

## Handoff state

**v28.6 is applied on `main`.** Runtime commit: `44b80f3541cac66c38b38f71bbba8538627830d0`. The blobs below were re-read from GitHub after deployment and are the canonical source-of-truth hashes.

The guarded patcher `tools/patch_ems_v28_6_hard_deny_20min.py` is retained only as migration/recovery documentation for the old v28.5 baseline. It is expected to refuse the current v28.6 blobs.

## Runtime control files for v28.6

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
