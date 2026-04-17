---
name: meeting-prep
description: Prepare a 1-page brief for an upcoming meeting by combining calendar context, recent threads with attendees, and relevant docs
when_to_use:
  - User invokes /meeting-prep for <time or person>
  - Scheduled 15 minutes before every calendar event with `prep:true` tag
toolsets:
  - email
  - slack
  - classify
  - memory
parameters:
  lookup:
    type: string
    description: "'next' | meeting title | attendee name | calendar event id"
    default: "next"
security:
  trust: trusted
  notes: |
    Reads your calendar + email + Slack + memory. Does not write. Never
    forwards any of the prep content outside your approved channels.
model_hint: google/gemini-2.5-flash
---

# meeting-prep — Pre-Meeting Brief

Produces a one-page markdown brief so you walk into meetings knowing what's going on.

## Output shape

```markdown
## Meeting: {title}
**When:** {datetime} · **Duration:** {duration} · **Where:** {location}
**Attendees:** {list with titles where known}

### Context
- Last topic we discussed: {summary}
- Open asks from them: {list}
- Open asks from me: {list}

### Likely agenda
1. {item}
2. {item}

### My position / notes
{bulleted; pulled from memory if relevant}

### Warnings
- {anything they sent recently that suggests a tough topic}

### Quick links
- [last email thread]({url})
- [shared doc]({url})
- [previous meeting notes]({memory-link})
```

## Procedure

1. **Resolve meeting** from `lookup:`:
   - "next" → next calendar event in personal calendar
   - a time → nearest event at that time
   - a person → next event where that person is an attendee
   - event id → that exact event

2. **Gather** (parallel):
   - Last 10 emails with each attendee (last 90 days)
   - Last Slack DMs / channel mentions with each attendee (last 30 days)
   - Relevant docs from memory (`/search` with meeting title + attendee names)
   - Previous meeting notes if exist in memory

3. **Summarize** each thread to 1–2 lines. Extract open asks (things needing response, either direction).

4. **Produce** the brief. Keep under 400 words. Bias for brevity — this is a read-in-60-seconds doc.

5. **Attach** the brief as a Telegram DM reply to the trigger event, or print to CLI if invoked there.

## Triggering 15 min before each meeting

```yaml
cron:
  - name: meeting-prep
    schedule: "*/5 * * * *"   # every 5 min, idempotent
    task: "/meeting-prep next"
    filter: "event_starts_within=15m AND event.metadata.prep=true"
    notify: telegram_dm
```

## Tips

- Route to Gemini Flash — you'll run this often and it's a long-context summarization task.
- If your calendar is Google → use the Google Workspace MCP; if Outlook → Microsoft Graph MCP.
- Tag your calendar events with `prep:true` (or similar) to opt in — don't default-on for privacy.

## Related

- [daily-inbox-triage](../../ops/daily-inbox-triage/SKILL.md) — morning briefing
- [hermes-weekly](../../ops/hermes-weekly/SKILL.md) — Friday digest
