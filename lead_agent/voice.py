"""Voice channel via Retell AI.

Why Retell: it runs the real-time telephony + speech stack (streaming STT, ElevenLabs/Cartesia
voices, barge-in, backchannels, ambient sound, voicemail detection) that makes a call sound
human. Our service keeps the brains for booking: Retell calls back into /voice/tools/* for
availability and booking, and posts call events to /voice/webhook.

Stdlib only. The Retell REST surface used:
  POST  /v2/create-phone-call
  POST  /create-retell-llm        PATCH /update-retell-llm/{llm_id}
  POST  /create-agent             PATCH /update-agent/{agent_id}
  GET   /v2/get-call/{call_id}
Webhook + tool requests carry `x-retell-signature: v=<ms>,d=<hmac-sha256(body + ms, api_key)>`.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from .config import Config
from .prompts import voice_begin_message, voice_general_prompt, voice_tool_specs, voicemail_message

log = logging.getLogger("lead_agent.voice")

RETELL_BASE = "https://api.retellai.com"
SIG_RE = re.compile(r"v=(\d+),d=([0-9a-f]{64})")


def verify_signature(body: str, api_key: str, signature: str | None, now_ms: int | None = None,
                     timeout_ms: int = 5 * 60 * 1000) -> bool:
    if not signature or not api_key:
        return False
    m = SIG_RE.fullmatch(signature.strip())
    if not m:
        return False
    ts, digest = int(m.group(1)), m.group(2)
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    if abs(now_ms - ts) > timeout_ms:
        return False
    expected = hmac.new(api_key.encode(), (body + str(ts)).encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, digest)


def sign(body: str, api_key: str, ts_ms: int | None = None) -> str:
    ts_ms = ts_ms or int(time.time() * 1000)
    d = hmac.new(api_key.encode(), (body + str(ts_ms)).encode(), hashlib.sha256).hexdigest()
    return f"v={ts_ms},d={d}"


class RetellError(RuntimeError):
    pass


class RetellClient:
    def __init__(self, api_key: str, dry_run: bool = False):
        self.api_key = api_key
        self.dry_run = dry_run

    def _req(self, method: str, path: str, body: dict | None = None) -> Any:
        req = urllib.request.Request(
            RETELL_BASE + path, method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raise RetellError(f"Retell {e.code} on {method} {path}: {e.read().decode(errors='replace')[:400]}") from None

    def create_phone_call(self, from_number: str, to_number: str, agent_id: str,
                          dynamic_variables: dict[str, str], metadata: dict[str, Any]) -> dict[str, Any]:
        body = {
            "from_number": from_number,
            "to_number": to_number,
            "override_agent_id": agent_id,
            "retell_llm_dynamic_variables": {k: str(v) for k, v in dynamic_variables.items()},
            "metadata": metadata,
        }
        if self.dry_run:
            log.info("[dry-run] call %s as %s vars=%s", to_number, agent_id, dynamic_variables)
            return {"call_id": f"dry-call-{int(time.time())}", "call_status": "registered"}
        return self._req("POST", "/v2/create-phone-call", body)

    def get_call(self, call_id: str) -> dict[str, Any]:
        return self._req("GET", f"/v2/get-call/{call_id}")

    def create_llm(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._req("POST", "/create-retell-llm", payload)

    def update_llm(self, llm_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._req("PATCH", f"/update-retell-llm/{llm_id}", payload)

    def create_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._req("POST", "/create-agent", payload)

    def update_agent(self, agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._req("PATCH", f"/update-agent/{agent_id}", payload)


# ---------------- agent definition from config ----------------

def build_llm_payload(cfg: Config, base_url: str) -> dict[str, Any]:
    v = cfg.voice
    tools: list[dict[str, Any]] = voice_tool_specs(base_url)
    tools.append({"type": "end_call", "name": "end_call", "description": "End the call once the conversation is wrapped up and you've said goodbye."})
    if v.get("transfer_number"):
        tools.append({
            "type": "transfer_call", "name": "transfer_to_team",
            "description": "Transfer the caller to a live team member. Only during office hours and only if the lead asks for a person right now.",
            "transfer_destination": {"type": "predefined", "number": v["transfer_number"]},
            "transfer_option": {"type": "cold_transfer", "show_transferee_as_caller": False},
        })
    return {
        "model": v.get("llm_model", "claude-5-sonnet"),
        "model_temperature": float(v.get("llm_temperature", 0.3)),
        "start_speaker": "agent",
        "begin_message": voice_begin_message(cfg),
        "general_prompt": voice_general_prompt(cfg),
        "general_tools": tools,
        "default_dynamic_variables": {
            "lead_first_name": "there",
            "service_interest": "physical therapy",
            "offered_slots": "none yet",
            "offered_slots_spoken": "a couple of times this week",
            "current_time": "unknown",
        },
    }


def build_agent_payload(cfg: Config, llm_id: str, base_url: str) -> dict[str, Any]:
    v = cfg.voice
    p = cfg.practice
    payload: dict[str, Any] = {
        "agent_name": v.get("agent_display_name", f"{cfg.agent_name} - {p.get('short_name', 'practice')} lead follow-up"),
        "response_engine": {"type": "retell-llm", "llm_id": llm_id},
        "voice_id": v.get("voice_id", "11labs-Adrian"),
        "voice_temperature": float(v.get("voice_temperature", 1.0)),
        "voice_speed": float(v.get("voice_speed", 1.0)),
        "language": v.get("language", "en-US"),
        "responsiveness": float(v.get("responsiveness", 0.9)),
        "interruption_sensitivity": float(v.get("interruption_sensitivity", 0.8)),
        "enable_dynamic_responsiveness": True,
        "enable_backchannel": bool(v.get("enable_backchannel", True)),
        "backchannel_frequency": float(v.get("backchannel_frequency", 0.7)),
        "backchannel_words": v.get("backchannel_words", ["mm-hmm", "yeah", "okay", "gotcha", "right"]),
        "reminder_trigger_ms": int(v.get("reminder_trigger_ms", 9000)),
        "reminder_max_count": int(v.get("reminder_max_count", 2)),
        "end_call_after_silence_ms": int(v.get("end_call_after_silence_ms", 25000)),
        "max_call_duration_ms": int(v.get("max_call_duration_ms", 6 * 60 * 1000)),
        "normalize_for_speech": True,
        "boosted_keywords": v.get("boosted_keywords", [p.get("short_name", ""), "physical therapy", cfg.agent_name]),
        "webhook_url": f"{base_url}/voice/webhook",
        "webhook_events": ["call_started", "call_ended", "call_analyzed"],
        "voicemail_option": {"action": {"type": "static_text", "text": voicemail_message(cfg)}},
        "post_call_analysis_data": [
            {"type": "enum", "name": "outcome", "description": "How the call ended for the lead.",
             "choices": ["booked", "callback_requested", "not_interested", "opted_out", "wrong_number", "existing_patient", "needs_human", "no_answer", "voicemail", "unclear"]},
            {"type": "boolean", "name": "appointment_booked", "description": "True only if book_inquiry_call succeeded during the call."},
            {"type": "string", "name": "appointment_time", "description": "The booked time as spoken, if any."},
            {"type": "string", "name": "callback_window", "description": "If the lead asked to be reached later, when."},
            {"type": "string", "name": "lead_concern", "description": "One line: what the lead is dealing with or wants."},
        ],
    }
    if v.get("voice_model"):
        payload["voice_model"] = v["voice_model"]
    if v.get("ambient_sound"):
        payload["ambient_sound"] = v["ambient_sound"]
        payload["ambient_sound_volume"] = float(v.get("ambient_sound_volume", 0.3))
    if v.get("pronunciation_dictionary"):
        payload["pronunciation_dictionary"] = v["pronunciation_dictionary"]
    if v.get("opt_out_sensitive_data_storage") is not None:
        payload["opt_out_sensitive_data_storage"] = bool(v["opt_out_sensitive_data_storage"])
    return payload


# ---------------- request parsing ----------------

def parse_tool_request(body: dict[str, Any], url_tool_name: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Retell posts {name, args, call} (or just args when 'args only' is on). Returns (name, args, call)."""
    if "args" in body or "call" in body:
        return body.get("name") or url_tool_name, body.get("args") or {}, body.get("call") or {}
    return url_tool_name, body, {}


