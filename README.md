# Message Waiter for AstrBot

This plugin delays AstrBot's default AI response until the user has been silent for a configurable period. If the same user sends several messages during that period, the plugin suppresses the older events and merges all text into the newest event before the normal AstrBot agent runs.

## Behavior

- Default silence window: `2.5` seconds.
- A new message from the same private conversation resets the timer.
- In group chats, buffers are isolated by sender so different users are not merged.
- Commands beginning with `/` or `!` bypass the delay by default.
- Optional semantic checking asks an existing AstrBot provider whether the input is complete and can extend the wait up to the configured maximum.
- Semantic checking is disabled by default because it adds one extra LLM request per turn.

## Installation

Copy this directory into AstrBot's `data/plugins/` directory, then reload or restart AstrBot. Configure the plugin in WebUI under the plugin settings dialog.

## Important limitation

AstrBot message events are independent. This plugin merges the plain-text prompt used by the final event. Media contained in earlier suppressed events is not copied into the final event; send text and media together when media context matters.
