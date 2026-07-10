# EMS force modes and adaptive load probing

Tento dokument doplňuje rozhodovací logiku pro wallboxy a bojlery. Cílem je, aby EMS umělo využít přebytek FVE i ve chvíli, kdy je baterie prakticky plná, ale zároveň aby zátěže nezačaly zbytečně tahat dům z baterky.

## Společné principy

Wallboxy i bojlery jsou řízené zátěže. V režimech `AUTO` i force musí vždy respektovat tvrdé bezpečnostní limity:

- nízké napětí baterie,
- `battery_load_locked`,
- přetížení fáze nebo měniče,
- chybějící / neplatná baterková data,
- nouzové dobíjení,
- recovery po nízkém napětí.

Force režim není trvalý provozní stav. Je to jednorázový požadavek na doběh. Po dokončení jednoho doběhu / cyklu se helper dané zátěže automaticky přepne na `OFF`.

## Režimy zátěží

Každá hlavní řízená zátěž má používat stejnou sadu režimů:

| Režim | Význam |
|---|---|
| `AUTO` | EMS rozhoduje podle priorit, přebytku, baterie, tarifu a potřeby zátěže. |
| `FORCE_SOLAR` | Jednorázově běžet ze soláru / baterkové podpory až do bezpečnostního limitu. Po doběhu přepnout na `OFF`. |
| `FORCE_ANYTIME` | Jednorázově běžet kdykoliv až do bezpečnostního limitu. Po doběhu přepnout na `OFF`. |
| `FORCE_NT` | Jednorázově běžet v NT / levném tarifu až do bezpečnostního limitu. Po doběhu přepnout na `OFF`. |
| `OFF` | Ručně vypnuto. EMS zátěž nespouští. |

`FORCE_SOLAR` nesmí znamenat bezhlavé vybíjení baterie. Smí využít krátkou baterkovou podporu jen tak, aby se našel stabilní provozní bod zátěže a nebyl porušen bezpečnostní limit.

## Wallbox proudová tabulka

Wallbox proud se nesmí zvyšovat po `+1 A`, protože wallboxy používají pevné povolené hodnoty. Adaptivní logika musí krokovat jen po tabulce:

```text
6 A -> 8 A -> 10 A -> 13 A -> 16 A
```

Pokud bude mít konkrétní wallbox helper s jinou tabulkou, použije se helper. Jinak platí výchozí tabulka výše.

## Adaptivní hledání proudu wallboxu

Když je auto připojené, potřebuje energii, baterie je na cíli nebo skoro plná a FVE má šanci dodat víc, EMS nemá zůstat zbytečně na 6 A. Má zkusit další proudový krok podle tabulky.

### Podmínky pro zahájení probe

Probe je povolený, když:

- wallbox režim je `AUTO` nebo `FORCE_SOLAR`,
- auto je připojené nebo latched jako připojené,
- auto potřebuje energii,
- domácí baterie je nad cílem / skoro plná,
- není aktivní `battery_load_locked`,
- napětí baterie je bezpečné,
- fáze a měniče mají rezervu,
- wallbox není v tvrdé chybě.

### Probe krok

1. Uložit výchozí výkon baterie před změnou proudu.
2. Zvednout proud na další povolený krok z tabulky.
3. Držet nový proud minimálně cca 10 s.
4. Po 10 s vyhodnotit výkon baterie.

### Vyhodnocení po 10 s

Další zvyšování proudu je povoleno jen když:

- výkon baterie je kladný, tedy baterie se pořád nabíjí,
- nebo je výkon baterie kolem nuly.

Další zvyšování proudu se zastaví, když:

- výkon baterie přejde do záporu,
- nebo už byl záporný a po přidání se záporný výkon prohloubil.

Limit např. `-3000 W` je jen tvrdá bezpečnostní brzda. Není to cíl, ke kterému se má EMS snažit dojít.

Příklad:

```text
Baterie +300 W -> EMS zkusí další proudový krok.
Po 10 s baterie -700 W -> proud nechá, ale dál už nepřidává.
Po 10 s baterie +100 W -> může zkusit další proudový krok.
Po 10 s baterie -3200 W -> vrátí předchozí proudový krok.
```

Tím se využije okamžik, kdy solár po zvýšení odběru opravdu zabere, ale EMS nebude schválně tlačit dům do vybíjení baterie.

## N/A / unavailable u wallboxu a auta

`unknown`, `unavailable`, `null` nebo krátký výpadek Wi-Fi u wallboxu nesmí být důvod k ukončení nabíjení.

Správné chování:

- neplatný stav znamená „nevím“, ne „vypni“,
- držet poslední známý platný stav enable/current,
- pokud je auto latched jako připojené, nabíjení se neukončuje kvůli jednorázovému N/A,
- reálné vypnutí nastane až po potvrzeném odpojení nebo po delším timeoutu bez platných dat,
- dispatcher nesmí přepsat `actualWallboxEnable` na `false` jen proto, že wallbox krátce vypadl z Wi-Fi.

## Bojlery

Bojlery mají používat stejnou filozofii jako wallboxy:

- v `AUTO` běžet podle stabilního přebytku, potřeby tepla a priorit,
- v `FORCE_SOLAR` běžet ze soláru / krátké baterkové podpory až do bezpečnostního limitu,
- v `FORCE_ANYTIME` běžet kdykoliv až do bezpečnostního limitu,
- v `FORCE_NT` běžet v NT / levném tarifu až do bezpečnostního limitu,
- po jednom doběhu force režimu přepnout helper na `OFF`.

U boilerů se probe neřídí proudovou tabulkou wallboxu, ale dostupnými stupni zátěže:

- spodní bojler: `T1`, potom `T1 + T2`,
- pergola bojler: `T1`, potom `T1 + T2`.

Po přidání dalšího stupně boileru platí stejné vyhodnocení výkonu baterie jako u wallboxu: dál přidávat jen pokud baterie pořád nabíjí nebo je kolem nuly. Jakmile přejde do záporu, další stupně se už nepřidávají. Pokud se překročí tvrdý bezpečnostní limit, stupeň se vrátí zpět.

## Implementační poznámky pro Node-RED

Doporučené stavové položky v `ems.memory`:

```js
ems.memory.wallbox_probe = {
  active: false,
  car: null,
  previous_current_a: null,
  target_current_a: null,
  battery_power_before_w: null,
  started_ts: 0,
  evaluated_ts: 0
};

ems.memory.boiler_probe = {
  active: false,
  load: null,
  previous_stage: null,
  target_stage: null,
  battery_power_before_w: null,
  started_ts: 0,
  evaluated_ts: 0
};
```

Doporučené konstanty:

```js
const WALLBOX_CURRENT_STEPS_A = [6, 8, 10, 13, 16];
const LOAD_PROBE_HOLD_MS = 10 * 1000;
const BATTERY_SUPPORT_HARD_LIMIT_W = -3000;
const BATTERY_ZERO_BAND_W = 100;
```

Vyhodnocení baterie:

```js
function batteryStillAllowsNextStep(batteryPowerNowW) {
  return batteryPowerNowW >= -BATTERY_ZERO_BAND_W;
}

function batteryHardLimitExceeded(batteryPowerNowW) {
  return batteryPowerNowW < BATTERY_SUPPORT_HARD_LIMIT_W;
}
```

Pozor: `BATTERY_SUPPORT_HARD_LIMIT_W` není podmínka pro další zvyšování. Je to jen hranice, kdy se musí couvnout.
