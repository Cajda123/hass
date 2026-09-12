#!/usr/bin/env python3
"""Guarded EMS v28.6 patch: hard EV DENY_GRID + 20min EV session/force unplug."""
from pathlib import Path
import json, hashlib, shutil, sys

root=Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()
flow_p=root/"nodered/flows.json"
base_p=root/"homeassistant/ems_base.yaml"
notif_p=root/"homeassistant/03_ems_notifications.yaml"

IN={
    flow_p:"a8e38895ac1f82eb00abe713a12017cd9a895bc5",
    base_p:"afbe1eec4571134a9961e2df711fbd0ca3c37f97",
    notif_p:"213123e234449ec8179df3f523b84c2477e9a8b5",
}
OUT={
    flow_p:"1390d47c4aa18983288d3bffd3850746afecc370",
    base_p:"27401d42ea9d3b93a19ea319fcdcab2720785e9d",
    notif_p:"c2e88f5d0aae20d7e21923faab83ba1ab887e582",
}
def bsha(p):
    b=p.read_bytes()
    return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()
def rep(s,a,b):
    if a not in s: raise RuntimeError("patch anchor missing")
    return s.replace(a,b,1)

for p,want in IN.items():
    if not p.exists() or bsha(p)!=want:
        raise SystemExit(f"REFUSING PATCH: {p} blob={bsha(p) if p.exists() else 'missing'} expected={want}")

flow=json.loads(flow_p.read_text(encoding="utf-8"))
n={x["id"]:x for x in flow}

