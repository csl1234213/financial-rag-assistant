import sys
from pathlib import Path
from threading import Lock
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from agent.agent_runtime import AgentRuntime
from agent.execution import strategies as _builtin_execution_strategies  # noqa: F401
from agent.execution.execution_dispatcher import ExecutionDispatcher
from agent.execution.execution_engine import StrategyExecutionEngine
from agent.execution.financial_metrics_handler import (
    FinancialMetricsStepHandler,
    authorize_financial_metrics_tool,
)
from agent.execution.step_execution_engine import StepExecutionEngine
from agent.execution_plan import StepType
from agent.query_planner import QueryPlanner
from agent.reasoning_engine import ReasoningEngine
from agent.tools import ToolEngine
from agent.workflow.workflow_engine import WorkflowEngine
from agent.workflow.workflow_executor import WorkflowExecutor
from agent.workflow.workflows import (  # noqa: F401 — auto-registration
    ComparisonWorkflow,
    DirectChatWorkflow,
    RAGWorkflow,
    ResearchWorkflow,
    ToolPipelineWorkflow,
)
from config import DEBUG_MODE
from core.citation_formatter import format_citations
from core.intent_analyzer import IntentAnalyzer
from core.rag_result import RAGResult
from core.report_builder import build_research_report
from core.research_analyzer import analyze_evidence
from core.retrieval_tool_adapter import TenantRetrievalToolExecutor
from document_loader import (
    load_documents,
)
from embedding import (
    load_embedding_model,
)
from llm.provider import call_llm
from llm.router import (
    CapabilityRoutingPolicy,
    ModelRouter,
    RoutingPolicy,
)
from prompt_builder import (
    build_compare_prompt,
    build_direct_chat_prompt,
    build_prompt,
    get_prompt_metadata,
    get_prompt_system_prompt,
)
from research_mode import (
    detect_research_mode,
)
from retrieval.hybrid_retriever import (
    HybridRetriever,
)
from storage.vector_models import VectorDocument

# =========================
# Pipeline Composition
# =========================

PDF_FOLDER = "pdfs/"
PUBLIC_TENANT_ID = 0

_store = None
_model = None
_model_init_lock = Lock()
_store_init_lock = Lock()


def _get_model():
    global _model
    if _model is None:
        with _model_init_lock:
            if _model is None:
                _model = load_embedding_model()
    return _model


def _get_store():
    global _store
    if _store is None:
        with _store_init_lock:
            if _store is None:
                from storage.chroma_store import ChromaEmbeddingStore

                _store = ChromaEmbeddingStore()
    return _store


# =========================
# Knowledge Base
# =========================


def refresh_knowledge_base():
    """Refresh only the intentionally public/demo knowledge base.

    Private uploads are processed by the tenant-aware worker path.  The old
    implementation deleted every collection before loading demo PDFs, which
    could erase tenant data during an unrelated refresh.
    """
    store = _get_store()
    model = _get_model()

    chunks = load_documents(PDF_FOLDER)

    store.create_collection("financial_reports")
    store.delete_by_tenant(PUBLIC_TENANT_ID)

    docs = []
    for chunk in chunks:
        embedding = model.encode(chunk["text"], convert_to_tensor=False).tolist()
        docs.append(
            VectorDocument(
                document_id=chunk["document_id"],
                chunk_id="public_%s_%d" % (chunk["document_id"], chunk["chunk_id"]),
                company=chunk["company"],
                content=chunk["text"],
                embedding=embedding,
                metadata={
                    "source": chunk["source"],
                    "quarter": chunk.get("quarter", ""),
                    "collection": "financial_reports",
                    "tenant_id": PUBLIC_TENANT_ID,
                },
            )
        )

    store.add_documents(docs)

    print(f"[RAG] Loaded {len(chunks)} chunks into ChromaDB")

    if len(chunks) > 0:
        print(chunks[0]["source"], chunks[0]["chunk_id"])


def get_chunk_count():
    store = _get_store()
    return store.count()


# =========================
# Runtime Wiring
# =========================

_retriever = None
_retrieval_tool_executor = None
_runtime = None


def _get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever(_get_model())
    return _retriever


def _get_retrieval_tool_executor():
    global _retrieval_tool_executor
    if _retrieval_tool_executor is None:
        _retrieval_tool_executor = TenantRetrievalToolExecutor(_get_retriever())
    return _retrieval_tool_executor


intent_analyzer = IntentAnalyzer()
query_planner = QueryPlanner()

engine = StepExecutionEngine()
reasoning_engine = ReasoningEngine()

strategy_engine = StrategyExecutionEngine()

dispatcher = ExecutionDispatcher()
financial_metrics_tool_engine = ToolEngine(
    authorization_hook=authorize_financial_metrics_tool,
)


