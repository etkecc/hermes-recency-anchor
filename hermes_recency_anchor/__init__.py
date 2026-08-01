"""recency-anchor: restate your instruction at the end of every user turn.

Message zero loses to message N on a recency-weighted model, and it loses
quietly: no error, no refusal, just an assistant that sounds like every other
one. This staples your block onto the API copy of the user turn instead, which
is the last thing the model reads before it opens its mouth.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

PLUGIN_ID = "recency-anchor"


def _entry() -> Dict[str, Any]:
    """Fish our block out of config.yaml, or hand back an empty one and let the caller go quiet."""
    try:
        from hermes_cli.config import load_config_readonly

        cfg = load_config_readonly() or {}
    except Exception as exc:
        logger.warning("%s: could not load config (%s), staying quiet", PLUGIN_ID, exc)
        return {}
    # Hand-written YAML: every level here can turn up as a list or a bare string, and .get bites on those.
    plugins = cfg.get("plugins")
    entries = plugins.get("entries") if isinstance(plugins, dict) else None
    entry = entries.get(PLUGIN_ID) if isinstance(entries, dict) else None
    return entry if isinstance(entry, dict) else {}


def _session_env(name: str) -> str:
    """Read a session ContextVar, falling back to the process env when no session is in scope."""
    try:
        from gateway.session_context import get_session_env

        value = get_session_env(name, "")
    except Exception:
        value = os.environ.get(name, "")
    return str(value or "").strip()


def _channel(platform: str) -> str:
    """The channel a turn arrived on: session source wins, the platform adapter name is the fallback."""
    return (_session_env("HERMES_SESSION_SOURCE") or platform or "cli").strip().lower()


def _as_set(values: Any) -> set[str]:
    """Channel names as a set. A bare string is one name, and anything unlistlike is no names at all."""
    if not values:
        return set()
    # An unbracketed `channels: cli` is a string, and strings iterate into letters. Matches nothing, says nothing.
    if isinstance(values, str):
        values = [values]
    # `channels: yes` is the boolean True to YAML, and iterating that is a TypeError straight out of the hook.
    if not isinstance(values, (list, tuple, set)):
        return set()
    return {str(v).strip().lower() for v in values}


def _ignored_keys(entry: Dict[str, Any]) -> list[str]:
    """Channel keys we could not read, so /anchor names them instead of shrugging."""
    return [
        key
        for key in ("channels", "exclude_channels")
        if entry.get(key) is not None and not isinstance(entry.get(key), (str, list, tuple, set))
    ]


def _verdict(entry: Dict[str, Any], channel: str) -> tuple[str, str]:
    """The one channel decision and the rule behind it: exclude wins, an absent allow-list means everywhere."""
    if channel in _as_set(entry.get("exclude_channels")):
        return "no", "exclude_channels lists this channel"
    allowed = _as_set(entry.get("channels"))
    if not allowed:
        return "yes", "no channel filter set"
    if channel in allowed:
        return "yes", "channels lists this channel"
    return "no", "this channel is missing from channels"


def _channel_allowed(entry: Dict[str, Any], channel: str) -> bool:
    return _verdict(entry, channel)[0] == "yes"


def _on_pre_llm_call(**kwargs: Any) -> Optional[Dict[str, str]]:
    """The whole plugin. Hand back the anchor, or None and we never happened."""
    entry = _entry()
    channel = _channel(str(kwargs.get("platform") or ""))
    if not _channel_allowed(entry, channel):
        return None
    text = str(entry.get("text") or "").strip()
    if not text:
        return None
    logger.debug("%s: anchoring %d chars on channel %r", PLUGIN_ID, len(text), channel)
    return {"context": text}


_HELP = """recency-anchor: show what the anchor would do on this turn.

  /anchor        the resolved channel, the filter verdict, and the configured text
  /anchor help   this
"""


def _handle_anchor(raw_args: str) -> str:
    """Answer the only question this plugin ever raises: is it firing, and if not, who said no."""
    argv = raw_args.strip().split()
    if argv and argv[0] in {"help", "-h", "--help"}:
        return _HELP
    if argv:
        return "Usage: /anchor [help]"

    entry = _entry()
    source = _session_env("HERMES_SESSION_SOURCE")
    # Same resolver the hook uses, so this command can never drift into reporting a stale rule.
    channel = _channel(_session_env("HERMES_SESSION_PLATFORM"))
    allowed, rule = _verdict(entry, channel)
    text = str(entry.get("text") or "").strip()

    lines = [
        "recency-anchor",
        f"  Channel    : {channel}",
        f"  Allowed    : {allowed}",
        f"  Decided by : {rule}",
    ]
    if text:
        body = text.splitlines()
        span = f" over {len(body)} lines" if len(body) > 1 else ""
        lines.append(f"  Anchor     : {body[0]}")
        lines.append(f"  Length     : {len(text)} characters{span}")
    else:
        lines.append("  Anchor     : nothing set, so the plugin stays quiet")
        lines.append(f"  Fix        : add a text: block under plugins.entries.{PLUGIN_ID} in config.yaml")
    for key in _ignored_keys(entry):
        lines.append(f"  Ignored    : {key} is not a list of channel names, so it had no effect")
    # Only this branch is a guess: the hook falls back to the agent's own platform, which we cannot see.
    if not source:
        lines.append("  Note       : no session source this turn, so the channel above came from")
        lines.append("               HERMES_SESSION_PLATFORM. The hook reads the agent's platform,")
        lines.append("               which can disagree.")
    return "\n".join(lines)


def register(ctx) -> None:
    """Hermes calls this once at load. One hook, one command, then we get out of the way."""
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_command(
        "anchor",
        handler=_handle_anchor,
        description="Show what recency-anchor would do on this turn.",
    )
