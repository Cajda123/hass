# EMS force modes and adaptive probing

Tento dokument popisuje aktuální pravidla pro jednorázové force režimy, solární probe logiku wallboxů a stupňové řízení boilerů.

## Force režimy

Force režim není trvalý provozní stav. Je to jednorázový požadavek na doběh konkrétní zátěže. Jakmile zátěž splní cíl, vyprší čas, doběhne energie, dosáhne teploty, nebo skončí relevantní tarifní okno, EMS má daný force helper automaticky přepnout zpět na `OFF`.

Používané režimy:

| Režim | Význam |
|---|---|
| `OFF` | Force je vypnutý. EMS zátěž řídí jen v AUTO logice nebo ji nechá vypnutou. |
| `FORCE_SOLAR` | Jednorázově využít FVE a bezpečnou krátkou podporu baterie. Nepřepínat wallbox na síť. |
| `FORCE_ANYTIME` | Jednorázově pustit zátěž kdykoliv, ale stále respektovat tvrdé bezpečnostní limity. |
| `FORCE_NT_ONLY` | Jednorázově pustit zátěž jen v NT / levném okně. Po skončení okna nebo doběhu přepnout na `OFF`. |

## Tvrdé bezpečnostní limity

Žádný force režim nesmí obejít ochranu domu.

Vždy mají přednost:

- nízké napětí baterie,
- `battery_load_locked`,
- nouzové dobíjení nebo recovery po nízkém napětí,
- limity fází, měničů a hlavního jističe,
- neplatná nebo chybějící klíčová baterková data,
- explicitní ruční `OFF` pro danou třídu zátěží.

## Wallbox proudová tabulka

Wallbox proud se nekrokuje po `+1 A`. Používá se pevná tabulka:

```text
6 A -> 8 A -> 10 A -> 13 A -> 16 A
```

Pokud má konkrétní wallbox v budoucnu vlastní helper s povolenými hodnotami, má mít přednost helper. Jinak platí výchozí tabulka výše.

## Adaptivní solar probe wallboxu

Když je baterie na cíli nebo skoro plná, auto je připojené a potřebuje energii, EMS nemá zůstat zbytečně na 6 A. Má zkusit další proudový krok a ověřit, zda FVE zareaguje.

Pravidla:

1. Zvednout pouze o jeden povolený krok z tabulky.
2. Nepokračovat na další krok, dokud dispatcher nepotvrdí, že `actual_current == target_current` a změna proudu není pending.
3. Po potvrzené změně držet nové nastavení minimálně cca 10 s.
4. Další krok povolit jen pokud výkon baterie zůstává kladný nebo kolem nuly.
5. Jakmile baterie přejde do záporu, proud se může nechat, ale další zvyšování se zastaví.
6. Pokud baterie překročí tvrdý limit podpory, například `-3000 W`, EMS musí couvnout o krok zpět.

Důležité: `-3000 W` není cílový stav. Je to jen nouzová brzda.

Příklad:

```text
Baterie +300 W -> zkusit další proudový krok.
Po 10 s baterie +100 W -> může se zkusit další krok.
Po 10 s baterie -700 W -> proud nechat, dál nepřidávat.
Po 10 s baterie -3200 W -> vrátit předchozí krok.
```

## N/A / unavailable wallboxu

Krátký výpadek Wi-Fi wallboxu nebo stav `unknown`, `unavailable`, `null`, `N/A` nesmí sám o sobě vypnout nabíjení.

Správné chování:

- neplatný stav znamená „nevím“, ne „vypnout“,
- držet poslední platný stav enable/current,
- pokud je auto latched jako připojené, nabíjení se neukončuje kvůli jednorázovému N/A,
- vypnutí až po potvrzeném odpojení nebo delším timeoutu bez platných dat.

## Bojlery

Bojlery používají stejnou filozofii jako wallboxy, ale místo proudové tabulky mají stupně výkonu.

Spodní bojler:

```text
OFF -> T1 -> T1 + T2
```

Pergola bojler:

```text
OFF -> T1 -> T1 + T2
```

U `FORCE_SOLAR` se druhý stupeň přidává jen pokud baterie po prvním stupni pořád nabíjí nebo je kolem nuly. Pokud baterie přejde do záporu, aktuální stupeň se může nechat, ale další stupeň se nepřidává. Pokud se překročí tvrdý bezpečnostní limit baterkové podpory, stupeň se vrátí zpět.

## Force auto-off

Po dokončení force úlohy musí EMS poslat službu:

```yaml
service: input_select.select_option
data:
  entity_id: <force helper>
  option: 'OFF'
```

Týká se to wallboxů i boilerů. Force režim se nesmí po doběhu tvářit jako nový trvalý AUTO režim.