def contact_id_from_call(call: dict[str, Any]) -> Optional[str]:
    meta = call.get("metadata") or {}
    return meta.get("contact_id") or (call.get("retell_llm_dynamic_variables") or {}).get("contact_id")


def summarize_call(call: dict[str, Any]) -> dict[str, Any]:
    analysis = call.get("call_analysis") or {}
    custom = analysis.get("custom_analysis_data") or {}
    return {
        "call_id": call.get("call_id"),
        "status": call.get("call_status"),
        "disconnection_reason": call.get("disconnection_reason"),
        "duration_ms": call.get("duration_ms"),
        "summary": analysis.get("call_summary"),
        "sentiment": analysis.get("user_sentiment"),
        "in_voicemail": analysis.get("in_voicemail"),
        "outcome": custom.get("outcome"),
        "appointment_booked": custom.get("appointment_booked"),
        "callback_window": custom.get("callback_window"),
        "lead_concern": custom.get("lead_concern"),
        "transcript": call.get("transcript") or "",
        "recording_url": call.get("recording_url"),
    }


NOT_REACHED = {"dial_no_answer", "dial_busy", "dial_failed", "voicemail_reached", "invalid_destination",
               "telephony_provider_unavailable", "telephony_provider_permission_denied", "marked_as_spam", "user_declined"}