# Task Manager: a wallbox force task is terminal after 20min continuous raw unplug,
# even while FORCE_NT_ONLY waits for NT. Short glitches only pause it.
t=n["ems_task_manager"]; s=t["func"]
t["name"]="Task Manager multiday balance campaign persistent v13 EV disconnect timeout + heating-aware"
s=rep(s,
"car_not_connected:'Čeká na připojení auta', manual_force_wallbox_charge:'Ruční nabíjení auta', no_battery_task:'Žádný bateriový úkol',",
"car_not_connected:'Čeká na připojení auta', car_disconnected_20min:'Auto je odpojené déle než 20 minut', manual_force_wallbox_charge:'Ruční nabíjení auta', no_battery_task:'Žádný bateriový úkol',")
s=rep(s,
"""    mem.wallboxes[id] = mem.wallboxes[id] || {
        active_since: 0, energy_kwh: 0, last_ts: 0, last_mode: 'OFF',
        last_goal: 'SOC', force_solar: null
    };
    const wm = mem.wallboxes[id];
""",
"""    mem.wallboxes[id] = mem.wallboxes[id] || {
        active_since: 0, energy_kwh: 0, last_ts: 0, last_mode: 'OFF',
        last_goal: 'SOC', force_solar: null,
        disconnect_since: 0, seen_connected: false
    };
    const wm = mem.wallboxes[id];

    // Force wallbox task lifecycle:
    // - short wallbox/state glitches only pause the task;
    // - continuous physical disconnect for 20 minutes terminates the force task;
    // - this check also runs while FORCE_NT_ONLY is waiting for the next NT.
    const rawConnected = id === 'id3'
        ? !!core.id3_connected_raw
        : !!core.id4_connected_raw;
    const FORCE_UNPLUG_TIMEOUT_MS = 20 * 60 * 1000;
    if (rawConnected) {
        wm.disconnect_since = 0;
        wm.seen_connected = true;
    } else if (!wm.disconnect_since) {
        wm.disconnect_since = now;
    }
    const unplugExpired = !rawConnected &&
        wm.disconnect_since > 0 &&
        (now - wm.disconnect_since) >= FORCE_UNPLUG_TIMEOUT_MS;
""")
s=rep(s,"    const forceGuard = forceSolarGuard(wm, m, taskKey, label);\n",
"""    if (m !== 'OFF' && unplugExpired) {
        const progress = `odpojeno ${round((now - wm.disconnect_since) / 60000, 1)} min`;
        mem.history.unshift({
            type:`${id}_wallbox_force`,
            result:'CANCELLED',
            finished_ts:now,
            goal,
            progress,
            energy_kwh:round(wm.energy_kwh || 0,2),
            soc:round(carSoc,1),
            reason:'car_disconnected_20min'
        });
        mem.history = mem.history.slice(0,20);
        wm.active_since = 0;
        wm.last_ts = now;
        wm.last_mode = m;
        wm.last_goal = goal;
        return {
            active:false, pending:false, completed:false, terminal:true,
            status:'CANCELLED', type:'wallbox_force', id, label, mode:m, goal,
            reason:'car_disconnected_20min', progress, current_a:current,
            energy_kwh:round(wm.energy_kwh || 0,3), soc:round(carSoc,1),
            solar_only:!!win.solar_only, grid_allowed:!!win.grid_allowed,
            disconnect_minutes:round((now - wm.disconnect_since) / 60000,1),
            run_id: wm.force_solar?.run_id || ''
        };
    }

    const forceGuard = forceSolarGuard(wm, m, taskKey, label);
""")
s=rep(s,
"""    if (!activeMode) {
        wm.active_since = 0; wm.energy_kwh = 0; wm.last_ts = now; wm.last_mode = m; wm.last_goal = goal;
        return { active:false, pending:win.pending, status:win.status, type:'wallbox_force', id, label, mode:m, goal, reason:win.reason, current_a:current, solar_only:!!win.solar_only, grid_allowed:!!win.grid_allowed };
    }
""",
"""    if (!activeMode) {
        wm.active_since = 0;
        if (m === 'OFF') {
            wm.energy_kwh = 0;
            wm.disconnect_since = 0;
            wm.seen_connected = false;
        }
        wm.last_ts = now; wm.last_mode = m; wm.last_goal = goal;
        return {
            active:false, pending:win.pending, status:win.status,
            type:'wallbox_force', id, label, mode:m, goal, reason:win.reason,
            current_a:current, solar_only:!!win.solar_only, grid_allowed:!!win.grid_allowed,
            disconnect_since:wm.disconnect_since || 0,
            disconnect_timeout_min:20
        };
    }
""")
s=rep(s,
"""    if (!connected) {
        wm.active_since = 0; wm.last_ts = now;
        return { active:false, pending:true, status:'WAITING_CAR', type:'wallbox_force', id, label, mode:m, goal, reason:'car_not_connected', current_a:current, solar_only:!!win.solar_only, grid_allowed:!!win.grid_allowed };
    }
""",
"""    if (!connected) {
        // Core connection latch already filtered short glitches. Keep the force request
        // pending until the independent 20min raw-disconnect timer expires.
        wm.last_ts = now;
        return {
            active:false, pending:true, status:'WAITING_CAR',
            type:'wallbox_force', id, label, mode:m, goal,
            reason:'car_not_connected', current_a:current,
            solar_only:!!win.solar_only, grid_allowed:!!win.grid_allowed,
            disconnect_since:wm.disconnect_since || 0,
            disconnect_minutes:wm.disconnect_since ? round((now-wm.disconnect_since)/60000,1) : 0,
            disconnect_timeout_min:20
        };
    }
""")
t["func"]=s

