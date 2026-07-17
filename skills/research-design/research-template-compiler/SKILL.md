---
name: research-template-compiler
description: Compile an open-ended research question into a declarative fill-in-the-blank slot graph, dispatch isolated agents to complete bounded keywords and artifacts, verify proposals independently, and synthesize only linked evidence into a complete research packet. Use when multi-agent research explicitly needs isolated task interfaces, resumable DAG execution, controlled graph expansion, or domain-precise terminology for architecture or microarchitecture studies. Triggers include "研究完形模板", "模板化研究", "让 Agent 补全研究", "隔离研究子任务", "研究术语规范化", "research template compiler", "cloze research", and "compile research tasks".
---

# Research Template Compiler

Turn a broad research request into a typed slot graph. Fix scope, safety, evidence, interfaces, and acceptance criteria; leave hypotheses, alternatives, methods, and interpretations as bounded blanks that agents complete independently.

Do not use executable Mako, Jinja, Python expressions, or arbitrary template evaluation. Use the bundled JSON DSL and standard-library compiler.

## Load Resources

- Read [references/slot-language.md](references/slot-language.md) before creating or modifying a template.
- Read [references/task-isolation-and-linking.md](references/task-isolation-and-linking.md) before dispatching slot workers or changing graph edges.
- Read [references/compilation-and-synthesis.md](references/compilation-and-synthesis.md) before verification, graph expansion, recovery, or synthesis.
- Read [references/terminology-and-semantic-fidelity.md](references/terminology-and-semantic-fidelity.md) before rewriting task prompts or rendering a report with a terminology profile.
- Copy templates from `assets/templates/`; never edit bundled templates during a run.

## Core Invariants

1. Treat the template as an interface, not an answer.
2. Keep authorization, prohibited actions, data handling, and release rules in locked context. Agents cannot override them.
3. Give each worker one slot contract and only the named input artifacts.
4. Link tasks through immutable `SLOT_ID.output_name` references, never through hidden conversation or direct agent handoff.
5. Require each generative slot to expose alternatives, unknowns, and falsification conditions when applicable.
6. A worker may propose a new slot but cannot add it to the graph. The manager reviews scope, composition risk, ownership, and dependencies, then recompiles a new template revision.
7. Discovery, verification, and synthesis are separate roles. Agreement between agents is not verification.
8. Preserve unresolved, blocked, rejected, and inconclusive slots. The synthesizer cannot guess missing values.
9. Do not request or expose private chain-of-thought. Require inspectable artifacts: filled keywords, claims, evidence locators, alternatives, decisions, and limitations.
10. Use domain terminology to improve precision while preserving canonical authorization, protected-state, information-flow, restricted-action, and `policy_blocked` semantics in auditable artifacts.

## Phase 0: Intake and Locked Context

Collect:

- research question and intended deliverable;
- authorized assets, sources, environments, and actions;
- prohibited actions and sensitive-data rules;
- available evidence and known facts;
- resource, time, and tool constraints;
- completion and release criteria.
- one supported `terminology_profile`; use it only for display language, never to change authorization or task meaning.

Choose the smallest template. Use `base-research.json` for general research and `microarchitecture-security.json` for processor, RTL, simulator, ISA, transient-execution, or side-channel research.

Populate `locked_context` and all `human` slots in an inputs file. If a required human slot is missing, compile the run as `needs_input`; do not assign it to an agent.

## Phase 1: Define the Cloze Graph

Represent each independent research obligation as one slot:

- `human` — supplied by the user;
- `evidence` — extracted from a named source;
- `generative` — proposes bounded alternatives or hypotheses;
- `derived` — transforms completed slot outputs;
- `verification` — independently reviews named upstream slots;
- `synthesis` — composes verified packets;
- `locked` — fixed at compile time and never assigned.

Each slot must declare:

- one objective in `prompt`;
- `depends_on` for scheduling;
- `consumes` references such as `ARCH_MAP.components`;
- `produces` output names;
- `required_keywords`;
- acceptance criteria;
- a candidate limit;
- stop and escalation conditions.

Prefer small semantic links. A downstream task should consume the minimum output it needs, not the entire upstream proposal.

## Phase 2: Compile Deterministically

Create an inputs file from `assets/templates/inputs.example.json`, then run:

```bash
SKILL_DIR="<absolute path to the directory containing this SKILL.md>"
python3 "$SKILL_DIR/scripts/compile_research.py" \
  "$SKILL_DIR/assets/templates/microarchitecture-security.json" \
  --inputs /absolute/path/to/inputs.json \
  --output /absolute/path/to/run
```

The compiler:

- resolves safe, local template inheritance;
- validates IDs, output references, and acyclic dependencies;
- freezes locked context and a template hash;
- marks provided human slots complete;
- creates isolated `tasks/<slot-id>/task.json` contracts;
- turns `consumes` into exact artifact pointers;
- computes runnable waves and task links;
- blocks synthesis behind verification.

Review `run-state.json` before dispatch. Do not manually reorder waves without recompiling.

## Phase 3: Dispatch Isolated Slot Workers

For each runnable task, materialize its declared input projections:

```bash
SKILL_DIR="<absolute path to the directory containing this SKILL.md>"
python3 "$SKILL_DIR/scripts/prepare_task_inputs.py" \
  /absolute/path/to/run HYPOTHESES
```

