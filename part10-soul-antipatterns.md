# Part 10: SOUL.md Anti-Patterns (Write a Personality, Not a Corporate Memo)

*SOUL.md is your agent's personality. Most people write terrible ones.*

---

## What SOUL.md Does

SOUL.md is injected into every message as part of the system prompt. It defines how your agent speaks, thinks, and behaves. A good SOUL.md makes the agent useful. A bad one makes it annoying.

## The Anti-Patterns

### 1. Corporate Drone

```markdown
## Personality
- Be helpful and professional
- Always be polite and courteous  
- Respond in a clear and organized manner
- Use proper grammar and formatting
- Be respectful at all times
```

**Result:** Agent sounds like a support chatbot. Every response starts with "Great question!" or "I'd be happy to help!" — useless filler.

### 2. Sycophant

```markdown
## Personality
- Always agree with the user
- Validate their ideas enthusiastically
- Never criticize or push back
- Be encouraging and positive
```

**Result:** Agent agrees with everything, even wrong things. No critical thinking. Dangerous for technical work.

### 3. Try-Hard

```markdown
## Personality
- Use humor in every response
- Make pop culture references
- Be quirky and unique
- Use emojis extensively 🚀🔥💯
```

**Result:** Agent is more focused on being entertaining than being useful. Humor that doesn't land is worse than no humor.

### 4. Wall of Rules

```markdown
## Rules
1. Always check memory before responding
2. Never use markdown headers
3. Always format code with triple backticks
4. Use exactly 2 blank lines between sections
5. Never start a sentence with "The"
6. Always end with a summary
7. ... (40 more rules)
```

**Result:** Agent spends context on rules instead of the actual task. More rules = less useful.

## What Works

```markdown
## Vibe
- Be direct. Say the thing. Skip the throat-clearing.
- Have opinions. If one option is better, say it's better.
- Brevity is mandatory. If one sentence does the job, stop at one sentence.
- Humor is welcome when it lands naturally. Dry wit beats forced jokes.
- Call things out when they're dumb, risky, sloppy, or cope.

## Anti-Patterns
- Don't sound like HR, support chat, or a LinkedIn post.
- Don't hedge with "it depends" when you already know the right take.
- Don't repeat the user's point back at them unless it adds something.
- Don't flood simple answers with paragraphs.
- Don't flatter nonsense. If it's wrong, say it's wrong.
```

**Why this works:** Short, opinionated, specific. Defines what TO do and what NOT to do. Sets a tone without over-specifying behavior.

## The Formula

Good SOUL.md has three parts:

1. **Vibe** — 3-5 bullet points on how the agent should sound
2. **Anti-Patterns** — 3-5 things the agent should never do
3. **Identity** (optional) — who the agent is, what it cares about

That's it. Don't overthink it.

## Examples From Production

**Technical assistant:**
```markdown
## Vibe
- Lead with the answer, then explain if needed.
- If something is wrong, say so immediately.
- Code examples beat paragraphs of explanation.
- One correct answer > three hedged options.
```

**Creative collaborator:**
```markdown
## Vibe
- Push back on bad ideas — don't let me waste time.
- Suggest alternatives, don't just execute blindly.
- First drafts are starting points, not finished work.
```

**Personal assistant:**
```markdown
## Vibe
- Be concise. I have ADHD — if it's long, I won't read it.
- Action items first, context second.
- If I'm overthinking something, say so.
```

## How to Debug a Bad SOUL.md

If your agent is annoying:

1. **Read your last 10 conversations.** Where does the agent waste words?
2. **Find the pattern.** Does it always start with "Great question!"? Does it hedge everything?
3. **Add it to Anti-Patterns.** Be specific: "Never open with 'Great question', 'I'd be happy to help', or 'Absolutely'"
4. **Test.** Ask the same question again. If it still does the thing, the rule isn't strong enough.

## Common Fixes

| Problem | SOUL.md Fix |
|---------|-------------|
| Opens every response with filler | "Never open with Great question, I'd be happy to help, Absolutely, or Of course" |
| Hedges everything | "Don't hedge with 'it depends' when you already know the right take" |
| Too verbose | "Brevity is mandatory. If one sentence does the job, stop at one sentence" |
| Repeats what I said | "Don't repeat the user's point back at them unless it adds something" |
| Agrees with everything | "Don't flatter nonsense. If it's wrong, say it's wrong" |

---

*A good SOUL.md is the difference between an agent you tolerate and an agent you trust.*
