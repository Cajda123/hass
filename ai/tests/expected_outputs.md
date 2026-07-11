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

## `family_surplus_boiler_oven_offer.json`

### Dobrý výstup

```text
Pračku nebo myčku teď klidně pusť, baterka je nad cílem a přebytky už jdou do spodního bojleru. Vaření je v pohodě, je na jiných fázích. Jestli chceš péct, můžu na tu dobu vypnout spodní bojler, protože trouba je s ním na L3.
```

### Špatný výstup

```text
Systém pracuje v režimu PV_ONLY a doporučuji sledovat spotřebu energie. Zkontrolujte nastavení bojleru a wallboxu.
```

Důvod: rodinný poradce má poradit prakticky pro domácí spotřebiče, ne dělat servisní report.

## Hodnocení

Každý výstup hodnotit 0–2 body v kategoriích:

- věrnost eventu,
- žádné halucinace,
- lidská čeština,
- stručnost,
- dodržení zakázaných témat.

Maximum je 10 bodů.
