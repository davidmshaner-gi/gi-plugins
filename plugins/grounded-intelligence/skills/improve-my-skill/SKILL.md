---
name: improve-my-skill
description: Change a workflow so it matches how your division actually runs, or fix one that stopped working right. Start from a ready-made one or from the one you built yourself. Use when someone says "this doesn't quite fit", "it keeps missing a step", "can I change this", "improve my skill", or "make this work for my team".
---

# Improve My Skill

The person doing the work makes the change. You hold the pen, they make the
calls.

## Step 1 — Find the skill they mean

Look in this order and say which one you found:

1. The company skill library plugin, under `skills/`
2. A skill they have in their own environment
3. This plugin's own skills, if they want to start from a ready-made one

If more than one matches, show the names and descriptions and let them pick.

## Step 2 — Read it back before changing anything

Summarize what the skill does today in plain sentences, in their vocabulary,
not the file's. Ask what is wrong with it. Two things are usually true and
worth asking about directly:

- A step that does not match how they actually work
- A step that is missing entirely because it lives in someone's head

## Step 3 — Change one thing at a time

Make the smallest edit that fixes what they named. Show them the changed section
and ask whether that is right. Do not restructure the whole skill because you
think it would be cleaner.

## Step 4 — Keep it valid

Whatever changes, the skill must still have:

- A frontmatter `name` that matches its directory name exactly
- A frontmatter `description` of at least 40 characters, written the way they
  would describe wanting it, including the phrases someone would actually say

If the change makes the description wrong, update the description too. A skill
nobody can find is a skill nobody uses.

## Step 5 — Try it

Run the changed skill on a real piece of their work, in front of them. If it
is wrong, go back to step 3. Do not declare it finished off a reading.

## Step 6 — Offer to save it

When it works, tell them `/save-my-skill` puts it in the company library so
their team gets it too, and offer to run it now.

## Rules

- Never rewrite a skill wholesale without being asked. They own it.
- Never remove a step because it looks redundant. Ask first; redundant-looking
  steps are usually where a past mistake got fixed.
