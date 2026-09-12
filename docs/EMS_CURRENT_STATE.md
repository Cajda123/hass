# EMS current state

**Handoff target version:** v28.6  
**Date:** 2026-09-12  
**Git runtime commit with v28.6 applied:** `44b80f3541cac66c38b38f71bbba8538627830d0`  
**Repository:** `Cajda123/hass`  
**Control stack:** Home Assistant + Node-RED + MQTT  
**Primary rule:** Node-RED is the deterministic control system. AI may explain state, but must not become a second actuator/controller.

This file is the permanent handoff context for Codex and future maintainers. Before changing EMS, read this file together with `AGENTS.md` and the runtime files listed in `EMS_SOURCE_MANIFEST.md`.

## Handoff status

**v28.6 is committed on `main` and is now the Git source of truth.** The runtime commit is `44b80f3541cac66c38b38f71bbba8538627830d0`. The three canonical runtime blobs are listed in `docs/EMS_SOURCE_MANIFEST.md` and were verified after the commit.

The guarded migration/recovery patcher remains in the repository as:

`tools/patch_ems_v28_6_hard_deny_20min.py`

Do **not** run that patcher on the current v28.6 runtime; it intentionally accepts only the pre-v28.6 baseline and will refuse the current blobs. Future Codex work should edit the current runtime files directly, keep changes small/reviewable, and update this document plus `EMS_SOURCE_MANIFEST.md` whenever behavior or source-of-truth hashes change.

## 1. Source of truth

The current EMS is split across:

- `nodered/flows.json` – deterministic runtime logic: core state, planning, wallbox, battery-grid, boilers, dispatcher, tasks, cost meter, safety, heating, notifications and debug logger.
- `homeassistant/ems_base.yaml` – helpers, template entities, scripts and MQTT entities used by the EMS core.
- `homeassistant/02_ems_heating.yaml` – heating/wood/buffer/gas/DHW layer. v28.6 deliberately does not change its behavior.
- `homeassistant/03_ems_notifications.yaml` – EV evening consent helpers, actionable mobile questions/answers and EV control audit.
- `homeassistant/ems_ai.yaml` – AI/commentary routing; AI is informational only.
- `homeassistant/dashboard_family.yaml` and `homeassistant/dashboard_technic.yaml` – family and technical UI.
- `nodered/ems_ai_commentator_flow.json` – separate AI commentator flow.

Git `main` is the canonical desired state. Production Home Assistant / Node-RED must still be deployed/reloaded manually after a Git-only change.

## 2. High-level architecture and authority

EMS is layered. The intended authority order is:

1. **Safety / dispatcher guards** – phase limits, inverter limits, stale/invalid data, emergency battery behavior.
2. **Explicit per-car user veto (`DENY_GRID`)** – hard block of grid energy for that car for the current physical plug-in session.
3. **Manual force tasks** – targeted wallbox/boiler/battery tasks, still subject to safety and per-car grid veto.
4. **Balance campaign / battery protection locks**.
5. **Planner / normal AUTO, SOLAR, GRID behavior**.
6. **Notifications / AI commentary** – may explain or ask, never directly override safety.

A later/lower layer must never silently bypass a higher layer.

## 3. EV identity and wallbox mapping

- **ID.3 / Gabča**
  - wallbox 2
  - enable: `switch.tuya_wallbox_2_wallbox_charge_enable`
  - power: `sensor.tuya_wallbox_2_wallbox_total_power`
  - force helper: `input_select.ems_id3_wallbox_force_mode`
  - evening consent: `input_select.ems_id3_evening_grid_consent`
- **ID.4 / David**
  - wallbox 1
  - enable: `switch.tuya_wallbox_1_wallbox_charge_enable`
  - power: `sensor.tuya_wallbox_1_wallbox_total_power`
  - force helper: `input_select.ems_id4_wallbox_force_mode`
  - evening consent: `input_select.ems_id4_evening_grid_consent`

`binary_sensor.ems_id3_wallbox_connected` and `binary_sensor.ems_id4_wallbox_connected` treat these Tuya states as still physically connected:

`Plugged`, `Waiting`, `Ready`, `Charging`, `Finished`.

`Finished` is intentionally included. Reaching charge-complete must not be mistaken for unplugging the cable.

## 4. EV physical session semantics

A physical session does not end because the wallbox reports a short error/idle/disconnect transition.

### Consent session

For evening GRID consent:

- short raw disconnects do not reset the decision;
- `DENY_GRID` survives reaching target SOC;
- `DENY_GRID` survives target changes while the same cable session continues;
- session reset to `AUTO` occurs only after **20 minutes of continuous raw disconnect**;
- after a real session reset, the next plug-in starts fresh.

