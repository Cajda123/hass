# Home Assistant / EMS

Tento repozitář obsahuje konfiguraci a řídicí logiku domácího EMS (Energy Management System) postaveného nad Home Assistantem, Node-RED, MQTT, ESPHome a vlastním firmwarem pro některá zařízení.

EMS není jen sada automatizací. Je to řídicí systém domu, který rozhoduje o využití FVE, baterie, sítě, wallboxů, bojlerů a dalších řízených zátěží. Cílem je držet dům co nejvíc na vlastní výrobě, bezpečně využívat baterii, nepřetěžovat fáze/měniče a zároveň umět využít levný tarif tam, kde to dává smysl.

## Aktuální obsah repozitáře

```text
homeassistant/
  ems_base.yaml      # Home Assistant helpers, senzory, šablony, skripty a dashboard základ EMS
  ems_ai.yaml        # MQTT senzory pro lokální AI komentátor

nodered/
  flows.json         # Node-RED flow s hlavní rozhodovací logikou EMS
  ems_ai_commentator_flow.json
                    # Samostatný importovatelný flow pro AI komentátor

docs/
  architecture.md                  # Architektura systému
  decision_logic.md                # Chování EMS a rozhodovací priority
  force_modes_and_probe_logic.md   # Force režimy, FORCE_SOLAR, probe wallboxů a boilerů
  entities.md                      # Důležité entity a význam
  todo.md                          # Další plánované práce
  EMS_AI_CODEX.md                  # Zadání pro Codex / další dodělávky AI vrstvy
```

## Hlavní cíle EMS

- Preferovat vlastní FV výrobu před sítí.
- Udržovat minimální bezpečný SOC baterie.
- Nabíjet baterii ze sítě jen podle tarifu, potřeby a predikce.
- Směrovat přebytky do bojlerů, aut a dalších zátěží.
- Řídit wallboxy podle SOC aut, přítomnosti, výkonu FVE, stavu baterie a tarifu.
- Nepřetěžovat žádnou fázi, měnič ani vstup ze sítě.
- Logovat a zobrazovat, proč EMS něco zapnulo nebo vypnulo.
- Udržet systém čitelný, modulární a rozšiřitelný.

## Aktuální řízení wallboxů a boilerů

Wallboxy a bojlery používají společnou filozofii řízených zátěží:

- `AUTO` – EMS rozhoduje podle přebytku, baterie, tarifu, potřeby a priorit.
- `FORCE_SOLAR` – jednorázově využít FVE a bezpečnou krátkou podporu baterie, bez přepnutí wallboxu na síť.
- `FORCE_ANYTIME` – jednorázově pustit zátěž kdykoliv, stále přes tvrdé bezpečnostní limity.
- `FORCE_NT_ONLY` – jednorázově pustit zátěž v NT / levném okně.
- `OFF` – force nebo daná třída řízení je vypnutá.

Force režimy jsou jednorázové. Po splnění cíle, doběhu času, dosažení energie/teploty nebo skončení relevantního okna se příslušný helper vrací na `OFF`.

Wallboxy nekrokují proud po `+1 A`, ale podle pevné tabulky:

```text
6 A -> 8 A -> 10 A -> 13 A -> 16 A
```

Adaptivní solar probe zvyšuje proud nebo stupeň zátěže jen po jednom kroku, čeká na potvrzení skutečného stavu a dál přidává pouze tehdy, když baterie pořád nabíjí nebo je kolem nuly. Záporný výkon baterie zastavuje další přidávání; tvrdý limit podpory baterie je jen bezpečnostní brzda, ne cílový stav.

Detailní pravidla jsou v `docs/force_modes_and_probe_logic.md`.

## Lokální AI komentátor

AI vrstva je pouze komentátor a analytik. Deterministické řízení zůstává v Node-RED. AI nikdy přímo neovládá relé, wallbox, bojler, AC-in ani nouzové dobíjení.

Doporučený tok:

```text
Node-RED EMS event / global.ems
        ↓
kompaktní AI snapshot
        ↓
Ollama API v lokální síti
        ↓
MQTT ems/ai/comment + ems/ai/status
        ↓
Home Assistant dashboard / notifikace
```

První cílový model na slabším CPU je `gemma3:4b`, pro obecné hraní přes Open WebUI může běžet i `qwen2.5:7b`.

## Základní topologie

- 3× Easun SMG II ostrovní měnič, každý 6,2 kW, každý na jedné fázi L1/L2/L3.
- Společná baterie pro všechny měniče.
- FVE přibližně 8,4 kWp, plánované rozšíření.
- Baterie aktuálně navýšená z cca 32 kWh směrem k cca 48 kWh.
- Bez exportu do sítě.
- Řízené zátěže: spodní bojler, pergola bojler, wallboxy, časem další appletové zátěže.
- EV: VW ID.3 a VW ID.4.

## Běžná pracovní pravidla

- Home Assistant YAML má obsahovat normalizované entity, helpery, senzory, skripty a dashboardy.
- Node-RED má obsahovat hlavní rozhodovací logiku.
- Entity ID mají být pokud možno anglicky a stabilní.
- UI názvy mohou být česky.
- Změny v rozhodování se mají dokumentovat v `docs/decision_logic.md` nebo detailním dokumentu v `docs/`.
- AI vrstva nesmí měnit bezpečnostní ani akční logiku bez explicitního lidského zásahu.
- Citlivé soubory, tokeny, credentials a runtime databáze do repozitáře nepatří.

## Bezpečnostní poznámka

Tento repozitář může obsahovat názvy zařízení, entity, MQTT topicy a architekturu domu. Pokud bude repozitář veřejný, nikdy do něj nedávat hesla, tokeny, `secrets.yaml`, `flows_cred.json`, certifikáty, databáze ani logy.
