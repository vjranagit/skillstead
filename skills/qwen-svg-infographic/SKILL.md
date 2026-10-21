---
name: qwen-svg-infographic
description: Create a technical process infographic as editable SVG and PNG using Skillstead svg-infographic. Trigger for architecture, lifecycle, flow, or topology one-pagers.
---
# Qwen SVG Infographic
1. Map the topic before writing. Put each subsystem, parallel path, or redundant unit in its own group (1–4 groups, each a row). List each group's parts in flow order (1–4 per group). Do not merge distinct named parts or force a network into one chain.
2. Add a link for each real relationship: flow, branch, fan-out, loop-back, or cross-link between groups. A side unit (backup, bypass, cross-link) connects where it acts, not in series. Add a link `label` saying what moves (material, power, data, signal) or the condition (e.g. "if X fails").
3. Each `detail` gives the part's function: what it acts on → what it does → effect. Check accuracy before rendering: for each part, does it limit, regulate, prioritize, or transfer? For each link, does it move material or only power/signal? The takeaway must not contradict any part or link, and must not make unqualified speed/performance claims.
4. Run `scripts/make.sh <content-file> <out-dir>` from this skill directory. The renderer does all layout, routing and text measurement, and copies your content to `<out-dir>/content.json`. Never write SVG or layout code.
5. If it returns `{"ok":false,"fix":...}`, apply that fix to the content and rerun. Then view the PNG at fit-to-page and close-up. Check that every named topic part is present and every arrow shows a true relationship in the right direction.

| Error | Fix |
|---|---|
| Invalid JSON / missing field | Restore the template keys. |
| Missing Chromium or Pillow | Report it; do not switch renderer. |

Content template: `templates/content.json`.