Start a fresh worker for each runnable non-human slot. Provide only:

- its `task.json`;
- locked context;
- its materialized `inbox/<slot-id>/` projections;
- the proposal template;
- its assigned output directory.

Require the worker to write `slots/<slot-id>/proposal.json` with:

- every required keyword;
- every declared output;
- candidate claims and evidence IDs;
- alternatives and unknowns;
- proposed new slots, if necessary;
- one lifecycle status.

Workers may render prose using the locked terminology profile. They must preserve canonical concepts in structured fields and include a term note when a preferred display term could be mistaken for a weaker concept.

Workers cannot read sibling task directories unless those paths appear in their input contract. Run them in a sandbox or worktree that exposes only the listed files when the runtime supports filesystem isolation. They cannot edit `run-state.json`, templates, graph edges, or other slots.

Parallelize tasks only when they are in the same compiled wave and do not share an exclusive resource or mutable path.

## Phase 4: Validate and Expand

Refresh lifecycle state from immutable proposals, then validate partial or complete artifacts:

```bash
SKILL_DIR="<absolute path to the directory containing this SKILL.md>"
python3 "$SKILL_DIR/scripts/validate_run.py" /absolute/path/to/run --refresh
```

The refresh step recomputes runnable dependencies and task statuses from saved proposals; it does not infer missing content. Return malformed proposals to their owner. Do not synthesize around a missing keyword or undeclared output.

If a proposal contains `new_slot_proposals`:

1. inspect why the existing template is insufficient;
2. reject duplicates or scope expansion;
3. define the new slot contract and links;
4. rerun authorization and composition-risk review;
5. create a new template revision;
6. recompile without deleting completed compatible artifacts.

This escape path preserves autonomy without allowing workers to mutate the orchestration contract.

Pass the explicit revision when compiling the approved child template:

```bash
python3 "$SKILL_DIR/scripts/compile_research.py" \
  /absolute/path/to/revised-template.json \
  --revision 2 \
  --inputs /absolute/path/to/inputs.json \
  --output /absolute/path/to/run-r2
```

Do not copy proposals blindly. Preserve a prior proposal only when its complete slot contract, locked context, named inputs, and source hashes are unchanged; record the old proposal hash in the revision decision log. Re-run the changed slot and every downstream consumer.

## Phase 5: Verify

Assign verification slots to fresh agents. Resolve each declared `#outputs/<name>` pointer and give only those output projections plus named source artifacts. Do not give the verifier the full originating proposal, confidence field, preferred verdict, or sibling conversation.

Require verification output to name:

- reviewed slot IDs;
- supported, contradicted, and unresolved claims;
- evidence and counter-evidence;
- invalid assumptions or confounders;
- verdicts and limitations.

A verification agent cannot review its own slot. A `synthesis` slot may become runnable only after its verification dependencies have terminal proposals.

## Phase 6: Synthesize

Give a fresh synthesis agent:

- locked context;
- verified packets;
- blocked and inconclusive records;
- accepted graph-expansion decisions;
- the final template.

Require it to:

- resolve placeholders only from declared outputs;
- preserve claim-to-evidence links;
- distinguish facts, proposals, inferences, and verdicts;
- disclose rejected paths and remaining blanks;
- avoid reconstructing missing operational detail;
- include the terminology profile and canonical-to-display glossary used;
- include the final slot-coverage table.

Output `final/research-report.md` and `final/slot-coverage.json`.

## Failure and Recovery

| Trigger | Response |
|---|---|
| Missing human value | Mark `needs_input`; pause only dependent slots |
| Tool or worker failure | Retry the identical slot contract within its attempt budget |
| Insufficient evidence | Keep the proposal `inconclusive` or create a bounded evidence slot |
| Contradictory proposals | Add a fresh verification slot; do not vote by majority |
| Template does not fit | Propose a new slot or child template; manager must approve and recompile |
| Safety or policy refusal | Mark `policy_blocked`; never rephrase, split, or reroute the same objective |
| Context loss | Resume from run state and proposal artifacts, not chat history |
| Synthesis dependency missing | Keep synthesis blocked and report exact missing slots |

Keep recovery transitions in `run-state.json` and audit artifacts. Do not append generic
user-facing recovery boilerplate to otherwise usable results. If continuation genuinely requires
user action, state only the specific missing scope, artifact, or authorization decision.

## Anti-Patterns

Do not:

- use blank slots for authorization, policy, or prohibited actions;
- let a broad slot such as `RESEARCH_EVERYTHING` replace decomposition;
- expose all upstream outputs to every worker;
- treat keyword completion as factual correctness;
- accept a proposal without alternatives or unknowns when the slot requires them;
- let workers create hidden dependencies through prose;
- permit direct worker-to-worker handoff;
- let a verifier review its own work;
- let synthesis fill unresolved blanks from intuition;
- silently change a template after work begins;
- execute arbitrary code embedded in a template;

## Run Layout

```text
<run-dir>/
├── run-state.json
├── resolved-template.json
├── tasks/
│   └── HYPOTHESES/
│       └── task.json
├── slots/
│   └── HYPOTHESES/
│       └── proposal.json
├── graph-expansion-proposals.json
└── final/
    ├── research-report.md
    └── slot-coverage.json
```
