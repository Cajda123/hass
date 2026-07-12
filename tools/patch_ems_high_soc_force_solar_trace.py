#!/usr/bin/env python3
"""Patch EMS Home Assistant helpers and Node-RED flow for high-SOC solar loads.

Run from repository root:

    python3 tools/patch_ems_high_soc_force_solar_trace.py

The patch is intentionally text based because Node-RED stores function bodies as
strings inside JSON. It fails loudly when an expected anchor is missing.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW_PATH = ROOT / "nodered" / "flows.json"
HA_PATH = ROOT / "homeassistant" / "ems_base.yaml"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Anchor not found for {label}")
    return text.replace(old, new, 1)


def ensure_force_solar_helpers(yaml_text: str) -> str:
    # Main wallbox mode keeps old SOLAR/GRID/AUTO behavior. Force one-shot modes
    # live in per-load force helpers.
    yaml_text = yaml_text.replace(
        "options: ['OFF', 'FORCE_ANYTIME', 'FORCE_NT_ONLY']",
        "options: ['OFF', 'FORCE_SOLAR', 'FORCE_ANYTIME', 'FORCE_NT_ONLY']",
    )

    # Boiler top-level mode also needs the generic one-shot modes, otherwise core
    # can see only legacy FORCE_BOTTOM/FORCE_PERGOLA.
    old = """  ems_boiler_mode:\n    name: EMS bojlery režim\n    icon: mdi:water-boiler\n    options:\n      - AUTO\n      - FORCE_BOTTOM\n      - FORCE_PERGOLA\n      - 'OFF'\n    initial: AUTO"""
    new = """  ems_boiler_mode:\n    name: EMS bojlery režim\n    icon: mdi:water-boiler\n    options:\n      - AUTO\n      - FORCE_SOLAR\n      - FORCE_ANYTIME\n      - FORCE_NT_ONLY\n      - FORCE_BOTTOM\n      - FORCE_PERGOLA\n      - 'OFF'\n    initial: AUTO"""
    if old in yaml_text:
        yaml_text = yaml_text.replace(old, new, 1)

    # Tunable core thresholds used by Node-RED. Add only once.
    if "ems_high_soc_load_threshold" not in yaml_text:
        anchor = """  ems_wallbox_max_current_a:\n    name: EMS wallbox maximální proud\n    min: 6\n    max: 16\n    step: 1\n    unit_of_measurement: A\n    icon: mdi:ev-station\n    initial: 16\n"""
        insert = anchor + """
  ems_high_soc_load_threshold:
    name: EMS SOC pro rychlé FV zátěže
    min: 50
    max: 100
    step: 1
    unit_of_measurement: "%"
    icon: mdi:battery-high
    initial: 90

  ems_full_soc_load_threshold:
    name: EMS SOC pro aktivní hledání zátěže
    min: 50
    max: 100
    step: 1
    unit_of_measurement: "%"
    icon: mdi:battery-charging-high
    initial: 95

  ems_high_soc_load_min_charge_w:
    name: EMS min. nabíjení baterie pro SOC zátěže
    min: 0
    max: 3000
    step: 50
    unit_of_measurement: W
    icon: mdi:solar-power
    initial: 100

  ems_solar_load_support_hard_limit_w:
    name: EMS tvrdý limit podpory FV zátěží z baterie
    min: -6000
    max: 0
    step: 100
    unit_of_measurement: W
    icon: mdi:battery-arrow-down
    initial: -3000
"""
        yaml_text = replace_once(yaml_text, anchor, insert, "HA high SOC helper block")

    # MQTT trace sensor for dashboard/debug. Add only once.
    if "ems_decision_trace" not in yaml_text:
        yaml_text += """

###############################################################################
# EMS decision trace
###############################################################################
mqtt:
  sensor:
    - name: EMS Decision Trace
      unique_id: ems_decision_trace
      state_topic: ems/decision/trace
      value_template: >-
        {{ value_json.summary | default(value_json.boiler.selected | default('unknown')) }}
      json_attributes_topic: ems/decision/trace
