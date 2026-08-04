# recency-anchor

Your system prompt is message zero. Whatever the user just typed is message N. On a model that leans hard on recency, that is not a fair fight.

This plugin restates your instruction at the end of the user turn, which is the last thing the model reads before it opens its mouth.

## Install

```
hermes plugins install etkecc/hermes-recency-anchor --enable
```

Then give it something to say, because out of the box it has opinions about nothing:

```yaml
plugins:
  enabled:
    - recency-anchor
  entries:
    recency-anchor:
      text: |
        Whatever you need restated. Keep it short and keep it sharp.
```

Edit that text and it lands on the next message. No restart, no reload, no ceremony.

Run `/anchor` in any chat and it tells you the channel it resolved, whether the anchor fired, and which rule decided. That command exists because this plugin's only failure mode is nothing happening, and "nothing happened" is the worst bug report ever filed.

## Update

```
hermes plugins remove recency-anchor
hermes plugins install etkecc/hermes-recency-anchor --enable
```

## The drift it fixes

You notice it as drift, and it is maddening precisely because nothing looks broken. No refusal, no error, no warning in the log. Your instruction is sitting right there in the context, being quietly outvoted by "review this Go function". The model answers the question well and sounds like every other assistant on earth while doing it.

Swapping model versions is where it bites hardest. The new one is a better engineer with nobody home: the old model was sloppy enough to leak character by accident, and discipline here means obeying whoever spoke most recently.

The fix is positional, and slightly humiliating. Appending to the system prompt, which is what every config knob in sight offers you, leaves you sitting at message zero with everybody else.

## The bill

You rent this block every turn. A 200-word anchor over a 50-turn conversation is 10,000 words of rent, so write it like a telegram. It fires once per user turn, so a fifteen-step agentic turn pays once.

Architecturally it is free. The block rides the API copy of the user message, so your cached system prefix stays byte-identical turn over turn and your stored transcript never sees it. Under the hood that is one `pre_llm_call` hook returning `{"context": "..."}`. That is the entire plugin.

## Channels

`channels` is an allow-list, `exclude_channels` is a deny-list, deny wins, and no `channels` at all means everywhere.

```yaml
      exclude_channels: [cli]
```

Reach for that when an entrypoint already injects a block of its own and you would rather not say everything twice.

Both keys match the channel a turn arrived on, which is the session source when one is set and the platform adapter name otherwise. Those two are not always the same string, and the day you find that out will be a great day: a desktop app driving a CLI-platform agent reports `desktop`, so one filter written against adapter names takes out your terminal and your desktop app together, in a single stroke, for free. We wrote that filter. `/anchor` prints the one it actually used.

## What it will not fix

A model that refuses. This moves where your instruction sits. Willingness gets decided somewhere this plugin cannot reach, so aim it at a hard guardrail and all you get is a refusal that arrives more recently.

A vague instruction, either. More weight on your words is good news only when the words are good.

Both lanes register as `recency-anchor` and read the same config block.

## Licence

LGPL-3.0. That is etke.cc house policy, and yes, we are aware of what the rest of the shelf is licensed as.

---

Tested against Hermes Agent v0.20.0 (2026-08-04).
