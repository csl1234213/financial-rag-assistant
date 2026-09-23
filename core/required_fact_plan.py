"""Provider-free required-fact planning and generation coverage checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from agent.planning.entity_extractor import extract_companies
from agent.reasoning_models import Evidence
from core.fact_ledger import (
    FactLedger,
    FinancialFact,
    canonical_company,
    canonical_metric_id,
    metric_aliases,
    periods_equivalent,
)
from core.financial_grounding import (
    NormalizedNumber,
    canonical_metrics,
    derived_growth,
    extract_normalized_numbers,
    numbers_equivalent,
)
from core.query_scope import (
    QueryScope,
    classify_query_scope,
    current_turn_query,
    is_nonfinancial_business_development_summary,
)
from retrieval.periods import extract_periods


@dataclass(frozen=True)
class RequiredFactSpec:
    company: str | None
    metric_id: str
    period: str | None
    reason: str
    accounting_basis: str | None = None
    growth_basis: str | None = None

    @property
    def key(self) -> str:
        parts = (canonical_company(self.company or ""), self.metric_id, self.period or "")
        if self.accounting_basis:
            parts = (*parts, self.accounting_basis)
        if self.growth_basis:
            parts = (*parts, f"growth_{self.growth_basis}")
        return "|".join(parts)


@dataclass(frozen=True)
class RequiredFactStatus:
    spec: RequiredFactSpec
    available: tuple[FinancialFact, ...]
    answer_present: bool = False


@dataclass(frozen=True)
class RequiredFactPlan:
    scope: str
    required: tuple[RequiredFactSpec, ...]

    def statuses(self, ledger: FactLedger, answer: str = "") -> tuple[RequiredFactStatus, ...]:
        return tuple(
            RequiredFactStatus(
                spec=spec,
                available=_facts_for_spec(spec, ledger),
                answer_present=answer_contains_fact(answer, spec, ledger),
            )
            for spec in self.required
        )

    def prompt_context(self, ledger: FactLedger) -> str:
        lines = ["REQUIRED FACT PLAN"]
        for status in self.statuses(ledger):
            state = "AVAILABLE" if status.available else "MISSING"
            lines.append(
                f"- company={status.spec.company or 'unspecified'}; metric_id={status.spec.metric_id}; "
                f"period={status.spec.period or 'unspecified'}; "
                f"accounting_basis={status.spec.accounting_basis or 'unspecified'}; "
                f"growth_basis={status.spec.growth_basis or 'unspecified'}; "
                f"status={state}; reason={status.spec.reason}"
            )
        return "\n".join(lines)

    def as_dict(self, ledger: FactLedger, answer: str = "") -> dict[str, object]:
        statuses = self.statuses(ledger, answer)
        return {
            "scope": self.scope,
            "required": [
                {
                    "company": status.spec.company,
                    "metric_id": status.spec.metric_id,
                    "period": status.spec.period,
                    "accounting_basis": status.spec.accounting_basis,
                    "growth_basis": status.spec.growth_basis,
                    "reason": status.spec.reason,
                    "available": bool(status.available),
                    "fact_ids": [fact.fact_id for fact in status.available],
                    "answer_present": status.answer_present,
                }
                for status in statuses
            ],
        }


def _period(question: str) -> str | None:
    periods = extract_periods(question)
    return periods[0] if periods else None


def _fact_accounting_basis(fact: FinancialFact) -> str | None:
    text = str(fact.evidence_text or "")
    # FactLedger prefixes each value with its explicit basis when a sentence
    # reports paired GAAP/non-GAAP margins. Prefer that scoped label over the
    # other basis mentioned later in the source sentence.
    scoped_basis = re.match(
        r"\s*(?P<basis>non[-\s\u2010-\u2014]?gaap|gaap)\b",
        text,
        re.IGNORECASE,
    )
    if scoped_basis:
        return "non_gaap" if scoped_basis.group("basis").casefold() != "gaap" else "gaap"
    if re.search(r"\bnon[-\s\u2010-\u2014]?gaap\b", text, re.IGNORECASE):
        return "non_gaap"
    if re.search(r"\bgaap\b", text, re.IGNORECASE):
        return "gaap"
    return None


def _facts_for_spec(spec: RequiredFactSpec, ledger: FactLedger) -> tuple[FinancialFact, ...]:
    facts = ledger.lookup(
        company=spec.company,
        metric_id=spec.metric_id,
        period=spec.period,
        growth_basis=spec.growth_basis,
    )
    if not spec.accounting_basis:
        return facts
    return tuple(fact for fact in facts if _fact_accounting_basis(fact) == spec.accounting_basis)


def _margin_specs_for_available_bases(
    company: str | None,
    metric_id: str,
    period: str | None,
    reason: str,
    ledger: FactLedger,
) -> list[RequiredFactSpec]:
    """Split a margin requirement only when source evidence labels both bases."""
    facts = ledger.lookup(company=company, metric_id=metric_id, period=period)
    bases = {_fact_accounting_basis(fact) for fact in facts}
    if metric_id in {"gross_margin", "operating_margin"} and bases >= {"gaap", "non_gaap"}:
        return [
            RequiredFactSpec(company, metric_id, period, reason, basis)
            for basis in ("gaap", "non_gaap")
        ]
    return [RequiredFactSpec(company, metric_id, period, reason)]


def _growth_specs_for_metrics(
    specs: Iterable[RequiredFactSpec], ledger: FactLedger
) -> list[RequiredFactSpec]:
    """Require reported or deterministically derivable comparison rates."""

    growth_specs: list[RequiredFactSpec] = []
    for spec in specs:
        for basis in ("yoy", "qoq"):
            if ledger.lookup(
                company=spec.company,
                metric_id=spec.metric_id,
                period=spec.period,
                growth_basis=basis,
            ):
                growth_specs.append(
                    RequiredFactSpec(
                        spec.company,
                        spec.metric_id,
                        spec.period,
                        f"explicitly reported {basis.upper()} change for a planned financial metric",
                        growth_basis=basis,
                    )
                )
                continue
            if basis != "yoy" or not spec.period:
                continue
            match = re.fullmatch(r"Q(?P<quarter>[1-4])_(?P<year>20\d{2})", spec.period)
            if not match:
                continue
            prior_period = f"Q{match.group('quarter')}_{int(match.group('year')) - 1}"
            current = ledger.lookup(company=spec.company, metric_id=spec.metric_id, period=spec.period)
            prior = ledger.lookup(company=spec.company, metric_id=spec.metric_id, period=prior_period)
            if current and prior:
                growth_specs.append(
                    RequiredFactSpec(
                        spec.company,
                        spec.metric_id,
                        spec.period,
                        "deterministically derivable YOY change from matching-period operands",
                        growth_basis="yoy",
                    )
                )
    return growth_specs


def _company_reporting_period(
    ledger: FactLedger,
    company: str,
    metric_id: str | None,
) -> str | None:
    """Choose the filing's reporting period for an unqualified comparison.

    Comparative tables often contain several historical quarters (and may
    even contain rows without a period).  When the question names companies
    but no explicit quarter, the document reporting period is the safest
    authoritative anchor: Tesla's Q2 2025 filing therefore maps to Q2_2025,
    while NVIDIA's Q1 FY2027 filing maps to Q1_FY2027.  A row period is only a
    fallback when no filing-level period is available.
    """

    facts = ledger.lookup(company=company, metric_id=metric_id)

    def usable_period(value: str | None) -> bool:
        normalized = str(value or "").strip().casefold().replace("-", "_")
        return normalized not in {
            "",
            "unknown",
            "undated",
            "none",
            "null",
            "n_a",
            "na",
            "not_available",
        }

    # Tenant uploads created by older ingestion versions may carry the
    # literal ``Unknown`` marker.  It is missing metadata, not an
    # authoritative filing period, and must not outvote a public filing's
    # real reporting period in mixed-scope retrieval.
    reporting = [
        fact.document_reporting_period
        for fact in facts
        if usable_period(fact.document_reporting_period)
    ]
    if reporting:
        # Preserve deterministic order while preferring the period repeated
        # by the greatest number of evidence rows.
        counts = {period: reporting.count(period) for period in dict.fromkeys(reporting)}
        report_period = max(counts, key=lambda period: (counts[period], period))
        if any(periods_equivalent(fact.fact_period, report_period) for fact in facts):
            return report_period
        # Filing-level quarter metadata is not row-level truth. When the
        # requested metric appears only in an annual comparison table, prefer
        # the matching fiscal year rather than relabeling it as Q4 actuals.
        report_year = re.search(r"20\d{2}", report_period)
        annual_period = f"FY{report_year.group(0)}" if report_year else None
        if annual_period and any(
            periods_equivalent(fact.fact_period, annual_period) for fact in facts
        ):
            return annual_period
        fact_periods = [fact.fact_period for fact in facts if usable_period(fact.fact_period)]
        if fact_periods:
            period_counts = {period: fact_periods.count(period) for period in dict.fromkeys(fact_periods)}
            return max(period_counts, key=lambda period: (period_counts[period], period))
        return report_period
    row_periods = [fact.fact_period for fact in facts if usable_period(fact.fact_period)]
    return row_periods[0] if row_periods else None


def infer_required_fact_plan(
    question: str, evidence: Iterable[Evidence], ledger: FactLedger | None = None
) -> RequiredFactPlan:
    items = list(evidence)
    ledger = ledger or FactLedger.from_evidence(items)
    intent_question = current_turn_query(question)
    scope = classify_query_scope(question)
    explicit_companies = [canonical_company(company) for company in extract_companies(question)]
    evidence_companies = list(ledger.companies())
    if explicit_companies:
        companies = explicit_companies
    elif scope == QueryScope.COMPARE:
        # A companyless comparison may refer to the set of available filings;
        # preserve each issuer partition rather than picking one at random.
        companies = evidence_companies[:3]
    elif len(evidence_companies) == 1:
        # A sole issuer in the conversation can safely resolve an elliptical
        # follow-up. Mixed-company context is ambiguous and must not silently
        # bind a generic fact question to whichever issuer sorts first.
        companies = evidence_companies
    else:
        companies = []
    if (
        not explicit_companies
        and scope in {QueryScope.FACT, QueryScope.SUMMARY}
        and len(evidence_companies) > 1
    ):
        return RequiredFactPlan(scope.value, ())
    period = _period(question)
    metric = canonical_metric_id(intent_question)

    def available_generic_margin_metrics() -> list[str]:
        return [
            metric_id
            for metric_id in ("gross_margin", "operating_margin")
            if any(
                ledger.lookup(company=company, metric_id=metric_id, period=period)
                for company in (companies or [None])
            )
        ]

    def margin_expanded_specs(
        company: str | None, metric_id: str, metric_period: str | None, reason: str
    ) -> list[RequiredFactSpec]:
        if metric_id in {"gross_margin", "operating_margin"}:
            return _margin_specs_for_available_bases(
                company, metric_id, metric_period, reason, ledger
            )
        return [RequiredFactSpec(company, metric_id, metric_period, reason)]

    asks_cash_flow = bool(re.search(r"\bcash\s+flows?\b|现金流", intent_question, re.I))
    if (metric == "cash_flow" or (metric is None and asks_cash_flow)) and ledger.lookup(
        metric_id="operating_cash_flow"
    ):
        metric = "operating_cash_flow"
    if scope == QueryScope.GENERAL_CONCEPT:
        return RequiredFactPlan(scope.value, ())
    if scope == QueryScope.ANALYSIS:
        # For causal/business-driver questions, complete only an explicitly
        # named segment's headline metric. This preserves a supported core
        # fact (e.g. Data Center revenue) without turning a driver question
        # into a whole-company financial summary.
        segment_metrics = {
            "automotive_revenue",
            "services_revenue",
            "data_center_revenue",
            "edge_computing_revenue",
        }
        requested_metrics = [
            metric_id
            for metric_id in canonical_metrics(intent_question)
            if metric_id in segment_metrics
        ]
        if not requested_metrics:
            return RequiredFactPlan(scope.value, ())
        return RequiredFactPlan(
            scope.value,
            tuple(
                RequiredFactSpec(
                    company,
                    metric_id,
                    period
                    or _company_reporting_period(ledger, company, metric_id)
                    or _company_reporting_period(ledger, company, None),
                    "explicit segment/business metric in an analytical query",
                )
                for company in (companies[:1] or [None])
                for metric_id in requested_metrics
            ),
        )
    if scope == QueryScope.FACT:
        requested_metrics = list(dict.fromkeys(canonical_metrics(intent_question)))
        if "cash_flow" in requested_metrics and ledger.lookup(metric_id="operating_cash_flow"):
            requested_metrics = [
                "operating_cash_flow" if item == "cash_flow" else item
                for item in requested_metrics
            ]
        if metric is not None and metric not in requested_metrics:
            requested_metrics.insert(0, metric)
        generic_margin_request = bool(
            re.search(r"\bmargins?\b|利润率", intent_question, re.IGNORECASE)
            and not re.search(
                r"\bgross\s+(?:profit\s+)?margins?\b|\boperating\s+(?:profit\s+)?margins?\b|毛利率|营业利润率",
                intent_question,
                re.IGNORECASE,
            )
        )
        if generic_margin_request:
            # An unqualified "margins" request does not assert that both
            # gross and operating margin are reported for this company/period.
            # Require the margin types actually present in evidence; explicitly
            # named metrics still remain required even when evidence is missing.
            requested_metrics = available_generic_margin_metrics() + [
                item for item in requested_metrics if item not in {"gross_margin", "operating_margin"}
            ]
        if not requested_metrics:
            # Do not silently answer an underspecified/general question with
            # whichever metric happened to be present in retrieved evidence.
            # The model may still answer from its grounded context, but the
            # fact ledger must not invent a revenue (or cash-flow) request.
            return RequiredFactPlan(scope.value, ())
        required_specs: list[RequiredFactSpec] = []
        for company in (companies[:1] or [None]):
            for requested_metric in requested_metrics:
                metric_period = period or (
                    _company_reporting_period(ledger, company, requested_metric)
                    or _company_reporting_period(ledger, company, None)
                )
                required_specs.extend(
                    margin_expanded_specs(
                        company, requested_metric, metric_period, "explicit fact request"
                    )
                )
        required_specs.extend(_growth_specs_for_metrics(required_specs, ledger))
        return RequiredFactPlan(scope.value, tuple(required_specs))
    if scope == QueryScope.COMPARE:
        comparison_metrics = list(dict.fromkeys(canonical_metrics(intent_question)))
        if "cash_flow" in comparison_metrics and ledger.lookup(metric_id="operating_cash_flow"):
            comparison_metrics = [
                "operating_cash_flow" if value == "cash_flow" else value
                for value in comparison_metrics
            ]
        general_financial_comparison = bool(
            re.search(
                r"\bfinancial\s+(?:performance|results?)\b|\bperform(?:ed|ance)\s+financially\b|"
                r"财务表现|财务业绩|财务状况|经营表现|经营业绩",
                intent_question,
                re.IGNORECASE,
            )
        )
        if not comparison_metrics and general_financial_comparison:
            comparison_metrics = [
                "revenue",
                "net_income",
                "gross_margin",
                "operating_margin",
                "operating_cash_flow",
                "eps",
            ]
        if not comparison_metrics:
            # Comparison intent alone does not imply a revenue comparison.
            # Risk, growth-driver, methodology, and business-factor questions
            # are prose comparisons; letting a default revenue requirement
            # leak into them created unrelated fact appends and inconsistent
            # EN/ZH coverage grades.
            return RequiredFactPlan(scope.value, ())
        required_specs: list[RequiredFactSpec] = []
        for company in companies:
            for requested_metric in comparison_metrics:
                metric_period = (
                    period
                    or _company_reporting_period(ledger, company, requested_metric)
                    or _company_reporting_period(ledger, company, None)
                )
                required_specs.extend(
                    margin_expanded_specs(
                        company,
                        requested_metric,
                        metric_period,
                        "one partition per named company, metric, and filing period",
                    )
                )
        return RequiredFactPlan(scope.value, tuple(required_specs))
    if scope == QueryScope.SUMMARY:
        headline_candidates = (
            "revenue",
            "automotive_revenue",
            "services_revenue",
            "net_income",
            "gross_profit",
            "eps",
            "operating_cash_flow",
            "gross_margin",
            "operating_margin",
            "data_center_revenue",
            "edge_computing_revenue",
        )
        # A summary-shaped sentence can still request one specific metric or
        # segment (e.g. "What does NVIDIA report about Data Center performance?").
        # Do not expand that narrow question into a whole-company financial
        # summary; the broader plan caused extra facts to be appended and made
        # otherwise-correct answers look incomplete. When the query names
        # financial metrics, keep the plan to those named metrics. A true
        # overall-performance question has no metric aliases and retains the
        # headline set below.
        requested_metrics = list(dict.fromkeys(canonical_metrics(intent_question)))
        segment_overview_request = bool(
            re.search(
                r"\b(?:business\s+)?segments?\b|\bbusiness\s+lines\b|"
                r"业务分部|业务板块|各业务|分部情况",
                intent_question,
                re.IGNORECASE,
            )
        )
        if (
            is_nonfinancial_business_development_summary(intent_question)
            and not requested_metrics
        ):
            # Narrative development questions must not inherit every headline
            # metric from the same filing. That caused automatic numeric
            # additions unrelated to the requested business developments.
            return RequiredFactPlan(scope.value, ())
        if segment_overview_request and not requested_metrics:
            # A request to summarize segment disclosures is not a request for
            # the issuer's consolidated headline metrics. Require only the
            # segment-level revenue facts that are actually present in the
            # evidence ledger; this also lets a supported segment fact replace
            # a model's stale "no segment data" refusal without appending
            # unrelated company-wide revenue/net-income figures.
            segment_metrics = (
                "automotive_revenue",
                "services_revenue",
                "data_center_revenue",
                "edge_computing_revenue",
            )
            required_segments = [
                RequiredFactSpec(
                    company,
                    metric_id,
                    period or (
                        _company_reporting_period(ledger, company, metric_id)
                        or _company_reporting_period(ledger, company, None)
                    ),
                    "available segment-level metric for a segment overview",
                )
                for company in (companies or [None])
                for metric_id in segment_metrics
                if ledger.lookup(company=company, metric_id=metric_id, period=period)
            ]
            return RequiredFactPlan(scope.value, tuple(required_segments))
        generic_margin_request = bool(
            re.search(r"\bmargins?\b|利润率", intent_question, re.I)
            and not re.search(r"gross|operating|毛利|营业利润", intent_question, re.I)
        )
        if generic_margin_request:
            # A generic follow-up such as "what about margins?" asks about
            # margin disclosures present in the filing, not every headline
            # metric and not margin types the filing does not report.
            requested_metrics = available_generic_margin_metrics() + [
                metric
                for metric in requested_metrics
                if metric not in {"gross_margin", "operating_margin"}
            ]
            if not requested_metrics:
                return RequiredFactPlan(scope.value, ())
        if "cash_flow" in requested_metrics and ledger.lookup(
            metric_id="operating_cash_flow"
        ):
            requested_metrics = [
                "operating_cash_flow" if metric == "cash_flow" else metric
                for metric in requested_metrics
            ]
        candidates = tuple(
            metric for metric in headline_candidates
            if not requested_metrics or metric in requested_metrics
        )
        company = companies[0] if companies else None
        required_items: list[RequiredFactSpec] = []
        for candidate in (requested_metrics or candidates):
            candidate_period = period or (
                (
                    _company_reporting_period(ledger, company, candidate)
                    or _company_reporting_period(ledger, company, None)
                )
                if company
                else None
            )
            # Preserve explicitly requested metrics even when current context
            # lacks them. The prompt must distinguish "not retrieved" from
            # "not requested"; completion still only uses available facts.
            if requested_metrics or ledger.lookup(company=company, metric_id=candidate, period=candidate_period):
                required_items.extend(
                    margin_expanded_specs(
                        company, candidate, candidate_period, "headline summary metric"
                    )
                )
        required_items.extend(_growth_specs_for_metrics(required_items, ledger))
        required = tuple(required_items)
        return RequiredFactPlan(
            scope.value,
            required
            or (RequiredFactSpec(companies[0] if companies else None, "revenue", period, "headline summary metric"),),
        )
    return RequiredFactPlan(scope.value, ())


def _fact_alias_present(line: str, metric_id: str) -> bool:
    lowered = line.casefold()
    aliases = metric_aliases(metric_id) or (metric_id,)
    if metric_id == "revenue":
        # A segment's revenue is not evidence for consolidated revenue, even
        # when the same numeric value happens to appear elsewhere in context.
        explicit_total = bool(
            re.search(
                r"\btotal\s+(?:net\s+)?revenues?\b|"
                r"总(?:收入|营收)|营业总收入|合并(?:收入|营收)",
                lowered,
            )
        )
        if explicit_total:
            return True
        segment_markers = (
            "automotive", "services", "service revenue", "data center", "datacenter",
            "data centre", "datacentre", "edge computing", "edge revenue", "segment",
            "product revenue", "iphone", "ipad", "mac revenue", "汽车业务", "服务收入",
            "服务业务", "数据中心", "边缘计算", "分部收入",
        )
        if any(marker in lowered for marker in segment_markers):
            return False
    return any(alias.casefold() in lowered for alias in aliases)


def _number_matches_fact(claim: NormalizedNumber, fact: FinancialFact) -> bool:
    """Compare a claim with a ledger fact without erasing its financial unit."""
    if fact.unit == "percent":
        if claim.kind == "percent":
            return claim.value == fact.normalized_value
        if claim.kind == "basis_points":
            return claim.value / Decimal("100") == fact.normalized_value
        return False
    return numbers_equivalent(
        claim,
        NormalizedNumber(fact.normalized_value, "amount", fact.currency),
    )


def answer_contains_fact(answer: str, spec: RequiredFactSpec, ledger: FactLedger) -> bool:
    facts = _facts_for_spec(spec, ledger)
    if not facts:
        return False
    for line in str(answer or "").splitlines():
        if spec.accounting_basis:
            if spec.accounting_basis == "non_gaap" and not re.search(
                r"\bnon[-\s\u2010-\u2014]?gaap\b|非\s*gaap|非通用会计准则",
                line,
                re.IGNORECASE,
            ):
                continue
            # Unqualified reported margin values use the GAAP basis by
            # default. Never let a line explicitly marked non-GAAP satisfy it.
            if spec.accounting_basis == "gaap" and re.search(
                r"\bnon[-\s\u2010-\u2014]?gaap\b|非\s*gaap|非通用会计准则",
                line,
                re.IGNORECASE,
            ):
                continue
        named = {canonical_company(company) for company in extract_companies(line)}
        if named and canonical_company(spec.company or "") not in named:
            continue
        named_periods = extract_periods(line)
        if spec.period and named_periods and not any(
            periods_equivalent(period, spec.period) for period in named_periods
        ):
            continue
        if not _fact_alias_present(line, spec.metric_id):
            continue
        if spec.growth_basis and not _growth_basis_present(line, spec.growth_basis):
            continue
        claims = extract_normalized_numbers(line)
        if any(
            _number_matches_fact(claim, fact)
            for claim in claims
            for fact in facts
        ):
            return True
    return False


def _growth_basis_present(line: str, basis: str) -> bool:
    if basis == "yoy":
        pattern = (
            r"\b(?:y\s*/\s*y|yoy|year[- ]over[- ]year|from\s+(?:a|the same period a)\s+year\s+ago)\b|"
            r"同比|较上年同期"
        )
    elif basis == "qoq":
        pattern = (
            r"\b(?:q\s*/\s*q|qoq|quarter[- ]over[- ]quarter|"
            r"from\s+(?:the\s+)?previous\s+quarter|sequential(?:ly)?)\b|环比|较上季度"
        )
    else:
        return False
    return bool(re.search(pattern, line, re.IGNORECASE))


def _render_fact(fact: FinancialFact) -> str:
    amount = fact.normalized_value
    if fact.display_unit == "million":
        # Explicit period-labelled table cells retain the source statement's
        # readable scale; narrative and legacy flattened rows use the
        # magnitude-based rendering below.
        displayed = amount / Decimal("1000000") if amount >= Decimal("1000000") else amount
        rendered = f"{int(displayed):,}" if displayed == displayed.to_integral_value() else _plain_decimal(displayed)
        return f"{rendered} million"
    if fact.unit == "billion":
        return f"{_plain_decimal(amount / Decimal('1000000000'))} billion"
    if fact.unit == "million":
        return f"{_plain_decimal(amount / Decimal('1000000'))} million"
    if fact.unit == "percent":
        return f"{_plain_decimal(amount)}%"
    return _plain_decimal(amount)


def _plain_decimal(value: Decimal) -> str:
    """Render normalized decimals without exponent notation for user-facing text."""
    return format(value.normalize(), "f")


def _label_unqualified_gaap_margin(
    answer: str, spec: RequiredFactSpec, facts: tuple[FinancialFact, ...]
) -> str:
    """Make the default GAAP basis explicit without duplicating a supported value."""
    output: list[str] = []
    chinese = any("\u3400" <= char <= "\u9fff" for char in answer)
    for line in str(answer or "").splitlines():
        if (
            _fact_alias_present(line, spec.metric_id)
            and not re.search(
                r"\b(?:non[-\s\u2010-\u2014]?gaap|gaap)\b|非\s*gaap|非通用会计准则",
                line,
                re.IGNORECASE,
            )
            and any(
                _number_matches_fact(value, fact)
                for value in extract_normalized_numbers(line)
                for fact in facts
            )
        ):
            alias = next(
                (value for value in metric_aliases(spec.metric_id) if value.casefold() in line.casefold()),
                None,
            )
            if alias:
                replacement = f"GAAP{alias}" if chinese else f"GAAP {alias}"
                line = re.sub(re.escape(alias), replacement, line, count=1, flags=re.IGNORECASE)
        output.append(line)
    return "\n".join(output)


def _preferred_fact(
    facts: tuple[FinancialFact, ...],
    metric_id: str,
    *,
    question: str = "",
    requested_period: str | None = None,
) -> FinancialFact:
    """Choose the most authoritative value when one row yields several facts.

    Financial statement chunks commonly contain both a metric's component rows
    (for example depreciation) and its total row.  The ledger keeps both for
    auditability; answer completion must prefer the explicit total/value row
    instead of whichever parser match happened to appear first.
    """

    prefer_non_gaap = bool(
        re.search(r"\bnon[-\s]?gaap\b|非\s*gaap|非通用会计准则", question, re.IGNORECASE)
    )
    prefer_basic_eps = metric_id == "eps" and bool(
        re.search(r"\bbasic\s+(?:earnings\s+per\s+share|eps)\b|基本每股收益", question, re.IGNORECASE)
    )
    prefer_cumulative = bool(
        re.search(
            r"\b(?:six[- ]months?|year[- ]to[- ]date|ytd|first half)\b|"
            r"(?:前六个月|前6个月|上半年|累计)",
            question,
            re.IGNORECASE,
        )
    )
    period_requests_quarter = bool(
        requested_period
        and re.search(r"(?:^|[^A-Z0-9])Q[1-4](?:$|[^A-Z0-9])", requested_period, re.IGNORECASE)
    )
    prefer_quarter = not prefer_cumulative and (period_requests_quarter or bool(
        re.search(
            r"\bq[1-4](?:\s*(?:fy\s*)?20\d{2})?\b|\bquarter(?:ly)?\b|"
            r"[一二三四1-4]\s*季度|季度",
            question,
            re.IGNORECASE,
        )
    ))

    def score(fact: FinancialFact) -> tuple[int, int, float, str]:
        text = fact.evidence_text.casefold()
        section = (fact.section or "").casefold()
        value_row = 0
        if prefer_cumulative:
            value_row += 24 if fact.period_type in {"six_months", "nine_months"} else 0
            value_row -= 24 if fact.period_type == "fiscal_quarter" else 0
        elif prefer_quarter:
            value_row += 24 if fact.period_type == "fiscal_quarter" else 0
            value_row -= 24 if fact.period_type in {"six_months", "nine_months"} else 0
        if metric_id == "operating_cash_flow":
            if re.search(
                r"cash\s+generated\s+by\s+operating\s+activities\s+(?:\$\s*)?[\d,(.-]+",
                text,
            ) or "经营活动现金流" in text:
                value_row += 20
            if any(
                marker in text
                for marker in ("depreciation and amortization", "share-based compensation")
            ):
                value_row -= 10
        elif metric_id == "net_income":
            # The cash-flow reconciliation repeats net income as a six-month
            # subtotal.  Prefer the statement-of-operations row for an
            # unqualified summary instead of that repeated subtotal.
            if "net income attributable to common stockholders" in text:
                value_row += _accounting_basis_score(text, prefer_non_gaap)
            if text.lstrip().startswith("net income"):
                value_row += 12
            if "operating activities" in section:
                value_row -= 15
            if any(marker in section for marker in ("instruments", "securities")):
                value_row -= 8
        elif metric_id == "eps":
            if "earnings per share" in section or text.lstrip().startswith("earnings per share"):
                value_row += 12
            if section.startswith("numerator"):
                value_row -= 5
            if re.search(r"\bdiluted\b", text):
                value_row += 14 if not prefer_basic_eps else -14
            elif re.search(r"\bbasic\b", text):
                value_row += 14 if prefer_basic_eps else -14
            value_row += _accounting_basis_score(text, prefer_non_gaap)
        elif metric_id in {
            "gross_profit",
            "gross_margin",
            "automotive_gross_margin",
            "operating_income",
            "operating_margin",
        }:
            value_row += _accounting_basis_score(text, prefer_non_gaap)
        elif metric_id == "revenue":
            if text.lstrip().startswith(("net sales", "total revenue", "total revenues")):
                value_row += 8
            # Segment/geography tables repeat net sales but are not the
            # consolidated headline revenue requested by a summary question.
            if any(marker in section for marker in ("china", "japan", "asia", "segment")):
                value_row -= 8
        if fact.table_row_period or fact.table_column_period:
            value_row += 2
        if fact.fact_period:
            value_row += 1
        return (value_row, int(fact.confidence * 1000), float(fact.normalized_value), fact.fact_id)

    return max(facts, key=score)


def _accounting_basis_score(text: str, prefer_non_gaap: bool) -> int:
    non_gaap = bool(re.search(r"\bnon[-\s]?gaap\b", text))
    gaap = bool(re.search(r"\bgaap\b", text)) and not non_gaap
    if non_gaap:
        return 24 if prefer_non_gaap else -12
    if gaap:
        return -12 if prefer_non_gaap else 24
    return 0


def complete_from_fact_ledger(
    answer: str, plan: RequiredFactPlan, ledger: FactLedger,
    *, question: str | None = None, evidence: Iterable[Evidence] | None = None,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """Complete omitted available facts without another provider call."""

    additions: list[str] = []
    fact_ids: list[str] = []
    labels = {
        "operating_cash_flow": "operating cash flow",
        "cash_paid_for_taxes": "cash paid for income taxes",
        "automotive_revenue": "Automotive revenue",
        "services_revenue": "Services revenue",
        "data_center_revenue": "Data Center revenue",
        "edge_computing_revenue": "Edge Computing revenue",
        "net_income": "net income",
        "gross_profit": "gross profit",
        "revenue": "revenue",
        "eps": "EPS",
        "gross_margin": "gross margin",
        "automotive_gross_margin": "automotive gross margin",
        "operating_margin": "operating margin",
    }
    chinese = any("\u3400" <= char <= "\u9fff" for char in str(question if question is not None else answer))
    citation_ranks = {str(item.metadata.get("chunk_id", "")): index
                      for index, item in enumerate(evidence or (), 1)}
    zh_labels = {
        "operating_cash_flow": "经营活动现金流",
        "automotive_revenue": "汽车业务收入",
        "services_revenue": "服务业务收入",
        "data_center_revenue": "数据中心收入",
        "edge_computing_revenue": "边缘计算收入",
        "net_income": "净利润",
        "gross_profit": "毛利额",
        "revenue": "营收",
        "eps": "每股收益",
        "gross_margin": "毛利率",
        "automotive_gross_margin": "汽车业务毛利率",
        "operating_margin": "营业利润率",
    }
    company_labels = {
        "apple": "Apple",
        "tesla": "Tesla",
        "nvidia": "NVIDIA",
        "microsoft": "Microsoft",
    }
    zh_company_labels = {
        "apple": "苹果",
        "tesla": "特斯拉",
        "nvidia": "英伟达",
        "microsoft": "微软",
    }
    for status in plan.statuses(ledger, answer):
        answer_present = status.answer_present
        if (
            status.spec.accounting_basis == "gaap"
            and answer_present
            and status.spec.metric_id in {"gross_margin", "operating_margin"}
        ):
            answer = _label_unqualified_gaap_margin(
                answer, status.spec, status.available
            )
        if answer_present and status.spec.metric_id == "net_income":
            # An explicitly labelled non-GAAP value must not satisfy an
            # unqualified net-income requirement (whose default basis is
            # GAAP), and vice versa. Otherwise a model can provide only the
            # adjusted figure and suppress completion of the reported GAAP
            # fact even when the filing contains both.
            prefer_non_gaap = bool(
                re.search(
                    r"\bnon[-\s]?gaap\b|非\s*gaap|非通用会计准则",
                    str(question or ""),
                    re.IGNORECASE,
                )
            )
            basis_facts = tuple(
                fact for fact in status.available
                if _accounting_basis_score(fact.evidence_text.casefold(), prefer_non_gaap) > 0
            )
            if basis_facts:
                answer_present = answer_contains_fact(
                    answer, status.spec, FactLedger(basis_facts)
                )
        if answer_present or not status.available:
            continue
        fact = _preferred_fact(
            status.available,
            status.spec.metric_id,
            question=str(question or ""),
            requested_period=status.spec.period,
        )
        label = (
            zh_labels.get(fact.metric_id, labels.get(fact.metric_id, fact.metric_id))
            if chinese
            else labels.get(fact.metric_id, fact.metric_id)
        )
        if status.spec.growth_basis:
            if chinese:
                label += "同比增长" if status.spec.growth_basis == "yoy" else "环比增长"
            else:
                label += " YoY growth" if status.spec.growth_basis == "yoy" else " QoQ growth"
        if status.spec.accounting_basis:
            if chinese:
                label = (
                    f"非GAAP{label}"
                    if status.spec.accounting_basis == "non_gaap"
                    else f"GAAP{label}"
                )
            else:
                label = (
                    f"non-GAAP {label}"
                    if status.spec.accounting_basis == "non_gaap"
                    else f"GAAP {label}"
                )
        if (plan.scope == QueryScope.COMPARE.value or evidence is not None) and fact.fact_period:
            company_label = (
                zh_company_labels.get(fact.company, fact.company)
                if chinese
                else company_labels.get(fact.company, fact.company)
            )
            rendered_period = fact.fact_period.replace("_", " ") if evidence is not None else fact.fact_period
            label = f"{company_label} {rendered_period} {label}"
        if evidence is not None and fact.period_type == "six_months":
            label += "（六个月累计）" if chinese else " (six months cumulative)"
        rendered = f"{label}: {_render_fact(fact)}"
        if evidence is not None:
            if fact.currency:
                rendered += f" {fact.currency.upper()}"
            rank = citation_ranks.get(fact.chunk_id)
            if rank is None:
                continue
            rendered += f" [Evidence {rank}]"
        additions.append(rendered)
        fact_ids.append(fact.fact_id)
    if not additions:
        return answer, (), ()
    prefix = "补充的已验证事实：" if chinese else "Verified facts: "
    if evidence is not None:
        completed = f"{str(answer).rstrip()}\n\n" + "\n".join(f"- {item}." for item in additions)
    else:
        completed = f"{str(answer).rstrip()}\n\n{prefix}{'; '.join(additions)}."
    return completed, tuple(fact_ids), tuple(additions)


@dataclass(frozen=True)
class GenerationCheck:
    disposition: str
    supported_fact_ids: tuple[str, ...]
    rejected_lines: tuple[str, ...]
    missing_fact_ids: tuple[str, ...]
    completed_answer: str


def check_generation(answer: str, plan: RequiredFactPlan, ledger: FactLedger) -> GenerationCheck:
    """Validate a draft and deterministically complete omitted available facts."""

    rejected: list[str] = []
    supported: list[str] = []
    for line in str(answer or "").splitlines():
        values = extract_normalized_numbers(line)
        if not values:
            continue
        metric = canonical_metric_id(line)
        if metric == "cash_paid_for_taxes" and any(spec.metric_id == "operating_cash_flow" for spec in plan.required):
            rejected.append(line)
            continue
        matched = False
        for spec in plan.required:
            if metric and metric != spec.metric_id:
                continue
            for fact in ledger.lookup(
                company=spec.company,
                metric_id=spec.metric_id,
                period=spec.period,
                growth_basis=spec.growth_basis,
            ):
                if any(_number_matches_fact(value, fact) for value in values):
                    supported.append(fact.fact_id)
                    matched = True
        if not matched and metric:
            rejected.append(line)
    completed, added_ids, _ = complete_from_fact_ledger(answer, plan, ledger)
    supported.extend(added_ids)
    missing = tuple(
        fact.fact_id
        for status in plan.statuses(ledger, completed)
        if status.available and not status.answer_present
        for fact in status.available[:1]
    )
    disposition = "REJECT" if rejected else ("COMPLETE" if added_ids else "KEEP")
    return GenerationCheck(disposition, tuple(dict.fromkeys(supported)), tuple(rejected), missing, completed)


def safe_answer_from_fact_ledger(
    answer: str, plan: RequiredFactPlan, ledger: FactLedger
) -> tuple[str, tuple[str, ...]]:
    """Remove numeric lines that cannot be proven by a planned ledger fact."""

    removed: list[str] = []
    output: list[str] = []

    def fragment_is_supported(fragment: str) -> bool:
        values = extract_normalized_numbers(fragment)
        if not values:
            return True
        metric = canonical_metric_id(fragment)
        candidates = [
            fact
            for spec in plan.required
            if (not metric or metric == spec.metric_id)
            for fact in ledger.lookup(
                company=spec.company,
                metric_id=spec.metric_id,
                period=spec.period,
                growth_basis=spec.growth_basis,
            )
        ]
        if any(value.kind == "percent" for value in values):
            for spec in plan.required:
                if spec.growth_basis != "yoy" or not spec.period:
                    continue
                match = re.fullmatch(r"Q(?P<quarter>[1-4])_(?P<year>20\d{2})", spec.period)
                if not match:
                    continue
                prior_period = f"Q{match.group('quarter')}_{int(match.group('year')) - 1}"
                current = ledger.lookup(company=spec.company, metric_id=spec.metric_id, period=spec.period)
                prior = ledger.lookup(company=spec.company, metric_id=spec.metric_id, period=prior_period)
                for current_fact in current:
                    for prior_fact in prior:
                        derived = derived_growth(
                            NormalizedNumber(current_fact.normalized_value, "amount", current_fact.currency),
                            NormalizedNumber(prior_fact.normalized_value, "amount", prior_fact.currency),
                        )
                        if derived and any(numbers_equivalent(value, derived) for value in values):
                            return True
        return all(
            any(_number_matches_fact(value, fact) for fact in candidates)
            for value in values
        )

    for line in str(answer or "").splitlines():
        values = extract_normalized_numbers(line)
        if not values:
            output.append(line)
            continue
        fragments = [
            part
            for part in re.split(r"(?<=[。；！!？?])\s*|(?<!\d)\.(?=\s|$)", line)
            if part
        ]
        if len(fragments) == 1 and ";" in line:
            fragments = [part for part in line.split(";") if part]
        supported_fragments = [fragment for fragment in fragments if fragment_is_supported(fragment)]
        if len(supported_fragments) == len(fragments):
            output.append(line)
        else:
            removed.append(line)
            if supported_fragments:
                output.append(" ".join(supported_fragments))
            else:
                output.append(
                    "证据不足，无法可靠支持该数字结论。"
                    if any("\u3400" <= char <= "\u9fff" for char in line)
                    else "Insufficient evidence to support this numeric claim."
                )
    return "\n".join(output).strip(), tuple(removed)
