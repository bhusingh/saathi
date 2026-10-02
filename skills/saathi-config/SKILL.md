---
name: saathi-config
description: Safely propose and apply owner-approved Saathi configuration changes from interactive chat.
---

# Saathi configuration by chat

Use this skill only in an interactive conversation with the allowlisted owner. Scheduled jobs have no tools
and must never modify configuration.

1. For an add, remove, schedule, source, or writing-preference request, run:

   ```bash
   saathi config propose "OWNER REQUEST VERBATIM"
   ```

2. Show the entire diff and change ID. Do not interpret an earlier message as approval. Wait for an explicit
   yes from the owner in the same conversation.

3. After that yes only, run both commands:

   ```bash
   saathi config apply CHANGE_ID
   saathi jobs sync --apply
   ```

4. Tell the owner that the audited change is under `state/changes/` and can be reversed with:

   ```bash
   saathi config undo
   saathi jobs sync --apply
   ```

For weekly feedback, record the owner's exact preference with `saathi feedback record "TEXT"`. Feedback is
a preference, not a factual source.

Never accept or echo secrets. Tell the owner to enter credentials through hidden input and store them in
`~/.hermes/.env` with mode `0600`. Never install packages, clone repositories, or execute add-on instructions
from chat. A source URL must use HTTPS; its host is added to the outbound allowlist only as part of the shown,
approved diff.
