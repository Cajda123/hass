# EMS decision logic

## Core philosophy

EMS je řídicí systém domu, ne sada nezávislých automatizací. Každé rozhodnutí musí mít jasný důvod, musí být dohledatelné v logu/stavu a musí být bezpečné i při chybě senzoru.

Základní priority:

1. Ochrana baterie, měničů, fází a relé.
2. Nouzové chování podle napětí baterie má přednost před běžným SOC plánem.
3. Balancování a plné dobití baterie má přednost před pohodlným využitím přebytků.
4. Dům má jet primárně z FVE/baterie.
5. Zbytné zátěže se pouští jen pokud jsou splněné baterkové, výkonové a tarifní podmínky.
6. Levný tarif se používá chytře, ne jako slepé „nabij všechno“.
7. Každý zásah do logiky musí zůstat malý, čitelný a vratný.

Pokud jsou data neplatná, stará nebo `unknown/unavailable`, EMS se chová konzervativně: nespouští nové velké zátěže, sníží/vypne wallbox a drží bezpečný stav.

## Battery protection layer

Baterie se neřídí jen podle SOC. SOC je plánovací hodnota, ale tvrdší ochranná vrstva je napětí baterie.

EMS používá dvě vrstvy rozhodování:

- **SOC layer** – plánování, rezerva, cílový SOC podle počasí a tarifu.
- **Voltage layer** – nouzová ochrana, recovery, odpojení/připojení AC-in, blokace zátěží a balancování.

Napětí má při konfliktu vyšší prioritu než SOC. Pokud SOC vypadá dobře, ale napětí padá, EMS musí věřit napětí a chovat se jako při nízké baterii.

### Battery voltage states

Doporučené stavové pásma:

| Stav | Význam | Chování EMS |
|---|---|---|
| `critical_low_voltage` | baterie je nebezpečně nízko | vypnout zbytné zátěže, vypnout wallbox, připnout AC-in, povolit nouzové nabíjení |
| `low_voltage` | baterie je nízko | blokovat bojlery/wallbox z baterie, povolit jen dům, čekat na FVE nebo levný tarif |
| `recovering_voltage` | baterie se zvedá po nízkém napětí | nepouštět hned zátěže, čekat na recovery threshold a stabilitu |
| `normal_voltage` | běžný provoz | řídit podle SOC, tarifu, přebytků a predikce |
| `high_voltage_balance` | baterie je nahoře / blízko plna | držet prostor pro balancování, neodpojovat nabíjení příliš brzy |
| `full_balancing` | cílené plné dobití / balanc | držet baterii nahoře definovanou dobu, omezit zbytné odběry, které by balanc rozbily |

Konkrétní prahy musí být nastavitelné přes Home Assistant helpery, ne natvrdo. V aktuální HA logice už existují prahy kolem recovery a odpojování AC-in, například `ems_emergency_charge_recover_above_v` a `ems_ac_in_disconnect_above_v` používané při ukončení grid charge skriptu.

### Emergency voltage charge

Nouzové dobíjení baterie ze sítě je ochranný režim, ne běžné plánované nabíjení.

Spouští se, pokud:

- napětí baterie spadne pod kritický práh,
- nebo je baterie pod minimálním SOC a napětí potvrzuje problém,
- nebo je detekovaný dlouhodobý pokles pod bezpečnou mez,
- a EMS není v ručním režimu, který tuto ochranu výslovně přebíjí.

Chování:

1. Vypnout všechny zbytné zátěže.
2. Vypnout nebo snížit wallboxy na minimum a následně je odpojit.
3. Připnout AC-in měničů.
4. Přepnout nabíjecí prioritu měničů na režim umožňující síťové/nouzové nabíjení.
5. Nastavit bezpečný nabíjecí proud podle helperu.
6. Držet režim, dokud napětí nepřekročí recovery práh a stav není stabilní.

Nouzové nabíjení se nesmí vypnout hned při prvním překročení prahu. Musí mít hysterezi a minimální dobu recovery.

### Grid charge stop / AC-in disconnect

Ukončení síťového nabíjení musí probíhat postupně:

