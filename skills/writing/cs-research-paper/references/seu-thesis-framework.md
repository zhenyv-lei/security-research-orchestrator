# SEU Thesis Narrative Framework

Use this reference when editing the thesis at `/Users/ovo/opt/seu-master-thesis`.

## Core Thesis

The thesis studies processor microarchitectural security verification across the processor life cycle. It has two complementary research routes:

1. Post-silicon vulnerability detection through feedback-driven black-box fuzzing.
2. Pre-silicon security proof through timing-contract-based decoupled formal verification.

The two routes are not separate projects. Together they form a full life-cycle security verification framework: fuzzing finds practical vulnerabilities in deployed processors, while formal verification proves security properties during design.

## Chapter Roles

- Chapter 1: Establish the research background and life-cycle framing. It should motivate why processors are the trusted computing base, why microarchitectural side channels matter, and why fuzzing and formal verification correspond to different development stages.
- Chapter 2: Establish the research gap. It should show that microarchitectural vulnerabilities extend from processor-core resources to SoC platform interactions, then review fuzzing and formal verification as two complementary methods.
- Chapter 3: Provide the shared theoretical foundation. Software-hardware contracts, contract traces, hardware traces, and constant-time contracts are the bridge that makes Chapter 4 and Chapter 5 part of one framework.
- Chapter 4: Present Revizor-E3 for post-silicon black-box fuzzing. The chapter's logic is: Revizor is open-loop -> input generation, violation reuse, and exploitability evaluation are weak -> Revizor-E3 adds Explore, Exploit, Evaluate -> experiments show better coverage, more useful violations, lower false positives, and new timing leaks.
- Chapter 5: Present SoC Contract for pre-silicon formal verification. The chapter's logic is: existing formal verification focuses on processor cores -> SoC platform timing leaks are missed -> full composition is impractical -> timing contracts and TCI enable decoupled CPU/platform verification -> experiments show equivalent detection, better scalability, reuse, and precise compatibility diagnosis.
- Chapter 6: Synthesize the two contributions as dynamic detection plus static proof. The conclusion should not read like two disconnected summaries.

## Persistent Terminology

- Processor microarchitectural security: 处理器微架构安全性
- Post-silicon: 硅后阶段
- Pre-silicon: 硅前阶段
- Fuzzing: 模糊测试
- Formal verification: 形式化验证
- Software-hardware security contract: 软件硬件安全合约
- Constant-time contract: 常数时间合约
- Model-based relational testing: 模型关系测试
- Revizor-E3: 基于反馈驱动的模糊测试框架
- SoC Contract: 基于片上系统时序合约的解耦验证框架
- Timing Contract Instrumentation: 时序合约插桩

## Contribution Chains

Revizor-E3:

- Limitation: black-box MRT lacks semantic-aware generation, reusable violation feedback, and exploitability-aware filtering.
- Method: semantic-aware coverage-guided generation, violation-driven mutation, two-dimensional exploitability filtering.
- Evidence: instruction coverage improves from 88.0% to 99.3%; violation discovery reaches 2.7x baseline; false positive rate drops from 29.8% to 3.2%.
- Finding: MOVNT implicit cache eviction and REP MOVS alignment-dependent microcode timing behavior.

SoC Contract:

- Limitation: core-only formal verification misses SoC interaction timing leaks; composition requires platform RTL, suffers state explosion, and lacks reuse.
- Method: three-level timing contracts `$C_1$/$C_2$/$C_3$`, CPU_TCI, Platform_TCI, and bidirectional decoupled verification with a composition safety theorem.
- Evidence: TCI detects the same timing vulnerabilities as composition; verification is about 1.8x faster in the direct comparison; decoupled verification finishes in 2.3 hours where composition times out after 7 days.
- Finding: interrupt/peripheral timing leakage can exist even without speculative execution if external interaction is not protected.

## Editing Guardrails

- Keep the distinction between detection and proof precise.
- Keep contract terminology consistent across Chapters 3, 4, and 5.
- Do not weaken the full-life-cycle framing.
- Do not turn experimental claims into universal claims across all processors unless the thesis explicitly supports that.
- When adding transitions, connect Chapter 4 to Chapter 5 through the limitation of fuzzing: it can detect but cannot prove absence of vulnerabilities.
