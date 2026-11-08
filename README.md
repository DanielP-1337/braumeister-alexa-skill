# Mein Brauhelfer

> **Voraussetzung: Home Assistant muss aus dem Internet über HTTPS auf Port 443 mit gültigem Zertifikat erreichbar sein.** Jede Sprachabfrage läuft über Amazon Alexa und AWS Lambda, auch wenn dein Echo im selben WLAN steht. Ein reiner LAN-Betrieb ist mit diesem Skill nicht möglich. Braumeister und Bridge können im Heimnetz bleiben.

Ein deutschsprachiger Alexa Custom Skill für die [Speidel-Braumeister-Integration](https://github.com/omphteliba/ha-speidel-braumeister). Ein Echo liest über Home Assistant den aktuellen Brauschritt, seine Restzeit und zwei Alarmmeldungen vor. Der Skill enthält ausschließlich Sprachabfragen.

Sage **„Alexa, öffne mein Brauhelfer“** und stelle dann eine Frage.

| Frage | Antwortgrundlage |
| --- | --- |
| Was macht der Braumeister? | Text des aktuellen Brauschritts |
| Wie lange dauert der aktuelle Schritt? | Schritt-Restzeit in Minuten, auf volle Minuten aufgerundet |
| Wie lange noch bis zur nächsten Hopfengabe? | Ein aktiver Alarm mit `alarm_type: hop_addition` bedeutet „Jetzt“. Für einen zukünftigen Termin fehlt ein verlässlicher Countdown. |
| Wann ist das Bier fertig? | Ein aktiver Alarm mit `alarm_type: brew_finished` bestätigt das Ende des Brauvorgangs. Eine Prognose für das Sudende oder die Gärung ist aus diesen Daten nicht möglich. |

## 1. Home Assistant einrichten

### Fernzugriff prüfen

Wenn du Home Assistant Cloud von Nabu Casa nutzt, kannst du den Fernzugriff ohne Portfreigabe im Router einrichten:

1. In Home Assistant **Einstellungen → Home Assistant Cloud** öffnen und bei deinem Cloud-Konto anmelden.
2. **Fernzugriff** einschalten. Sobald die Adresse bereitsteht, die angezeigte HTTPS-Adresse kopieren.
3. Am Handy das WLAN ausschalten und die Adresse über Mobilfunk öffnen. Erscheint deine Home-Assistant-Anmeldung oder dein Dashboard, ist die Adresse von außen erreichbar. Der Fernzugriff muss auch bei späteren Sprachabfragen aktiv sein.

Eine bereits eingerichtete öffentliche HTTPS-Adresse von Home Assistant kannst du ebenfalls verwenden. Die gewählte Adresse brauchst du als `BASE_URL` für Lambda und für die beiden URLs zur Kontoverknüpfung. [Nabu Casa – Fernzugriff](https://www.nabucasa.com/config/remote/)

### Braumeister-Entitäten zuordnen

1. Unter **Einstellungen → Geräte & Dienste → Entitäten** die IDs für den aktuellen Schritt, die Restzeit und den binären Alarm kopieren. Unter **Entwicklerwerkzeuge → Zustände** kannst du Werte, Einheit und das Attribut `alarm_type` prüfen.
2. [brauhelfer.yaml](home-assistant/brauhelfer.yaml) als `packages/brauhelfer.yaml` neben deiner `configuration.yaml` speichern. Alle Vorkommen der drei Beispiel-IDs durch deine eigenen ersetzen. Die Restzeit erwartet eine Dauer mit der Einheit `min`, `s` oder `h`.
3. Packages in `configuration.yaml` aktivieren. Wenn der Abschnitt `homeassistant:` schon existiert, die Zeile für `packages` dort ergänzen. Bei bereits aktivierten Packages das vorhandene Verzeichnis verwenden. Ist `alexa:` bereits konfiguriert, die leere Zeile `alexa:` aus dem neuen Package entfernen.

```yaml
homeassistant:
  packages: !include_dir_named packages
```

4. Die HA-Konfiguration prüfen und Home Assistant neu starten.

## 2. Skill und Lambda verbinden

1. In der [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask) einen Skill **Mein Brauhelfer** mit **German (DE)**, **Custom**, **Provision your own** und einem leeren Modell anlegen.
2. Unter **Build → Interaction Model → JSON Editor** den gesamten Inhalt von [de-DE.json](alexa/de-DE.json) einsetzen. **Save Model** und **Build Model** wählen. Die Skill-ID kopieren.
3. In der [AWS Lambda Console](https://console.aws.amazon.com/lambda/) in **Europa (Irland), eu-west-1** eine Python-3-Lambda-Funktion mit einer einfachen Lambda-Ausführungsrolle erstellen. Den Inhalt von [lambda_function.py](lambda_function.py) in die gleichnamige Datei einsetzen. Handler auf `lambda_function.lambda_handler`, Funktions-Timeout auf **7 Sekunden** setzen und **Deploy** wählen.
4. Unter **Environment variables** die geprüfte Fernzugriffsadresse als `BASE_URL` eintragen, ohne abschließenden Schrägstrich oder API-Pfad. `SKILL_ID` auf die vollständige `amzn1.ask.skill.…`-ID setzen. Als Trigger **Alexa Skills Kit** hinzufügen und die Prüfung auf dieselbe Skill-ID aktivieren.
5. Die Lambda-ARN in der Alexa Developer Console unter **Endpoint → AWS Lambda ARN → Default Region** eintragen und speichern.

## 3. Konto verknüpfen und ausprobieren

Unter **Account Linking** den **Authorization Code Grant** konfigurieren. Die folgenden Werte gelten für ein EU-Konto. Andere Regionen sind in der [Home-Assistant-Anleitung für Alexa Custom Skills](https://www.home-assistant.io/integrations/alexa.intent/) beschrieben.

| Feld | Wert |
| --- | --- |
| Authorization URI | An dieselbe Fernzugriffsadresse `/auth/authorize` anhängen |
| Access Token URI | An dieselbe Fernzugriffsadresse `/auth/token` anhängen |
| Client ID | `https://layla.amazon.com/` einschließlich abschließendem Schrägstrich |
| Client Secret | Eigenen zufälligen Wert eintragen. HA wertet das Feld nicht aus. |
| Client Authentication Scheme | Credentials in request body |
| Scope | `intent` |

Im Tab **Test** den Modus **Development** aktivieren. In der Alexa-App mit demselben Amazon-Konto unter **Deine Skills → Entwickler-Skills** den Skill aktivieren und bei der eigenen HA-Instanz anmelden. Die Lambda-Funktion verwendet das Token dieser Kontoverknüpfung.

Zum ersten Test „Alexa, öffne mein Brauhelfer“ sagen. Nach der Begrüßung „Was macht der Braumeister?“ fragen und mit dem Schritt in HA vergleichen. Die Begrüßung kommt von Lambda, erst die zweite Antwort prüft auch die Verbindung zu HA. Die Entwicklungsversion lässt sich mit dem eigenen Konto ohne Veröffentlichung im Alexa Skills Store testen.

## Lokale Tests

Im Repo mit Python 3 in einer virtuellen Umgebung ausführen:

```sh
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```

Die Tests rendern die HA-Sprachvorlagen mit Beispielzuständen und prüfen die Alexa-Anbindung ohne Netzwerkzugriffe. Die Lambda-Funktion selbst benötigt nur die Python-Standardbibliothek.
