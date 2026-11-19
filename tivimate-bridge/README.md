# TiviMate Channel Bridge (pre LG webOS Extras)

Malá Android služba zjednodušeného ovládania (accessibility), ktorá číta z informačnej lišty TiviMate
**aktuálny kanál, program, čas programu a nasledujúci program** a posiela ich do Home Assistantu.
Funguje bez rootu, inštaluje sa cez ADB.

Vychádza z projektu [jkfran/tivimate-channel-bridge](https://github.com/jkfran/tivimate-channel-bridge)
(MIT licencia, © 2026 Fran / @jkfran). Úpravy: posiela aj program, čas, nasledujúci program,
číslo kanála a všetky texty z lišty (na doladenie), plus automatické zostavenie APK cez GitHub Actions.

TiviMate neposiela aktuálny kanál cez MediaSession ani iné API – jediný spôsob bez rootu je prečítať
text, ktorý ukazuje na obrazovke (lišta sa zobrazí pri každom prepnutí kanála).

## 1. Stiahni APK

GitHub → **Releases → TiviMate Channel Bridge (APK)** → `tivimate-channel-bridge.apk`
(alebo Actions → posledný beh → Artifacts).

## 2. Nainštaluj na Fire TV – priamo z Home Assistantu (ADB integrácia)

Fire TV väčšinou dovolí len jedno ADB pripojenie, ktoré už drží Home Assistant – preto je najjednoduchšie
inštalovať cez HA. Fire2MQTT tiež používa službu zjednodušeného ovládania, preto ju **nevypínaj** –
príkaz nižšie novú službu iba pridá k existujúcim.

1. Nahraj APK do HA ako `/config/tivimate-channel-bridge.apk` (File editor / Samba).
2. Do `configuration.yaml` pridaj a reštartuj HA:
   ```yaml
   homeassistant:
     allowlist_external_dirs:
       - /config
   ```
3. V **Nástroje pre vývojárov → Akcie** spusti postupne (v YAML režime, `IP_HA` nahraď IP adresou HA):
   ```yaml
   action: androidtv.upload
   target: {entity_id: media_player.spalna_fire_tv_spalna}
   data:
     local_path: /config/tivimate-channel-bridge.apk
     device_path: /data/local/tmp/tmb.apk
   ```
   ```yaml
   action: androidtv.adb_command
   target: {entity_id: media_player.spalna_fire_tv_spalna}
   data:
     command: pm install -r /data/local/tmp/tmb.apk
   ```
   ```yaml
   action: androidtv.adb_command
   target: {entity_id: media_player.spalna_fire_tv_spalna}
   data:
     command: >-
       mkdir -p /sdcard/Android/data/com.jkfran.tivimatebridge/files &&
       echo 'ha_webhook_url=http://IP_HA:8123/api/webhook/tivimate_channel'
       > /sdcard/Android/data/com.jkfran.tivimatebridge/files/config.properties
   ```
   ```yaml
   action: androidtv.adb_command
   target: {entity_id: media_player.spalna_fire_tv_spalna}
   data:
     command: >-
       S=com.jkfran.tivimatebridge/com.jkfran.tivimatebridge.ChannelAccessibilityService;
       C=$(settings get secure enabled_accessibility_services);
       case "$C" in *tivimatebridge*) ;; null|"") settings put secure enabled_accessibility_services $S;;
       *) settings put secure enabled_accessibility_services "$C:$S";; esac;
       settings put secure accessibility_enabled 1;
       settings get secure enabled_accessibility_services
   ```
   Výsledok posledného príkazu (atribút `adb_response`) musí obsahovať Fire2MQTT **aj** `tivimatebridge`.

Kontrola: prepni v TiviMate kanál a pozri senzor **TiviMate kanál**, prípadne
`adb_command: logcat -d -s TiviMateBridge | tail -n 20`.

Po aktualizácii APK Android službu vypne – zopakuj posledný príkaz. Každé zostavenie má nový
podpisový kľúč, takže pri aktualizácii najprv `pm uninstall com.jkfran.tivimatebridge`.

### Alternatíva: z počítača
`adb install -r tivimate-channel-bridge.apk` a rovnaké príkazy cez `adb shell` (najprv dočasne vypni ADB integráciu v HA).

## 3. Home Assistant

Integrácia **LG webOS Extras** prijíma webhook `tivimate_channel` sama a vytvorí senzory
**TiviMate kanál** a **TiviMate program** (s atribútmi čas, nasledujúci program, číslo kanála, texty).
Nič ďalšie netreba nastavovať.

## Údaje, ktoré služba posiela

```json
{"channel": "SK| Markíza HD", "number": "101", "program": "Krimi",
 "program_time": "19:00 - 19:30", "next_program": "Televízne noviny",
 "source": "infobar", "texts": ["101", "SK| Markíza HD", "25 FPS", "..."]}
```

Rozpoznanie programu je odhad podľa rozloženia lišty. Ak sa niečo zle priradí, pozri atribút `texts`
senzora a upravíme pravidlá.
