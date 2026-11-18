# LG webOS Extras

Doplnok k oficiálnej integrácii **LG webOS TV** v Home Assistante. Pridá k televízoru:

- **Časovač vypnutia** (`select`): Vypnutý / 15 / 30 / 45 / 60 / 90 / 120 / 180 min
- **Senzor**, ktorý ukazuje, kedy časovač vypne TV (časovač prežije aj reštart HA)
- **Upozornenie na TV** 1 minútu pred vypnutím (dá sa vypnúť v Možnostiach)
- **Tlačidlá ovládača** ako entity (Domov, Späť, šípky, OK, Nastavenia, Rýchle menu, hlasitosť, kanály…); menej používané sú predvolene vypnuté a zapneš ich na stránke zariadenia
- **Zvukový výstup** (`select`): reproduktory TV, HDMI ARC, optický výstup, Bluetooth…

Všetky entity sa zobrazia priamo na zariadení tvojho televízora.

## Inštalácia cez HACS

1. Repozitár: `https://github.com/soso8782/LGTV-webos-extended`
2. HACS → ⋮ → **Custom repositories** → vlož URL repozitára, typ **Integration**.
3. Nájdi **LG webOS Extras**, stiahni a reštartuj Home Assistant.
4. Nastavenia → Zariadenia a služby → **Pridať integráciu** → **LG webOS Extras** → vyber televízor.

### Bez GitHubu
Skopíruj priečinok `custom_components/lg_webos_extras` do `/config/custom_components/` (napr. cez doplnok File editor alebo Samba) a reštartuj HA.

## Príklad karty na dashboard

Názvy entít sa môžu líšiť podľa názvu tvojho TV – skontroluj ich na stránke zariadenia.

```yaml
type: vertical-stack
cards:
  - type: entities
    entities:
      - entity: select.lg_webos_tv_casovac_vypnutia
      - entity: sensor.lg_webos_tv_casovac_vypne_tv_o
      - entity: select.lg_webos_tv_zvukovy_vystup
  - type: grid
    columns: 3
    square: false
    cards:
      - type: button
        entity: button.lg_webos_tv_domov
        tap_action: {action: perform-action, perform_action: button.press, target: {entity_id: button.lg_webos_tv_domov}}
      - type: button
        entity: button.lg_webos_tv_hore
        tap_action: {action: perform-action, perform_action: button.press, target: {entity_id: button.lg_webos_tv_hore}}
      - type: button
        entity: button.lg_webos_tv_nastavenia
        tap_action: {action: perform-action, perform_action: button.press, target: {entity_id: button.lg_webos_tv_nastavenia}}
      - type: button
        entity: button.lg_webos_tv_vlavo
        tap_action: {action: perform-action, perform_action: button.press, target: {entity_id: button.lg_webos_tv_vlavo}}
      - type: button
        entity: button.lg_webos_tv_ok
        tap_action: {action: perform-action, perform_action: button.press, target: {entity_id: button.lg_webos_tv_ok}}
      - type: button
        entity: button.lg_webos_tv_vpravo
        tap_action: {action: perform-action, perform_action: button.press, target: {entity_id: button.lg_webos_tv_vpravo}}
      - type: button
        entity: button.lg_webos_tv_spat
        tap_action: {action: perform-action, perform_action: button.press, target: {entity_id: button.lg_webos_tv_spat}}
      - type: button
        entity: button.lg_webos_tv_dole
        tap_action: {action: perform-action, perform_action: button.press, target: {entity_id: button.lg_webos_tv_dole}}
      - type: button
        entity: button.lg_webos_tv_rychle_menu
        tap_action: {action: perform-action, perform_action: button.press, target: {entity_id: button.lg_webos_tv_rychle_menu}}
```

## Poznámky

- Časovač beží v Home Assistante, nie vo vstavanom časovači TV (ten LG cez sieťové API nesprístupňuje).
- Ak TV vypneš inak, časovač sa automaticky zruší.
- Ak upozornenie na TV nefunguje, vypni ho v Možnostiach integrácie – vypnutie TV funguje aj tak.
