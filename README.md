# Mein Brauhelfer

> **Voraussetzung: Home Assistant muss aus dem Internet über HTTPS auf Port 443 mit gültigem Zertifikat erreichbar sein.** Jede Sprachabfrage läuft über Amazon Alexa und AWS Lambda, auch wenn dein Echo im selben WLAN steht. Ein reiner LAN-Betrieb ist mit diesem Skill nicht möglich. Braumeister und Bridge können im Heimnetz bleiben.
>
> Für diese Einrichtung brauchst du ein Amazon-Developer-Konto für den Skill und ein AWS-Konto für die Lambda-Funktion.

## Was kostet Mein Brauhelfer?

**Der Skill selbst ist kostenlos.** Für den Betrieb der Lambda-Funktion gelten die Konditionen deines AWS-Kontos.

- **Privat testen:** Im AWS-Tarif *Free account plan* fallen während der Laufzeit keine AWS-Gebühren an. Der Tarif endet nach sechs Monaten oder sobald das Guthaben aufgebraucht ist, je nachdem, was zuerst eintritt. Lässt du den Tarif auslaufen, schließt AWS das Konto und der Skill kann keine Braudaten mehr abrufen. [AWS-Kontotarife](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html)
- **Dauerhaft nutzen:** Für den Weiterbetrieb kannst du vor Ablauf zum *Paid account plan* wechseln. Das monatliche Lambda-Freikontingent umfasst eine Million Aufrufe und 400.000 GB-Sekunden Rechenzeit. Ein paar kurze Brauabfragen pro Tag liegen üblicherweise innerhalb dieser Grenzen. Bei höherer Gesamtnutzung deines AWS-Kontos oder durch andere AWS-Dienste können Kosten entstehen. [AWS-Lambda-Preise](https://aws.amazon.com/lambda/pricing/)

Falls du noch kein AWS-Konto hast, kannst du bei der Registrierung den passenden Tarif wählen. [Zur AWS-Registrierung](https://signup.aws.amazon.com/)

## Was kann ich fragen?

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

### Skill anlegen und Skill-ID kopieren

1. In der [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask) einen Skill **Mein Brauhelfer** mit **German (DE)**, **Custom**, **Provision your own** und einem leeren Modell anlegen.
2. Unter **Build → Interaction Model → JSON Editor** den gesamten Inhalt von [de-DE.json](alexa/de-DE.json) einsetzen. **Save Model** und **Build Model** wählen.
3. Unter **Build → Endpoint → AWS Lambda ARN** steht **Your Skill ID**. Mit **Copy to Clipboard** die vollständige ID mit dem Präfix `amzn1.ask.skill.` kopieren. Diese ID wird gleich zweimal in AWS benötigt.

### Python-Lambda-Funktion erstellen

1. Die [AWS Lambda Console für Europa (Irland), eu-west-1](https://eu-west-1.console.aws.amazon.com/lambda/home?region=eu-west-1#/functions) öffnen und mit deinem AWS-Zugang anmelden. Die Ansicht **IAM user sign in** ist für eingerichtete IAM-Benutzer und fragt nach AWS-Konto-ID oder Alias und IAM-Benutzername. Hast du bereits ein eigenes AWS-Konto, verwende dessen üblichen Anmeldeweg.
2. Oben rechts **Europe (Ireland)** prüfen. Von der AWS-Startseite aus kannst du auch oben nach **Lambda** suchen und den Dienst öffnen.
3. Unter **Functions** beziehungsweise **Event Functions** auf **Create function** beziehungsweise **Create Event Function** klicken und **Author from scratch** wählen.
4. Als **Function name** beispielsweise `mein-brauhelfer`, als **Runtime** **Python 3.13** und als **Architecture** **x86_64** wählen. Python 3.13 war im Einrichtungstest verfügbar; Python 3.14 wurde in dieser Konsole nicht angeboten.
5. Unter **Permissions** die automatisch erstellte einfache Ausführungsrolle beibehalten. Je nach Ansicht steht dort **Change default execution role → Create a new role with basic Lambda permissions**, oder die Konsole erklärt direkt, dass sie eine Rolle mit Berechtigung zum Schreiben von CloudWatch-Logs erstellt. Dann **Create function** wählen.

### Code und Einstellungen speichern

1. Unter **Code** die Datei **lambda_function.py** öffnen und deren gesamten Inhalt durch [lambda_function.py](lambda_function.py) ersetzen.
2. **Deploy** anklicken. Solange **Undeployed** angezeigt wird, ist der bearbeitete Code noch nicht bereitgestellt. Die Erfolgsmeldung abwarten.
3. Unter **Code → Runtime settings** den Handler `lambda_function.lambda_handler` prüfen.
4. Unter **Configuration → General configuration → Edit** den **Timeout auf 0 min 7 sec** setzen und **Save** wählen.
5. Unter **Configuration → Environment variables → Edit** mit **Add environment variable** diese beiden Einträge anlegen und **Save** wählen:

| Key | Value |
| --- | --- |
| `BASE_URL` | Die zuvor geprüfte öffentliche Home-Assistant-HTTPS-Adresse, ohne abschließenden Schrägstrich und ohne API-Pfad; bei Nabu Casa beispielsweise `https://deine-adresse.ui.nabu.casa` |
| `SKILL_ID` | Die vollständige, unter **Your Skill ID** kopierte `amzn1.ask.skill.…`-ID |

Ein Home-Assistant-Token wird hier nicht eingetragen. Die Anmeldung erfolgt später über die Kontoverknüpfung.

### Alexa-Trigger hinzufügen

1. In der Funktionsübersicht **Add trigger** anklicken.
2. Die Liste **Select a source** öffnen. In der im Einrichtungstest angezeigten Konsole heißt der Eintrag zunächst **Alexa**.
3. Unter **Choose an Alexa product** **Alexa Skills Kit** auswählen.
4. **Skill ID verification → Enable (recommended)** beibehalten und unter **Skill ID** dieselbe vollständige ID wie bei `SKILL_ID` eintragen.
5. Mit **Add** bestätigen. Anschließend erscheint der Alexa-Trigger unter **Configuration → Triggers**.

### Lambda-ARN im Skill hinterlegen

Der Trigger erlaubt Alexa den Aufruf der Funktion. Zusätzlich muss der Skill wissen, welche Funktion er aufrufen soll:

1. In der AWS-Funktionsübersicht oben die **Function ARN** kopieren. Für die hier erstellte Funktion hat sie das Format `arn:aws:lambda:eu-west-1:<AWS-Konto-ID>:function:mein-brauhelfer`.
2. In der Alexa Developer Console **Build → Endpoint → AWS Lambda ARN** öffnen.
3. Unter **Default Region (Required)** die eigene Lambda-ARN einsetzen. Falls dort noch eine `ReflectorTemplate…`-ARN des Startmodells steht, diese vollständig ersetzen.
4. Falls unter **Europe and India** bereits eine abweichende ARN eingetragen ist, dort ebenfalls die eigene ARN einsetzen. Bei einem leeren optionalen Feld genügt der Eintrag unter **Default Region**.
5. Oben rechts **Save** wählen. Die Lambda-ARN ist ein anderer Wert als die Skill-ID.

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