# Wallbox Manager: DENY_GRID is a downstream hard veto, including grid force tasks.
w=n["ems_wallbox_decision"]; s=w["func"]
w["name"]="wallbox self-load compensated regulator v24 hard EV DENY_GRID veto campaign-aware"
s=rep(s,
"""const states = ha?.homeAssistant?.states || {};

let ems = global.get('ems') || {};
""",
"""const states = ha?.homeAssistant?.states || {};

function eveningGridConsent(id) {
    const entity = id === 'id3'
        ? 'input_select.ems_id3_evening_grid_consent'
        : 'input_select.ems_id4_evening_grid_consent';
    return String(states[entity]?.state || 'AUTO').toUpperCase();
}
function gridDeniedByUser(id) {
    return eveningGridConsent(id) === 'DENY_GRID';
}

let ems = global.get('ems') || {};
""")
a=s.index("function gridCharge(forceFallback = false, reason = 'grid_allowed_by_planner') {")
b=s.index("\n\nfunction forceWallboxTasks()",a)
grid="""function gridCharge(forceFallback = false, reason = 'grid_allowed_by_planner') {
    decision.mode = 'GRID';
    decision.reason = reason;
    decision.transfer_switch = 'GRID';

    const l3 = plan.grid_purchase?.loads?.id3;
    const l4 = plan.grid_purchase?.loads?.id4;
    const denied3 = gridDeniedByUser('id3');
    const denied4 = gridDeniedByUser('id4');

    // DENY_GRID is a hard per-car veto for the whole physical plug-in session.
    // It must beat planner output, global GRID mode and manual FORCE_NT/ANYTIME fallbacks.
    if (l3?.active && !denied3) {
        decision.id3.current_a = clamp(roundCurrent(l3.current_a || 6), 6, 16);
        decision.id3.charge_enable = true;
    }
    if (l4?.active && !denied4) {
        decision.id4.current_a = clamp(roundCurrent(l4.current_a || 6), 6, 16);
        decision.id4.charge_enable = true;
    }

    if (!decision.id3.charge_enable && !decision.id4.charge_enable && forceFallback) {
        let selected = pickPriorityCar(core, plan, mem.active_car);
        if (selected && gridDeniedByUser(selected)) {
            const alternate = selected === 'id3' ? 'id4' : 'id3';
            selected = carNeedsTarget(plan, alternate) && !gridDeniedByUser(alternate)
                ? alternate
                : null;
        }
        if (selected) setCar(decision, selected, 6);
    }

    // Last defensive gate: even if an upstream branch changes later,
    // never leave a denied car enabled on a GRID decision.
    if (denied3) decision.id3.charge_enable = false;
    if (denied4) decision.id4.charge_enable = false;

    if (!decision.id3.charge_enable && !decision.id4.charge_enable) {
        disable(denied3 || denied4 ? 'grid_denied_by_user' : 'grid_no_active_car');
        decision.debug.grid_consent_veto = {
            id3: eveningGridConsent('id3'),
            id4: eveningGridConsent('id4')
        };
        return;
    }

    mem.active_car = decision.id3.charge_enable ? 'id3' : (decision.id4.charge_enable ? 'id4' : null);
    mem.active_since = mem.active_car ? (mem.active_since || now) : 0;
    mem.current_a = Math.max(decision.id3.current_a || 6, decision.id4.current_a || 6);
    decision.debug.grid_consent_veto = {
        id3: eveningGridConsent('id3'),
        id4: eveningGridConsent('id4')
    };
}"""
s=s[:a]+grid+s[b:]
a=s.index("function forceWallboxTasks() {"); b=s.index("\n\nif (!core.ems_enabled)",a)
force="""function forceWallboxTasks() {
    const wt = ems.tasks?.wallbox || {};
    const activeTasks = [wt.id3, wt.id4].filter(t => t?.active);
    const solarOnly = activeTasks.some(t =>
        t?.solar_only === true ||
        String(t?.source || '').toUpperCase() === 'SOLAR' ||
        String(t?.mode || '').toUpperCase() === 'FORCE_SOLAR'
    );
    decision.mode = solarOnly ? 'SOLAR' : 'GRID';
    decision.reason = solarOnly ? 'manual_wallbox_task_force_solar' : 'manual_wallbox_task';
    decision.transfer_switch = solarOnly ? 'SOLAR' : 'GRID';
    decision.ask_priority = false;
    decision.notification_reason = null;
    decision.id3.charge_enable = false;
    decision.id4.charge_enable = false;
    decision.id3.current_a = 6;
    decision.id4.current_a = 6;

    const denied3 = !solarOnly && gridDeniedByUser('id3');
    const denied4 = !solarOnly && gridDeniedByUser('id4');

    if (wt.id3?.active && !denied3) {
        decision.id3.charge_enable = true;
        decision.id3.current_a = clamp(roundCurrent(wt.id3.current_a || 6), 6, 16);
    }
    if (wt.id4?.active && !denied4) {
        decision.id4.charge_enable = true;
        decision.id4.current_a = clamp(roundCurrent(wt.id4.current_a || 6), 6, 16);
    }

    // Explicit "Ne, bez sítě" must beat a stale/manual FORCE_NT_ONLY task too.
    if (!solarOnly && !decision.id3.charge_enable && !decision.id4.charge_enable) {
        disable('grid_denied_by_user_force_task');
        decision.debug.wallbox_task = wt;
        decision.debug.grid_consent_veto = {
            id3: eveningGridConsent('id3'),
            id4: eveningGridConsent('id4')
        };
        return;
    }

    mem.active_car = decision.id3.charge_enable ? 'id3' : (decision.id4.charge_enable ? 'id4' : null);
    mem.active_since = mem.active_car ? (mem.active_since || now) : 0;
    mem.current_a = Math.max(decision.id3.current_a || 6, decision.id4.current_a || 6);
    decision.debug.wallbox_task = wt;
    decision.debug.grid_consent_veto = {
        id3: eveningGridConsent('id3'),
        id4: eveningGridConsent('id4')
    };
}"""
w["func"]=s[:a]+force+s[b:]

