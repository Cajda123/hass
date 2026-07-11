# EMS AI expected outputs

Tyto příklady slouží pro ruční kontrolu modelu při benchmarku.

## Wallbox stop

Vstup: `ai/examples/wallbox_stop.json`

Očekávaný styl: krátce vysvětlit, že nabíjení je vypnuté nebo zastavené podle `reason_display`; nedoporučovat ruční zapnutí mimo `recommendation_hint`.

## Boiler start/stop

Vstupy: `ai/examples/boiler_started.json`, `ai/examples/boiler_stop.json`

Očekávaný styl: popsat pouze bojler a důvod ohřevu/vypnutí. Nemíchat wallbox ani battery grid, pokud nejsou v eventu.

## Battery grid charge

Vstupy: `ai/examples/battery_grid_charge.json`, `ai/examples/battery_grid_stop.json`

Očekávaný styl: popsat pouze dobíjení baterie ze sítě a důvod. Nenavrhovat změnu proudu ani režimu.

## Safety / emergency

Vstupy: `ai/examples/safety_ac_in_change.json`, `ai/examples/emergency_charge.json`

Očekávaný styl: klidně a jasně popsat bezpečnostní stav. U kritického eventu nepřidávat spekulace ani servisní návody.

## Weekly battery balance

Vstup: `ai/examples/weekly_battery_balance.json`

Očekávaný styl: vysvětlit, že jde o plánované/balanční dobití baterie, pokud to uvádí `reason_display` nebo `human_hint`.
