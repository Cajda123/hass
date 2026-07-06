# EMS AI vrstva

Tahle složka drží verzované prompty, schémata, příklady a testy pro lokální AI komentátor/analytik nad EMS.

## Princip

- EMS rozhoduje deterministicky v Node-RED.
- AI pouze vysvětluje stav, event nebo rozhodnutí EMS.
- AI nikdy přímo neovládá zařízení.
- Do AI neposílat celý `global.ems`, ale kompaktní snapshot + konkrétní event.

## Režimy

### Komentátor

Krátký automatický komentář k eventu. Výstup typicky do MQTT topicu `ems/ai/comment`.

### Analytik

Delší ruční odpověď na otázku nad historií, logy nebo agregovaným průběhem.

### Notifikátor

Velmi krátká notifikace pro mobil / HA, jen pokud je event důležitý.

## Ověřený runtime

- Ollama: `http://10.200.5.122:11434`
- EMS komentář: `gemma3:4b`
- WebUI / obecné hraní: `qwen2.5:7b`

## Doporučené volání Ollamy

```json
{
  "model": "gemma3:4b",
  "prompt": "<prompt + compact snapshot>",
  "stream": false,
  "options": {
    "temperature": 0.1,
    "num_predict": 120
  }
}
```

U `gemma3:4b` se zatím v testech líp choval jeden velký `prompt` než oddělený `system` + `prompt`.
