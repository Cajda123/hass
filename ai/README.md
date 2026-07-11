# EMS AI vrstva

Tahle složka drží verzované prompty, schémata, příklady a testy pro lokální AI komentátor/analytik nad EMS.

## Princip

- EMS rozhoduje deterministicky v Node-RED.
- AI pouze vysvětluje stav, event nebo rozhodnutí EMS.
- AI nikdy přímo neovládá zařízení.
- Do AI neposílat celý `global.ems`, ale kompaktní snapshot + konkrétní event.
- Rodinný poradce může nabídnout akci, ale nikdy ji nesmí provést bez potvrzení uživatele.
- O příjemci mobilní notifikace, expiraci otázky a provedení potvrzené akce rozhoduje pouze Node-RED notification router.

## Režimy

### Komentátor

Krátký automatický komentář k eventu. Výstup typicky do MQTT topicu `ems/ai/comment`.

### Rodinný poradce

Praktická odpověď pro domácnost: jestli je vhodná chvíle pustit pračku, myčku, vaření nebo troubu.

Používá:

- `ai/prompts/family_advisor.txt`,
- `ai/house/knowledge.yaml`,
- `event.family_hint`,
- `event.question_hint`,
- `event.action_offers`.

Typický výstup:

```text
Myčku teď klidně pusť. Pračka i trouba jsou ale na L3 společně se spodním bojlerem. Jestli chceš péct, mám na tu dobu spodní bojler vypnout?
```

### Analytik

Delší ruční odpověď na otázku nad historií, logy nebo agregovaným průběhem.

### Notifikátor a router

AI vytvoří lidský text. Deterministický router pak podle `event.notification`, původce akce a přítomnosti osob rozhodne, komu ho poslat.

Pravidla:

- `error` a `critical` → vždy oba mobily, i když nikdo není doma,
- `question` → nejdřív původci akce, jinak osobě doma,
- neznámý původce + oba doma → oběma, první odpověď vyhrává,
- `advice` a `info` → pouze lidem doma,
- každá otázka má `question_id`, expiraci a předem povolené `action_id`,
- potvrzenou akci provede Node-RED až po nové kontrole podmínek.

Soubory:

- `ai/notifications/policy.yaml`
- `ai/notifications/README.md`
- `ai/schemas/notification.schema.json`
- `ai/examples/question_pause_bottom_boiler_for_oven.json`
- `ai/examples/critical_error_both_phones.json`

## Ověřený runtime

- Ollama: `http://10.200.5.122:11434`
- EMS komentář: `gemma3:4b`
- WebUI / obecné hraní: `qwen2.5:7b`

## Doporučené volání Ollamy

```json
{
  "model": "gemma3:4b",
  "prompt": "<prompt + compact snapshot>",
  "stream": false,
  "options": {
    "temperature": 0.1,
    "num_predict": 120
  }
}
```

U `gemma3:4b` se zatím v testech líp choval jeden velký `prompt` než oddělený `system` + `prompt`.

## SDK a benchmark

- `ai/sdk/ems_ai_sdk.js` obsahuje společné helpery pro standardní `ems.ai.event`, compact snapshot a Ollama payload. Node-RED flow má stejný tvar helperů vložený inline, aby nebylo nutné povolovat externí runtime moduly ve Function nodech.
- `ai/benchmarks/benchmark_ollama.py` porovná jeden nebo více Ollama modelů nad stejným promptem a snapshotem.

### Kam skripty patří

Skripty patří do repozitáře, ne do Home Assistant konfigurace:

- `ai/sdk/ems_ai_sdk.js` je vývojová knihovna / referenční implementace pro testy, budoucí tooling a případné generování Node-RED Function kódu. Node-RED ji teď přímo nenačítá, protože Function nody v běžné HA add-on instalaci nemají automaticky povolené `require()` z repozitáře.
- `ai/benchmarks/benchmark_ollama.py` je ručně spouštěný benchmark z terminálu nad lokální Ollamou. Není součást runtime EMS a nic nezapíná ani nevypíná.
- `ai/house/knowledge.yaml` je kontext pro AI, ne řídicí konfigurace.
- `ai/notifications/policy.yaml` je referenční routing policy; produkční Node-RED Function node musí stejná pravidla implementovat deterministicky.

Aktuální produkční runtime je pořád:

```text
nodered/flows.json  → Node-RED AI flow + notification router
homeassistant/ems_ai.yaml → MQTT senzory
homeassistant/dashboard_family.yaml → karta s komentářem
```

### Jak použít JS SDK

SDK se dá použít lokálně přes Node.js pro ověření tvaru eventu a snapshotu:

```bash
node - <<'NODE'
const sdk = require('./ai/sdk/ems_ai_sdk');
const event = sdk.createEvent('ems/wallbox', 'wallbox', {
  mode: 'DISABLED',
  reason: 'no_connected_car_needs_energy',
});
const snapshot = sdk.compactSnapshot({ core: { ems_enabled: true } }, event);
console.log(JSON.stringify(sdk.buildOllamaPayload('Krátce okomentuj stav.', snapshot), null, 2));
NODE
```

Pokud by se SDK mělo někdy používat přímo v Node-RED, je potřeba ho nejdřív zpřístupnit Node-RED runtime prostředí, například přes `functionGlobalContext` nebo vlastní Node-RED modul. Bez toho je bezpečnější držet helpery ve Function nodech inline, jak je to udělané teď.

### Jak použít benchmark

Benchmark se spouští ručně z kořene repozitáře. Výchozí vstup je `ai/prompts/commentator.txt` a `ai/examples/safety_event.json`.

```bash
python3 ai/benchmarks/benchmark_ollama.py --model gemma3:4b --model qwen2.5:7b --runs 3
```

Užitečné volby:

```bash
# Porovnat jiné modely
python3 ai/benchmarks/benchmark_ollama.py --model gemma3:4b --model llama3.1:8b

# Použít jiný příklad/snapshot
python3 ai/benchmarks/benchmark_ollama.py --snapshot ai/examples/wallbox_disabled.json

# Použít rodinného poradce
python3 ai/benchmarks/benchmark_ollama.py --prompt ai/prompts/family_advisor.txt --snapshot ai/examples/question_pause_bottom_boiler_for_oven.json

# Použít jinou Ollama URL
python3 ai/benchmarks/benchmark_ollama.py --url http://10.200.5.122:11434/api/generate
```

Výstup je Markdown tabulka s průměrným/min/max časem a krátkou ukázkou odpovědi. Kvalitu je potřeba posoudit ručně: odpověď má být česky, krátká, bez vymýšlení hodnot a bez návrhů na přímé ovládání zařízení.
