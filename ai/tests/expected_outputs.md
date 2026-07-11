# Očekávané výstupy EMS AI

Tyhle příklady slouží pro ruční benchmark modelů a kontrolu promptu.

## `safety_event.json`

### Dobrý výstup

```text
AC-in manager je vypnutý a dům zůstává v ostrovním provozu. Není potřeba žádný zásah.
```

### Špatný výstup

```text
Doporučuji zapnout týdenní balanc a sledovat deficit energie.
```

Důvod: týdenní balanc ani deficit nejsou tématem eventu.

## `wallbox_disabled.json`

### Dobrý výstup

```text
Wallbox je vypnutý, protože není připojené žádné auto. Není potřeba nic řešit.
```

### Špatný výstup

```text
Zkontrolujte komunikaci s wallboxem nebo nastavení EMS.
```

Důvod: `no_car_connected` není chyba komunikace.

## `boiler_started.json`

### Dobrý výstup

```text
Spodní bojler se zapnul z přebytku FVE. Baterie už je nad cílem, takže je energie kam uložit.
```

### Špatný výstup

```text
Doporučuji sledovat teplotu vody a případně bojler vypnout.
```

Důvod: takové doporučení není ve vstupu.

## `battery_grid_charge.json`

### Dobrý výstup

```text
Baterie se v levném tarifu dobíjí k cílovému SOC. EMS tím připravuje rezervu na horší výrobu.
```

### Špatný výstup

```text
Zkontrolujte, zda je síťové dobíjení opravdu nutné.
```

Důvod: event už obsahuje autoritativní rozhodnutí EMS.

## Hodnocení

Každý výstup hodnotit 0–2 body v kategoriích:

- věrnost eventu,
- žádné halucinace,
- lidská čeština,
- stručnost,
- dodržení zakázaných témat.

Maximum je 10 bodů.