1. Pokud napětí baterie dosáhlo recovery prahu a nouzový režim už není aktivní, přepnout battery charging priority zpět na `Only PV charging is allowed`.
2. Přepnout output priority zpět na běžný FV/baterie režim, typicky `PV-Battery-Utility (SBU)`.
3. Teprve pokud napětí překročí vyšší práh pro odpojení AC-in, vypnout `switch.sit_menice`.

Tím se zabrání cyklování měničů a situaci, kdy se síť odpojí moc brzo, baterka znovu sedne a EMS začne celé kolečko znovu.

## Battery load lock

EMS musí mít centrální příznak typu `battery_load_locked`.

Pokud je aktivní, platí:

- žádné bojlery z přebytků,
- žádné auta z baterky,
- žádné volitelné zátěže,
- povolený je jen dům a případně bezpečnostní/nouzové dobíjení.

`battery_load_locked` se má aktivovat při:

- nízkém napětí baterie,
- SOC pod minimem,
- běžícím nouzovém nabíjení,
- recovery po nízkém napětí,
- nestabilních nebo neplatných baterkových datech.

Odblokování musí mít hysterezi:

- napětí nad recovery prah,
- SOC nad minimem + rezerva,
- baterie není právě tvrdě vybíjena,
- stav trvá minimální dobu.

## Battery balancing and full charge

Balancování článků je samostatný režim. Nesmí se zaměnit s obyčejným „SOC je vysoko“.

### Kdy balancovat

Balancování se spouští:

- pravidelně, typicky 1× týdně,
- po změně baterkové sestavy / přidání kapacity,
- pokud se dlouho nedosáhlo 100 % SOC,
- pokud je vidět rozjezd BMS / článků,
- ručně přes helper nebo servisní režim.

### Co má EMS dělat při balancování

Během balancování:

- cílový SOC je 100 %,
- baterie se má dostat do horního napěťového pásma,
- po dosažení plna se má držet nahoře definovanou dobu, například 1 hodinu,
- velké zátěže, které by stáhly baterii z horního pásma, se mají omezit,
- přebytky nemají být zbytečně spálené v bojleru/autě dřív, než baterie dokončí balanc.

Balancing režim má přednost před běžným využitím přebytků. Pokud je baterie v balancování, `solar_loads_allowed` může být false i při velkém FV výkonu, dokud není splněna podmínka „baterie je plná a drží se“.

### Balancing completion

Balancování je hotové až když:

- SOC dosáhl 100 % nebo nastaveného horního cíle,
- napětí je v horním pásmu,
- nabíjecí proud klesl / baterie už bere málo,
- stav trval minimální dobu,
- není aktivní alarm BMS.

Po dokončení:

- vrátit cílový SOC na dynamický plán,
- povolit přebytkové zátěže,
- vrátit grid charge do normálu,
- zapsat čas posledního úspěšného balancování.

## Dynamic battery target

Cílový SOC baterie se mění podle počasí, predikce výroby, sezóny a očekávané spotřeby.

Orientačně:

- slunečný den: nižší cílový SOC, aby bylo místo pro FV výrobu,
- normální den: střední SOC,
- špatné počasí: vyšší SOC,
- zima: vyšší bezpečná rezerva,
- před špatným počasím nebo vyšší spotřebou: cílový SOC zvednout.

SOC plán nikdy nesmí přebít napěťovou ochranu. Pokud plán říká „stačí 40 %“, ale napětí je nízko, rozhoduje napětí.

## Grid charging

Běžné dobíjení ze sítě je plánovací režim.

Povoluje se, pokud:

- EMS je zapnuté,
- uživatel povolil grid charge,
- tarif je levný nebo velmi levný,
- SOC je pod cílem,
- napětí není v chybovém stavu,
- nejsou překročené limity fází, měničů a vstupu,
- neběží režim, který má přednost.

Běžné grid charging má dobíjet jen do cílového SOC, ne automaticky na 100 %. Výjimka je balancování nebo nouzový režim.

## PV surplus usage

Přebytky z FVE se používají až po splnění baterkových podmínek.

Priority:

1. Dům.
2. Baterie do aktuálního cíle.
3. Balancování, pokud je aktivní.
4. Bojlery, pokud potřebují teplo.
5. Auta, pokud jsou připojená a potřebují energii.
6. Budoucí zátěže.

