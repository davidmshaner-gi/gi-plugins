---
name: suggest-a-build
description: Tell Grounded Intelligence about a piece of your work that still eats time, so it gets considered for what we build next. Use when someone says "this is still painful", "can GI build something for this", "I wish this were automated", "suggest a build", or describes a repetitive task they are tired of doing by hand.
---

# Suggest a Build

Capture one painful process well enough that GI can scope it without another
meeting. Four questions, then a message they send.

## Step 1 — Load the context pack

Read `context/pack.yaml` from the company's private skill library, plus the
process maps it lists. Match the user to a leader in the pack.

If the pack is missing, still run the interview. Ask the user their name, role,
and division instead, and send to `foundations@groundedintelligence.io`.

## Step 2 — Check whether it is already mapped

Search the process maps for the work they are describing. If it is already
mapped, say so and ask whether this is the same pain or a different part of it.
A mapped process that still hurts is a stronger signal than a new one, and GI
needs to know which it is.

## Step 3 — Ask exactly these four, one at a time

1. What is the work? Ask them to describe it the way they would to a new hire.
2. How often, and how long does it take each time?
3. What makes it slow — the looking-up, the waiting on someone, the retyping,
   the judgment call?
4. What would good look like? What would you rather be doing with that time?

Do not add questions. Do not turn this into a process mapping session; that is
a different skill and a different hour.

## Step 4 — Play it back

Summarize in five sentences or fewer and ask them to correct it. Their
correction is the version that goes to GI.

## Step 5 — Draft the message

Produce a message with:

- **To:** the `gi_email` from the pack
- **Subject:** `[Foundations] <company> idea: <short name for the work>`
- **Body:** their name, role, and division, then the corrected summary, then the
  frequency and time figures as their own line

Tell them to send it from their own mail. Do not claim it has been sent.

## Rules

- If they cannot give a time figure, record that it is unknown. Never estimate
  one for them. Made-up hours poison the roadmap.
- Never promise that GI will build it. This feeds a prioritized roadmap; it is
  not an order form.
- Never name another Grounded Intelligence client.
