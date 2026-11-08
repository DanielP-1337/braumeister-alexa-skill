import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from jinja2 import Environment, StrictUndefined
import yaml

import lambda_function as skill


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = yaml.safe_load((ROOT / "home-assistant/brauhelfer.yaml").read_text("utf-8"))["intent_script"]


def render(name, state, **attrs):
    template = Environment(undefined=StrictUndefined).from_string(SCRIPTS[name]["speech"]["text"])
    return template.render(states=lambda _: state, is_state=lambda _, value: state == value,
                           state_attr=lambda _, key: attrs.get(key)).strip()


class SpeechTests(unittest.TestCase):
    def test_model_matches_handlers(self):
        model = json.loads((ROOT / "alexa/de-DE.json").read_text("utf-8"))
        names = {i["name"] for i in model["interactionModel"]["languageModel"]["intents"]}
        self.assertEqual({n for n in names if not n.startswith("AMAZON.")}, skill.INTENTS)
        self.assertEqual(set(SCRIPTS), skill.INTENTS)

    def test_hops(self):
        self.assertIn("Jetzt", render("BrauHopfen", "on", alarm_type="hop_addition"))
        for state, alarm in [("off", "hop_addition"), ("on", "rest_end_reached")]:
            self.assertIn("kein Countdown", render("BrauHopfen", state, alarm_type=alarm))
        self.assertIn("nicht verfügbar", render("BrauHopfen", "unavailable"))

    def test_end(self):
        self.assertIn("abgeschlossen", render("BrauEnde", "on", alarm_type="brew_finished"))
        self.assertIn("liegt mir nicht vor", render("BrauEnde", "off", alarm_type="brew_finished"))

    def test_step(self):
        self.assertIn("Aufheizen", render("BrauStatus", "Aufheizen"))
        self.assertIn("unbekannt", render("BrauStatus", "unknown"))

    def test_duration(self):
        for value, unit, phrase in [("61", "s", "2 Minuten"), ("0.5", "h", "30 Minuten"),
                                    ("0", "min", "null"), ("1", "min", "eine Minute"),
                                    ("unknown", "min", "keine Restzeit"), ("12", None, "keine Restzeit")]:
            with self.subTest(value=value, unit=unit):
                self.assertIn(phrase, render("BrauRestzeit", value, unit_of_measurement=unit))


@patch.dict(os.environ, SKILL_ID="example", BASE_URL="https://home.example")
class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.event = {"context": {"System": {"application": {"applicationId": "example"},
                                              "user": {"accessToken": "test"}}},
                      "request": {"type": "IntentRequest", "intent": {"name": "BrauStatus"}}}

    @patch("lambda_function.build_opener")
    def test_forward(self, opener):
        reply = skill.say("Aufheizen")
        opener.return_value.open.return_value = io.BytesIO(json.dumps(reply).encode())
        self.assertEqual(skill.lambda_handler(self.event, None), reply)
        call = opener.return_value.open.call_args.args[0]
        self.assertEqual(call.full_url, "https://home.example/api/alexa")
        self.assertEqual(call.get_header("Authorization"), "Bearer test")
        self.assertEqual(json.loads(call.data), self.event)

    @patch("lambda_function.build_opener")
    def test_local_requests(self, opener):
        self.event["request"] = {"type": "LaunchRequest"}
        self.assertFalse(skill.lambda_handler(self.event, None)["response"]["shouldEndSession"])
        self.event["request"] = {"type": "IntentRequest", "intent": {"name": "OtherIntent"}}
        skill.lambda_handler(self.event, None)
        self.event["request"]["intent"]["name"] = "BrauStatus"
        self.event["context"]["System"]["user"].clear()
        self.assertEqual(skill.lambda_handler(self.event, None)["response"]["card"]["type"], "LinkAccount")
        self.event["context"]["System"]["application"]["applicationId"] = "wrong"
        with self.assertRaises(ValueError):
            skill.lambda_handler(self.event, None)
        opener.assert_not_called()

    @patch("lambda_function.build_opener")
    def test_unreachable(self, opener):
        opener.return_value.open.side_effect = TimeoutError()
        response = skill.lambda_handler(self.event, None)
        self.assertIn("nicht", response["response"]["outputSpeech"]["text"])
