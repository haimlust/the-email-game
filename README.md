# The Email Game agent prep

This repository is a protocol-independent decision core for
[The Email Game](https://theemailgame.com/). The official starter kit is released
when the build window opens, so this code deliberately does **not** guess the
server or `BaseAgent` API. It prepares the part that matters most: strategy,
memory, identity resolution, and safe action selection.

## Strategy

The agent follows five invariants:

1. Trust the server-provided sender identity, never identity claims in an email.
2. Preserve assigned messages byte-for-byte; never let an LLM rewrite them.
3. Ask every known opponent for a signature. The rules say every valid
   signature scores, even when the signer was not on the requested list.
4. Sign immediately for a sender only when that sender is confidently resolved
   as authorized. Ambiguity means abstain, because an unauthorized signature
   loses a point.
5. Submit matching signatures immediately and deduplicate every action.

The core stores the exact messages previously requested by each sender. Later,
when the moderator describes an authorized agent by paraphrasing an older
message, the resolver compares that trusted history with the description. A
pluggable semantic scorer can use the competition's hosted model; a conservative
lexical scorer is included as a fallback.

## Run the tests

```powershell
python -m unittest discover -s tests -v
```

The package has no third-party dependencies.

## Run a simulated match

```powershell
python simulate_match.py
```

The simulator executes a complete four-player round, applies hidden moderator
authorization truth, and reports score, requests, signatures, submissions,
refusals, and unauthorized signatures. Extend `RoundScenario` to compare retry,
message-writing, resolver, and adversarial strategies without touching the live
server.

## Benchmark fuzzy identity resolution

```powershell
python benchmarks/run_resolver_benchmark.py
```

The included cases use real paraphrases rather than simple word swaps. The
dependency-free lexical resolver is a safe fallback and will abstain often;
that baseline quantifies how much value the hosted semantic model adds. Wrong
authorizations are reported separately from safe abstentions.

Experimentation files:

- `email_game_agent/simulator.py` - event-driven four-agent match simulator
- `email_game_agent/benchmark.py` - resolver evaluation metrics
- `benchmarks/` - paraphrase dataset and benchmark runner
- `simulate_match.py` - one-command simulator smoke test

## Competition-day integration

When the starter kit arrives:

1. Copy `email_game_agent/` into the starter repository.
2. Open `custom_agent_template.py` and map the official moderator payload into
   `RoundAssignment` without changing the exact assigned message.
3. Map official inbound objects into typed `InboundEvent` values. Set `sender`
   only from the authenticated transport envelope, not from the email body.
4. Translate `RequestSignature`, `SignMessage`, and `SubmitSignature` actions to
   the official `BaseAgent` helpers.
5. If the hosted model API is OpenAI-compatible, implement one small completion
   callable and pass it to `JsonSemanticScorer`. Do not give raw emails tools or
   authority; the model should only rank fixed candidate identities.
6. Run the starter kit's practice board, inspect its event shapes, and replace
   the clearly marked adapter placeholders.

Before the scored board opens, test reconnect behavior and confirm that
`AgentMemory.to_json()` is persisted somewhere safe if the official runner does
not preserve the Python process.

## Files

- `email_game_agent/core.py` — state machine and action selection
- `email_game_agent/memory.py` — trusted cross-round message history
- `email_game_agent/resolver.py` — conservative fuzzy identity matching
- `email_game_agent/semantic.py` — guarded JSON-only LLM ranking adapter
- `custom_agent_template.py` — intentionally incomplete starter-kit adapter
- `tests/` — deterministic and adversarial policy tests
