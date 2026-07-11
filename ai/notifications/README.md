# EMS notification router

Notification router je deterministická vrstva mezi hotovým EMS eventem a mobilními notifikacemi Home Assistantu.
AI pouze vytvoří lidský text. Router rozhodne, komu se text pošle, zda má mít tlačítka a co se smí po potvrzení provést.

## Vstupy

Router potřebuje:

- `event.notification` podle `ai/schemas/notification.schema.json`,
- `event.actor.person_id`, pokud je znám původce,
- aktuální stav `person.*` entit,
- mapování osob na `notify.mobile_app_*` služby,
- seznam povolených akcí z `event.action_offers`.

## Routing

### Error / critical

- vždy oba mobily,
- nezávisle na tom, kdo je doma,
- stejná chyba používá stabilní `collapse_key`,
- kritická chyba může být opakována, dokud trvá,
- při vyřešení se notifikace stáhne nebo nahradí stavem vyřešeno.

### Question

1. Pokud je známý `actor.person_id`, poslat dotaz jemu.
2. Pokud původce známý není nebo není dostupný, poslat osobě doma.
3. Když jsou doma oba a původce není známý, poslat oběma.
4. První platná odpověď vyhrává.
5. Po odpovědi stáhnout stejný `collapse_key` z ostatních mobilů.
6. Před provedením znovu ověřit:
   - že otázka je stále `open`,
   - že nevypršela,
   - že `action_id` existuje v `event.action_offers`,
   - že `requires_confirmation` je `true`,
   - že podmínka `valid_when` stále platí.

### Advice / info

- posílat jen lidem doma,
- mimo domov neposílat běžné rady,
- bez tlačítek, pokud event není `question`.

## Doporučený stav otázky

```json
{
  "question_id": "oven-bottom-boiler-1783773944058",
  "state": "open",
  "created_at": "2026-07-11T12:45:44.058Z",
  "expires_at": "2026-07-11T12:50:44.058Z",
  "recipients": ["partner"],
  "answered_by": null,
  "answer": null,
  "action_id": "pause_bottom_boiler_for_oven"
}
```

Stavy:

- `open`
- `answered`
- `expired`
- `cancelled`

## MQTT

Doporučené topicy:

- `ems/ai/notification/request` – hotová žádost routeru o odeslání,
- `ems/ai/notification/status` – kam a kdy byla notifikace odeslána,
- `ems/ai/response` – odpověď z mobilního tlačítka,
- `ems/ai/question_state` – stav otázky,
- `ems/ai/action_result` – výsledek potvrzené akce.

## Home Assistant actionable notification

Příklad dat, která má vytvořit Node-RED po routingu:

```yaml
message: "Jestli chceš péct, mám na tu dobu vypnout spodní bojler?"
title: "EMS doma"
data:
  tag: "ems-question-oven-bottom-boiler"
  persistent: true
  actions:
    - action: "EMS_YES_oven-bottom-boiler-1783773944058"
      title: "Ano"
    - action: "EMS_NO_oven-bottom-boiler-1783773944058"
      title: "Ne"
```

## Bezpečnost

- LLM nesmí generovat název libovolné HA služby.
- `action_id` musí být mapovaný na předem schválený skript v Node-REDu.
- Žádná odpověď z mobilu nesmí přímo obsahovat spustitelný název služby.
- Duplicitní nebo pozdní odpovědi se ignorují.
- Při změně podmínek se otevřený dotaz zruší.