This 20-minute timeout intentionally filters transient Tuya/wallbox state errors.

### Force-task session

A wallbox force task has its normal terminal conditions (SOC, ENERGY, TIME, NT_END, FORCE_SOLAR guards) **plus physical unplug**:

- short disconnect: task is preserved / may wait for car;
- continuous raw disconnect for **20 minutes**: task becomes `CANCELLED`, reason `car_disconnected_20min`;
- terminal cleanup sets the corresponding `input_select.ems_id*_wallbox_force_mode` back to `OFF`;
- the disconnect timer is evaluated even while `FORCE_NT_ONLY` is waiting in `PENDING_NT`.

This prevents an old overnight `FORCE_NT_ONLY` request from surviving all day after the car has actually left.

## 5. Per-car GRID consent

Consent values:

- `AUTO` – planner decides normally.
- `PENDING` – question has been sent and is waiting for the user.
- `ALLOW_GRID` – the approved missing energy may be bought from GRID; planner caps it to the approved shortfall.
- `BATTERY_ONLY` – automatic calculation says the target should be possible without GRID.
- `DENY_GRID` – explicit user decision: **do not use GRID for this car during this physical session**.

### v28.6 hard-veto invariant

`DENY_GRID` is checked again in the Wallbox Manager, not only in the planner.

Therefore a denied car must not be enabled on GRID by:

- normal grid-purchase planner output;
- global GRID/force fallback paths;
- stale `FORCE_NT_ONLY`;
- `FORCE_ANYTIME`;
- any future upstream plan that accidentally marks the car active.

If every requested GRID car is denied, the Wallbox Manager returns a disabled decision (`grid_denied_by_user` or `grid_denied_by_user_force_task`) instead of energizing a wallbox.

`FORCE_SOLAR` is solar-only and is not blocked by `DENY_GRID`, because the veto is specifically against grid energy.

## 6. Evening EV question

Notification Manager evaluates evening EV energy roughly from **18:00 to 23:45**.

Safe energy for cars from the house battery is:

- energy above the protected floor;
- protected floor = maximum of hard minimum, effective minimum and active balance-campaign preserve floor;
- multiplied by 0.90 efficiency factor.

The evening calculation intentionally does **not** separately subtract projected overnight house consumption; this is an explicit existing design decision.

When both cars need energy, allocation order is:

1. explicit wallbox priority;
2. earlier departure;
3. proportional allocation if neither distinguishes the cars.

In `AUTO`:

- if battery energy is enough: informational `BATTERY_ONLY`;
- if not enough and GRID is globally allowed: actionable question to the owner;
- YES -> `ALLOW_GRID`;
- NO -> `DENY_GRID`.

In manual `SOLAR` / `FORCE_SOLAR` / `OFF`, EMS does not silently switch to GRID. It may warn that the target will not be reached.

Owners:

- ID.4 -> David, direct mobile app notify.
- ID.3 -> Gabča; direct notifier is configured by `input_text.ems_id3_owner_notify_service`.

## 7. Force modes

Per-car wallbox force helper supports:

- `OFF`
- `FORCE_ANYTIME`
- `FORCE_NT_ONLY`
- `FORCE_SOLAR`

Goals:

- `SOC`
- `ENERGY`
- `TIME`
- `NT_END`

Important semantics:

- `FORCE_NT_ONLY` may remain pending between NT windows only while the force task itself is valid.
- 20-minute real unplug cancels it.
- `DENY_GRID` blocks GRID force modes for the denied car.
- `FORCE_SOLAR` remains solar/battery only and is still subject to its voltage / AC-in safety guards.

## 8. Wallbox normal modes

Global helper `input_select.ems_wallbox_mode` currently exposes:

- `AUTO`
- `SOLAR`
- `GRID`
- `OFF`

AUTO uses planner output. SOLAR uses PV/battery only within protection limits. GRID follows allowed grid plan. OFF disables controllable EV charging.

The wallbox regulator includes:

- stepped current;
- wallbox self-load compensation;
- battery support limit;
- inverter per-phase hard guard;
- actual-vs-target stabilization;
- priority selection between cars.

The dispatcher independently enforces actual output/current changes and safety guards.

## 9. Planner / GRID purchase

Planner tracks each car independently:

- SOC and target;
- required kWh;
- connected state;
- optional departure deadline;
- effective evening consent;
- approved grid kWh.

For `DENY_GRID`, planner grid need is zero in AUTO. v28.6 adds the downstream Wallbox Manager veto as a second independent safety barrier.

For `ALLOW_GRID`, only the approved shortfall is eligible for purchase. It is not permission to buy arbitrary extra energy.