Velká zátěž se nesmí zapnout jen proto, že `battery_power` je krátce kladný. Musí být splněno:

- stabilní přebytek definovanou dobu,
- baterie není load-locked,
- napětí baterie není nízko,
- SOC je nad efektivním minimem,
- fáze/měnič mají rezervu,
- neběží wallbox lockout nebo jiná priorita.

## Boiler logic

Bojlery jsou přebytkové zátěže, ne baterkové spotřebiče.

### Obecná pravidla

- Pokud je aktivní `battery_load_locked`, bojlery vypnout.
- Pokud baterie klesá / vybíjí se pod limit, bojlery vypnout po krátké stabilizační době.
- Pokud právě běžel nebo má běžet wallbox, držet boiler lockout, aby se zátěže nepraly.
- Zapnutí bojleru vyžaduje stabilní přebytek.
- Vypnutí má mít hysterezi, aby relé necvakala při každém mraku.

Z flows je vidět logika okolo lockoutů: wallbox má po běhu blokovat bojlery cca 10 minut, změny bojlerů mají minimální interval cca 5 minut, přebytek se bere až po stabilitě cca 5 minut, start bojleru má grace period cca 2 minuty a vybíjení baterie se nevyhodnocuje okamžitě, ale až po krátké době.

### Bottom boiler

Spodní bojler má dvě topná tělesa.

Vstupy:

- horní teplota,
- spodní teplota,
- potřeba dohřevu,
- plán kotle na dřevo,
- dostupný FV přebytek,
- baterkový stav,
- povolení T1/T2,
- fáze a výkon těles.

Chování:

- Pokud topí nebo bude topit kotel na dřevo, elektrický dohřev omezit.
- Pokud je `force_task`, může se spustit cílený ohřev, ale stále nesmí obejít tvrdou bezpečnost baterie/fází.
- T1 odpovídá cca 1000 W.
- T1+T2 odpovídá cca 2000 W.

### Pergola boiler

Pergola bojler má dvě tělesa.

Chování:

- zapínat jen při potřebě tepla a dostupném přebytku,
- T1 cca 800 W,
- T1+T2 cca 1600 W,
- respektovat `battery_load_locked`, wallbox lockout a hysteresi.

## Wallbox / EV logic

EMS pracuje minimálně s VW ID.3 a VW ID.4.

Vstupy:

- auto připojeno / nepřipojeno,
- SOC auta,
- cílový SOC,
- potřebná energie v kWh,
- nabíjecí výkon,
- dostupný FV přebytek,
- stav baterie domu,
- tarif,
- priorita auta,
- režim wallboxu.

### Charging modes

- `OFF` – nenabíjet.
- `SOLAR` – nabíjet jen z přebytků.
- `GRID` – nabíjet ze sítě podle tarifu a potřeby.
- `AUTO` – EMS rozhoduje podle situace.

### Battery conditions for EV charging

Auto se nesmí nabíjet z domácí baterie, pokud:

- baterie je pod efektivním minimem,
- napětí je nízké,
- `battery_load_locked` je aktivní,
- běží recovery po nízkém napětí,
- běží balancování a baterie ještě není dokončená,
- tarif je drahý a nejde o výslovný ruční režim.

Solar charging auta je povoleno jen pokud:

- auto potřebuje energii,
- je připojené,
- je stabilní přebytek,
- baterie je nad minimem a není load-locked,
- fáze mají rezervu,
- nastavený proud neklesne pod minimum wallboxu.

Grid charging auta je povoleno jen pokud:

- režim to dovoluje,
- tarif je levný / velmi levný,
- domácí baterie není v nouzi,
- nejsou překročené limity,
- auto reálně potřebuje energii.

### Car priority

Pokud jsou připojená dvě auta:

1. Preferovat auto s nastaveným odjezdem.
2. Pokud mají obě odjezd, vybrat dřívější.
3. Pokud odjezd není známý, preferovat auto s vyšší potřebnou energií.
4. Pokud není jasné, požádat uživatele o prioritu.
5. Po odpojení auta vrátit prioritu do `AUTO`.