# Notification Manager: DENY survives target changes/reached; session reset after 20min raw unplug.
q=n["ems_notify_manager_v28"]; s=q["func"]
q["name"]="Notification Manager v28.6 20min EV session + hard-deny lifecycle"
s=rep(s,
"""        id3: { connected:false, target:null, enough_key:null, question_key:null },
        id4: { connected:false, target:null, enough_key:null, question_key:null }
""",
"""        id3: { connected:false, target:null, enough_key:null, question_key:null, disconnect_since:0 },
        id4: { connected:false, target:null, enough_key:null, question_key:null, disconnect_since:0 }
""")
a=s.index("// Connection / target lifecycle."); b=s.index("\n\nconst evening =",a)
life="""// Connection / target lifecycle.
// Explicit DENY_GRID is valid for the whole physical plug-in session.
// A short wallbox/state glitch must not clear it. Session reset happens only
// after 20 minutes of continuous raw disconnect.
const SESSION_UNPLUG_TIMEOUT_MS = 20 * 60 * 1000;
for (const id of ['id3','id4']) {
    const c = cars[id];
    const cm = mem.cars[id];

    if (c.raw_connected) {
        cm.disconnect_since = 0;
    } else if (!cm.disconnect_since) {
        cm.disconnect_since = now;
    }

    const disconnectedLong = !c.raw_connected &&
        cm.disconnect_since > 0 &&
        (now - cm.disconnect_since) >= SESSION_UNPLUG_TIMEOUT_MS;

    if (disconnectedLong) {
        if (c.consent !== 'AUTO') {
            planUpdate(id, 'AUTO', 0, 0, 0);
            c.consent = 'AUTO';
        }
        mem.cars[id] = {
            connected:false, target:null, enough_key:null, question_key:null,
            disconnect_since:cm.disconnect_since
        };
        continue;
    }

    // Keep explicit DENY for the whole session. A target change is a new planning
    // question only for non-denied states; DENY remains authoritative.
    if (cm.target !== null && Math.abs(n(cm.target) - c.target) >= 0.5) {
        if (c.consent !== 'DENY_GRID') {
            planUpdate(id, 'AUTO', 0, 0, 0);
            c.consent = 'AUTO';
        }
        cm.enough_key = null;
        cm.question_key = null;
    }

    // Reaching the target must not erase DENY_GRID. Other transient/approved
    // states may return to AUTO after their purpose is fulfilled.
    if (!c.needs) {
        if (c.consent !== 'AUTO' && c.consent !== 'DENY_GRID') {
            planUpdate(id, 'AUTO', 0, c.soc, 0);
            c.consent = 'AUTO';
        }
        cm.connected = c.connected || c.raw_connected || cm.connected;
        cm.target = c.target;
        cm.enough_key = null;
        cm.question_key = null;
        continue;
    }

    cm.connected = c.connected || c.raw_connected || cm.connected;
    cm.target = c.target;
}"""
s=s[:a]+life+s[b:]
for car in ("id3","id4"):
    s=rep(s,
f"""            consent:cars.{car}.consent,
            notification_decision:eveningDecision.{car}
""",
f"""            consent:cars.{car}.consent,
            notification_decision:eveningDecision.{car},
            disconnect_since:mem.cars.{car}.disconnect_since || 0,
            session_unplug_timeout_min:20
""")
q["func"]=s

# Debug audit topic -> existing EMS file logger.
d=n["ems_debug_logger_format"]; s=d["func"]
d["name"]="Format compact JSON line v20 EV audit + notifications-aware"
s=rep(s,"    if (topic === 'ems/notifications/state') {\n",
"""    if (topic === 'ems/audit/control_change') {
        return {
            entity_id:p.entity_id,
            from:p.from,
            to:p.to,
            user_id:p.user_id || null,
            context_id:p.context_id || null,
            parent_id:p.parent_id || null,
            source:p.source || 'home_assistant',
            ts:p.ts || null
        };
    }
    if (topic === 'ems/notifications/state') {
""")
d["func"]=s
if not any(x.get("id")=="ems_audit_control_mqtt_in_v286" for x in flow):
    broker=next(x["id"] for x in flow if x.get("type")=="mqtt-broker")
    flow.append({"id":"ems_audit_control_mqtt_in_v286","type":"mqtt in","z":"ems_debug_logger_tab",
        "name":"EMS audit control changes","topic":"ems/audit/control_change","qos":"0",
        "datatype":"auto-detect","broker":broker,"nl":False,"rap":True,"rh":0,"inputs":0,
        "x":170,"y":260,"wires":[["ems_debug_logger_format"]]})