def _retrieve_handler(step, shared_context):
    evidences = _get_retrieval_tool_executor().execute(
        store=_get_store(),
        query=step.query or "",
        company=step.company,
        document_ids=step.document_ids or None,
        top_k=step.parameters.get("top_k", 4),
        filters=step.parameters.get("filters", {}),
        tenant_id=shared_context.get("tenant_id", 0),
        include_public=shared_context.get("include_public", False),
    )

    shared_context.setdefault("_all_evidence", []).extend(evidences)
    return evidences


engine.register_handler(StepType.RETRIEVE, _retrieve_handler)
engine.register_handler(StepType.COMPARE, lambda s, c: None)
engine.register_handler(StepType.SYNTHESIS, lambda s, c: None)
engine.register_handler(
    StepType.TOOL_CALL,
    FinancialMetricsStepHandler(financial_metrics_tool_engine),
)

router = ModelRouter(policy=RoutingPolicy(CapabilityRoutingPolicy()))


def _get_runtime():
    global _runtime
    if _runtime is None:
        _runtime = AgentRuntime(
            planner=query_planner,
            executor=engine,
            reasoner=reasoning_engine,
            retriever=_get_retriever(),
            intent_analyzer=intent_analyzer,
            router=router,
            strategy_engine=strategy_engine,
            dispatcher=dispatcher,
            workflow_engine=WorkflowEngine(),
            workflow_executor=WorkflowExecutor(),
        )
    return _runtime


# =========================
# RAG MAIN
# =========================


def run_rag(
    question: str,
    company=None,
    *,
    tenant_id: int = 0,
    thread_id: str | None = None,
    conversation_history: Sequence[dict[str, Any]] | None = None,
) -> RAGResult:
    research_mode = detect_research_mode(question)
    result = _get_runtime().run(
        question,
        company,
        tenant_id=tenant_id,
        thread_id=thread_id,
    )

    is_tool_call = (
        result.execution
        and result.execution.get("strategy") == "tool_calling"
    )
    if is_tool_call:
        # A deterministic tool result is already the final answer.  Do not
        # route it through retrieval or an LLM, and never fabricate citations.
        answer = (
            result.context
            or "The financial calculation could not be completed."
        )
        return RAGResult(
            report=answer,
            citations=[],
            context=result.context,
            research_mode=research_mode,
            intent=result.intent_result,
            evidence=[],
            plan=result.plan,
            routing=result.routing,
            planning=result.planning,
            execution=result.execution,
            workflow=result.workflow,
        )

    is_direct_chat = result.workflow and result.workflow.get("type") == "direct_chat"

    if is_direct_chat:
        prompt_name = "direct_chat"
        prompt_metadata = get_prompt_metadata(prompt_name)
        prompt = build_direct_chat_prompt(
            question,
            history=conversation_history,
        )
        if result.planning is not None:
            result.planning["prompt"] = prompt_metadata
        answer = call_llm(
            prompt,
            provider=result.provider_instance,
            system_prompt=get_prompt_system_prompt(prompt_name),
        )
        return RAGResult(
            report=answer,
            citations=result.citations,
            context=result.context,
            research_mode=research_mode,
            intent=result.intent_result,
            evidence=result.evidence,
            plan=result.plan,
            routing=result.routing,
            planning=result.planning,
            execution=result.execution,
            workflow=result.workflow,
        )

    if research_mode == "compare":
        prompt_name = "financial_compare"
        prompt_metadata = get_prompt_metadata(prompt_name)
        prompt = build_compare_prompt(
            question,
            result.context,
            history=conversation_history,
        )
    else:
        prompt_name = "financial_rag"
        prompt_metadata = get_prompt_metadata(prompt_name)
        prompt = build_prompt(
            question,
            result.context,
            history=conversation_history,
        )

    if result.planning is not None:
        result.planning["prompt"] = prompt_metadata

    if DEBUG_MODE:
        return RAGResult(
            report=prompt,
            citations=result.citations,
            context=result.context,
            research_mode=research_mode,
            intent=result.intent_result,
            evidence=result.evidence,
            plan=result.plan,
            routing=result.routing,
            planning=result.planning,
            execution=result.execution,
            workflow=result.workflow,
        )

    if len(result.citations) == 0:
        return RAGResult(
            report="No relevant evidence found in uploaded documents.",
            citations=[],
            context="",
            research_mode=research_mode,
            intent=result.intent_result,
            evidence=result.evidence,
            plan=result.plan,
            routing=result.routing,
            planning=result.planning,
            execution=result.execution,
            workflow=result.workflow,
        )

    answer = call_llm(
        prompt,
        provider=result.provider_instance,
        system_prompt=get_prompt_system_prompt(prompt_name),
    )

    evidence_stats = analyze_evidence(result.citations)

    report = build_research_report(question, answer, result.citations, evidence_stats, result.reasoning_result)

    citation_text = format_citations(result.citations)

    answer = answer + "\n\n" + citation_text

    return RAGResult(
        report=report,
        citations=result.citations,
        context=result.context,
        research_mode=research_mode,
        intent=result.intent_result,
        evidence=result.evidence,
        plan=result.plan,
        routing=result.routing,
        planning=result.planning,
        execution=result.execution,
        workflow=result.workflow,
    )
