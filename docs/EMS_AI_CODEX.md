# EMS AI komentátor – zadání pro Codex

## Cíl

Doplnit nad stávající EMS lokální AI vrstvu, která umí lidsky okomentovat stav domu a vysvětlit rozhodnutí EMS. AI nesmí být druhý řídicí systém. EMS rozhoduje deterministicky v Node-RED, AI pouze překládá hotové eventy a snapshoty do čitelného textu.

## Aktuální runtime

- Home Assistant + Node-RED + MQTT.
- Lokální Ollama v LAN: `http://10.200.5.122:11434`.
- Ověřený model pro EMS komentář: `gemma3:4b`.
- Open WebUI může používat jiné modely, ale pro automatické EMS komentáře počítat s Ollama API přímo z Node-RED.

## Základní pravidla

1. AI nikdy přímo nevolá Home Assistant služby, nezapíná relé, wallbox, bojler, AC-in ani nouzové dobíjení.
2. AI výstup je pouze text / doporučení / vysvětlení.
3. Všechna bezpečnostní rozhodnutí zůstávají v Node-RED.
4. Neposílat celý `global.ems`, pokud to není debug. Posílat kompaktní snapshot a konkrétní event.
5. Preferovat už přeložené `reason_display`, `status_display` a hotové `decision.reason` před tím, aby AI sama hádala důvody.
6. Ignorovat startovní/redeploy bordel: po deployi Node-RED počkat minimálně 90 sekund a nekomentovat krátkodobé `ems_disabled` přechody.

## Doporučený Node-RED tok

```text
MQTT in / link in / inject
        ↓
AI event gate
        ↓
build compact AI snapshot
        ↓
HTTP POST http://10.200.5.122:11434/api/generate
        ↓
parse response
        ↓
MQTT out ems/ai/comment
MQTT out ems/ai/status
```

## Doporučený Ollama payload

```json
{
  "model": "gemma3:4b",
  "prompt": "Jsi domácí EMS analytik...\nStav:\n{...kompaktní JSON...}",
  "stream": false,
  "options": {
    "temperature": 0.1,
    "num_predict": 120
  }
}
```

U modelu `gemma3:4b` se v testech lépe choval jeden velký `prompt` než oddělené pole `system` + `prompt`.

## Prompt – výchozí text

```text
Jsi domácí EMS analytik. Odpovídej pouze česky, stručně, maximálně 3 věty.
Nikdy si nevymýšlej údaje. Nikdy nepopisuj JSON ani jeho strukturu.
EMS je deterministické řízení a ty pouze vysvětluješ jeho stav a rozhodnutí.
Pokud je důvod "ems_disabled", znamená to, že EMS je vypnuté nebo zakázané, ne porucha komunikace.
Řekni, co se právě děje v domě a co doporučuješ.
```

## Kompaktní AI snapshot

Snapshot má být malý a stabilní. Doporučený tvar:

```json
{
  "timestamp": "2026-07-05T20:30:44.108Z",
  "event": {
    "topic": "ems/safety",
    "type": "safety",
    "status": "Ostrovní provoz",
    "reason": "Správce vypnutý, drží aktuální stav"
  },
  "core": {
    "ems_enabled": true,
    "hdo_state": "NT",
    "battery_soc": 72,
    "battery_power": -350,
    "pv_power": 8200,
    "grid_power": 0,
    "surplus_power": 2200,
    "house_power": 4100,
    "target_soc": 80,
    "effective_min_soc": 40
  },
  "safety": {
    "voltage": 52.55,
    "ac_in_status": "Ostrovní provoz",
    "ac_in_reason": "Správce vypnutý, drží aktuální stav",
    "emergency_status": "V klidu",
    "emergency_reason": "Nouzové dobíjení vypnuto"
  },
  "wallbox": {
    "mode": "DISABLED",
    "reason": "Není připojené žádné auto",
    "id3_connected": false,
    "id4_connected": false
  },
  "boiler": {
    "mode": "IDLE",
    "reason": "Čeká na přebytek"
  }
}
```

## Eventy vhodné ke komentování

- `ems/safety` – AC-in manager, nouzové dobíjení, napětí baterie.
- `ems/wallbox` – auto připojeno/odpojeno, start/stop nabíjení, priorita auta.
- `ems/boiler` – spuštění/vypnutí těles, blokace dřevem, teplotní stav.
- `ems/battery_grid` – dobíjení baterie ze sítě, týdenní balancing, levný tarif.
- `ems/plan` – významná změna plánu, cílového SOC, forecast day type.

## Anti-spam / stabilita

- Automatický komentář maximálně jednou za 2 minuty.
- Stejný `event_key` nekomentovat opakovaně.
- Po deploy/startu ignorovat 90 sekund.
- `ems_disabled` automaticky nekomentovat, pokud nejde o ruční dotaz.
- Ruční inject musí projít vždy.

## MQTT výstupy

- `ems/ai/comment` – čistý text pro HA kartu.
- `ems/ai/status` – JSON s metadaty: model, duration, event_key, timestamp, error.
- `ems/ai/error` – chyba HTTP/Ollama nebo prázdná odpověď.

## Home Assistant

Doplnit MQTT senzory do `homeassistant/ems_ai.yaml`:

- `sensor.ems_ai_comment`
- `sensor.ems_ai_status`
- `sensor.ems_ai_last_error`

## Další rozvoj

1. Udělat AI komentář pro konkrétní MQTT eventy.
2. Přidat historický kontext posledních 30–60 minut, ale jen agregovaný.
3. Přidat rozlišení režimů:
   - komentátor: krátký automatický text,
   - analytik: delší odpověď na ruční dotaz.
4. Později umožnit HA notifikace jen pro důležité komentáře.
