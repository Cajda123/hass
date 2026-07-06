# EMS TODO

## Repository cleanup

- Přidat tento dokumentační balík do rootu repozitáře.
- Ověřit, že `nodered/flows.json` je validní JSON export všech flow bez credentials.
- Ověřit, že `homeassistant/ems_base.yaml` projde YAML validací.
- Přidat popis repozitáře na GitHubu.
- Zkontrolovat, že v repozitáři nejsou secrets, tokeny, credentials, databáze ani logy.

## Documentation

- Doplnit přesné fáze a výkony všech řízených zátěží.
- Doplnit aktuální entity pro ID.4.
- Doplnit aktuální entity pro Tuya wallbox.
- Doplnit MQTT topic mapu.
- Doplnit restart/reload postup pro Home Assistant a Node-RED.

## EMS behavior

- Ujasnit finální minimální SOC baterie po navýšení kapacity.
- Přepočítat procentuální limity pro novou baterii cca 48 kWh.
- Doladit dynamický cílový SOC podle predikce počasí.
- Přidat spolehlivý výpočet potřebné energie pro ID.3 a ID.4.
- Přidat prioritu aut při současném připojení.
- Přidat reset priority po odpojení auta.
- Přidat senzor rychlosti nabíjení auta v %/h.

## Dashboard

- Zobrazit důvod každého EMS rozhodnutí.
- Zobrazit požadovanou energii pro auta.
- Zobrazit požadovanou energii pro baterii domu.
- Zobrazit přehled blokací: SOC minimum, drahý tarif, málo přebytku, limit fáze, neplatný senzor.
- Přidat jednoduchý rodinný dashboard s českými názvy.

## Future modules

- Týdenní logger topení pro zimní období.
- Applet pro řízení topného systému podle reálného chování člověka.
- Budoucí zátěžový modul pro bazén / klimatizace / další spotřebiče.
- Přesnější tarifní plánování po vyřešení měření a HDO/smart meteru.
