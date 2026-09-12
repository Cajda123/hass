# Incident: EV charged from GRID after explicit DENY_GRID

**Date investigated:** 2026-09-12  
**Resolved in:** EMS v28.6

## User-visible symptom

Both car owners received the evening EMS question about using low-tariff GRID energy for the remaining EV deficit and both chose **"Ne, bez sítě"**. By morning both cars had nevertheless received grid energy.

## What the logs established

The two cars escaped the intended policy through different paths.

### ID.4

An older `FORCE_NT_ONLY` wallbox task existed before the evening decision. The task could remain `PENDING_NT` across tariff windows. When NT became active, the Wallbox Manager's manual-force path could energize ID.4 from GRID even though the evening consent helper was `DENY_GRID`.

Historical EMS logs recorded the force task itself, but did not contain Home Assistant context metadata identifying who/what originally changed the force helper. v28.6 adds control-change audit for future attribution.

### ID.3

ID.3 correctly received `DENY_GRID`, but connection/session lifecycle later reset the consent to `AUTO`. Normal planner logic was then allowed to schedule grid purchase for the remaining deficit.

## Root causes

1. `DENY_GRID` was enforced in the planner only.
2. Manual wallbox force tasks bypassed planner consent.
3. A pending force task had no terminal "car really left" condition.
4. EV connected template did not count wallbox state `Finished` as still plugged.
5. The old HA notification package contained 30-second raw disconnect consent-reset automations.
6. Notification Manager could clear consent at target/session lifecycle transitions.

## v28.6 regression-prevention rules

- `DENY_GRID` is a hard per-car Wallbox Manager veto.
- It overrides planner GRID and GRID-based force tasks.
- `FORCE_SOLAR` remains allowed because it does not use GRID.
- `DENY_GRID` survives reaching target and target changes within the same physical session.
- Real session reset requires 20 minutes of continuous raw disconnect.
- Force tasks are cancelled and cleaned to `OFF` after 20 minutes of continuous raw disconnect, including while waiting in `PENDING_NT`.
- `Finished` counts as connected.
- EV force/consent changes are audited with HA context ids and `user_id`.

## Required regression test

At minimum, create an active ID.4 `FORCE_NT_ONLY` task, set `input_select.ems_id4_evening_grid_consent=DENY_GRID`, make NT active, and verify Wallbox Manager returns disabled with `grid_denied_by_user_force_task` and ID.4 `charge_enable=false`.
