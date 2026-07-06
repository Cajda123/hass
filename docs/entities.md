# EMS entities

Tento soubor popisuje důležité entity, helpery a významy. Názvy se mohou v čase měnit, ale entity ID by měly zůstat stabilní.

## Core control helpers

- `input_boolean.ems_enabled` – hlavní povolení EMS.
- `input_select.ems_mode` – režim EMS, například auto/manual/test podle aktuální implementace.
- `input_boolean.ems_allow_solar_loads` – povolení řízených zátěží z přebytků.
- `input_boolean.ems_allow_grid_charging` – povolení dobíjení ze sítě.
- `input_boolean.ems_allow_notifications` – povolení notifikací.

## Battery helpers

- `input_number.ems_battery_soc_min` – minimální SOC baterie.
- `input_number.ems_battery_soc_sunny_target` – cílový SOC pro slunečný den.
- `input_number.ems_battery_soc_normal_target` – cílový SOC pro normální den.
- `input_number.ems_battery_soc_bad_weather_target` – cílový SOC pro špatné počasí.

## Forecast helpers

- `input_number.ems_forecast_bad_day_threshold_kwh` – hranice predikce pro špatný den.
- `input_number.ems_forecast_sunny_day_threshold_kwh` – hranice predikce pro slunečný den.

## Phase and power limits

- `input_number.ems_inverter_phase_limit_w` – limit výkonu na fázi/měnič.
- `input_number.ems_grid_phase_limit_w` – limit vstupu ze sítě na fázi.
- `input_number.ems_surplus_start_w` – přebytek potřebný pro start zátěží.
- `input_number.ems_surplus_stop_w` – přebytek / deficit pro vypnutí zátěží.

## Tariff

- `input_boolean.hdo_aktivni` – stav nízkého tarifu / HDO, pokud je dostupný.
- `sensor.ems_dynamic_tariff_discount` – sleva / relativní výhodnost dynamického okna, pokud je implementováno.
- `sensor.ems_dynamic_tariff_class` – třída tarifu, například cheap/expensive/very_cheap.
- `binary_sensor.ems_cheap_grid_allowed_now` – zda je teď povolená levná síť.
- `binary_sensor.ems_very_cheap_grid_now` – zda je teď velmi levné okno.

## Battery / PV sensors

- `sensor.bat_soc_ave` – primární SOC baterie.
- `sensor.ems_soc_baterie` – normalizovaný SOC pro EMS.
- `sensor.battery_power_total` – výkon baterie, kladně do baterie, záporně z baterie.
- `sensor.ems_baterie_vykon` – normalizovaný výkon baterie.
- `sensor.vykon_solary` – okamžitý výkon FVE.
- `sensor.ems_vykon_solary` – normalizovaný výkon FVE.
- `sensor.ems_battery_target_soc_dynamic` – dynamický cílový SOC.
- `sensor.ems_day_type_tomorrow` – typ zítřejšího dne podle predikce.

## Inverter and grid sensors

- `sensor.easun_l1_output_active_power` – výkon měniče L1.
- `sensor.easun_l2_output_active_power` – výkon měniče L2.
- `sensor.easun_l3_output_active_power` – výkon měniče L3.
- `sensor.power_meter_vstup_power_a` – výkon sítě fáze A/L1.
- `sensor.power_meter_vstup_power_b` – výkon sítě fáze B/L2.
- `sensor.power_meter_vstup_power_c` – výkon sítě fáze C/L3.
- `sensor.ems_inverter_l1_power` – normalizovaný výkon L1.
- `sensor.ems_inverter_l2_power` – normalizovaný výkon L2.
- `sensor.ems_inverter_l3_power` – normalizovaný výkon L3.
- `sensor.ems_available_l1` – dostupná rezerva L1.
- `sensor.ems_available_l2` – dostupná rezerva L2.
- `sensor.ems_available_l3` – dostupná rezerva L3.

## Boiler helpers and sensors

- `input_boolean.ems_load_boiler_bottom_t1_enabled` – povolení prvního tělesa spodního bojleru.
- `input_boolean.ems_load_boiler_bottom_t2_enabled` – povolení druhého tělesa spodního bojleru.
- `input_boolean.ems_load_boiler_pergola_t1_enabled` – povolení prvního tělesa pergola bojleru.
- `input_boolean.ems_load_boiler_pergola_t2_enabled` – povolení druhého tělesa pergola bojleru.
- `sensor.ems_bottom_boiler_top_temp` – horní teplota spodního bojleru.
- `sensor.ems_bottom_boiler_bottom_temp` – spodní teplota spodního bojleru.
- `binary_sensor.ems_bottom_boiler_needs_heat` – spodní bojler potřebuje dohřát.
- `binary_sensor.ems_wood_boiler_heating_bottom_boiler` – bojler nahřívá kotel na dřevo / ruční indikace.
- `sensor.ems_pergola_boiler_temp` – teplota pergola bojleru.
- `binary_sensor.ems_pergola_boiler_needs_heat` – pergola bojler potřebuje dohřát.

## EV / wallbox entities

- `binary_sensor.eaton_wallbox_cm4_1_wallbox_auto_pripojeno` – ID.3 / auto připojeno na Eaton wallboxu, podle aktuálního zapojení.
- `sensor.tronity_id_3_level` – SOC VW ID.3 z Tronity.
- `sensor.ems_car_id3_required_energy` – odhad potřebné energie pro ID.3.
- `input_boolean.ems_load_car_id3_enabled` – povolení nabíjení ID.3.

Další entity pro ID.4 a Tuya wallbox mají být doplněné podle aktuálních názvů v Home Assistantu.

## Scripts / dispatchers

- `script.ems_wallboxes_apply_decision` – aplikuje rozhodnutí EMS pro wallboxy.

Skripty mají být bezpečný obal nad konkrétními zařízeními. Node-RED má rozhodnout, skript má provést změnu.

## MQTT / global state

Node-RED používá sdílený stav `global.ems` a/nebo MQTT publikaci pro dashboard.

Doporučené oblasti stavu:

- `core` – snapshot domu.
- `planner` – cíle, typ dne, očekávané potřeby.
- `battery` – rozhodnutí baterie.
- `wallbox` – rozhodnutí aut.
- `boiler` – rozhodnutí bojlerů.
- `last_action` – poslední provedená akce.
- `reason` – lidsky čitelný důvod rozhodnutí.