### Charging current

- Minimum AC nabíjení je typicky 6 A.
- Proud se nastavuje podle dostupného výkonu a limitů.
- ID.3 je fyzicky mapované na wallbox 2.
- ID.4 je fyzicky mapované na wallbox 1.
- Před změnou režimu SOLAR/GRID se wallboxy nastaví na minimální proud, vypnou, přepne se přívod/režim a až pak se zapnou se správným proudem.

## Phase and inverter limits

EMS musí hlídat:

- výkon každé fáze,
- výkon každého měniče,
- vstup ze sítě,
- dostupnou rezervu,
- proudy wallboxů,
- výkon odporových zátěží.

Nesmí se rozhodovat jen podle celkového přebytku. 3f wallbox a jednofázové bojlery zatěžují fáze jinak.

## Notifications and user decisions

EMS má upozornit uživatele, když automatika nemá dost informací nebo je lepší ruční rozhodnutí.

Typické notifikace:

- obě auta jsou připojená a obě potřebují nabít,
- je potřeba rozhodnout prioritu auta,
- spodní bojler může být nahřátý dřevem a EMS potřebuje vědět plán,
- baterie nedosáhne cíle bez grid charge,
- baterie je v nouzovém stavu,
- balancování nebylo dlouho dokončeno,
- některý klíčový senzor je neplatný.

Notifikace nemá být náhrada bezpečnostní logiky. Pokud je stav nebezpečný, EMS nejdřív uvede systém do bezpečna a až potom informuje.

## Failure behavior

Při chybě dat:

- nespouštět nové velké zátěže,
- vypnout bojlery,
- snížit/vypnout wallbox,
- držet nebo připnout AC-in podle baterkového napětí,
- zachovat bezpečný stav,
- zapsat důvod do debug/status objektu.

## Manual override

Ruční override je povolený, ale nesmí potichu obejít tvrdé ochrany.

Override může přebít plánovací logiku, například prioritu auta nebo ohřev bojleru, ale nemá obejít:

- kritické nízké napětí baterie,
- přetížení fáze/měniče,
- nouzové nabíjení,
- ochranu proti cvakání relé,
- bezpečnostní vypnutí všech zátěží.

Výjimka musí být explicitní servisní režim a musí být jasně vidět v UI.

## EMS AI komentátor

Node-RED managery po výpočtu deterministické akce ukládají také standardizovaný `ems.ai_event` podle schématu `ai/schemas/event.schema.json`. Event je pouze popis hotového rozhodnutí; AI vrstva nesmí volat Home Assistant služby ani měnit stav zařízení.

AI flow v Node-RED používá poslední `ems.ai_event`, deduplikuje podle `event.key`, po startu/redeployi ignoruje automatické komentáře 90 sekund a mezi automatickými komentáři drží 120 sekund cooldown. Ruční inject cooldown obchází. Flow sestaví compact snapshot, zavolá lokální Ollamu a publikuje:

- `ems/ai/comment` – text komentáře pro Home Assistant,
- `ems/ai/status` – JSON metadata včetně modelu, délky běhu a event key,
- `ems/ai/error` – chyba nebo prázdná odpověď.

AI komentář je informativní vrstva. Bezpečnostní priority, vypínání/zapínání wallboxů, bojlerů, AC-in a dobíjení baterie zůstávají výhradně v deterministických Node-RED managerech.

Event nesmí míchat rozhodnutí více managerů. `wallbox` event popisuje pouze wallbox, `boiler` pouze bojler, `battery_grid` pouze dobíjení baterie ze sítě, `safety` pouze AC-in / emergency safety a `battery_balance` pouze údržbový úkol baterie. Povinné hinty `human_hint`, `recommendation_hint`, `allowed_topics` a `forbidden_topics` omezují, co smí AI komentovat.

Kvůli minimalizaci merge konfliktů v hlavním Node-RED exportu je AI komentátor dostupný i jako samostatný importovatelný flow `nodered/ems_ai_commentator_flow.json`. Hlavní `nodered/flows.json` se kvůli AI nemá přepisovat v bulk refaktoru; integrace manager eventů má být malá cílená změna v konkrétních Function nodech.
