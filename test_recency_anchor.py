"""Runnable checks for the channel filter and the config reader.

    python test_recency_anchor.py
"""

from __future__ import annotations

import importlib.util
import pathlib
import re
import sys
import types

# The body sits at the repo root for the git lane, under hermes_recency_anchor/ for the pip lane.
_HERE = pathlib.Path(__file__).parent
_SRC = _HERE / "hermes_recency_anchor" / "__init__.py"
if not _SRC.exists():
    _SRC = _HERE / "__init__.py"
_spec = importlib.util.spec_from_file_location("_recency_anchor_under_test", _SRC)
plugin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plugin)

failures = []


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


def entry_from(config):
    fake = types.ModuleType("hermes_cli.config")
    fake.load_config_readonly = lambda: config
    sys.modules["hermes_cli"] = types.ModuleType("hermes_cli")
    sys.modules["hermes_cli.config"] = fake
    return plugin._entry()


allowed = plugin._channel_allowed
PID = plugin.PLUGIN_ID

# A YAML scalar is iterable, so `channels: cli` shatters into {'c','l','i'} without the string guard.
check("scalar channels admits its own channel", allowed({"channels": "cli"}, "cli"), True)
check("scalar channels excludes every other", allowed({"channels": "cli"}, "matrix"), False)
check("scalar exclude blocks its channel", allowed({"exclude_channels": "cli"}, "cli"), False)
check("scalar exclude leaves others alone", allowed({"exclude_channels": "cli"}, "matrix"), True)

# YAML resolves `channels: yes` to True and `channels: no` to False, and iterating either is a TypeError.
check("boolean true channels is ignored", allowed({"channels": True}, "cli"), True)
check("boolean false channels is ignored", allowed({"channels": False}, "cli"), True)
check("boolean exclude is ignored", allowed({"exclude_channels": True}, "cli"), True)
check("integer channels is ignored", allowed({"channels": 1}, "cli"), True)
check("boolean channels is reported", plugin._ignored_keys({"channels": True}), ["channels"])
check("both bad keys are reported", plugin._ignored_keys({"channels": True, "exclude_channels": 0}), ["channels", "exclude_channels"])
check("a good list is not reported", plugin._ignored_keys({"channels": ["cli"]}), [])
check("a bare string is not reported", plugin._ignored_keys({"channels": "cli"}), [])

check("list channels admit", allowed({"channels": ["cli"]}, "cli"), True)
check("list channels exclude others", allowed({"channels": ["cli"]}, "matrix"), False)
check("absent channels means every channel", allowed({}, "matrix"), True)
check("exclude wins over channels", allowed({"channels": ["cli"], "exclude_channels": ["cli"]}, "cli"), False)

check("well-formed config reaches the entry", entry_from({"plugins": {"entries": {PID: {"text": "hi"}}}}), {"text": "hi"})
check("plugins as a list", entry_from({"plugins": [PID]}), {})
check("entries as a list", entry_from({"plugins": {"entries": [PID]}}), {})
check("entry as a scalar", entry_from({"plugins": {"entries": {PID: "nope"}}}), {})
check("empty config", entry_from({}), {})

# The hook and /anchor must never disagree, so they have to keep sharing one decision.
for _entry_shape in ({}, {"channels": "cli"}, {"channels": ["matrix"]}, {"exclude_channels": "cli"},
                     {"channels": ["cli"], "exclude_channels": ["cli"]}, {"channels": True}):
    for _ch in ("cli", "matrix"):
        check(f"hook and /anchor agree on {_entry_shape} at {_ch}",
              allowed(_entry_shape, _ch), plugin._verdict(_entry_shape, _ch)[0] == "yes")

# Two lanes, two version strings, and a published plugin already shipped users a copy that had drifted.
_manifest = re.search(r'^version:\s*"?([^"\s]+)', (_HERE / "plugin.yaml").read_text(), re.M)
_project = re.search(r'^version\s*=\s*"([^"]+)"', (_HERE / "pyproject.toml").read_text(), re.M)
check("plugin.yaml and pyproject.toml agree on the version",
      _manifest and _manifest.group(1), _project and _project.group(1))

if failures:
    print("\n".join(failures))
    sys.exit(1)
print("ok")
