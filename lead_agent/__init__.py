"""After-hours / busy-hours lead follow-up agent for GoHighLevel.

Texts (GHL SMS) and calls (Retell voice) new leads, aims to book an inquiry call on a
GHL calendar, and hands off to the team when a human should take over.

Modules:
  config        practice config (agent_config.json) + secrets (env)
  db            SQLite store: conversations, jobs, events, sent messages, settings
  hours         business hours, busy mode, quiet hours, next allowed send time
  ghl           GoHighLevel API client (contacts, SMS, calendar slots, appointments, notes, tags)
  prompts       system prompts for the SMS brain and the voice agent
  brain         Claude-powered SMS conversation engine with booking tools
  voice         Retell voice provider: outbound calls, tool webhooks, post-call processing
  orchestrator  lead lifecycle: cadence, inbound handling, human takeover, stop rules
  scheduler     background job runner
  server        HTTP server (GHL webhooks, Retell webhooks, admin)
  cli           python -m lead_agent serve | setup-voice | simulate | busy | status
"""

__version__ = "0.1.0"
