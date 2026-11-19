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

## 2. Nainštaluj na Fire TV (cez počítač s ADB)

```bash
adb connect <IP_FIRE_TV>:5555
adb install -r tivimate-channel-bridge.apk

# webhook – použi IP adresu Home Assistantu
echo "ha_webhook_url=http://<IP_HA>:8123/api/webhook/tivimate_channel" > config.properties
adb shell mkdir -p /sdcard/Android/data/com.jkfran.tivimatebridge/files
adb push config.properties /sdcard/Android/data/com.jkfran.tivimatebridge/files/config.properties

# zapni službu (pozor: prepíše iné zapnuté accessibility služby)
adb shell settings put secure enabled_accessibility_services com.jkfran.tivimatebridge/com.jkfran.tivimatebridge.ChannelAccessibilityService
adb shell settings put secure accessibility_enabled 1
```

Kontrola: `adb logcat -s TiviMateBridge` – po prepnutí kanála uvidíš `CHANNEL=… PROGRAM=…` a `POST 200`.

Po aktualizácii APK Android službu vypne – zopakuj posledné dva príkazy. Každé zostavenie má nový
podpisový kľúč, takže pri aktualizácii najprv `adb uninstall com.jkfran.tivimatebridge`.

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
