# Sample MathMate Conversation

This walks through a realistic multi-turn session, annotated with what's
happening in `session.state` and which tools get called. It illustrates
the "context-aware, multi-turn tutoring" behavior described in the
project summary.

---

**You:** hi, I want to practice algebra

**MathMate:** Hey! I'd love to help. Want to work on linear equations,
quadratics, systems of equations, polynomials, or inequalities? And
should I keep it easy, medium, or hard?

> *State so far:* `current_problem = None` → agent asks for topic/difficulty
> instead of guessing.

**You:** linear equations, medium

*(tool call: `generate_practice_problem("linear_equations", "medium")` →
returns `"2*x + 5 = 3*x - 7"`, resets `current_step`, `hints_used_this_problem`, `attempts_this_problem` to 0)*

**MathMate:** Great choice. Here's your problem:

`2x + 5 = 3x - 7`

What's the first step you'd take to start isolating x?

**You:** subtract 2x from both sides so 5 = x - 7

*(tool call: `check_algebra_step("2*x + 5 = 3*x - 7", "5 = x - 7")` →
`{"valid": true, ...}`; `current_step` increments to 1)*

**MathMate:** Exactly right! Now what do you do with that `-7`?

**You:** add 7 to both sides, so 12 = x

*(tool call: `check_algebra_step("5 = x - 7", "12 = x")` → `{"valid": true}`;
`current_step` → 2)*

**MathMate:** You've got it — `x = 12`. Nice work solving that without
any hints!

*(tool call: `update_mastery("linear_equations", solved_without_hints=True)`
→ mastery for `linear_equations` bumps from `0.0` to `0.15`;
`problems_solved` → 1)*

Want another linear equation problem, maybe a bit harder, or ready to
try a new topic?

**You:** another one, harder

*(tool call: `generate_practice_problem("linear_equations", "hard")`)*

**MathMate:** Here's a tougher one:

`3(2x - 1) + 4 = 5(x + 2) - 3`

Where would you start?

**You:** distribute the 3 and the 5 first... 6x - 3 + 4 = 5x + 7

*(tool call: `check_algebra_step(...)` → invalid: the right-hand side
distribution has an error)*

**MathMate:** Good instinct to distribute first! Double check the right
side — what's `5 × 2` and `5 × 2` (the constant)? Try that distribution
again.

> Notice: instead of just saying "wrong," MathMate asks a guiding
> question. `hints_used_this_problem` increments so the agent can
> escalate specificity if the student is still stuck after a couple more
> tries.

**You:** oh wait, 5(x+2) is 5x + 10, so 6x + 1 = 5x + 17

*(tool call: `check_algebra_step("3*(2*x - 1) + 4 = 5*(x + 2) - 3", "6*x + 1 = 5*x + 17")`
→ `{"valid": true}`)*

**MathMate:** That's it! Keep going from there.

---

## What this demonstrates

- **Multi-turn, context-aware tutoring**: the agent never re-explains or
  re-asks for the topic once it's set in state; it references the
  in-progress problem across turns.
- **Exact verification, not vibes**: every step check is backed by
  sympy symbolic comparison, so feedback is always mathematically
  correct — the LLM decides *how* to phrase it, not *whether* it's right.
- **Adaptive difficulty & mastery tracking**: `mastery` scores persist
  across problems and topics, giving the agent a running signal for what
  the student should practice next.