"""
    return yaml_text


def patch_core_function(func: str) -> str:
    if "high_soc_load_threshold" in func:
        return func

    old = """    ems_live_notifications: b('input_boolean.ems_live_notifications'),\n\n    battery_soc: n(s('sensor.ems_battery_soc')),"""
    new = """    ems_live_notifications: b('input_boolean.ems_live_notifications'),\n\n    high_soc_load_threshold: n(s('input_number.ems_high_soc_load_threshold'), 90),\n    full_soc_load_threshold: n(s('input_number.ems_full_soc_load_threshold'), 95),\n    high_soc_load_min_charge_w: n(s('input_number.ems_high_soc_load_min_charge_w'), 100),\n    solar_load_support_hard_limit_w: n(s('input_number.ems_solar_load_support_hard_limit_w'), -3000),\n\n    battery_soc: n(s('sensor.ems_battery_soc')),"""
    func = replace_once(func, old, new, "core helper reads")

    old = """ems.core.battery_above_effective_min = ems.core.battery_soc > ems.core.effective_min_soc && !ems.core.battery_load_locked;\nems.core.battery_above_hard_min = ems.core.battery_soc > ems.core.hard_min_soc;"""
    new = """ems.core.battery_above_effective_min = ems.core.battery_soc > ems.core.effective_min_soc && !ems.core.battery_load_locked;\nems.core.battery_above_hard_min = ems.core.battery_soc > ems.core.hard_min_soc;\nems.core.high_soc_loads_allowed = !!(\n    ems.core.ems_enabled &&\n    ems.core.ems_allow_solar_loads &&\n    !ems.core.battery_load_locked &&\n    ems.core.battery_above_effective_min &&\n    ems.core.battery_soc >= ems.core.high_soc_load_threshold &&\n    ems.core.battery_power >= ems.core.solar_load_support_hard_limit_w\n);\nems.core.full_soc_load_probe = !!(\n    ems.core.high_soc_loads_allowed &&\n    ems.core.battery_soc >= ems.core.full_soc_load_threshold\n);\nems.core.decision_inputs = {\n    soc: ems.core.battery_soc,\n    battery_power_w: ems.core.battery_power,\n    target_soc: ems.core.target_soc,\n    effective_min_soc: ems.core.effective_min_soc,\n    locked: ems.core.battery_load_locked,\n    solar_loads_allowed: ems.core.ems_allow_solar_loads,\n    high_soc_loads_allowed: ems.core.high_soc_loads_allowed,\n    full_soc_load_probe: ems.core.full_soc_load_probe,\n    hdo: ems.core.hdo_state,\n    tariff: ems.core.tariff_class\n};"""
    return replace_once(func, old, new, "core high SOC state")


def patch_boiler_function(func: str) -> str:
    if "high_soc_loads_allowed" in func and "decision_trace" in func:
        return func

    func = func.replace(
        "const FORCE_BATTERY_SUPPORT_HARD_LIMIT_W = -3000;",
        "const FORCE_BATTERY_SUPPORT_HARD_LIMIT_W = n(core.solar_load_support_hard_limit_w, -3000);",
    )

    old = """const highSurplus = batteryPower > 2500;\nconst veryHighSurplus = batteryPower > 5500;\nconst fullBatteryProbeMode = n(core.battery_soc) >= 95 && Math.abs(batteryPower) < 150;"""
    new = """const highSurplus = batteryPower > 2500;\nconst veryHighSurplus = batteryPower > 5500;\nconst highSocLoadMode = !!core.high_soc_loads_allowed;\nconst fullBatteryProbeMode = !!core.full_soc_load_probe;\nconst highSocFirstStageAllowed = highSocLoadMode && batteryPower >= n(core.solar_load_support_hard_limit_w, -3000);\nconst highSocSecondStageAllowed = highSocLoadMode && batteryPower >= -BATTERY_ZERO_BAND_W;"""
    func = replace_once(func, old, new, "boiler high SOC mode")

    old = """} else if (!surplusStable && !fullBatteryProbeMode) {\n    decision = makeDecision('IDLE', 'waiting_for_stable_surplus');"""
    new = """} else if (!surplusStable && !fullBatteryProbeMode && !highSocFirstStageAllowed) {\n    decision = makeDecision('IDLE', 'waiting_for_stable_surplus');"""
    func = replace_once(func, old, new, "boiler stable surplus bypass")

    old = """} else if (bottomNeedsHeat) {\n    decision = makeDecision('BOTTOM_BOILER', 'bottom_boiler_stable_surplus');\n    bottom(decision, veryHighSurplus);\n\n} else if (pergolaNeedsHeat) {\n    decision = makeDecision('PERGOLA_DUMMY_LOAD', fullBatteryProbeMode ? 'full_battery_probe_mode' : 'low_priority_dummy_load_stable_surplus');\n    pergola(decision, veryHighSurplus || fullBatteryProbeMode);"""
    new = """} else if (bottomNeedsHeat) {\n    decision = makeDecision('BOTTOM_BOILER', highSocFirstStageAllowed && !surplusStable ? 'high_soc_use_available_energy_bottom' : 'bottom_boiler_stable_surplus');\n    bottom(decision, veryHighSurplus || highSocSecondStageAllowed);\n\n} else if (pergolaNeedsHeat) {\n    decision = makeDecision('PERGOLA_DUMMY_LOAD', highSocFirstStageAllowed && !surplusStable ? 'high_soc_use_available_energy_pergola' : (fullBatteryProbeMode ? 'full_battery_probe_mode' : 'low_priority_dummy_load_stable_surplus'));\n    pergola(decision, veryHighSurplus || fullBatteryProbeMode || highSocSecondStageAllowed);"""
    func = replace_once(func, old, new, "boiler high SOC decisions")

    old = """    full_battery_probe_mode: fullBatteryProbeMode,"""
    new = """    full_battery_probe_mode: fullBatteryProbeMode,\n    high_soc_load_mode: highSocLoadMode,\n    high_soc_first_stage_allowed: highSocFirstStageAllowed,\n    high_soc_second_stage_allowed: highSocSecondStageAllowed,"""
    func = replace_once(func, old, new, "boiler debug high SOC")

    old = """ems.memory.boiler_stable = mem;\nems.ai_event = aiEvent('ems/boiler', 'boiler', decision);\nems.boiler = decision;"""
    new = """ems.memory.boiler_stable = mem;\nems.decision_trace = ems.decision_trace || {};\nems.decision_trace.boiler = {\n    selected: decision.mode,\n    reason: decision.reason,\n    inputs: {\n        soc: n(core.battery_soc),\n        battery_power_w: batteryPower,\n        target_soc: n(core.target_soc),\n        solar_loads_allowed: solarLoadsAllowed,\n        high_soc_loads_allowed: highSocLoadMode,\n        full_soc_load_probe: fullBatteryProbeMode,\n        bottom_needs_heat: bottomNeedsHeat,\n        pergola_needs_heat: pergolaNeedsHeat,\n        wallbox_recently_active: wallboxRecentlyActive\n    },\n    checks: [\n        {check:'ems_enabled', result:!!core.ems_enabled},\n        {check:'mode_not_off', value:modeHelper, result:modeHelper !== 'OFF'},\n        {check:'battery_load_locked', result:!core.battery_load_locked},\n        {check:'battery_safe', result:batterySafe},\n        {check:'wallbox_lockout', result:!wallboxRecentlyActive},\n        {check:'solar_loads_allowed', result:solarLoadsAllowed},\n        {check:'stable_surplus', result:!!surplusStable},\n        {check:'high_soc_bypass_stable_surplus', value:n(core.battery_soc), threshold:n(core.high_soc_load_threshold,90), result:highSocFirstStageAllowed},\n        {check:'battery_not_below_hard_support_limit', value:batteryPower, threshold:n(core.solar_load_support_hard_limit_w,-3000), result:batteryPower >= n(core.solar_load_support_hard_limit_w,-3000)},\n        {check:'second_stage_allowed', value:batteryPower, threshold:-BATTERY_ZERO_BAND_W, result:highSocSecondStageAllowed}\n    ]\n};\nems.ai_event = aiEvent('ems/boiler', 'boiler', decision);\nems.boiler = decision;"""
    return replace_once(func, old, new, "boiler decision trace")


def patch_decision_state_function(func: str) -> str:
    if "ems/decision/trace" in func:
        return func

    # Most flow versions have a single decision/state publisher. If it cannot be
    # found, this is harmless because boiler still stores ems.decision_trace.boiler.
    marker = "msg.topic = 'ems/decision/state';"
    if marker not in func:
        return func

    old = """msg.topic = 'ems/decision/state';\nmsg.payload = state;\nreturn msg;"""
    new = """const trace = {\n    ts: Date.now(),\n    summary: `${state.mode || 'READY'} / boiler=${state.boiler || 'unknown'} / wallbox=${state.wallbox || 'unknown'} / grid=${state.grid || 'unknown'}`,\n    state,\n    core: ems.core?.decision_inputs || null,\n    boiler: ems.decision_trace?.boiler || null,\n    wallbox: ems.decision_trace?.wallbox || null,\n    grid: ems.decision_trace?.grid || null\n};\nnode.send({topic:'ems/decision/trace', payload:trace});\nmsg.topic = 'ems/decision/state';\nmsg.payload = state;\nreturn msg;"""
    return func.replace(old, new, 1) if old in func else func


def patch_flow() -> None:
    data = json.loads(FLOW_PATH.read_text(encoding="utf-8"))
    touched = []
    for node in data:
        if node.get("type") != "function":
            continue
        name = node.get("name", "")
        func = node.get("func", "")
        new_func = func
        if node.get("id") == "ems_core_build" or name.startswith("build global.ems.core"):
            new_func = patch_core_function(func)
        elif node.get("id") == "ems_boiler_decision" or name.startswith("boiler decision"):
            new_func = patch_boiler_function(func)
        elif "decision/state" in func and "ems/decision/state" in func:
            new_func = patch_decision_state_function(func)
        if new_func != func:
            node["func"] = new_func
            touched.append(node.get("id") or name)

    if not touched:
        raise RuntimeError("No Node-RED function nodes were patched")
    FLOW_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print("patched flow nodes:", ", ".join(touched))


def patch_ha() -> None:
    text = HA_PATH.read_text(encoding="utf-8")
    new = ensure_force_solar_helpers(text)
    if new != text:
        HA_PATH.write_text(new, encoding="utf-8")
        print("patched", HA_PATH)
    else:
        print("HA helpers already patched")


def main() -> None:
    patch_ha()
    patch_flow()
    # Validate final JSON and function syntax sufficiently for Node-RED import.
    data = json.loads(FLOW_PATH.read_text(encoding="utf-8"))
    function_count = sum(1 for n in data if n.get("type") == "function")
    print(f"validated JSON with {len(data)} nodes, {function_count} function nodes")


if __name__ == "__main__":
    main()
