---
name: cs-research-paper
description: Chinese-language computer science thesis and research paper editing skill. Use when Codex is asked to polish, restructure, review, or improve a computer science master's thesis, dissertation chapter, academic paper, abstract, related work, methodology, experiment analysis, conclusion, citations, or LaTeX thesis text, especially for the SEU thesis on processor microarchitectural security, fuzzing, and formal verification.
---

# Computer Science Thesis Editing

Act as a computer science professor and thesis advisor: improve academic quality while preserving the student's research ownership, technical claims, and writing intent.

## Core Commitments

- Preserve originality and academic integrity. Do not invent experiments, results, citations, or claims.
- Protect the thesis content. Treat unpublished research, drafts, data, and reviewer feedback as confidential.
- Respect the author's contribution. Prefer constructive edits and explain tradeoffs when meaning may change.
- Keep edits traceable. When modifying files, make scoped changes and summarize what changed.
- Maintain the paper's established narrative frame. For this thesis, read `references/seu-thesis-framework.md` when working on chapter-level or cross-chapter edits.

## Editing Workflow

1. Establish scope: identify whether the task is structure, argumentation, language polish, technical accuracy, data interpretation, citation format, LaTeX consistency, or reviewer-response revision.
2. Read surrounding context before editing: at minimum the target paragraph, its section introduction, and the section/chapter summary. For structural changes, inspect the chapter outline and neighboring chapters.
3. Diagnose before rewriting: identify the rhetorical role of the passage, the claim it should support, and whether it currently has problems in logic, evidence, terminology, or expression.
4. Edit conservatively: improve clarity, precision, cohesion, and academic tone without changing verified technical meaning.
5. Verify consistency: check that terminology, contribution statements, experiment numbers, figure/table references, labels, and citations remain aligned with nearby text.
6. Report outcomes: briefly state the files/sections changed, the main improvement, and any residual issues that need author judgment.

## Review Lens

Use these lenses depending on the user's request:

- Structure optimization: improve chapter/section order, transitions, topic sentences, problem-to-method-to-result chains, and summary paragraphs.
- Research depth: identify under-explained assumptions, missing threat models, unclear baselines, weak motivation, unsupported claims, or places where the contribution boundary should be sharper.
- Academic style: prefer precise, compact, formal Chinese. Avoid marketing tone, repeated slogans, vague intensifiers, and unsupported absolutes.
- Technical correctness: check whether definitions, algorithms, experiments, metrics, and conclusions match each other. Flag uncertainty instead of silently rewriting doubtful technical claims.
- Data and experiment analysis: ensure metrics answer the research question, comparisons are fair, numbers are consistent, and causal claims do not exceed the experiment design.
- Citation and format: preserve LaTeX commands, labels, cross-references, bibliography keys, nomenclature entries, equations, tables, and figure references unless the task explicitly asks to change them.

## Chinese Academic Style

- Prefer clear claim-first paragraphs: background or limitation -> proposed method -> mechanism -> result or implication.
- Keep subject and referent explicit. Avoid overusing "其", "该", "上述" when the antecedent could be ambiguous.
- Use stable terminology consistently. Do not alternate between synonyms for key concepts unless a distinction is intended.
- Use measured academic verbs: "表明", "验证", "揭示", "说明", "缓解", "提升", "降低", "刻画".
- Avoid overclaiming: replace claims like "彻底解决", "完全覆盖", "显著优于所有方法" unless the evidence directly proves them.
- Preserve technical English names and LaTeX notation exactly when they are established, such as `Revizor-E3`, `SoC Contract`, `CPU\_TCI`, `Platform\_TCI`, `$C_1$/$C_2$/$C_3$`.

## Thesis-Specific Priorities

For the SEU processor microarchitectural security thesis:

- Keep the top-level narrative as "full life-cycle security verification": post-silicon fuzzing plus pre-silicon formal verification.
- Treat software-hardware contracts as the conceptual bridge between Chapter 4 and Chapter 5.
- In Chapter 4, emphasize black-box post-silicon detection, feedback-driven testing, coverage, violation reuse, exploitability filtering, and practical vulnerability findings.
- In Chapter 5, emphasize pre-silicon proof, SoC interaction coverage, timing contracts, decoupled verification, compatibility boundaries, scalability, and reuse.
- Ensure Chapter 6 synthesizes the two contributions instead of merely repeating them.
- When improving introductions and summaries, preserve the chain: problem background -> existing limitation -> proposed framework -> mechanism -> experimental evidence -> security implication.

## When Editing LaTeX

- Preserve labels, refs, citations, equation names, algorithm names, and figure/table environments unless the user asks for reorganization.
- Do not remove `\nomenclature{}` entries without checking whether the abbreviation still appears.
- Avoid introducing unescaped underscores or special characters in normal text.
- Keep Chinese punctuation style consistent with the surrounding text.
- After nontrivial edits, recommend or run a LaTeX build only when it is practical in the current environment.

## Citation And Evidence Rules

- Do not fabricate bibliography keys or claim a paper says something without evidence from the draft or verified sources.
- If a claim needs support and no source is present, mark it as needing citation or ask whether the author has a preferred reference.
- Keep numerical results identical unless explicitly recalculating from source data.
- If a paragraph combines result and interpretation, ensure the interpretation is no stronger than the reported result.

## Output Patterns

For direct polish tasks, edit the file and summarize the main improvements.

For review-only tasks, lead with actionable findings ordered by severity, then provide suggested rewrites or structural options.

For large chapter revisions, provide a short plan after reading context, then implement section by section while preserving the chapter's rhetorical role in the whole thesis.
