# EMS AI rozhodnutí a zkušenosti

Tento soubor drží praktické poznatky z vývoje AI vrstvy, aby se neztratily v chatu ani v Node-RED function nodech.

## Architektura

- AI je hlas EMS, ne druhý mozek EMS.
- Deterministické rozhodování zůstává v Node-RED.
- AI nesmí sama ovládat zařízení.
- AI dostává event + kompaktní snapshot, ne celý `global.ems`.
- Preferovat event-driven komentáře před časovým pollingem.

## Promptování

- U `gemma3:4b` se líp choval jeden velký `prompt` než oddělené `system` + `prompt`.
- Model má tendenci popisovat JSON, pokud dostane příliš obecné instrukce.
- Prompt musí explicitně zakázat popis JSONu a seznamy položek.
- Používat české `reason_display` a `status_display`, aby AI nehádala význam interních kódů.

## Anti-spam

- Po startu/redeployi Node-RED ignorovat minimálně 90 sekund.
- Stejný event nekomentovat opakovaně.
- Automatické komentáře omezit minimálně na 2 minuty mezi výstupy.
- `ems_disabled` nekomentovat automaticky, pokud nejde o ruční dotaz.

## Modely

- `gemma3:4b`: použitelná pro krátké EMS komentáře přes přímé Ollama API.
- `qwen2.5:7b`: použitelný ve WebUI, umí tools, ale umí být kreativní a ukecaný.

## Bezpečnost

- Port Ollama API neotevírat do internetu.
- AI výstup brát jako komentář, ne jako bezpečnostní rozhodnutí.
- Kritické funkce jako AC-in manager, nouzové dobíjení a hard min SOC musí zůstat plně deterministické.
