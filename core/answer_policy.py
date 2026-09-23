"""One production boundary for completing and grounding the final answer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from agent.planning.entity_extractor import extract_companies
from agent.reasoning_models import Evidence
from core.answer_grounding import GroundingResult, sanitize_answer
from core.fact_ledger import FactLedger, canonical_company, canonical_metric_id, periods_equivalent
from core.financial_grounding import canonical_metrics, extract_normalized_numbers, numbers_equivalent
from core.growth_driver_evidence import (
    answer_has_cited_growth_driver,
    extract_growth_driver_passages,
    is_driver_absence_claim,
)
from core.query_scope import (
    QueryScope,
    classify_query_scope,
    current_turn_query,
    is_nonfinancial_business_development_summary,
)
from core.required_fact_plan import (
    RequiredFactPlan,
    _fact_alias_present,
    complete_from_fact_ledger,
    infer_required_fact_plan,
)
from retrieval.periods import extract_periods


@dataclass(frozen=True)
class FinalAnswer:
    grounded: GroundingResult
    raw_grounding: GroundingResult
    plan: RequiredFactPlan
    ledger: FactLedger
    added_fact_ids: tuple[str, ...]
    removed_lines: tuple[str, ...]
    prepared_answer: str
    verified_facts_only_projection: bool = False

    @property
    def answer(self) -> str:
        return self.grounded.answer


def no_evidence_response(question: str) -> str:
    """Return a useful, localized explanation when retrieval found no source.

    Keep this issuer-agnostic: absence from the current retrieval result must
    not be converted into a benchmark-specific answer or a claim that a
    company does not publish the requested data.
    """

    if any("\u3400" <= char <= "\u9fff" for char in str(question or "")):
        return (
            "当前可检索的上传财报中没有找到足以支持该问题的证据，"
            "证据不足以可靠回答。"
            "请上传相关公司及报告期的财报后再试。"
        )
    return (
        "No relevant uploaded-filing evidence was retrieved for this question, "
        "so I can't answer it reliably. Upload the relevant company's filing "
        "for the requested period and try again."
    )


def _retrieved_evidence_insufficient_response(question: str) -> str:
    """Describe a non-empty retrieval set that yielded no trusted evidence."""
    if any("\u3400" <= char <= "\u9fff" for char in str(question or "")):
        return "当前检索到的证据不足以可靠回答该问题。"
    return "The retrieved passages are insufficient to answer this question reliably."


def _scope_claim_fragments(line: str) -> list[str]:
    """Split an answer line into clauses without breaking decimals/citations."""
    bound = re.sub(
        r"([.;；。!?])\s*((?:\[Evidence\s+\d+\]\s*)+)",
        lambda match: " " + match.group(2).strip() + match.group(1) + " ",
        line,
        flags=re.I,
    )
    # Requiring whitespace after a Latin full stop avoids splitting decimals
    # such as 17.2%; CJK sentence punctuation may be immediately adjacent.
    fragments = re.split(r"(?<=[!?。！？；;])\s*|(?<=\.)\s+", bound)
    return [fragment for fragment in fragments if fragment.strip()]


def _scope_answer(question: str, answer: str) -> tuple[str, tuple[str, ...]]:
    """Drop answer claims that exceed the financial scope the user requested."""
    intent_question = current_turn_query(question)
    scope = classify_query_scope(intent_question)
    if is_nonfinancial_business_development_summary(intent_question):
        financial_metrics = {
            "revenue",
            "automotive_revenue",
            "services_revenue",
            "data_center_revenue",
            "edge_computing_revenue",
            "gross_profit",
            "net_income",
            "operating_income",
            "gross_margin",
            "operating_margin",
            "eps",
            "operating_cash_flow",
            "free_cash_flow",
        }
        financial_heading = re.compile(
            r"(?i)^\s{0,3}#{0,3}\s*(?:financial\s+(?:summary|performance|results?)|"
            r"财务(?:摘要|表现|业绩|情况)|经营业绩)\s*:?\s*$"
        )
        business_heading = re.compile(
            r"(?i)^\s{0,3}#{0,3}\s*(?:business\s+developments?|operational\s+highlights?|"
            r"业务发展|业务进展|运营亮点|经营动态)\s*:?\s*$"
        )
        event_language = re.compile(
            r"(?i)launch|launched|roll(?:ed)?\s+out|deployed|began|opened|expanded|"
            r"production|deliver(?:y|ies)|robotaxi|cybercab|optimus|FSD|storage|"
            r"milestone|initiative|partnership|announced|introduced|built|installed|"
            r"推出|发布|启动|部署|开展|扩大|生产|交付|储能|里程碑|合作|建成|安装|投产|开设"
        )
        financial_section = False
        kept: list[str] = []
        removed: list[str] = []
        for line in answer.splitlines():
            if financial_heading.search(line):
                financial_section = True
                kept.append(line)
                continue
            if business_heading.search(line):
                financial_section = False
                kept.append(line)
                continue
            fragments = _scope_claim_fragments(line)
            retained: list[str] = []
            for fragment in fragments:
                metrics = set(canonical_metrics(fragment))
                if metrics & financial_metrics:
                    removed.append(fragment)
                elif (
                    financial_section
                    and extract_normalized_numbers(fragment)
                    and not event_language.search(fragment)
                ):
                    # A financial-summary table is not evidence of a dated
                    # business development. Keep operational milestones and
                    # launch/update claims, but not adjacent financial stats.
                    removed.append(fragment)
                else:
                    retained.append(fragment)
            if retained:
                kept.append(" ".join(retained))
            elif not line.strip():
                kept.append(line)
        return "\n".join(kept).strip(), tuple(removed)
    risk_only_query = bool(
        re.search(r"(?i)\brisk\b|\brisks\b|\bchallenge\b|\bchallenges\b|风险|挑战", intent_question)
        and not canonical_metrics(intent_question)
    )
    if risk_only_query:
        # Risk answers may contain quantitative exposure evidence, but a
        # supported revenue/earnings fact is not automatically relevant just
        # because it came from the same filing. Keep metric claims only when
        # the same sentence connects them to an identified risk mechanism.
        risk_link = re.compile(
            r"(?i)risk|uncertain|challenge|exposure|concentrat|depend|reliance|"
            r"vulnerab|threat|pressure|shortage|constraint|regulat|tariff|litigat|"
            r"debt|liquidity|supply|safety|风险|不确定|挑战|暴露|集中|依赖|脆弱|"
            r"威胁|压力|短缺|约束|监管|关税|诉讼|债务|流动性|供应|安全"
        )
        kept: list[str] = []
        removed: list[str] = []
        for line in answer.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                kept.append(line)
                continue
            fragments = _scope_claim_fragments(line)
            kept_fragments: list[str] = []
            for fragment in fragments:
                if not fragment.strip():
                    continue
                metrics = canonical_metrics(fragment)
                if metrics and not risk_link.search(fragment):
                    removed.append(fragment)
                else:
                    kept_fragments.append(fragment)
            if kept_fragments:
                kept.append(" ".join(kept_fragments))
        return "\n".join(kept).strip(), tuple(removed)

    segment_overview = bool(
        scope == QueryScope.SUMMARY
        and re.search(
            r"\b(?:business\s+)?segments?\b|\bbusiness\s+lines\b|"
            r"业务分部|业务板块|各业务|分部情况",
            question,
            re.IGNORECASE,
        )
        and not canonical_metrics(intent_question)
    )
    if segment_overview:
        # Segment summaries can include segment-level metrics, but unrelated
        # consolidated figures should not be appended as extra answer claims.
        segment_metrics = {
            "automotive_revenue",
            "services_revenue",
            "data_center_revenue",
            "edge_computing_revenue",
        }
        consolidated_metrics = {
            "revenue", "net_income", "operating_income", "eps",
            "gross_margin", "operating_margin", "operating_cash_flow",
        }
        kept, removed = [], []
        for line in answer.splitlines():
            kept_fragments: list[str] = []
            for fragment in _scope_claim_fragments(line):
                line_metrics = set(canonical_metrics(fragment))
                if (
                    line_metrics & consolidated_metrics
                    and not line_metrics & segment_metrics
                    and not _EVIDENCE_ABSENCE.search(fragment)
                ):
                    removed.append(fragment)
                else:
                    kept_fragments.append(fragment)
            if kept_fragments:
                kept.append(" ".join(kept_fragments))
            elif not line.strip():
                kept.append(line)
        return "\n".join(kept).strip(), tuple(removed)

    if scope not in {QueryScope.FACT, QueryScope.COMPARE} or not canonical_metric_id(intent_question):
        return answer, ()
    irrelevant = re.compile(
        r"business strategy|ai technology|infrastructure|competitive advantages|investment (?:implications|outlook)|"
        r"opportunities|risks|future outlook|业务战略|商业战略|人工智能技术|基础设施|"
        r"竞争优势|投资建议|投资展望|风险|未来展望", re.I,
    )
    kept, removed = [], []
    skip = False
    for line in answer.splitlines():
        heading = line.strip().strip("#* ").strip()
        is_heading = line.lstrip().startswith("#") or bool(re.fullmatch(r"\d+[.)]\s+[^.!?。]+", heading))
        if is_heading:
            skip = bool(irrelevant.search(heading))
        if skip:
            removed.append(line)
        else:
            kept.append(line)
    return "\n".join(kept), tuple(removed)


_EN_REFUSAL = "Insufficient evidence to support this numeric claim."
_ZH_REFUSAL = "证据不足，无法可靠支持该数字结论。"
_REFUSAL_FRAGMENT = re.compile(
    r"(?i)insufficient evidence to support this numeric claim\.?|"
    r"证据不足，无法可靠支持该数字结论。?"
)
_RETRIEVAL_LIMITATION = re.compile(
    r"(?i)(?:(?:the\s+)?(?:retrieved\s+passages|retrieved\s+evidence|available\s+evidence)\s+"
    r"(?:are|is)\s+insufficient\s+to\s+(?:establish\s+this\s+information|"
    r"answer\s+(?:this|the)\s+question\s+reliably|reliably\s+answer\s+"
    r"(?:this|the)\s+question|support\s+(?:this|the)\s+answer)\.?|"
    r"当前检索到的证据不足以(?:确认该信息|可靠回答该问题|回答该问题|"
    r"可靠回答此问题|确认该事项)。?)"
)
_EVIDENCE_ABSENCE = re.compile(
    r"(?i)(?:\b(?:evidence|filing|report|document|source|passages?|provided data)\s+"
    r"(?:does not|doesn't|did not|didn't|do not|don't)\s+"
    r"(?:provide|contain|include|show|identify|disclose|report|establish)\b|"
    r"\b(?:not provided|not contained|not included|not disclosed|not reported|not available|"
    r"no\s+(?:[\w-]+\s+){0,5}(?:revenue|sales|income|earnings|margin|eps|cash flow|"
    r"segment data|business segments)\b|"
    r"(?:is|are|remains?)\s+(?:absent|missing|unavailable)\b|"
    r"(?:evidence|filing|report|document|source)\s+(?:lacks?|omits?)\b|"
    r"\bno\b.{0,180}\b(?:figures?|values?|facts?|data|breakdown|disclosures?)\s+"
    r"(?:appear|appears|are|is|were|was)\s+(?:in|from|within)\s+(?:the\s+)?"
    r"(?:retrieved\s+)?(?:evidence|filing|report|document|source)\b|"
    r"no\s+(?:[\w-]+\s+){0,12}(?:figures?|values?|facts?|data|breakdown|disclosures?)\s+"
    r"(?:appear|appears|are|is|were|was)\s+(?:in|from|within)\s+(?:the\s+)?"
    r"(?:evidence|filing|report|document|source)\b|"
    r"cannot determine|can't determine|unable to determine|unable to verify|"
    r"insufficient evidence|evidence.{0,24}insufficient)\b|"
    r"(?:證據|证据|财报|財報|报告|報告|资料|資料|文档|文件).{0,36}"
    r"(?:未提供|未披露|未报告|未報告|没有包含|沒有包含|没有出现|沒有出現|不包含|不包括|缺少|缺失|未见|未找到|不存在|无法确认|無法確認|无法确定|無法確定)|"
    r"(?:未提供|未披露|未报告|未報告|没有包含|沒有包含|没有出现|沒有出現|不包含|不包括|缺少|缺失|未见|未找到|不存在).{0,36}"
    r"(?:财报|財報|报告|報告|证据|證據|资料|資料|文档|文件)|"
    r"所引财报证据不足以支持该表述|"
    r"(?:没有|沒有|未能|无法|無法).{0,12}(?:提供|披露|报告|報告|确认|確認|找到|确定|確定))"
)

_UNSTRUCTURED_METRIC_PATTERNS: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (
        re.compile(r"(?i)\b(?:price\s+target|target\s+price|12[- ]month\s+target)\b|股价目标|目标股价|目标价"),
        ("price target", "target price", "12-month target", "股价目标", "目标股价", "目标价"),
    ),
    (
        re.compile(r"(?i)\b(?:expected\s+stock\s+price|stock\s+price\s+(?:forecast|prediction)|future\s+stock\s+price)\b|预期股价|(?:预测|未来)股价"),
        (
            "expected stock price", "stock price forecast", "stock price prediction",
            "future stock price", "预期股价", "股价预测", "预测股价", "未来股价",
        ),
    ),
    (
        re.compile(r"(?i)\b(?:stock|share)\s+price\b|股价|股票价格"),
        ("stock price", "share price", "股价", "股票价格"),
    ),
    (
        re.compile(r"(?i)\bmarket\s+share\b|市场份额|市场占有率"),
        ("market share", "市场份额", "市场占有率"),
    ),
    (
        re.compile(r"(?i)\b(?:gross\s+hires?|hires?|employees?\s+hired)\b|招聘人数|招聘总人数|新招聘"),
        ("gross hires", "gross hire", "hires", "employees hired", "招聘人数", "招聘总人数", "新招聘"),
    ),
)


def _unstructured_metric_aliases(question: str) -> tuple[str, ...] | None:
    question_lower = str(question or "").casefold()
    for pattern, aliases in _UNSTRUCTURED_METRIC_PATTERNS:
        if not pattern.search(question_lower):
            continue
        return aliases
    return None


def _unstructured_metric_answer_is_grounded(
    question: str,
    answer: str,
    evidence: Iterable[Evidence],
) -> bool:
    """Require same-citation, same-local-row support for non-ledger metrics.

    A keyword anywhere in a chunk is not enough: the chunk might mention
    market share in one paragraph and contain a percentage for an unrelated
    metric elsewhere. Numeric claims must be backed by values in the same
    source fragment that names the requested metric.
    """
    aliases = _unstructured_metric_aliases(question)
    if aliases is None:
        return True
    items = list(evidence)
    seen_claim = False
    safe_refusal = re.compile(
        r"(?i)insufficient evidence|does not establish the requested metric|"
        r"证据不足|未能证明所询|无法可靠作答"
    )
    for raw_line in str(answer or "").splitlines():
        line = raw_line.strip()
        if not line or re.fullmatch(r"\|?\s*:?-{2,}:?(?:\s*\|\s*:?-{2,}:?)*\s*\|?", line):
            continue
        if safe_refusal.search(line):
            continue
        if line.startswith("#") or re.fullmatch(r"[*_`|\s-]+", line):
            continue
        seen_claim = True
        references = [int(value) for value in re.findall(r"\[Evidence\s+(\d+)\]", line, re.I)]
        cited = [items[rank - 1] for rank in references if 1 <= rank <= len(items)]
        if not cited:
            return False
        claim_text = re.sub(r"\[Evidence\s+\d+\]", "", line, flags=re.I)
        claim_companies = {canonical_company(value) for value in extract_companies(claim_text)}
        if claim_companies:
            cited = [item for item in cited if canonical_company(item.company) in claim_companies]
        claim_numbers = extract_normalized_numbers(claim_text)
        if not claim_numbers:
            # These requests require a numeric answer. A qualitative narrative
            # that merely repeats the metric name is not proof of a value.
            return False
        supported = False
        for item in cited:
            source_lines = [
                fragment.strip()
                for fragment in re.split(r"[\r\n]+|(?<=[;。.!?])\s+", str(item.content or ""))
                if fragment.strip()
            ]
            for source_line in source_lines:
                if not any(alias.casefold() in source_line.casefold() for alias in aliases):
                    continue
                source_numbers = extract_normalized_numbers(source_line)
                if all(
                    any(numbers_equivalent(value, source_value) for source_value in source_numbers)
                    for value in claim_numbers
                ):
                    supported = True
                    break
            if supported:
                break
        if not supported:
            return False
    return seen_claim


def _insufficient_metric_answer(question: str) -> str:
    query = str(question or "").casefold()
    for pattern, _ in _UNSTRUCTURED_METRIC_PATTERNS:
        if not pattern.search(query):
            continue
        if any(token in query for token in ("hire", "hires", "employee", "招聘", "员工")):
            return (
                "现有财报证据未能证明所询招聘人数，无法可靠作答。"
                if any("\u3400" <= char <= "\u9fff" for char in query)
                else "The available filing evidence does not establish the requested metric: hires."
            )
        if any(token in query for token in ("market share", "市场份额", "市场占有率")):
            return (
                "现有财报证据未能证明所询市场份额，无法可靠作答。"
                if any("\u3400" <= char <= "\u9fff" for char in query)
                else "The available filing evidence does not establish the requested metric: market share."
            )
        target_terms = ("price target", "target price", "target", "目标价", "股价目标", "目标股价")
        if any(token in query for token in target_terms):
            return (
                "现有财报证据未能证明所询股价目标，无法可靠作答。"
                if any("\u3400" <= char <= "\u9fff" for char in query)
                else "The available filing evidence does not establish the requested metric: price target."
            )
        if any(token in query for token in (
            "expected", "forecast", "prediction", "future", "next", "2027", "12 months",
            "12-month", "预期", "预测", "未来",
        )):
            return (
                "现有财报证据未能证明所询股价预测，无法可靠作答。"
                if any("\u3400" <= char <= "\u9fff" for char in query)
                else "The available filing evidence does not establish the requested metric: stock price forecast."
            )
        if any(token in query for token in ("stock price", "share price", "股价", "股票价格")):
            return (
                "现有财报证据未能证明所询股价，无法可靠作答。"
                if any("\u3400" <= char <= "\u9fff" for char in query)
                else "The available filing evidence does not establish the requested metric: stock price."
            )
        return (
            "现有财报证据未能证明所询股价目标，无法可靠作答。"
            if any("\u3400" <= char <= "\u9fff" for char in query)
            else "The available filing evidence does not establish the requested metric: price target."
        )
    if any("\u3400" <= char <= "\u9fff" for char in str(question or "")):
        return "现有财报证据未能证明所询指标，无法可靠作答。"
    return "The available filing evidence does not establish the requested metric."


def _answer_language_mismatch(question: str, answer: str) -> bool:
    """Return whether the response prose clearly ignores the user's language.

    Short entity/unit tokens such as ``NVIDIA``, ``Q1 FY2027`` and ``USD`` are
    acceptable in a Chinese answer.  The check is deliberately only a guard
    for an answer written almost entirely in the other language; it does not
    attempt to score code-switching or translate arbitrary prose.
    """

    value = re.sub(
        r"(?:Growth-driver source excerpt|财报原文（增长相关驱动）)[:：]\s*"
        r"[\"“].*?[\"”]\s*\[Evidence\s+\d+\]",
        "",
        str(answer or ""),
        flags=re.I | re.S,
    )
    value = re.sub(r"\[Evidence\s+\d+\]", "", value, flags=re.I)
    cjk = len(re.findall(r"[\u3400-\u9fff]", value))
    latin = len(re.findall(r"[A-Za-z]", value))
    if any("\u3400" <= char <= "\u9fff" for char in current_turn_query(question)):
        # Company names, financial acronyms, and period labels are naturally
        # Latin in Chinese answers.  Detect a language violation by the share
        # of Latin prose, not by requiring the answer to contain almost no
        # Chinese at all; otherwise a short Chinese heading can mask a wholly
        # English response.
        return latin >= 24 and latin >= max(24, (cjk + latin) * 0.8)
    # An English response can contain isolated Chinese company names or a
    # quoted term.  A substantial CJK share, however, indicates that the
    # provider answered mainly in Chinese despite the English question.
    return cjk >= 12 and cjk >= (cjk + latin) * 0.12


def _remove_driver_absence_claims(answer: str) -> tuple[str, tuple[str, ...]]:
    """Drop stale refusals/driver denials when retrieved text proves a driver."""

    def contradicted_by_driver(fragment: str) -> bool:
        value = fragment.strip()
        return bool(
            is_driver_absence_claim(value)
            or _RETRIEVAL_LIMITATION.fullmatch(value)
            or _REFUSAL_FRAGMENT.fullmatch(value)
            or re.fullmatch(
                r"(?i)(?:the cited filing evidence is insufficient to support this statement\.?|"
                r"所引财报证据不足以支持该表述。?)",
                value,
            )
        )

    kept_lines: list[str] = []
    removed: list[str] = []
    for line in str(answer or "").splitlines():
        fragments = _scope_claim_fragments(line)
        kept_fragments = [
            fragment for fragment in fragments
            if fragment.strip() and not contradicted_by_driver(fragment)
        ]
        removed.extend(
            fragment for fragment in fragments if contradicted_by_driver(fragment)
        )
        if kept_fragments:
            kept_lines.append(" ".join(kept_fragments))
        elif not fragments and not line.strip():
            kept_lines.append(line)
    return "\n".join(kept_lines).strip(), tuple(removed)


def _render_driver_source_excerpt(question: str, passages) -> str:
    chinese = any("\u3400" <= char <= "\u9fff" for char in current_turn_query(question))
    explicit_attribution = any(
        passage.explicit_financial_attribution for passage in passages
    )
    if explicit_attribution:
        heading = (
            "### \u8d22\u62a5\u539f\u6587\uff08\u589e\u957f\u76f8\u5173\u9a71\u52a8\uff09"
            if chinese
            else "### Growth-driver source excerpt:"
        )
    else:
        heading = (
            "### \u8d22\u62a5\u76f8\u5173\u80cc\u666f"
            "\uff08\u672a\u660e\u786e\u5f52\u56e0\u4e8e\u672c\u62a5\u544a\u671f\u589e\u957f\uff09"
            if chinese
            else "### Related filing context "
            "(not an explicit attribution of reported-period growth):"
        )
    rendered = [heading]
    for passage in passages:
        rendered.append(
            f"\u201c{passage.text}\u201d [Evidence {passage.evidence_rank}]"
        )
    return "\n".join(rendered)


def _localized_grounded_fallback(
    question: str,
    plan: RequiredFactPlan,
    ledger: FactLedger,
    evidence: list[Evidence],
) -> str:
    """Render only verified planned facts when the draft is in the wrong language."""

    intent_question = current_turn_query(question)
    projected, _, _ = complete_from_fact_ledger(
        "", plan, ledger, question=intent_question, evidence=evidence,
    )
    if projected.strip():
        return projected.strip()
    if any("\u3400" <= char <= "\u9fff" for char in intent_question):
        return "当前证据不足以用中文可靠回答该问题。"
    return "The available evidence is insufficient to answer this question reliably."


_PROSE_INTENT_CUE = re.compile(
    r"(?i)\b(?:why|factor|factors|driver|drivers|cause|causes|caused|affect|affected|"
    r"impact|influence|growth|performance|perform|what happened)\b|"
    r"\bhow\s+(?:is|was|did)\b.{0,100}\b(?:business|segment|company|service)\b|"
    r"因素|驱动|原因|影响|增长|表现|业绩|经营情况|业务发展|业务进展|怎么样|如何表现"
)


def _can_project_verified_facts_only(
    question: str, plan: RequiredFactPlan, ledger: FactLedger,
) -> bool:
    """Use ledger-only output for fully evidenced fact/comparison queries.

    A direct fact or numeric comparison has a deterministic answer in the
    source. Keeping provider prose in that response can turn otherwise
    correct values into a wrong-company, wrong-period, or unsupported answer.
    This does not apply to summaries, analysis, risks, or general-concept
    questions; comparison plans without a complete set of source facts also
    remain on the ordinary grounded path.
    """
    if (
        plan.scope not in {QueryScope.FACT.value, QueryScope.COMPARE.value}
        or not plan.required
        or _PROSE_INTENT_CUE.search(current_turn_query(question))
    ):
        return False
    statuses = plan.statuses(ledger, "")
    return bool(statuses) and all(status.available for status in statuses)


def _localize_standard_refusals(question: str, answer: str) -> str:
    """Keep deterministic grounding refusals in the requested UI language."""

    chinese = any("\u3400" <= char <= "\u9fff" for char in current_turn_query(question))
    replacements = (
        (
            "Direct financial answer:",
            "直接财务回答：",
        ),
        (
            "Insufficient evidence to support this numeric claim.",
            "证据不足，无法可靠支持该数字结论。",
        ),
        (
            "The cited filing evidence is insufficient to support this statement.",
            "所引财报证据不足以支持该表述。",
        ),
    )
    for english, chinese_text in replacements:
        source, target = (english, chinese_text) if chinese else (chinese_text, english)
        answer = re.sub(re.escape(source), target, answer, flags=re.I)
    return answer


def _compact_refusal_fragments(
    answer: str,
    *,
    has_supported_facts: bool,
) -> str:
    """Remove repeated provider refusal placeholders after fact completion.

    Providers often emit a refusal for a missing sub-field and then also emit
    the supported requested fact.  Repeating that placeholder makes a valid
    answer look contradictory and can cause downstream evaluators to treat
    the response as unsupported.  We retain one refusal only when no trusted
    fact is available at all; explanatory limitation sentences are untouched.
    """

    kept: list[str] = []
    retained_refusal = False
    for raw_line in str(answer or "").splitlines():
        line = raw_line.strip()
        if not line:
            kept.append(raw_line)
            continue
        limitation_matches = list(_RETRIEVAL_LIMITATION.finditer(raw_line))
        if limitation_matches:
            pieces: list[str] = []
            cursor = 0
            for match in limitation_matches:
                pieces.append(raw_line[cursor:match.start()])
                if not has_supported_facts and not retained_refusal:
                    pieces.append(match.group(0))
                    retained_refusal = True
                cursor = match.end()
            pieces.append(raw_line[cursor:])
            cleaned = "".join(pieces)
            cleaned = re.sub(r"\s{2,}", " ", cleaned)
            cleaned = re.sub(r"\s+([,.;:!?，。；：！？])", r"\1", cleaned)
            cleaned = re.sub(r"(?:[.;。]\s*){2,}", ". ", cleaned)
            cleaned = cleaned.strip(" \t-•")
            if cleaned:
                kept.append(cleaned)
            continue
        had_refusal = bool(_REFUSAL_FRAGMENT.search(line))
        cleaned = _REFUSAL_FRAGMENT.sub("", line)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = re.sub(r"\s+([,.;:!?，。；：！？])", r"\1", cleaned).strip()
        if cleaned:
            # Remove a trailing placeholder from a conclusion, but keep the
            # factual sentence and its citation intact.
            kept.append(cleaned if had_refusal else raw_line)
            continue
        if had_refusal and not has_supported_facts and not retained_refusal:
            kept.append(_ZH_REFUSAL if any("\u3400" <= char <= "\u9fff" for char in line) else _EN_REFUSAL)
            retained_refusal = True
    return "\n".join(kept).strip()


def _refusal_matches_available_fact(line: str, plan: RequiredFactPlan, ledger: FactLedger) -> bool:
    """Detect a stale absence claim only when its same metric/scope is proven."""
    companies = {canonical_company(value) for value in extract_companies(line)}
    periods = extract_periods(line)
    for spec in plan.required:
        facts = ledger.lookup(
            company=spec.company,
            metric_id=spec.metric_id,
            period=spec.period,
            growth_basis=spec.growth_basis,
        )
        line_lower = line.casefold()
        alias_present = _fact_alias_present(line, spec.metric_id)
        if not alias_present and spec.metric_id in {"gross_margin", "operating_margin"}:
            # A generic statement such as "no margin figures are reported"
            # denies either requested margin type. Keep this special case in
            # absence handling only: a bare "margin" must not make an answer
            # containing one value count as both gross and operating margin.
            alias_present = bool(
                re.search(r"\bmargins?\b|利润率", line_lower)
                and not re.search(
                    r"\bgross\b|\boperating\b|毛利|营业利润|经营利润",
                    line_lower,
                )
            )
        if spec.metric_id in {"data_center_revenue", "edge_computing_revenue"} and (
            ("segment" in line_lower and "revenue" in line_lower)
            or ("business" in line_lower and "revenue" in line_lower)
            or ("分部" in line and "收入" in line)
        ):
            alias_present = True
        if not facts or not alias_present:
            continue
        if companies and canonical_company(spec.company or "") not in companies:
            continue
        if spec.period and periods and not any(periods_equivalent(value, spec.period) for value in periods):
            continue
        return True
    return False


def _is_redundant_wrong_period_correction(
    line: str, question: str, plan: RequiredFactPlan, ledger: FactLedger
) -> bool:
    """Drop a number-free outlook-vs-actual correction after its false denial is removed.

    The correction is only redundant when one supported fact exists for the
    requested period. Numeric outlook comparisons remain for ordinary
    grounding and are never removed here.
    """
    if classify_query_scope(question) != QueryScope.FACT:
        return False
    query_periods = extract_periods(question)
    if len(query_periods) != 1:
        return False
    requested_period = query_periods[0]
    line_periods = extract_periods(line)
    if not any(periods_equivalent(period, requested_period) for period in line_periods):
        return False
    if not any(not periods_equivalent(period, requested_period) for period in line_periods):
        return False
    correction = re.search(
        r"\b(?:outlook|guidance|forecast)\b.*\bnot\b.*\b(?:reported|actual|result)\b|"
        r"(?:展望|指引|预测).{0,48}(?:并非|不是|而非).{0,24}(?:实际|报告|实绩)",
        line,
        re.IGNORECASE,
    )
    if not correction:
        return False
    if re.search(
        r"[$€£¥]\s*\d|\d(?:[.,]\d+)?\s*%|\b(?:USD|dollars?|millions?|billions?)\b",
        line,
        re.IGNORECASE,
    ):
        return False
    return any(
        spec.period
        and periods_equivalent(spec.period, requested_period)
        and ledger.lookup(
            company=spec.company,
            metric_id=spec.metric_id,
            period=spec.period,
            growth_basis=spec.growth_basis,
        )
        for spec in plan.required
    )


def _remove_superseded_absence_claims(
    answer: str, question: str, plan: RequiredFactPlan, ledger: FactLedger
) -> tuple[str, tuple[str, ...]]:
    """Remove or scope absence claims to what retrieval actually established.

    Non-financial refusals (e.g. gross employee hires) are not removed merely
    because another metric exists in the same filing. Scope is bound to an
    available fact, matching metric alias, and any company/period named in the
    refusal text. If no matching fact was retrieved, however, a partial top-k
    result cannot prove that the filing itself lacks that information. Rewrite
    the global absence assertion as a retrieval-scoped limitation and remove
    its citation markers, which otherwise imply that an unrelated chunk
    proves absence from the whole report.
    """

    def retrieval_scoped_limitation(line: str) -> str:
        # Preserve the standardized numeric refusal; it makes no claim about
        # whether the complete source document contains the requested fact.
        if _REFUSAL_FRAGMENT.search(line):
            return line
        if any("\u3400" <= char <= "\u9fff" for char in current_turn_query(question)):
            return "当前检索到的证据不足以确认该信息。"
        return "The retrieved passages are insufficient to establish this information."

    kept_paragraphs: list[str] = []
    removed: list[str] = []
    for paragraph in str(answer or "").split("\n\n"):
        kept_lines: list[str] = []
        for line in paragraph.splitlines():
            kept_fragments: list[str] = []
            # Grounding sanitization may place a supported sentence and a
            # refusal in one physical line after splitting citation-bound
            # clauses. Process each sentence independently so a stale
            # evidence-absence statement cannot erase its supported sibling.
            for fragment in _scope_claim_fragments(line):
                if _EVIDENCE_ABSENCE.search(fragment):
                    removed.append(fragment)
                    if _refusal_matches_available_fact(fragment, plan, ledger):
                        continue
                    rewritten = retrieval_scoped_limitation(
                        re.sub(r"\[Evidence\s+\d+\]", "", fragment, flags=re.I).strip()
                    )
                    if rewritten:
                        kept_fragments.append(rewritten)
                elif _is_redundant_wrong_period_correction(fragment, question, plan, ledger):
                    removed.append(fragment)
                else:
                    kept_fragments.append(fragment)
            if kept_fragments:
                kept_lines.append(" ".join(kept_fragments))
            elif not line.strip():
                kept_lines.append(line)
        if kept_lines:
            kept_paragraphs.append("\n".join(kept_lines))
    return "\n\n".join(part for part in kept_paragraphs if part.strip()).strip(), tuple(removed)


def finalize_grounded_answer(question: str, raw_answer: str, evidence: Iterable[Evidence]) -> FinalAnswer:
    """Every completion passes through the final validator before serialization.

    The ledger only supplies missing requested facts, with original citation
    ranks. No legacy unscaled-value appender is run after this boundary.
    """
    intent_question = current_turn_query(question)
    items = list(evidence)
    scoped, removed = _scope_answer(intent_question, str(raw_answer))
    driver_passages = extract_growth_driver_passages(intent_question, items)
    driver_removed: tuple[str, ...] = ()
    synthesized_driver_excerpt = ""
    explicit_driver_passages = tuple(
        passage for passage in driver_passages
        if passage.explicit_financial_attribution
    )
    if (
        driver_passages
        and not answer_has_cited_growth_driver(scoped, driver_passages)
    ):
        if explicit_driver_passages:
            # Only a cited, period-compatible statement explicitly connecting
            # a financial result to its cause can overturn an insufficiency
            # claim. Related industry commentary is shown as context instead.
            scoped, driver_removed = _remove_driver_absence_claims(scoped)
        synthesized_driver_excerpt = _render_driver_source_excerpt(
            intent_question, driver_passages,
        )
        scoped = "\n\n".join(
            part for part in (scoped, synthesized_driver_excerpt) if part
        )
    raw_grounding = sanitize_answer(
        question, scoped, items, require_qualitative_citations=True,
    )
    trusted = raw_grounding.evidence
    if synthesized_driver_excerpt:
        # The first grounding pass removes incompatible/untrusted candidates
        # and compacts citation ranks. Rebuild the synthesized source quote
        # against that exact trusted order; keeping its pre-filter rank can
        # bind the quote to another chunk (or to a rank that no longer exists),
        # especially for a Chinese summary with English filing evidence.
        driver_passages = extract_growth_driver_passages(intent_question, trusted)
        synthesized_driver_excerpt = _render_driver_source_excerpt(
            intent_question, driver_passages,
        )
    if not trusted:
        # An empty or scope-mismatched retrieval set cannot support qualitative
        # prose either. Numeric sanitization alone used to leave uncited
        # narrative claims untouched, which let stale-company and
        # out-of-period drafts escape when no trusted chunks survived.
        empty_ledger = FactLedger()
        empty_plan = infer_required_fact_plan(question, (), empty_ledger)
        raw_text = str(raw_answer or "").strip()
        if raw_text in {_EN_REFUSAL, _ZH_REFUSAL} or _RETRIEVAL_LIMITATION.fullmatch(raw_text):
            refusal = _localize_standard_refusals(intent_question, raw_text)
        elif items:
            refusal = _retrieved_evidence_insufficient_response(intent_question)
        else:
            refusal = no_evidence_response(intent_question)
        grounded_refusal = sanitize_answer(intent_question, refusal, [])
        return FinalAnswer(
            grounded_refusal,
            raw_grounding,
            empty_plan,
            empty_ledger,
            (),
            tuple(line for line in str(raw_answer or "").splitlines() if line.strip()),
            refusal,
            False,
        )
    ledger = FactLedger.from_evidence(trusted)
    plan = infer_required_fact_plan(question, trusted, ledger)
    grounded_draft, absence_removed = _remove_superseded_absence_claims(
        raw_grounding.answer, question, plan, ledger
    )
    completed, added, _ = complete_from_fact_ledger(
        grounded_draft, plan, ledger, question=question, evidence=trusted,
    )
    verified_facts_only_projection = False
    projection_removed: tuple[str, ...] = ()
    if _can_project_verified_facts_only(question, plan, ledger):
        projected, projected_ids, _ = complete_from_fact_ledger(
            "", plan, ledger, question=question, evidence=trusted,
        )
        if projected_ids and len(projected_ids) == len(plan.required):
            verified_facts_only_projection = True
            projection_removed = tuple(
                line for line in str(raw_answer or "").splitlines() if line.strip()
            )
            completed = projected.strip()
            added = projected_ids
    # If the ledger contains a trusted requested fact, refusal-only lines are
    # stale provider placeholders rather than useful uncertainty.  Remove
    # them before the final grounding pass so the user sees one coherent
    # answer while genuine evidence limitations remain explicit.
    completed = _compact_refusal_fragments(
        completed,
        # An unrelated fact in the same retrieval context must not erase an
        # insufficiency refusal (e.g. Tesla revenue cannot answer a price-target
        # or gross-hires question). Count only facts required by this question.
        has_supported_facts=bool(added or any(
            status.available and status.answer_present
            for status in plan.statuses(ledger, completed)
        )),
    )
    completed = _localize_standard_refusals(question, completed)
    grounded = sanitize_answer(
        question, completed, trusted, require_qualitative_citations=True,
    )
    grounded = GroundingResult(
        _localize_standard_refusals(question, grounded.answer),
        grounded.evidence,
        grounded.claims,
    )
    # Citation ranks are compacted relative to the trusted evidence set. When
    # duplicate or filtered evidence changes that rank space, one normalization
    # pass may expose a stale marker from the prior rank map. Iterate to a
    # stable answer so downstream serializers and audits see the same claims
    # and citations on every validation pass.
    for _ in range(min(3, len(grounded.evidence) + 1)):
        normalized = sanitize_answer(
            question,
            grounded.answer,
            grounded.evidence,
            require_qualitative_citations=True,
        )
        normalized = GroundingResult(
            _localize_standard_refusals(question, normalized.answer),
            normalized.evidence,
            normalized.claims,
        )
        if normalized.answer == grounded.answer:
            grounded = normalized
            break
        grounded = normalized
    language_removed: tuple[str, ...] = ()
    # The model prompt requests the question's language, but historic and
    # provider-generated answers can still violate that contract.  Do not
    # expose an untranslated answer: project the scoped evidence ledger into
    # the requested language using deterministic labels, or fail closed when
    # no structured requested fact exists.  This deliberately avoids a second
    # model/provider call and does not translate unsupported prose.
    language_check_answer = grounded.answer
    if synthesized_driver_excerpt:
        # A cited, verbatim filing quotation may remain in English inside an
        # otherwise Chinese response. Do not misclassify that deliberate
        # source excerpt as untranslated model prose; doing so would replace a
        # valid narrative answer with a generic refusal when no numeric fact
        # is present in the ledger.
        language_check_answer = language_check_answer.replace(
            synthesized_driver_excerpt, "",
        ).strip()
    if _answer_language_mismatch(intent_question, language_check_answer):
        language_removed = (grounded.answer,)
        localized = _localized_grounded_fallback(intent_question, plan, ledger, trusted)
        # A source excerpt is not untranslated model prose: it is a verbatim,
        # cited passage deliberately added because the question asks for
        # qualitative drivers that are present in English-language filings.
        # Keep that evidence beside the localized ledger facts rather than
        # dropping it during the language-safety fallback.
        if synthesized_driver_excerpt:
            localized = "\n\n".join(
                part for part in (localized, synthesized_driver_excerpt) if part
            )
        grounded = sanitize_answer(
            question, localized, trusted, require_qualitative_citations=True,
        )
        completed = localized
    # Price targets, market share, and hires are not fungible with their nearby
    # financial facts. Until a source contains an explicit metric phrase,
    # fail closed even if the provider emitted qualitative prose without a
    # number (or unrelated evidence happened to contain the same number).
    if not _unstructured_metric_answer_is_grounded(intent_question, grounded.answer, grounded.evidence):
        unavailable = _insufficient_metric_answer(intent_question)
        grounded = sanitize_answer(question, unavailable, trusted)
        completed = unavailable
        language_removed += (str(raw_answer),) if str(raw_answer).strip() else ()
    return FinalAnswer(
        grounded, raw_grounding, plan, ledger, added,
        removed + driver_removed + absence_removed + language_removed + projection_removed,
        completed,
        verified_facts_only_projection,
    )
