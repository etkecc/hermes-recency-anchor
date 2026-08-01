# Silence doesn't look like a crash.

It looks like a model that forgot who it was two messages ago. This plugin is the two fingers under its chin: I said what I said, say it again.

```yaml
  entries:
    recency-anchor:
      text: |
        Whatever you need restated. Keep it short, you rent it every turn.
```

Put that in the `plugins:` block in your `config.yaml`.

Do not paste a fresh `plugins:` line above it. That block is already there, and overwriting it un-enables the plugin you just installed.

Then run `/anchor` in any chat. It names the channel, says whether the anchor fired, and names the rule that decided. It exists because this thing fails by doing nothing at all, and nothing is a nightmare to debug.
