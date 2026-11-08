"""German read-only Braumeister custom skill. AWS Lambda, Python standard library."""
import json
import os
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

INTENTS = {"BrauStatus", "BrauRestzeit", "BrauHopfen", "BrauEnde"}
HELP = ("Du kannst fragen: Was macht der Braumeister? Wie lange dauert der aktuelle "
        "Schritt? Wann ist die nächste Hopfengabe? Oder: Wann ist das Bier fertig?")


def say(text, *, listen=False, link=False):
    speech = {"type": "PlainText", "text": text}
    response = {"outputSpeech": speech, "shouldEndSession": not listen}
    if listen:
        response["reprompt"] = {"outputSpeech": speech}
    if link:
        response["card"] = {"type": "LinkAccount"}
    return {"version": "1.0", "response": response}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def lambda_handler(event, context):
    system = event.get("context", {}).get("System", {})
    skill = os.environ.get("SKILL_ID")
    if not skill or system.get("application", {}).get("applicationId") != skill:
        raise ValueError("Unexpected skill ID")
    request = event["request"]
    kind = request["type"]
    if kind == "SessionEndedRequest":
        return {"version": "1.0", "response": {}}
    name = request.get("intent", {}).get("name")
    if kind == "LaunchRequest" or name in {"AMAZON.HelpIntent", "AMAZON.FallbackIntent"}:
        return say(HELP, listen=True)
    if name in {"AMAZON.StopIntent", "AMAZON.CancelIntent"}:
        return say("Bis zum nächsten Sud!")
    if kind != "IntentRequest" or name not in INTENTS:
        return say(HELP, listen=True)
    token = system.get("user", {}).get("accessToken")
    if not token:
        return say("Bitte verknüpfe Home Assistant in der Alexa App.", link=True)
    base = os.environ["BASE_URL"].rstrip("/")
    url = urlsplit(base)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError("Configure an HTTPS BASE_URL")
    call = Request(base + "/api/alexa", data=json.dumps(event).encode(),
                   headers={"Content-Type": "application/json", "Authorization": "Bearer " + token})
    try:
        with build_opener(NoRedirect()).open(call, timeout=4) as result:
            reply = json.load(result)
        if isinstance(reply, dict) and "outputSpeech" in reply.get("response", {}):
            return reply
    except HTTPError as error:
        if error.code in (401, 403):
            return say("Bitte prüfe die Kontoverknüpfung in der Alexa App.", link=True)
    except (OSError, ValueError):
        pass
    return say("Ich kann die Braudaten gerade nicht von Home Assistant abrufen.")
