# 📊 Financial Research Assistant

## AI-Powered Financial RAG System for Multi-Document Analysis

---

## 🧭 1. Product Vision / 产品定位

### English

A production-level AI system that transforms financial documents into structured research insights.

It is designed to help users analyze multiple financial reports with **evidence-backed reasoning**, not simple chat responses.

---

### 中文

一个生产级 AI 金融研究系统。

用于将多份财报转化为结构化研究结果，支持**基于证据的分析，而不是简单问答**。

---

## 🎯 2. What This Project Does / 项目能力

### ✔ Core Capabilities

* Upload multiple financial PDFs
* Cross-document semantic retrieval
* Evidence-based answer generation
* Structured financial research reports
* Transparent AI reasoning system

---

### 🧠 Key Output

Instead of:

> “Here is the answer”

The system provides:

> ✔ Answer
> ✔ Evidence
> ✔ Source documents
> ✔ Reasoning trace

---

## 🖼️ 3. UI Preview (Landing Layout Design)

> 👉 这是 GitHub 首页最关键部分（建议你按这个放截图）

---

### 🟦 ① Main Dashboard

📌 **位置建议：README顶部第一张图**

```
[Screenshot: Main UI Dashboard]
```

👉 展示内容：

* 上传PDF界面
* 左侧 Knowledge Base
* 中间 Chat / Query
* 右侧 Evidence Panel

---

### 🟩 ② Evidence Panel（核心卖点）

📌 **建议放第二张图**

```
[Screenshot: Evidence Panel]
```

👉 展示：

* chunk来源
* document引用
* score ranking
* traceable reasoning

---

### 🟨 ③ Research Report Output

📌 **第三张图**

```
[Screenshot: Structured Report]
```

👉 展示：

* Summary
* Key Insights
* Risks
* Evidence Used

---

### 🟥 ④ Multi-Document Query Example

📌 **第四张图**

```
[Screenshot: Cross-company analysis]
```

👉 展示：

* Apple vs Tesla vs NVIDIA
* cross-document reasoning

---

## 🏗️ 4. System Architecture / 系统架构

```
User Question
     ↓
Retrieval Layer
(semantic search + ranking)
     ↓
Context Builder
(filter + compress + structure)
     ↓
Prompt Builder
(strict instruction control)
     ↓
LLM Reasoning
     ↓
Output Layer
 ├── Research Report
 └── Evidence Panel
```

---

## 🧠 5. Key Engineering Highlights / 核心设计亮点

---

### 1. ❌ Removed Document Router

**EN:** Simplified architecture by removing fragile routing logic
**CN:** 移除不稳定的文档路由逻辑，降低系统复杂度

---

### 2. 🧠 Context Engineering Layer

**EN:** Introduced structured context instead of raw chunks
**CN:** 用 Context Builder 替代原始 chunk 输入

---

### 3. 📌 Evidence-Based Output

**EN:** Every answer must be traceable to source documents
**CN:** 所有回答必须可追溯到原始证据

---

### 4. 🔒 Output Boundary Control

**EN:** LLM is strictly constrained to prevent hallucination
**CN:** 对模型输出进行严格约束，防止幻觉

---

## 📊 6. System Evolution / 系统演进

```
V1   → PDF QA Prototype
V2   → Multi-document RAG
V2.1 → Router Experiment (removed)
V2.2 → Stable Architecture
V3.0 → Agent Runtime Edition ⭐
```

---

## ✨ 7. Agent Runtime (V3)

Unlike traditional RAG pipelines, V3 introduces a dedicated Agent Runtime.

### Features

* **Query Planning** — Structured execution plans with DAG dependencies
* **Execution Engine** — Handler-based dispatch with step status tracking
* **Runtime Context** — Unified state management for one Agent execution
* **Structured Reasoning** — Facts / Risks / Opportunities extraction
* **Explainable Evidence Pipeline** — Every output traceable to source documents

### Architecture

```
User Query
    ↓
Intent Analyzer
    ↓
Query Planner
    ↓
Execution Plan
    ↓
Execution Engine
    ↓
Reasoning Engine
    ↓
Context Builder
    ↓
Prompt Builder
    ↓
LLM
    ↓
Report Builder
```

### Agent Modules

| Module | Role |
|---|---|
| `agent_runtime.py` | Unified lifecycle manager |
| `query_planner.py` | Intent → ExecutionPlan |
| `execution_plan.py` | StepType / PlanStep / ExecutionPlan |
| `execution_engine.py` | Handler dispatch + dependency resolution |
| `reasoning_engine.py` | Evidence → Facts / Risks / Opportunities |
| `runtime_context.py` | Runtime state (replaces shared_context dict) |
| `runtime_result.py` | Unified output (replaces long return tuple) |

---

## 💡 8. Design Philosophy / 设计理念

> Simplicity improves reliability more than complexity improves intelligence.

> 简单性带来的稳定性，远比复杂系统带来的“智能感”更重要。

---

## 🖥️ 9. Recommended GitHub Layout (VERY IMPORTANT)

👉 你 GitHub README 建议这样排：

```
1. Title + Short Description
2. UI Screenshots (4 images)
3. Key Features
4. Architecture Diagram
5. Engineering Highlights
6. Project Evolution
7. Design Philosophy
8. Future Work
```

---

## 📌 10. Screenshot Placement Strategy（关键）

你一定要这样放：

```
[ HERO IMAGE - Dashboard ]

[ Evidence Panel ]

[ Report Output ]

[ Multi-document Comparison ]
```

---

## 🔥 11. Why This Project Matters

### English

This is not a demo RAG system.

It is a **financial reasoning system with evidence-based AI outputs**.

---

### 中文

这不是一个简单的 RAG Demo。

而是一个**具备证据驱动能力的金融分析系统**。

---

## 🚀 Final Statement

> Built not to answer questions, but to support financial reasoning.

> 不是为了回答问题，而是为了支持金融研究。