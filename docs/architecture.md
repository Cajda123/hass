# EMS architecture

## Purpose

EMS řídí domácí energetiku tak, aby dům co nejvíc využíval vlastní FVE a baterii, bezpečně pracoval s levným tarifem, hlídal limity fází a měničů a rozumně spínal velké zátěže.

Systém je postavený jako kombinace:

- Home Assistant – entity, helpery, normalizované senzory, skripty, dashboardy.
- Node-RED – hlavní rozhodovací logika.
- MQTT – sdílení stavu a rozhodnutí.
- ESPHome / vlastní firmware – lokální zařízení, wallboxy, displeje a budoucí moduly.

## Physical topology

### Inverters

- 3× Easun SMG II.
- Každý měnič má výkon cca 6,2 kW.
- Každý měnič obsluhuje jednu fázi: L1, L2, L3.
- Měniče umí brát energii ze sítě a nabíjet společnou baterii.
- Export do sítě se nepoužívá.

### PV

- Instalovaný FV výkon přibližně 8,4 kWp.
- Do budoucna je počítáno s rozšířením.
- EMS používá okamžitý výkon FVE a predikci výroby pro plánování SOC baterie a řízených zátěží.

### Battery

- Společná baterie pro všechny tři měniče.
- Historický základ cca 32 kWh.
- Po rozšíření se počítá přibližně s 48 kWh.
- Baterie je řízena podle minimálního SOC, cílového SOC podle počasí a tarifu.

### Grid / tariff

- Distribuční tarif D27d.
- EMS počítá s HDO / levnými okny.
- Levný tarif se může použít pro dobíjení baterie nebo aut, ale jen podle pravidel.
- Drahá denní pásma má EMS ideálně překlenout z baterie.

### Controlled loads

Aktuálně řízené nebo plánované zátěže:

- Spodní bojler se dvěma topnými tělesy.
- Pergola bojler se dvěma topnými tělesy.
- Wallboxy / nabíjení aut.
- Budoucí appletové zátěže, například bazén, topení, klimatizace nebo další odporové spotřebiče.

### EVs

- VW ID.3, běžná denní potřeba cca 11 kWh.
- VW ID.4 Pro, běžná větší potřeba cca 35 kWh.
- Nabíjení se řídí podle připojení auta, SOC, potřebné energie, tarifu, přebytku a priority.

## Software split

### Home Assistant layer

Home Assistant má být zdroj normalizovaných stavů a bezpečných akčních bodů.

Patří sem:

- template senzory,
- input booleany,
- input number helpery,
- input select režimy,
- skripty pro bezpečné volání zařízení,
- dashboardy,
- ruční override prvky,
- MQTT senzory pro stav Node-RED rozhodování.

Home Assistant by neměl obsahovat hlavní složitou rozhodovací logiku EMS, pokud to není jednoduchý lokální výpočet nebo bezpečnostní obal.

### Node-RED layer

Node-RED je hlavní mozek EMS.

Patří sem:

- snapshot aktuálního stavu,
- planner,
- battery decision,
- wallbox decision,
- boiler decision,
- dispatcher,
- publikace rozhodnutí do MQTT,
- zápis `global.ems` pro dashboard a debug.

Node-RED má rozhodovat co se má stát, Home Assistant má poskytovat stavy a bezpečné skripty pro vykonání rozhodnutí.

### MQTT layer

MQTT se používá jako mezivrstva pro:

- publikaci stavů EMS,
- přenos rozhodnutí,
- integraci displejů,
- budoucí malé moduly.

Důležité je držet topicy stabilní a dokumentované.

## Main data flow

```text
Sensors / helpers / tariffs / forecasts
        ↓
Home Assistant normalized entities
        ↓
Node-RED snapshot
        ↓
Planner + decision modules
        ↓
global.ems + MQTT status
        ↓
Home Assistant scripts / switches / numbers / selects
        ↓
Wallboxy, bojlery, baterie, další zátěže
```

## Important design principle

EMS musí být vysvětlitelné. Každé větší rozhodnutí má mít důvod:

- proč se zátěž zapnula,
- proč se vypnula,
- proč se auto nenabíjí,
- proč se baterie dobíjí ze sítě,
- proč je zátěž blokovaná.

Tyto důvody mají být dostupné v dashboardu, logu nebo MQTT stavu.
