# Financial RAG — offline semantic repair checkpoint

Date: 2026-09-17

## Safety status

```text
DEEPSEEK_API_USED: NO
REAL_PROVIDER_CALLS: 0
EVALUATOR_CALLS: 0
API_COST: $0
ALLOW_REAL_PROVIDER: false for the offline replay and test processes
```

No answer was regenerated and no frozen benchmark label or historical result
was edited. This checkpoint is not a semantic re-grade of the 100 answers.

## Frozen baseline provenance

The requested historical counts **33 INCORRECT / 1 FAILED**, **223
VALID_BUT_NOT_SUPPORTED**, and **19 bilingual grade mismatches** come from
``evaluation/results/formal_20260916/``. Its frozen semantic review contains
100 answers and 341 citation reviews (118 supported, 223 not supported under
that evaluator's rubric). The counts are audit inputs, not current-code test
results; those files are not edited by this repair.

Do not confuse this baseline with the earlier, separately frozen
``evaluation/results/formal_20260914_p0_quality_sprint1_1_final/`` artifact. It
has different historical labels (35 incorrect, 1 failed, 121 not-supported
citations over 243 citation reviews) and is not the source for the 33/223/19
gate.

## Offline changes

- Qualitative citations on period-specific questions must now have period
  evidence in the cited text or period-specific metadata. A Q4/FY risk passage
  cannot support a Q2-specific narrative claim solely because it is from the
  same company/report. Numeric table claims continue to use their exact row and
  column period validation.
- English/Chinese financial query normalization now recognizes Services and
  Automotive business/segment wording, and British ``data centre`` spelling.
- Chinese business-performance follow-ups are classified as summaries. A
  requested specific metric with no matching evidence no longer silently falls
  back to an unrelated total-revenue fact.
- Generic bilingual margin follow-ups are planned against available gross and
  operating margin facts only. The plan carries the inherited issuer and
  reporting period when those are present in the conversation context.
- The new replay harness feeds frozen raw answers and exact frozen citation
  chunks through ``core.answer_policy.finalize_grounded_answer`` and mirrors the
  production API's citation projection. It refuses to run if real Provider use
  is enabled and never overwrites an existing output directory.
- The ingestion guide records the GitHub-derived safeguards: structured
  format adapters, table/prose isolation, preserved locators, and source order
  independent of embedding similarity.
- The semantic-review contract now separates three questions that were
  previously conflated: whether a cited passage entails the exact attached
  answer claim, whether that claim is relevant to the user's question, and
  whether a retrieved passage was cited at all. A valid but tangential cited
  claim can be locally supported while the overall answer remains incomplete;
  an unreferenced retrieval candidate is recorded as
  ``UNUSED_RETRIEVED_CONTEXT`` rather than as an unsupported answer citation.
- This separation was prompted by inspection of frozen review records such as
  EN-014, where locally quoted wording was judged against whole-question
  coverage. The old rubric therefore mixed citation entailment and answer
  completeness. This is a measurement defect, not evidence that those old
  citations were all correct.
- The evaluator change only affects future explicitly authorized reviews. No
  historical semantic review, benchmark grade, or artifact was rewritten.
- Both report finalizers now preserve and display the separate unused-context
  category when present. When consuming a legacy ledger with no such field,
  they say it was not measured instead of emitting a misleading zero. Manual
  supported-rank overrides do not relabel an unreferenced chunk as a user-facing
  cited claim.
- Added an offline EN-046-style retrieval regression that resolves the prior
  Tesla Q2 2025 user turn, verifies the plan binds the follow-up to Tesla plus
  ``Q2_2025``/``gross_margin``, then retrieves only Tesla's Q2 comparative-row
  evidence from a mixed Apple/NVIDIA/Tesla candidate pool. This exercises the
  deterministic planner/retriever boundary; it does not simulate or claim a
  new HTTP/provider answer.
- Follow-up scope resolution now stops at a standalone companyless user
  question instead of reaching across a topic change to resurrect an older
  issuer. Chained referential turns such as “What about margins?” followed by
  “And operating margin?” still retain the active entity.
- The EN-045-style elliptical follow-up “What was the main growth driver?” is
  now recognized as referential even without a pronoun, so the immediately
  preceding NVIDIA request supplies the issuer and keeps the turn on the
  document-QA path rather than direct chat. The equivalent Chinese elliptical
  follow-up is covered by the parallel growth-driver vocabulary.
- Growth-driver reranking now reserves issuer-specific reported commentary
  before the generic company slot. Previously a high-scoring safe-harbor chunk
  could consume that slot ahead of a lower-scoring but substantive
  AI-factory/agentic-AI passage. Company metadata that is absent still has a
  generic driver-evidence fallback; this is a ranking coverage rule, not a
  hard filter on uncertain metadata.
- Added a mixed-company bilingual regression: both English and Chinese
  follow-ups inherit NVIDIA, plan document QA, exclude an Apple growth chunk,
  and retrieve the reported NVIDIA driver passage ahead of safe-harbor
  boilerplate. This is a deterministic retrieval test, not a regenerated
  answer or a regrade of the historical pair.
- Risk/constraint questions now use separate per-company coverage slots for
  substantive risk factors and explicitly requested operating constraints.
  On multi-company risk questions, a resolved company mismatch is excluded
  from final context while missing/unknown issuer metadata remains eligible.
  The same bounded issuer-mismatch exclusion now applies to explicit
  multi-company financial comparisons; unknown issuer metadata stays eligible.
  If the query yields no concrete risk evidence, retrieval returns an empty
  evidence set rather than padding with boilerplate. Regression cases cover
  statutory “Litigation Reform Act” wording, routine “regulatory conditions,”
  table-of-contents hits, safe-harbor prose, real Apple-style “materially and
  adversely affected” wording, and Tesla-style “important factors … could
  cause” wording. The focused hybrid retrieval suite passes **29 tests** with
  BLAS/OpenMP thread counts constrained; no Provider/evaluator call was made.
  The tests prove the offline retrieval contract only; they do not re-grade the
  historical 100 answers.
- Grounding no longer treats an English filing date such as ``April 26, 2026``
  as an ungrounded financial amount, and period parsing accepts the canonical
  metadata key ``Q1_FY2027`` as well as its display form. A provider-free
  regression uses NVIDIA's actual three-month table header and the historically
  over-sanitized EN-007 reporting-period sentence.
- A real checked-in Apple Q2 FY2026 PDF was parsed through the canonical PDF
  loader and passed through the public hybrid retrieval entry point with a fake
  embedding store. Revenue retrieval returns the actual `$111,184m` vs
  `$95,359m` row; the cash-flow query returns the actual six-month operating
  cash-flow figure `$82,627m`. This is an offline retrieval integration test,
  not a model-answer or semantic-accuracy re-grade.
- Broad, metric-unspecified summary queries now add compact multi-metric
  highlights and non-boilerplate growth-driver chunks to the candidate pool,
  then reserve those evidence types ahead of generic company/context fillers.
  This addresses a reproduced NVIDIA Q1 failure where top-k contained income
  statement/cash-flow chunks and a shareholder-return paragraph but omitted
  the report's Data Center headline and AI-factory/agentic-AI drivers. A new
  canonical `NVIDIA_sample.pdf` test asserts revenue and growth, Data Center
  revenue/growth, gross margins, diluted EPS, and reported drivers all fit in
  the four-result context, while the Q2 `$91.0B` outlook is not substituted for
  Q1 actuals. No retrieval weights, RRF constant, or top-k were changed.
- English ``financially`` questions now classify as broad summaries rather
  than falling through to FACT. A canonical Apple Q2 FY2026 10-Q replay exposed
  a second format-specific problem: detailed statements split across adjacent
  table-row chunks lost revenue/net-income/EPS facts to narrative slots in the
  four-chunk context. When structured statement-of-operations evidence is
  detected, the selector now reserves revenue, net income, gross margin, and
  diluted EPS rows before optional narrative. It recognizes a ``Diluted`` row
  as EPS only when the same table text explicitly supplies an ``Earnings per
  share`` heading. Apple regression coverage checks Q2 net sales 111,184,
  operating income 35,885, net income 29,578, and diluted EPS 2.01 (USD
  millions except per-share amount). The NVIDIA earnings-release regression
  still follows the compact-highlight + substantive-driver path. No issuer ID,
  exact question, benchmark row, retrieval weight, or final top-k is hardcoded.
- Metric extraction now preserves simultaneous gross/operating-margin intent;
  unqualified “margins” means both measures instead of a gross-margin-only
  filter. Explicit multi-metric questions get per-metric evidence slots and a
  wider candidate pool without increasing final top-k. Structured financial
  table rows are recognized even when their headers only appear as row-label
  metadata. A canonical Tesla FY2025 PDF regression retrieves the historical
  Q2-2025 values (gross margin 17.2%, operating margin 4.1%) rather than a
  nearby FY2025/Q4 summary.
- The approved synthetic multi-company risk contract was rerun through the
  public hybrid retrieval entry point: both requested issuers retain their
  substantive risk evidence, known third-issuer evidence is excluded, and
  safe-harbor boilerplate does not occupy the context. **4 passed**; no
  Provider/evaluator request.

## Verification

- Focused grounding, answer-policy, query-scope, and cross-format contracts:
  **45 passed**.
- Semantic-review contract suite after rubric separation:
  **15 passed** (no Provider/evaluator request).
- PDF/XLSX/DOCX/CSV format and document-loader regressions:
  **77 passed** (no Provider/evaluator request).
- Semantic-review plus frozen-report contract tests:
  **21 passed** (no Provider/evaluator request).
- EN-046 inherited-company/period retrieval regression:
  **1 passed** (no Provider/evaluator request).
- EN-045 bilingual growth-driver follow-up plus issuer-aware retrieval
  regression: **passed** (no Provider/evaluator request).
- Hybrid retrieval and period-aware retrieval suites, including the canonical
  Apple PDF retrieval integration: **36 passed** (no Provider/evaluator
  request).
- Agent Runtime, prompt, answer-policy, grounding-contract, and query-scope
  suites: **103 passed** with ``ALLOW_REAL_PROVIDER=false`` (no
  Provider/evaluator request).
- Combined changed-area suite (semantic-review/reporting, ingestion formats,
  hybrid retrieval, period-aware retrieval, and Agent Runtime):
  **142 passed**; Ruff and ``git diff --check`` pass.
- Latest cross-format, retrieval, Agent Runtime, grounding, and semantic-review
  focused suite: **181 passed**. This includes the bilingual EN-045 growth-driver
  regression and existing PDF/XLSX/DOCX/CSV canonical-fact fixtures.
- Full backend suite with plan-limit evaluation bypass disabled for the test
  process (earlier checkpoint): **2,332 passed, 23 skipped**.
- Final full backend suite with ``ALLOW_REAL_PROVIDER=false``, evaluation-plan
  bypass disabled only for the pytest process, and ordinary plan limits enabled:
  **2,341 passed, 23 skipped**, one deprecation warning. This run made no
  Provider/evaluator calls and did not modify the local ``.env``.
- Latest full backend suite after EN-045 and rerank coverage changes:
  **2,344 passed, 23 skipped**, one deprecation warning in 255.07s. The
  process used ``ALLOW_REAL_PROVIDER=false`` and made no Provider/evaluator
  calls.
- Authoritative full backend rerun for this checkpoint, with
  ``ALLOW_REAL_PROVIDER=false``, ``EVALUATION_BYPASS_PLAN_LIMITS=false``, and
  ``CHAT_PLAN_LIMITS_ENABLED=true`` explicitly set for the test process:
  **2,352 passed, 23 skipped**, one Starlette/httpx deprecation warning in
  256.82s. This was the previous full-suite checkpoint. An initial run without
  explicit plan switch values produced seven quota-test failures because the
  evaluation bypass behavior was active; the seven cases passed both in
  isolation and in this correctly configured full run. No billing
  implementation was changed.
- Latest full backend suite after the summary-evidence coverage change, using
  ``ALLOW_REAL_PROVIDER=false``, ``EVALUATION_BYPASS_PLAN_LIMITS=false``, and
  ``CHAT_PLAN_LIMITS_ENABLED=true``: **2,354 passed, 23 skipped**, one
  Starlette/httpx deprecation warning in 261.23s. No Provider/evaluator call
  was made.
- Previous hybrid retrieval + period-aware retrieval checkpoint: **37 passed**.
- Latest hybrid retrieval, period-aware retrieval, and query-scope suites:
  **41 passed**, one Starlette/httpx deprecation warning. This includes the
  public Apple/NVIDIA/Tesla PDF integrations, the multi-company risk evidence
  contract, and financial-summary scope classification.
- Latest changed-area grounding, answer-policy, hybrid/period retrieval, and
  final-answer contract suite: **84 passed**, one deprecation warning.
- Latest full backend suite after all summary and multi-metric retrieval fixes,
  with ``ALLOW_REAL_PROVIDER=false``, ``EVALUATION_BYPASS_PLAN_LIMITS=false``,
  and ``CHAT_PLAN_LIMITS_ENABLED=true``: **2,357 passed, 23 skipped**, one
  Starlette/httpx deprecation warning in 266.36s. No Provider/evaluator call
  was made.
- Ruff: **PASS**.
- ``git diff --check``: **PASS** (Git reports existing line-ending conversion
  notices for dirty files; no whitespace errors).
- Frozen 100-answer deterministic production-policy replay:
  **100/100 replayed**, **0 unsupported numeric claims after the policy**,
  **49/50 bilingual required-fact coverage pairs equal**. These are
  deterministic policy/coverage measurements, not semantic answer grades.
- Latest immutable-input replay at
  ``evaluation/results/offline_grounding_replay_20260917_v8`` again processed
  **100/100** rows and **341** input citation records with **0** unsupported
  numeric claims after policy projection. It retained historical counts of
  **33 INCORRECT / 1 FAILED** and **49/50** required-fact parity; its one
  mismatch remains frozen EN/ZH-046 because this projection intentionally uses
  only each old answer's original citations, not today's retrieval path.
- Post-date-parser immutable-input replay at
  ``evaluation/results/offline_grounding_replay_20260917_v9`` processed
  **100/100** historical rows and **341** original citation records with **0**
  final unsupported numeric claims. It preserved the requested-period sentence
  in EN-007 that v8 had replaced, retained **100%** deterministic required-fact
  coverage for the EN/ZH-007 pair, and left the frozen **33/1/223/19** labels
  unchanged. This is a grounding-policy replay, not a semantic re-grade; one
  other required-fact parity difference remains at EN/ZH-046 because replay
  intentionally uses each historical answer's original citations.
- In the frozen replay, the remaining mismatch is multi-turn ``046``: the
  historical English answer carries only Apple evidence after a Tesla
  follow-up, while the historical Chinese answer carries Tesla evidence. A new
  offline regression now proves the current deterministic planner/retriever
  selects Tesla Q2 margin evidence from mixed-company candidates, and the
  production finalizer projects the same supported facts in both languages.
  This does not alter the frozen **49/50** historical measurement or verify a
  live Docker request; no new Provider response was requested.

### 2026-09-18 offline follow-up

- Re-ran the multi-company risk regression through public
  ``HybridRetriever.retrieve`` with local synthetic chunks and a fake vector
  store: **5 passed**. Apple and Tesla each retain their own concrete risk
  evidence; unrelated NVIDIA risk content and generic safe-harbor disclaimers
  do not occupy the requested result slots. This verifies retrieval behavior,
  not generated answer quality.
- Re-ran the frozen 100-answer deterministic grounding replay into
  ``evaluation/results/offline_grounding_replay_20260918/``: **100/100**
  rows processed, **0** final unsupported numeric claims, **0** Provider or
  evaluator calls, and **$0** cost. The historical answer labels remain
  unchanged. This citation-only replay snapshot reports **48/50** required-
  fact parity pairs (EN/ZH-037 and EN/ZH-046 differ); it predates the
  current-path repair below and cannot regenerate evidence missing from the
  frozen answers.
- Applying the current deterministic citation annotation contract read-only
  to all **341** frozen citation records separates **127**
  ``UNUSED_RETRIEVED_CONTEXT`` records (122 previously labeled
  ``VALID_BUT_NOT_SUPPORTED``, 5 previously labeled
  ``VALID_SUPPORTED``), **113** cited ``VALID_SUPPORTED`` records, and
  **101** cited records retaining the old ``VALID_BUT_NOT_SUPPORTED``
  annotation. This only checks rank-marker usage and exact source/quote
  validity; it is not a semantic re-review of the 101 claims and does not
  rewrite the frozen labels.
- Fixed the reproducible ZH-037 route split: “iPhone maker” / “做 iPhone 的
  公司” now resolves to Apple in the canonical entity extractor, the runtime
  intent router reuses that extractor instead of a divergent alias map, and
  “业绩” is recognized as a company-performance cue. The bare product query
  “What is an iPhone?” remains direct chat. Planner, runtime-router,
  required-fact parity, and real Apple Q2 FY2026 PDF retrieval regressions
  pass; both language variants retrieve the same headline rows, and the
  six-month operating-cash-flow fact remains explicitly labeled as cumulative.
- The complete adjacent planning, hybrid/period retrieval, query-scope,
  citation-gate, grounding, and answer-policy suite now has **183 passed**.
  The additional runtime intent-router and AgentRuntime regressions have
  **95 passed** after centralizing company extraction; the former “unknown
  Microsoft” fixture now uses an actually unknown issuer (Acme), while
  Microsoft follows the canonical single-company route.
  Ruff, Python compilation, and ``git diff --check`` pass. Processes set
  ``ALLOW_REAL_PROVIDER=false``; no Provider/evaluator calls were made.
- Final full backend offline suite after the alias and runtime-router repairs:
  **2,365 passed, 23 skipped** in 261.82s. The process explicitly used
  ``ALLOW_REAL_PROVIDER=false``, ``EVALUATION_BYPASS_PLAN_LIMITS=false``,
  and ``CHAT_PLAN_LIMITS_ENABLED=true``; no Provider/evaluator calls were
  made.
- These offline regressions do not re-grade or modify the frozen **33
  INCORRECT / 1 FAILED / 223 VALID_BUT_NOT_SUPPORTED / 19** baseline. The
  production semantic-quality gate remains open.

### 2026-09-18 follow-up: unsupported metric fail-closed

- A production-policy defect was reproduced with synthetic local evidence:
  an unsupported request for a future stock-price target could become an
  empty answer when the retrieved Tesla filing contained an unrelated revenue
  fact. ``_compact_refusal_fragments`` had treated any fact in the ledger as
  support for the requested answer and removed the grounding refusal. It now
  removes refusal placeholders only when a required fact for this question is
  actually available and present in the completed answer.
- Specific requests for stock-price targets/forecasts, market share, and gross
  hires now remain evidence-seeking ``FACT`` queries instead of falling
  through the generic ``What is`` definition branch. The final answer policy
  now requires the metric phrase and every claimed number to co-occur in the
  same cited local source fragment. A metric word on one row and a matching
  number on another row can no longer be combined. Adjacent facts such as
  revenue, vehicle volume, or headcount cannot stand in for these metrics.
  Missing evidence yields an explicit localized insufficiency response; a
  matching cited target-price fixture remains answerable. Generic definitions
  (``What is gross margin?`` and ``什么是毛利率？``), summaries, analyses, and
  company/period-scoped ordinary financial facts retain their prior behavior.
- Added contract coverage for stock target, 2027 expected stock price, China
  market share, gross hires vs. headcount, bilingual refusal, and a genuinely
  cited price-target fact. The affected answer-policy, scope, retrieval,
  grounding, and bilingual-routing group reports **132 passed**. Ruff passes
  for changed Python modules and tests; ``git diff --check`` passes.
- Replayed the frozen 100 answers through the current deterministic
  production finalizer into
  ``evaluation/results/offline_grounding_replay_20260918_v3/``: **100/100**
  processed, **0** final unsupported numeric claims, **0** Provider/evaluator
  calls, and **$0** cost. Historical grades remain **29 CORRECT / 37 PARTIAL /
  33 INCORRECT / 1 FAILED**. Deterministic required-fact parity is still
  **48/50** (the same 037 and 046 citation-only differences); this replay is
  not a semantic re-grade and cannot repair facts absent from a frozen answer's
  cited evidence.
- Tightened the new unstructured-metric boundary after a counterexample showed
  that a keyword and a coincidentally matching number on different table rows
  could still be joined by chunk-level validation. A cited price target now
  passes only when its value is in the same local source fragment; market
  share cannot borrow a neighboring revenue percentage. Added a regression
  proving that split-row evidence fails closed. The focused suite now reports
  **133 passed**.
- Replayed once more after this stricter check into
  ``evaluation/results/offline_grounding_replay_20260918_v4/``: **100/100**
  processed, still **0** final unsupported numeric claims, **0** Provider and
  evaluator calls, and **$0** cost. Frozen grades remain unchanged and
  deterministic required-fact parity remains **48/50**.
- Full backend test run: **2,366 passed, 23 skipped, 1 failed**. The one
  failure was the existing perf-marked 10,000-increment latency assertion
  (170.38 ms vs. its 100 ms threshold during the full suite); an isolated
  rerun of that same test passed. No test was skipped or xfailed to conceal a
  failure. Provider guard was explicitly set to ``false`` throughout.
- After the same-metric/same-row grounding check was added, the complete
  non-performance backend suite was rerun with real Providers disabled:
  **2,349 passed, 23 skipped, 19 perf-marked tests deselected**, 260.85s. The
  isolated performance assertion passed separately, and the 100-answer
  offline production replay remained at zero unsupported numeric claims.
- The 19 historical bilingual grade mismatches and 223 old
  ``VALID_BUT_NOT_SUPPORTED`` annotations remain frozen. The quality/semantic
  gates remain open: deterministic grounding improvements do not establish
  that the prior model answers are semantically correct or that citations
  entail every natural-language statement.
- Read-only GitHub review was performed because the ingestion design must
  survive diverse statement layouts, not just a new embedding model. RAGFlow
  exposes parser-backend dispatch (including Docling and MinerU) in
  ``rag/app/naive.py`` and its project describes dedicated PDF/table parsing;
  Docling documents multi-format conversion, PDF layout/reading-order/table
  structure, OCR, XBRL financial reports, local processing, and structured
  JSON export. These point to a parser/provenance/validation boundary before
  embedding, plus format-specific golden ingestion tests. No dependency was
  installed and no parser migration or data reindex was performed in this
  offline repair; parser selection is a separate change to benchmark on the
  three public sample filings first. References:
  [RAGFlow parser dispatch](https://github.com/infiniflow/ragflow/blob/main/rag/app/naive.py),
  [RAGFlow](https://github.com/infiniflow/ragflow),
  [Docling](https://github.com/docling-project/docling),
  [Docling hybrid chunking example](https://github.com/docling-project/docling/blob/main/docs/examples/hybrid_chunking.ipynb).

### 2026-09-18 citation-review false-negative audit

- Rechecked the frozen ``formal_20260916`` citation ledger against the actual
  ``[Evidence N]`` markers in each answer, without changing its rows. Of 341
  annotations, **122** old unsupported labels are unused retrieved context,
  **5** old supported labels are also unused, **113** supported labels are
  actually cited, and **101** actually cited labels retain the old unsupported
  annotation. This confirms that the headline 223 is not 223 user-visible
  unsupported citations.
- Among those 101 cited/unsupported records, **41 across 20 answers** do not
  pass the evaluator's own exact-span contract: the attached claim is missing,
  too short, or not an exact main-answer substring, and/or the attached quote
  is missing, too short, or not an exact cited-chunk substring. These records
  cannot be treated as proven unsupported claims from the stored annotation.
  The other **60** have structurally verifiable quote/claim spans but still
  need a fresh local-entailment review; no semantic relabeling was performed.
- Reapplying the corrected offline annotation contract to all 341 frozen rows
  yields **113** cited ``VALID_SUPPORTED``, **127** ``UNUSED_RETRIEVED_CONTEXT``,
  **60** cited ``VALID_BUT_NOT_SUPPORTED``, and **41**
  ``REVIEW_INDETERMINATE``. This is a deterministic accounting pass over the
  stored answer markers and exact spans; it does not override or rewrite the
  frozen 223-label count and does not semantically resolve the 60 remaining
  claims.
- A reason-text scan also found **10** of the 101 records whose rationale
  explicitly discusses off-topic/tangential relevance. This is a targeted
  review queue, not a claim that those 10 citations are supported: relevance
  and entailment must be adjudicated separately.
- Fixed the *future review contract* so invalid/missing exact spans produce
  ``REVIEW_INDETERMINATE`` rather than ``VALID_BUT_NOT_SUPPORTED``. A valid
  unsupported label is retained only when both the exact cited quote and exact
  answer claim can be verified. New retest reports now display indeterminate
  annotation counts separately. Added offline tests for malformed annotations
  and for preserving a verifiable unsupported judgment. Frozen **33/1/223/19**
  labels and raw answers remain unchanged; this does not re-grade history or
  claim to have fixed natural-language answer quality.

### 2026-09-18 source-period binding and bilingual fact projection

- Strictly replayed all 100 frozen questions against the three checked-in
  public source PDFs using the current production HybridRetriever, deterministic
  retrieval probes, fact ledger, and answer finalizer. The denominator contains
  142 exact company/metric/period/value facts extracted from those PDFs.
- The v19 audit had reached 138/142 facts retrieved (97.18%) and 134/142
  projected into the final answer (94.37%). Investigating the remaining
  projection gaps exposed two implementation defects rather than a need for
  more embedding recall:
  - Tesla's Q4/FY2025 narrative states full-year operating cash flow of
    $14.7B and Q4 cash flow of $3.8B in one passage. The full-year amount was
    incorrectly assigned the filing's Q4 period. Narrative amounts now bind to
    an immediately stated annual period, while the structured Q4 table remains
    authoritative for the quarterly value ($3.813B).
  - Decimal normalization rendered $840 million as ``8.4E+2 million`` during
    deterministic completion. The final grounding pass rejected that valid
    claim, leaving an obsolete insufficiency response. User-facing normalized
    values now use plain decimal formatting; an end-to-end regression verifies
    that Tesla's supported Q4 net income survives final grounding.
- Strict audit v21: **142/142** source facts retrieved, **142/142** exact facts
  projected, **0** unsupported numeric/fact claims, and **0/50** English/Chinese
  pairs differ in source targets, retrieved facts, or context-plan facts.
  EN-021 and ZH-021 now both include Tesla Q4 net income ($840M) and Q4
  operating cash flow ($3.813B), each with period-correct evidence.
- Frozen-history production-grounding replay v30: **100/100** processed,
  **0** final unsupported numeric claims, **0** provider/evaluator calls, and
  **$0** cost. It still reports five answer-fact-coverage differences across
  50 bilingual pairs when restricted to historical citation chunks; these
  are not semantic grades and do not contradict the current full retrieval
  audit. The replay retains the original frozen grade labels unchanged.
- Focused tests after these fixes: **130 passed** (one upstream Starlette
  deprecation warning); Ruff and ``git diff --check`` passed. The strict audit
  records ``provider_calls=0``, ``evaluator_calls=0`` and ``api_cost_usd=0``.

### 2026-09-18 qualitative citation-boundary repair

- A focused NVIDIA growth-driver regression exposed two mismatched contracts:
  the main evidence filter accepted report-period metadata such as ``periods``
  while the qualitative citation selector did not read that key; separately,
  a synthetic ``Growth-driver source excerpt`` prefix was being parsed as part
  of the factual sentence, so the word ``growth`` triggered trend-direction
  checking against a verbatim source quote. Qualitative evidence selection now
  reads the same period metadata aliases as the main filter, and generated
  source excerpts use a distinct heading plus quoted, individually cited source
  passages.
- Chinese-language fallback had also discarded those verified English source
  excerpts together with untranslated provider prose. It now keeps only the
  deterministic fact projection plus the independently sourced, exact quoted
  driver passages; it does not preserve the untranslated model narrative.
- Strict qualitative sanitation now treats blank lines as layout, not as
  unsupported prose claims. This fixes a phantom unsupported-claim count when
  localized facts and source excerpts are separated by a paragraph break.
- Added/updated provider-free regressions. The focused grounding, policy,
  retrieval-probe, ledger, and query-scope suites report **147 passed**. Ruff
  reports clean and ``git diff --check`` exits successfully (Git emits only
  existing line-ending normalization warnings). One upstream Starlette/httpx
  deprecation warning remains.
- Historical raw-answer replay v31:
  ``evaluation/results/offline_grounding_replay_20260918_v31/``. All **100**
  frozen answers were replayed through current retrieval and production
  grounding with **0** Provider/evaluator calls and **$0** cost. The finalizer
  projected **142/142** audited source facts; its final unsupported numeric and
  qualitative-claim counters were both **0**. Source-fact projection differs
  for **0/50** English/Chinese pairs. These are deterministic policy/replay
  results, not semantic answer re-grades; the frozen labels remain
  **29 CORRECT / 37 PARTIAL / 33 INCORRECT / 1 FAILED**, and the paired grade
  mismatch count remains **19**. The old citation-review annotations remain
  frozen; the 60 structurally verifiable unsupported annotations still need
  source-grounded local-entailment adjudication.
- The credential-free full backend rerun initially exposed an additional
  cross-quarter leak in a mixed-company answer: after the parsed fact ledger
  scoped Tesla revenue to the filing's Q2-2025 column, raw table-number
  supplementation could re-add the neighboring Q4-2025 value. Raw numeric
  supplementation is now limited to the period/metric row when a comparative
  table is recognized, and fails closed if that row cannot be mapped. The
  existing mixed-company regression and **119** focused policy/grounding tests
  pass after the fix.
- Final full offline backend suite after that repair:
  **2,478 passed, 2 skipped, 40 deselected** (``live`` and ``perf``), with
  ``ALLOW_REAL_PROVIDER=false``; the only warning is the upstream
  Starlette/httpx deprecation.
- Historical production-grounding replay v32:
  ``evaluation/results/offline_grounding_replay_20260918_v32/``. It processed
  **100/100** answers with **0** Provider/evaluator calls and **$0** cost;
  final unsupported numeric/qualitative counters are **0/0**, source facts
  projected are **142/142**, and source-fact projection differs for **0/50**
  language pairs. The stricter quarter boundary flags **194** unsupported raw
  numeric claims versus **186** in v31; that is a conservative removal count,
  not an accuracy gain, and warrants per-claim over-sanitization review. Only
  EN-001 and ZH-035 final replay text changed from v31; all frozen semantic
  grades remain unchanged. No conclusion is drawn that the 33 incorrect,
  1 failed, 223 original citation labels, or 19 paired grade mismatches are
  resolved.
- The v32 comparison exposed that an answer bullet omitting its period was
  defaulting to the filing-level quarter even when the question explicitly
  requested one historical quarter. Numeric grounding now inherits a single
  explicit query period for unqualified answer claims; explicit periods in a
  claim still take precedence, and queries without a period still use the
  source's default/reporting-period evidence. Comparative table recovery stays
  bounded to the matching metric row/period. An offline regression verifies
  that Tesla Q2-2025 total revenue of $22,496m is retained from an unqualified
  bullet while the adjacent Q4-2025 value of $24,901m is rejected for that Q2
  query.
- Replay v33:
  ``evaluation/results/offline_grounding_replay_20260918_v33/`` processed
  **100/100** frozen answers with **0** Provider/evaluator calls and **$0**
  cost. Source facts remain **142/142**, final unsupported numeric/qualitative
  counters remain **0/0**, and source-fact projection differs for **0/50**
  bilingual pairs. Relative to v32, final text changed in five rows; notably,
  the Q2 Tesla revenue/operating-income/net-income bullets were restored for
  EN-001 and ZH-035. Raw unsupported numeric claims decreased from **194** to
  **191**. Frozen grades and the 19 paired grade mismatches remain unchanged;
  this replay is not a semantic re-grade.
- Full offline backend suite after query-period inheritance:
  **2,479 passed, 2 skipped, 40 deselected** (``live`` and ``perf``), with
  ``ALLOW_REAL_PROVIDER=false``. Ruff and ``git diff --check`` also pass; the
  only test warning is the upstream Starlette/httpx deprecation.

## Gates that remain open

The following are retained as historical findings, not claimed fixed or
re-evaluated:

```text
historical answer grades: 33 INCORRECT / 1 FAILED
historical citation review: 223 VALID_BUT_NOT_SUPPORTED
historical bilingual grade mismatches: 19
```

The historical ``223 VALID_BUT_NOT_SUPPORTED`` value is a label count under the
old rubric. That rubric required a citation to support a material claim
answering the whole question, so it did not cleanly distinguish local claim
entailment from answer relevance/completeness; additionally, old result rows
could include retrieved chunks not actually cited in the user-visible answer.
The number is preserved unchanged for auditability and is **not** reinterpreted
as either 223 proven hallucinations or 223 supported citations. A future
authorized re-review must report separate local-entailment, query-relevance,
and unused-context counts. It must not overwrite these frozen records.

The offline policy can validate exact numeric/company/period support and can
project verified requested facts. It cannot independently determine whether
all natural-language paraphrases entail their citations or whether newly
generated answers have become semantically correct. Doing so requires a
source-grounded human review or an explicitly authorized evaluator run; neither
was performed. The one frozen 046 context mismatch also remains unresolved by
answer post-processing alone.

```text
OFFLINE_REPAIR: PARTIAL
READY_FOR_DEEPSEEK: NO
```

Do not enable or call DeepSeek until the remaining offline reproducible failure
cases have been converted into and passed as regressions, and a separately
authorized review can re-evaluate semantic answer quality. No Docker rebuild,
live E2E, commit, or push was done.

## Follow-up evidence audit (2026-09-18, v34)

The latest immutable historical replay is
``evaluation/results/offline_grounding_replay_20260918_v34/``. It retains the
frozen grades and makes no Provider/evaluator calls. Across the 34 frozen
``INCORRECT``/``FAILED`` rows, 19 have at least one audited source-backed
required fact; all 19 of those rows had every such fact retrieved and
projected by the current deterministic production grounding path. The other
15 rows have no structured source-fact target in this ledger. That does **not**
prove the report lacks the requested information: qualitative claims, routing,
and knowledge-scope cases require separate source review. Thus missing report
content is a valid explanation for some cases, but cannot explain all the
known failures.

Failure-mode labels on those 34 historical rows include 27 ``Reasoning
Failure``, 23 ``Data Missing``, 21 ``Retrieval Failure``, 9 ``Citation
Failure``, and 9 ``LLM Hallucination`` (labels overlap per question). These are
the original evaluator annotations, not independently adjudicated causes.
The v34 finalizer reports zero unsupported numeric and qualitative claims and
142/142 audited source facts projected; those safety/coverage numbers do not
change the frozen semantic grades.

The previously approved public ``HybridRetriever.retrieve`` synthetic
multi-company risk check was rerun with real-provider access disabled:
**4 passed**. It confirms that, in the tested cases, each requested company’s
concrete risk evidence survives retrieval while generic safe-harbor text does
not consume the limited result slots. This is a focused regression, not proof
that every PDF layout or risk disclosure parses correctly.

The subsequent full offline backend rerun exposed three canonical-PDF
regressions that the retrieval-only risk checks did not cover: Apple revenue
performance, NVIDIA Q1 FY2027 summary, and Apple/Tesla income comparison. The
source rows were present. Root cause was intent reuse: a predicate that
allowed financial summaries to receive extractive growth-driver text was also
used to activate driver-only retrieval, removing statement rows from summary
context. Retrieval now uses a narrower explicit-driver intent while the
answer-policy layer can still add cited driver excerpts to broad summaries.
The Chinese Apple summary also exposed stale citation ranks on synthesized
English source excerpts after incompatible candidates were filtered; the
excerpt is now rebuilt against the trusted evidence order.

Verification after these repairs:

```text
focused canonical-PDF/query-intent regressions: 6 passed
full provider-disabled offline backend suite: 2,488 passed, 2 skipped, 40 deselected
Ruff (changed Python files): PASS
git diff --check: PASS
DeepSeek/provider calls: 0
```

The full suite is regression evidence, not semantic re-grading of the frozen
100 answers. Historical grades remain 33 ``INCORRECT`` / 1 ``FAILED``, and
the 19 answer-grade mismatches and citation-entailment review remain open.
The overall gate therefore remains ``OFFLINE_REPAIR: PARTIAL`` and
``READY_FOR_DEEPSEEK: NO``.

## Source-presence and bilingual scope audit (2026-09-18, v26)

The question “were the facts absent from the filings?” was checked against the
actual frozen corpus, rather than inferred from old model refusals. The local
source references confirm, for example:

- Apple Q2 FY2026 reports **$30.976B** Services net sales and says the increase
  was primarily from advertising, the App Store, and cloud services; it also
  attributes iPhone net-sales growth to higher Pro-model sales.
- NVIDIA Q1 FY2027 reports **$81.6B** total revenue and **$75.2B** Data Center
  revenue, and discusses AI factories, agentic AI, and Data Center compute and
  networking growth.
- Tesla's Q4/FY2025 update contains a historical Q2-2025 column, including
  **$22.496B** total revenue and **$16.661B** automotive revenue. That supports
  Q2 numeric answers, but does not make Q4 narrative a Q2-specific explanation;
  the answer must disclose that limitation.
- Alibaba is absent from the three-document corpus, so ZH-034 remains a
  genuine knowledge-scope case.

This confirms a mixed diagnosis: some requested narrative is not in the
selected filing/period, but several prior “evidence missing” answers were
retrieval/context failures even though the facts are present. Historical
examples include Apple Services (EN/ZH-040) and Tesla margin follow-up
(EN/ZH-046); the current deterministic source audit now finds and projects the
required values for both language variants. This is retrieval/projection
evidence, not a new semantic grade of a generated answer.

The v25 audit also exposed seven English/Chinese scope-label differences.
Generic routing rules now classify business-driver requests as analysis,
multi-company superlative rankings as comparisons, broad business-status
questions as summaries, and coreferential margin follow-ups as metric facts.
The new benchmark-wording regressions pass. After the change, the v26 local
source audit reports **142/142** required source facts retrieved and projected,
**0** unsupported projected claims, and **0/50** bilingual differences in
source targets, retrieved facts, or required-fact context plans. Scope-label
differences fell from **7 to 2**. The remaining pair 002 (“what does the report
say about revenue?” vs. “how did revenue perform?”) and pair 047 (“focus on
drivers” vs. “compare their drivers”) differ in wording/intent; the frozen
dataset was not rewritten to force artificial parity.

Verification for this change:

```text
tests/evaluation/test_query_scope.py + tests/planning/test_bilingual_financial_routing.py: 40 passed
Ruff (changed scope/test files): PASS
full provider-disabled backend suite after this change: 2,492 passed, 2 skipped, 40 deselected
current source audit v26: 142/142 retrieved and projected; provider/evaluator calls 0; cost $0
git diff --check: PASS (only line-ending normalization warnings)
```

These results do not adjudicate semantic correctness, do not alter the 19
historical answer-grade mismatches, and do not close the separate citation
entailment review.

### 2026-09-18 Chinese growth-driver wording regression

The v26 source audit showed that the filing content was present but the
English/Chinese answer paths diverged for the frozen NVIDIA Q1 FY2027 growth
question. The broad query scope was already ``ANALYSIS`` in both languages;
the narrower explicit-driver detector missed the Chinese word order
``增长的主要驱动因素`` (and the punctuation variant ``增长，主要驱动因素``).
Consequently, Chinese retrieval did not enter the driver-evidence selection
path and the answer finalizer left an insufficiency response, while the
English variant extracted the report passage.

The detector now accepts general Chinese word-order variants for main/core/key
growth drivers, causes, and drivers/power, without a benchmark ID or exact
question rule. The answer policy distinguishes an explicit financial
attribution (a financial outcome and causal link in the same source passage)
from related industry commentary. Only period/company-compatible explicit
attribution may remove a driver insufficiency statement. Context-only passages
are labeled as related filing context, explicitly not as an attribution of
reported-period growth; the insufficiency qualification is preserved. The
checked-in NVIDIA release includes commentary about AI-factory buildout and
agentic AI; it does **not** quantitatively attribute Q1 revenue growth to
those themes, so the synthesized answer presents them as source context, not
as a proven causal decomposition of the quarter.

Offline regressions now check the Chinese variants in scope and explicit
intent classification, actual ``NVIDIA_sample.pdf`` retrieval alongside its
English counterpart, and finalization through the production grounding
boundary with company/period constraints. A direct-causation fixture removes
the refusal; commentary-only evidence retains the caveat. The synthetic
safe-harbor, wrong-issuer, and wrong-period cases remain excluded. After the
direct-attribution/context distinction, source audit v28 repeats **142/142**
source-fact recall/projection, **0** unsupported projected facts, and **0/50**
bilingual source-target, retrieval, or context-plan differences. EN-009 and
ZH-009 retrieve the same NVIDIA page-1 chunk and receive the same cited source
excerpt under a “related filing context” heading; it explicitly says this is
not an attribution of reported-period growth and preserves the insufficiency
qualification.

Current-retrieval historical raw-answer replay v15 processes **100/100** rows,
projects **142/142** source facts, retains **0** final unsupported
numeric/qualitative claims, and reports **0/50** differences in exact source-
fact projection. Frozen historical grades remain **29 CORRECT / 37 PARTIAL /
33 INCORRECT / 1 FAILED**; this is not a semantic re-grade. The raw answers
still contain **187** unsupported numeric and **881** unsupported qualitative
claim fragments before final grounding, so historical answer quality is not
claimed fixed.

Verification after the context-vs-attribution change:

```text
tests/evaluation/test_query_scope.py + tests/evaluation/test_final_answer_policy.py: 69 passed
focused growth-driver / canonical NVIDIA PDF regressions: 5 passed
full backend offline suite (ALLOW_REAL_PROVIDER=false, not live/perf): 2,495 passed, 2 skipped, 40 deselected
Ruff (changed Python files): PASS
source audit v28: 142/142 retrieved and projected; 0/50 bilingual evidence-plan differences
historical replay v15: 100/100; 142/142 projected; 0 final unsupported numeric/qualitative claims
Provider calls: 0; evaluator calls: 0; API cost: $0
```

These tests prove deterministic evidence-path and grounding contracts, not
that all historical prose is semantically correct. No Provider/evaluator call
was made.

### 2026-09-18 Apple Services evidence-path regression

The Apple Q2 FY2026 Form 10-Q **does contain** the requested explanation: it
says Services net sales increased primarily due to higher net sales from
advertising, the App Store, and cloud services. The earlier English
"service-related business" wording did not retrieve that MD&A paragraph in its
final top-k context, while the Chinese wording happened to retrieve it. This
was a retrieval/coverage asymmetry, not missing filing content.

For a query that names a reportable segment, the retriever now promotes only
same-issuer, requested-segment causal passages into the bounded candidate
pool, then reserves a same-period passage beside the period-matched numeric
row when one exists. This does not make filename metadata authoritative and
does not relax company/period checks. A real-PDF regression verifies both
English and Chinese Apple Services questions retain the $30.976B row and the
three reported drivers. It also guards against treating the 10-Q cover's
"emerging growth company" checkbox boilerplate as financial-driver evidence.
The general AI-factory narrative detector also accepts the filing's closed
"buildout" spelling; it remains explicitly labeled as related context rather
than a financial causal attribution.

Verification after this retrieval-coverage change:

```text
Focused query/final-answer/real-PDF regressions: 13 passed
Ruff (changed retrieval, evidence, and regression-test files): PASS
Full provider-disabled backend suite (ALLOW_REAL_PROVIDER=false, not live/perf): 2,497 passed, 2 skipped, 40 deselected
Current source audit v29: 142/142 source facts retrieved and projected; 0 unsupported projection claims; 0/50 bilingual target/retrieval/context-plan differences
Historical raw-answer replay v16: 100/100 rows; 142/142 projected; 0 final unsupported numeric/qualitative claims; 0/50 exact source-fact projection differences
Historical grades unchanged: 29 CORRECT / 37 PARTIAL / 33 INCORRECT / 1 FAILED (not semantically re-graded)
Provider calls: 0; evaluator calls: 0; API cost: $0
```

The offline evidence-path issue is fixed for the covered Apple Services
regression, but the historical 33 INCORRECT / 1 FAILED ratings and the broader
semantic citation/bilingual review remain unresolved. No Provider/evaluator
call was made.

### 2026-09-18 NVIDIA paired-margin basis and period binding

`NVIDIA_sample.pdf` page 1 explicitly reports Q1 FY2027 GAAP and non-GAAP gross
margin as 74.9% and 75.0%, respectively. The fact parser's ordinary
single-metric window treated the second margin label as a boundary, dropping
the second value. When both values were retained, positional mapping across
the whole PDF chunk incorrectly assigned the second value to a later
comparative period. In addition, summary and comparison plans used one generic
margin requirement even when retrieved evidence explicitly distinguished both
accounting bases.

The parser now preserves only this explicit paired-margin clause, qualifies
each extracted value with its corresponding GAAP basis, and binds both values
to the same period slot. Summary, comparison, and fact plans now require both
bases only when both are separately supported in the evidence. Regression
coverage checks English and Chinese final answers, summary/comparison planning,
and a page containing multiple comparative periods. A direct extraction and
production-finalizer check against the actual NVIDIA PDF confirms Q1 facts
74.9% GAAP and 75.0% non-GAAP; Q2 outlook remains separately period-scoped.

Verification after the paired-margin change:

```text
Focused final-answer / evidence-first / fact-ledger tests: 151 passed
Full backend suite with ALLOW_REAL_PROVIDER=false: 2,518 passed, 23 skipped
Ruff (changed Python files): PASS
git diff --check (changed Python files): PASS
Historical raw-answer grounding replay v19: 100/100 rows; 142/142 source facts projected; 0 final unsupported numeric/qualitative claims; 0/50 exact source-fact projection differences
EN-007, EN-010, EN-023 and Chinese pairs: both NVIDIA Q1 gross-margin bases retained
Frozen historical grades unchanged: 29 CORRECT / 37 PARTIAL / 33 INCORRECT / 1 FAILED (not semantically re-graded)
Provider calls: 0; evaluator calls: 0; API cost: $0
```

The paired-margin extraction/period-binding regression is closed for the
covered filing and offline cases. This does not resolve or re-grade the
historical answer-quality failures, semantic citation support, or the full
bilingual quality audit. No Provider/evaluator call was made.

### 2026-09-18 Basis-aware source-target audit

The first current-code source audit after splitting margin requirements by
basis reported 142/148 projected facts. Inspection showed its source-target
builder selected a preferred value from all facts sharing company/metric/period
without filtering by `accounting_basis`. For a GAAP target that caused it to
select the distinct non-GAAP 75.0% value, so the correct answer was falsely
counted as missing. This was an audit/replay validation defect, not a new
retrieval or production-answer defect.

The source audit now selects target facts through the same basis-aware
requirement filter used by the production fact plan and stores basis identity
in each target. Historical replay also checks the cited answer against that
basis. Regression coverage verifies GAAP/non-GAAP target values and confirms
that swapping their labels fails projection.

Verification after the audit-target correction:

```text
Focused source-target / final-answer / evidence-first / fact-ledger tests: 153 passed
Full backend suite with ALLOW_REAL_PROVIDER=false: 2,519 passed, 23 skipped
Frontend tests: 33 passed
Frontend production build (TypeScript + Vite): PASS
Current source audit v31: 148/148 source facts retrieved and projected; 0 unsupported projected claims; 0/50 bilingual target/retrieval/context-plan differences
Historical raw-answer grounding replay v20: 100/100 rows; 148/148 basis-aware source targets projected; 0 final unsupported numeric/qualitative claims; 0/50 exact source-fact projection differences
Frozen historical grades unchanged: 29 CORRECT / 37 PARTIAL / 33 INCORRECT / 1 FAILED (not semantically re-graded)
Provider calls: 0; evaluator calls: 0; API cost: $0
```

This closes the false-positive projection gap caused by dropping accounting
basis in the audit target. The historical semantic grades, citation entailment
reviews, and full bilingual answer-quality equivalence remain separate open
gates. No Provider/evaluator call was made.

### 2026-09-18 Review-scope audit: explicit source restrictions

The frozen ZH-050 question explicitly asks the assistant to use only Apple's
filings to answer a question about NVIDIA Data Center growth. The frozen
answer says no relevant evidence was found and cites nothing. However, the
historical semantic reviewer was supplied the NVIDIA PDF based on the dataset's
`company: [NVIDIA]` metadata, and its rubric did not explicitly state that a
user's allowed-source restriction takes precedence over that metadata. The
review therefore may have penalized a refusal for not using evidence outside
the requested source scope. This is an evaluator-scope risk, not proof that the
frozen grade is wrong; the historical grade remains unchanged pending a
properly scoped adjudication.

The semantic-review rubric now explicitly says that user source restrictions
are binding, and that other-company PDFs and benchmark metadata cannot override
them. A provider-free contract test locks this rule. The original frozen
criteria, answer, reviews, and grades were not edited, and no semantic re-grade
was run.

Verification:

```text
ALLOW_REAL_PROVIDER=false pytest -q tests/evaluation/test_semantic_review_contract.py: 20 passed
Ruff (semantic reviewer and contract test): PASS
git diff --check (touched evaluation files): PASS
Provider/evaluator calls: 0; API cost: $0
```
