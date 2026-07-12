# EMS high-SOC FV zátěže a decision trace

Tento návrh doplňuje aktuální EMS o chování, které se v logu ukázalo jako chybějící:

- při vysokém SOC baterie se nemá čekat na velký stabilní přebytek, pokud je už baterie prakticky plná,
- bojlery mají umět použít dostupnou energii i při menším kladném výkonu do baterie,
- každý manager má do `ems/decision/trace` zapsat, proč k výsledku došel.

## Problém z logu

Při SOC okolo 97 % bylo `solar_loads=true`, baterka byla nad cílem a wallbox neměl co nabíjet, ale bojler zůstal ve stavu `waiting_for_stable_surplus`.

To znamená, že současná logika moc tvrdě čeká na `highSurplus`, i když horní část baterie už má být používána jako signál „pusť užitečnou zátěž“.

## Nové core příznaky

`global.ems.core` má nést společný stav, aby jej nemusely znovu počítat jednotlivé managery:

```js
core.high_soc_load_threshold          // default 90 %
core.full_soc_load_threshold          // default 95 %
core.high_soc_load_min_charge_w       // default 100 W
core.solar_load_support_hard_limit_w  // default -3000 W
core.high_soc_loads_allowed
core.full_soc_load_probe
core.decision_inputs
```

`high_soc_loads_allowed` znamená, že EMS může spustit první užitečný stupeň FV zátěže bez pětiminutového čekání na velký stabilní přebytek.

`full_soc_load_probe` znamená, že baterie je už tak vysoko, že EMS má aktivně hledat zátěž: bojler T1, potom T2, potom pergola T1/T2, pokud to baterie dovolí.

## Boiler pravidla

Běžné nízké SOC:

```text
SOC < high_soc_load_threshold
=> držet původní konzervativní logiku, čekat na stabilní přebytek
```

Vysoké SOC:

```text
SOC >= high_soc_load_threshold
battery_load_locked = false
battery_power >= solar_load_support_hard_limit_w
=> smí spustit první užitečný stupeň bojleru bez čekání na highSurplus
```

Druhý stupeň:

```text
battery_power >= -100 W
=> může přidat druhý stupeň
battery_power < -100 W
=> první stupeň nech, ale dál nepřidávej
battery_power < -3000 W
=> bezpečnostní brzda, ubrat/vypnout
```

Priorita boilerů:

1. spodní bojler T1,
2. spodní bojler T2, pokud baterie pořád nabíjí nebo je kolem nuly,
3. pergola T1,
4. pergola T2, pokud baterie pořád nabíjí nebo je kolem nuly.

## Decision trace

Krátký stav zůstává na:

```text
ems/decision/state
```

Detailní dohledatelný trace má jít na:

```text
ems/decision/trace
```

Ukázková struktura:

```json
{
  "summary": "READY / boiler=BOTTOM_BOILER / wallbox=no_connected_car_needs_energy / grid=battery_target_already_reached",
  "core": {
    "soc": 97,
    "battery_power_w": 800,
    "target_soc": 50,
    "high_soc_loads_allowed": true,
    "full_soc_load_probe": true
  },
  "boiler": {
    "selected": "BOTTOM_BOILER",
    "reason": "high_soc_use_available_energy_bottom",
    "checks": [
      {"check":"ems_enabled", "result":true},
      {"check":"battery_load_locked", "result":true},
      {"check":"wallbox_lockout", "result":true},
      {"check":"stable_surplus", "result":false},
      {"check":"high_soc_bypass_stable_surplus", "value":97, "threshold":90, "result":true}
    ]
  }
}
```

## Patch script

`tools/patch_ems_high_soc_force_solar_trace.py` aplikuje změny do:

- `homeassistant/ems_base.yaml`,
- `nodered/flows.json`.

Spuštění z rootu repozitáře:

```bash
python3 tools/patch_ems_high_soc_force_solar_trace.py
```

Po spuštění zkontrolovat diff, import Node-RED flow a restart/reload HA helperů.
