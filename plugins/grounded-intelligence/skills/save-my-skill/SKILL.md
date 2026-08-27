---
name: save-my-skill
description: Send a workflow you built or changed to Grounded Intelligence so it goes in your company library and your whole team gets it. Use when someone says "save this", "share this with my team", "add this to the library", "save my skill", or has just finished making a workflow work.
---

# Save My Skill

A skill that lives only on one person's machine dies with their laptop. This
puts it in the company library, where GI keeps it working and the rest of the
team gets it automatically.

## Step 1 — Load the context pack

Read `context/pack.yaml` from the company's private skill library and match the
user to a leader in it. If the pack is missing, ask their name, role, and
division, and send to `foundations@groundedintelligence.io`.

## Step 2 — Find the skill and check it

Locate the skill directory. Before packaging, confirm all of the following, and
fix anything that fails with the user rather than sending it broken:

- `SKILL.md` exists
- Its frontmatter `name` matches the directory name exactly
- Its frontmatter `description` is at least 40 characters and describes the want
  in the words someone would actually say

## Step 3 — Ask what it is for

One question: what does this do, and who else on your team would use it? Their
answer goes in the message. GI needs it to decide whether this belongs to one
division or the whole company.

## Step 4 — Check it for anything that should not travel

Read every file. Flag and remove before sending:

- Passwords, tokens, or keys of any kind
- Named individuals outside the company, especially clients or tenants
- Anything the user says is confidential when you show it to them

Show them what you found and confirm the removal. When in doubt, ask.

## Step 5 — Draft the message

Produce a message with:

- **To:** the `gi_email` from the pack
- **Subject:** `[Foundations] <company> skill: <skill name>`
- **Body:** their name, role, and division; what the skill does and who else
  would use it; then the full contents of every file, each under a heading
  naming its path

Tell them to send it from their own mail. Do not claim it has been sent.

## Step 6 — Say what happens next

Tell them plainly: GI reviews it, adds it to the company library, and it shows
up for their team on its own. Do not give a date.

## Rules

- Never send a file you have not read.
- Never send a skill that fails the checks in step 2. Fix it first.
- Never claim the skill is in the library. It is in the library when GI has
  added it, not when the message is drafted.
