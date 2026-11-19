# LG webOS Extras

Doplnok k oficiálnej integrácii **LG webOS TV** v Home Assistante. Pridá k televízoru:

- **Časovač vypnutia** (`select`): Vypnutý / 15 / 30 / 45 / 60 / 90 / 120 / 180 min
- **Senzor**, ktorý ukazuje, kedy časovač vypne TV (časovač prežije aj reštart HA)
- **Upozornenie na TV** 1 minútu pred vypnutím (dá sa vypnúť v Možnostiach)
- **Tlačidlá ovládača** ako entity (Domov, Späť, šípky, OK, Nastavenia, Rýchle menu, hlasitosť, kanály…); menej používané sú predvolene vypnuté a zapneš ich na stránke zariadenia
- **Zvukový výstup** (`select`): reproduktory TV, HDMI ARC, optický výstup, Bluetooth…
- **Výber aplikácie** (`select`): predvolene Netflix, HBO Max a TiviMate (ak sú v zozname zdrojov TV). Zoznam si upravíš v **Možnostiach** integrácie – dá sa pridať akákoľvek aplikácia alebo HDMI vstup.
- **Obrazovka** (`switch`): vypne obrazovku, zvuk hrá ďalej (hudba, podcasty). Zapnutím alebo stlačením tlačidla na ovládači sa obrazovka znova rozsvieti.

Všetky entity sa zobrazia priamo na zariadení tvojho televízora.

## Inštalácia cez HACS

1. Repozitár: `https://github.com/soso8782/LGTV-webos-extended`
2. HACS → ⋮ → **Custom repositories** → vlož URL repozitára, typ **Integration**.
3. Nájdi **LG webOS Extras**, stiahni a reštartuj Home Assistant.
4. Nastavenia → Zariadenia a služby → **Pridať integráciu** → **LG webOS Extras** → vyber televízor.

### Bez GitHubu
Skopíruj priečinok `custom_components/lg_webos_extras` do `/config/custom_components/` (napr. cez doplnok File editor alebo Samba) a reštartuj HA.

## Aplikácie na Fire TV (Fire2MQTT)

Ak máš k TV pripojený Fire TV s integráciou [Fire2MQTT](https://github.com/Harrypulvirenti/Fire2MQTT), výber **Aplikácia** vie spúšťať aplikácie priamo na ňom:

1. LG webOS Extras → **Konfigurovať**
2. **Fire TV** – vyber prehrávač z Fire2MQTT
3. **Vstup TV** – HDMI vstup, kde je Fire TV (TV sa naň pred spustením prepne)
4. **Aplikácie na Fire TV** – `Názov=balíček`, predvolene:
   `Netflix=com.netflix.ninja, HBO Max=com.wbd.stream, TiviMate=ar.tvplayer.tv`

Ďalšie aplikácie pridáš rovnako (názov balíčka nájdeš napr. v atribúte `app_id` prehrávača Fire2MQTT, keď je aplikácia spustená).

## TiviMate – aktuálny kanál a program

TiviMate tieto údaje neposiela cez žiadne API, preto je v priečinku [`tivimate-bridge/`](tivimate-bridge/) malá Android aplikácia
(služba zjednodušeného ovládania), ktorá ich číta z informačnej lišty TiviMate a posiela do HA.
Integrácia ich prijíma na webhooku `tivimate_channel` a vytvorí senzory **TiviMate kanál** a **TiviMate program**
(atribúty: číslo kanála, čas programu, nasledujúci program). Návod na inštaláciu je v [tivimate-bridge/README.md](tivimate-bridge/README.md).

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
      - entity: select.lg_webos_tv_aplikacia
      - entity: switch.lg_webos_tv_obrazovka
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
- TiviMate je aplikácia pre Android – na webOS neexistuje. Ak ho máš na Android boxe cez HDMI, pridaj do výberu aplikácií príslušný HDMI vstup.
- **Staršie TV (webOS 1/2, modely 2014–2015)** nemajú príkaz na vypnutie obrazovky. Prepínač Obrazovka potom použije postupnosť tlačidiel, ktorú nastavíš v **Možnostiach** integrácie (cesta *Nastavenia → Obraz → Úspora energie → Vypnutie obrazovky*). Formát: `MENU, wait 2, DOWN*3, ENTER` – `KLÁVES*N` = N-krát, `wait X` = pauza X sekúnd. Obrazovku znova zapne tlačidlo EXIT.
- Stav prepínača Obrazovka je odhadovaný (TV ho do Home Assistantu nehlási) a po zapnutí TV sa vráti na „zapnutá“.
- Novšie verzie Home Assistantu majú vypínač obrazovky aj v oficiálnej integrácii (predvolene vypnutý) – stačí používať jeden z nich.