base=base_p.read_text(encoding="utf-8")
base=rep(base,
"""state: '{{ states(''select.tuya_wallbox_2_wallbox_state'') in [''Plugged'', ''Waiting'',
      ''Ready'', ''Charging''] }}""",
"""state: '{{ states(''select.tuya_wallbox_2_wallbox_state'') in [''Plugged'', ''Waiting'',
      ''Ready'', ''Charging'', ''Finished''] }}""")
base=rep(base,
"""state: '{{ states(''select.tuya_wallbox_1_wallbox_state'') in [''Plugged'', ''Waiting'',
      ''Ready'', ''Charging''] }}""",
"""state: '{{ states(''select.tuya_wallbox_1_wallbox_state'') in [''Plugged'', ''Waiting'',
      ''Ready'', ''Charging'', ''Finished''] }}""")

notif=notif_p.read_text(encoding="utf-8")
notif=rep(notif,"# EMS V28 - Notification Manager / EV evening grid consent",
                "# EMS V28.6 - Notification Manager / EV evening grid consent")
marker="  # Hard reset on real unplug: new plug-in session gets a fresh decision.\n"
i=notif.find(marker)
if i<0: raise RuntimeError("legacy 30s reset block missing")
notif=notif[:i]+"""  # Odpojení/session reset vlastní Node-RED Notification Manager.
  # V28.6 se explicitní DENY_GRID drží po celou fyzickou session a resetuje se
  # až po 20 minutách souvislého raw odpojení. Krátké chyby/stavové přechody ho nesmažou.

  # Audit změn EV force režimů a večerního GRID souhlasu.
  # Uloží i HA context.user_id / context_id, takže příště lze dohledat,
  # zda změnu provedl uživatel, automatizace nebo jiný servisní call.
  - id: ems_ev_control_audit_v28_6
    alias: EMS EV - audit force a GRID consent změn
    mode: queued
    max: 50
    trigger:
      - platform: state
        entity_id:
          - input_select.ems_id3_wallbox_force_mode
          - input_select.ems_id4_wallbox_force_mode
          - input_select.ems_id3_evening_grid_consent
          - input_select.ems_id4_evening_grid_consent
          - input_select.ems_wallbox_mode
    variables:
      audit_payload: >-
        {{ {
          'ts': now().isoformat(),
          'entity_id': trigger.entity_id,
          'from': trigger.from_state.state if trigger.from_state is not none else none,
          'to': trigger.to_state.state if trigger.to_state is not none else none,
          'user_id': trigger.to_state.context.user_id if trigger.to_state is not none else none,
          'context_id': trigger.to_state.context.id if trigger.to_state is not none else none,
          'parent_id': trigger.to_state.context.parent_id if trigger.to_state is not none else none,
          'source': 'home_assistant'
        } | tojson }}
    action:
      - service: mqtt.publish
        data:
          topic: ems/audit/control_change
          qos: 0
          retain: false
          payload: "{{ audit_payload }}"
      - service: system_log.write
        data:
          level: info
          logger: ems.audit
          message: "EMS AUDIT {{ audit_payload }}"
"""

for p in (flow_p,base_p,notif_p):
    shutil.copy2(p,p.with_suffix(p.suffix+".bak-v28.6"))
flow_p.write_text(json.dumps(flow,ensure_ascii=False,indent=4)+"\n",encoding="utf-8")
base_p.write_text(base,encoding="utf-8")
notif_p.write_text(notif,encoding="utf-8")
for p,want in OUT.items():
    if bsha(p)!=want: raise SystemExit(f"OUTPUT MISMATCH {p}: {bsha(p)} != {want}")
print("EMS v28.6 patch applied successfully.")
for p in (flow_p,base_p,notif_p):
    print(f"{p.relative_to(root)} blob={bsha(p)}")
