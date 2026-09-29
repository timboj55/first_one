"""The SMS brain: a Claude conversation per lead with booking tools.

The transcript for a lead is append-only and stored as raw content blocks, so thinking
blocks and tool calls replay exactly. Each turn is one user message (a lead text, a system
event, or both) followed by a tool loop until Claude produces the outgoing text.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import anthropic

from .config import Config
from .prompts import sms_system_prompt
from .tools import TOOL_DEFS, Tools

log = logging.getLogger("lead_agent.brain")

NO_REPLY = "NO_REPLY"
MAX_TOOL_ROUNDS = 6
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class BrainError(RuntimeError):
    """Transient failure (rate limit, network, 5xx). The job runner retries."""


@dataclass
class BrainResult:
    reply: Optional[str]
    messages: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str = ""
    usage: dict[str, Any] = field(default_factory=dict)


def _dump(block: Any) -> dict[str, Any]:
    if isinstance(block, dict):
        return block
    if hasattr(block, "model_dump"):
        return block.model_dump(mode="json", exclude_none=True)
    return {k: v for k, v in vars(block).items() if not k.startswith("_") and v is not None}


class Brain:
    def __init__(self, cfg: Config, client: Any | None = None, model: str | None = None, effort: str | None = None):
        self.cfg = cfg
        self.client = client or anthropic.Anthropic()
        self.model = model or cfg.sms_model
        self.effort = effort or cfg.sms_effort
        self.system = sms_system_prompt(cfg)

    def _create(self, messages: list[dict[str, Any]]) -> Any:
        kwargs: dict[str, Any] = dict(
            model=self.model,
            max_tokens=4096,
            system=[{"type": "text", "text": self.system, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
            tools=TOOL_DEFS,
            output_config={"effort": self.effort},
        )
        try:
            # Server-side refusal fallback: if a safety classifier declines, the API re-runs on a
            # fallback model inside the same call, so the lead still gets a reply.
            return self.client.beta.messages.create(betas=[FALLBACK_BETA], fallbacks="default", **kwargs)
        except anthropic.BadRequestError as e:
            if "fallback" in str(e).lower() or "beta" in str(e).lower():
                log.warning("fallbacks not accepted, retrying without: %s", e)
                return self.client.messages.create(**kwargs)
            raise
        except anthropic.RateLimitError as e:
            raise BrainError(f"rate limited: {e}") from e
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                raise BrainError(f"api {e.status_code}: {e}") from e
            raise
        except anthropic.APIConnectionError as e:
            raise BrainError(f"connection: {e}") from e

    def turn(self, messages: list[dict[str, Any]], tools: Tools, *, user_text: str | None = None,
             event: str | None = None, now_text: str = "") -> BrainResult:
        parts: list[str] = []
        if event:
            parts.append(f"<event>{event}</event>")
        if user_text:
            stamp = f"[{now_text}] " if now_text else ""
            parts.append(f"{stamp}{user_text}")
        if not parts:
            raise ValueError("turn needs user_text or event")
        history = list(messages) + [{"role": "user", "content": "\n".join(parts)}]
        tool_calls: list[dict[str, Any]] = []
        response = None
        for _ in range(MAX_TOOL_ROUNDS + 1):
            response = self._create(history)
            history.append({"role": "assistant", "content": [_dump(b) for b in response.content]})
            if response.stop_reason == "tool_use":
                results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    args = block.input if isinstance(block.input, dict) else json.loads(block.input or "{}")
                    out, is_err = tools.run(block.name, args)
                    tool_calls.append({"name": block.name, "args": args, "result": out, "error": is_err})
                    item: dict[str, Any] = {"type": "tool_result", "tool_use_id": block.id, "content": out}
                    if is_err:
                        item["is_error"] = True
                    results.append(item)
                history.append({"role": "user", "content": results})
                continue
            break
        assert response is not None
        text = "".join(getattr(b, "text", "") for b in response.content if b.type == "text").strip()
        if response.stop_reason == "refusal":
            log.warning("model refused turn for lead; handing off")
            tools.run("flag_for_team", {"reason": "other", "summary": "Automated assistant could not continue this conversation."})
            text = "Thanks for reaching out! A member of our team will follow up with you directly."
        elif response.stop_reason == "tool_use":
            # Hit MAX_TOOL_ROUNDS mid-loop. Leave history consistent: drop the dangling assistant turn.
            history.pop()
            text = NO_REPLY
        reply: Optional[str] = None if (not text or text == NO_REPLY) else text
        if reply and reply.startswith(NO_REPLY):
            reply = None
        usage = _dump(response.usage) if getattr(response, "usage", None) else {}
        return BrainResult(reply=reply, messages=history, tool_calls=tool_calls, stop_reason=response.stop_reason or "", usage=usage)