GRID purchase is scheduled into HDO/NT windows and uses per-car load records.

## 10. Battery protection and balancing

Existing behavior is retained from v27/v28.5:

- effective minimum / target hysteresis;
- persistent battery-load lock;
- AC-in safety manager;
- emergency charge separated from normal AUTO grid charge;
- stable NT grid-start/stop sequencing;
- weekly/multiday balance campaign;
- balance campaign preserve floor;
- `RUNNING` / `WAITING_NEXT_SOLAR_DAY` campaign states and grid fallback logic;
- inverter per-phase hard guard.

Normal home-battery AUTO grid charge is an energy-balance decision. Effective/target SOC is not blindly treated as a grid-charge target.

## 11. Heating / DHW

`homeassistant/02_ems_heating.yaml` and EMS 10 Heating Manager are intentionally unchanged by v28.6.

Current heating layer includes:

- WOOD / BUFFER / GAS source selection;
- common wood-availability question;
- configurable wait before gas fallback;
- DHW source coordination;
- `FORCE_GAS`;
- protection of heating circuit during gas DHW.

Do not modify heating as a side effect of EV work.

## 12. Notifications and physical-state events

Notification Manager also emits low-noise state changes for meaningful physical events, for example:

- house actually switches to GRID / back to SBU;
- each car starts/stops actual GRID charging;
- house battery starts/stops GRID charging;
- emergency charge start/end;
- useful balance campaign transitions.

Physical EV grid charging is based on actual wallbox enable + measured wallbox power, not a synthetic wallbox-state selector.

## 13. EV control audit

v28.6 adds audit for changes of:

- `input_select.ems_id3_wallbox_force_mode`
- `input_select.ems_id4_wallbox_force_mode`
- `input_select.ems_id3_evening_grid_consent`
- `input_select.ems_id4_evening_grid_consent`
- `input_select.ems_wallbox_mode`

Home Assistant publishes `ems/audit/control_change` including:

- entity id;
- old/new state;
- `context.user_id`;
- context id / parent id;
- timestamp.

Node-RED Debug Logger subscribes to this topic and writes it into the normal EMS debug log. This exists because historical logs could prove that a stale `FORCE_NT_ONLY` existed but could not identify the original actor that set it.

## 14. Incident that motivated v28.6

On the night of 2026-09-11/12 both users explicitly chose **"Ne, bez sítě"** after the evening question.

Two separate escape paths were found:

1. ID.4 had an older `FORCE_NT_ONLY` task waiting for NT. When NT became active, manual wallbox task logic had higher practical authority than planner consent, so the car charged from GRID despite `DENY_GRID`.
2. ID.3 later lost `DENY_GRID` after connection/session handling interpreted the wallbox state as disconnected; once consent returned to AUTO, the normal planner was allowed to schedule GRID.

Contributing weaknesses:

- `DENY_GRID` existed only as planner input, not a downstream hard veto.
- force task did not terminate after a long real unplug while pending for NT.
- `Finished` was not considered connected.
- old HA package contained a 30-second raw-unplug consent reset.
- Notification Manager cleared explicit consent on target lifecycle transitions.

v28.6 closes all of those paths.

## 15. Debugging / regression checks

For any future EV change, test at least:

1. ID.3 denied, ID.4 allowed, both connected.
2. ID.4 denied while a `FORCE_NT_ONLY` task is active.
3. Both denied, planner requests GRID.
4. `Finished` state while cable remains plugged.
5. raw disconnect <20 min then recovery.
6. raw disconnect >20 min -> consent reset + force task cancellation/cleanup.
7. target reached while DENY remains set.
8. Node-RED deploy/restart with PENDING notification.
9. both cars connected with different SOC, targets and departures.
10. phase/inverter guard while a force task asks for high current.

Expected hard rule: a denied car must never have `decision.*.charge_enable=true` when Wallbox Manager decision source is GRID.

## 16. Deployment

After changing `nodered/flows.json`:

- import/replace the full flow set;
- use **Full Deploy**;
- confirm Node-RED starts without function syntax errors.

After changing `homeassistant/ems_base.yaml` or `03_ems_notifications.yaml`:

- reload applicable template/package/automation configuration if supported;
- otherwise restart Home Assistant;
- verify helper/entity states before enabling large loads.

After v28.6 deployment verify in logs:

- `ems/audit/control_change` appears after changing an EV force helper;
- `DENY_GRID` plus `FORCE_NT_ONLY` produces `grid_denied_by_user_force_task`;
- force mode returns to `OFF` after >20 min real unplug;
- `Finished` keeps the car connected.
