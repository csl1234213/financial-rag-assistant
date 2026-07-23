"""
Sprint 9.3 Phase 1 — Full End-to-End Validation v4
"""
import requests, io, json, time, subprocess, uuid

BASE = "http://localhost:8000/api/v1"
RESULTS = []

def test(name, fn):
    try:
        fn()
        RESULTS.append((name, "PASS", ""))
    except Exception as e:
        RESULTS.append((name, "FAIL", str(e)[:120]))

def report():
    print("\n" + "=" * 70)
    print("SPRINT 9.3 PHASE 1 — E2E VALIDATION REPORT")
    print("=" * 70)
    print(f"\n{'Test Case':<45} {'Result':<8} {'Issue'}")
    print("-" * 70)
    for name, result, issue in RESULTS:
        print(f"{name:<45} {result:<8} {issue}")
    passed = sum(1 for _, r, _ in RESULTS if r == "PASS")
    total = len(RESULTS)
    print("-" * 70)
    print(f"Total: {passed}/{total} passed")
    score = int(passed / total * 100) if total else 0
    print(f"Production Readiness Score: {score}%")

# Unique emails
uid = uuid.uuid4().hex[:8]
EMAIL_A = f"test_a_{uid}@example.com"
EMAIL_B = f"test_b_{uid}@example.com"

# ============================================================
# 1. Application Health
# ============================================================
def test_health():
    resp = requests.get(f"{BASE}/health")
    assert resp.status_code == 200, f"Status: {resp.status_code}"
    data = resp.json()
    assert data["status"] == "ok", f"Expected 'ok', got: {data['status']}"
    assert data["service"] == "Financial Research Copilot"

test("1.1 Health API", test_health)

# ============================================================
# 2. Authentication Flow
# ============================================================
tokens = {}

def test_register():
    resp = requests.post(f"{BASE}/auth/register", json={
        "email": EMAIL_A,
        "password": "Test@123456",
        "name": "Test User A"
    })
    assert resp.status_code == 201, f"Register: {resp.status_code} {resp.text}"
    data = resp.json()
    assert "token" in data, "No token"
    assert data["email"] == EMAIL_A
    tokens["user_a"] = data["token"]

test("2.1 Register User A", test_register)

def test_me():
    resp = requests.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {tokens['user_a']}"})
    assert resp.status_code == 200, f"Me: {resp.status_code} {resp.text}"
    data = resp.json()
    assert data["email"] == EMAIL_A
    assert "tenant" in data, "No tenant"
    assert "id" in data["tenant"], "No tenant id"

test("2.2 /auth/me with tenant", test_me)

def test_login():
    resp = requests.post(f"{BASE}/auth/login", json={
        "email": EMAIL_A,
        "password": "Test@123456"
    })
    assert resp.status_code == 200, f"Login: {resp.status_code} {resp.text}"
    data = resp.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token: {list(data.keys())}"
    assert data.get("token_type") == "bearer"
    tokens["user_a"] = token

test("2.3 Login returns access_token", test_login)

# ============================================================
# 3. Upload & Task Processing
# ============================================================
task_ids = {}

def test_upload_pdf():
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 0>>endobj\ntrailer<</Size 3/Root 1 0 R>>\n%%EOF"
    files = {"file": ("tesla_report.pdf", io.BytesIO(pdf_content), "application/pdf")}
    headers = {"Authorization": f"Bearer {tokens['user_a']}"}
    resp = requests.post(f"{BASE}/upload", files=files, headers=headers)
    assert resp.status_code == 200, f"Upload: {resp.status_code} {resp.text}"
    data = resp.json()
    assert "task_id" in data, "No task_id"
    assert data["status"] == "pending"
    task_ids["task_a"] = data["task_id"]

test("3.1 Upload PDF -> task created", test_upload_pdf)

def test_task_processing():
    task_id = task_ids["task_a"]
    headers = {"Authorization": f"Bearer {tokens['user_a']}"}
    for i in range(20):
        time.sleep(3)
        resp = requests.get(f"{BASE}/tasks/{task_id}", headers=headers)
        data = resp.json()
        status = data["status"]
        progress = data["progress"]
        if status == "success":
            assert progress == 100, f"Success but progress={progress}"
            return
        if status == "failed":
            raise AssertionError(f"Task failed: {data.get('error')}")
    raise AssertionError(f"Timed out: {data['status']}")

test("3.2 Task pending->running->success", test_task_processing)

# ============================================================
# 4. Knowledge Workspace
# ============================================================
def test_knowledge():
    headers = {"Authorization": f"Bearer {tokens['user_a']}"}
    resp = requests.get(f"{BASE}/knowledge", headers=headers)
    assert resp.status_code == 200, f"Knowledge: {resp.status_code} {resp.text}"
    data = resp.json()
    assert "documents" in data, "No documents field"
    assert data["document_count"] >= 1, f"Expected at least 1 doc, got {data['document_count']}"

test("4.1 Knowledge /knowledge endpoint", test_knowledge)

# ============================================================
# 5. Chat Copilot
# ============================================================
def test_chat():
    headers = {"Authorization": f"Bearer {tokens['user_a']}"}
    resp = requests.post(f"{BASE}/chat", json={
        "question": "Summarize this financial report"
    }, headers=headers)
    assert resp.status_code == 200, f"Chat: {resp.status_code} {resp.text[:300]}"
    data = resp.json()
    assert "report" in data, f"No 'report' field: {list(data.keys())}"
    assert "citations" in data, "No 'citations' field"
    assert "execution_time" in data, "No 'execution_time' field"

test("5.1 Chat copilot with question", test_chat)

# ============================================================
# 6. Multi-Tenant Isolation
# ============================================================
def test_tenant_isolation():
    # Register User B
    resp = requests.post(f"{BASE}/auth/register", json={
        "email": EMAIL_B,
        "password": "Test@123456",
        "name": "Test User B"
    })
    assert resp.status_code == 201, f"Register B: {resp.status_code} {resp.text}"
    token_b = resp.json()["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Upload Apple PDF for User B
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 0>>endobj\ntrailer<</Size 3/Root 1 0 R>>\n%%EOF"
    files = {"file": ("apple_report.pdf", io.BytesIO(pdf_content), "application/pdf")}
    resp = requests.post(f"{BASE}/upload", files=files, headers=headers_b)
    assert resp.status_code == 200, f"Upload B: {resp.status_code} {resp.text}"
    task_id_b = resp.json()["task_id"]

    # Wait for task
    for i in range(20):
        time.sleep(3)
        resp = requests.get(f"{BASE}/tasks/{task_id_b}", headers=headers_b)
        if resp.json()["status"] == "success":
            break
        if resp.json()["status"] == "failed":
            raise AssertionError(f"Task B failed: {resp.json().get('error')}")

    # User A's documents (should only see Tesla, NOT Apple)
    headers_a = {"Authorization": f"Bearer {tokens['user_a']}"}
    resp = requests.get(f"{BASE}/knowledge", headers=headers_a)
    assert resp.status_code == 200, f"Docs A: {resp.status_code}"
    docs_a = resp.json()
    doc_names_a = [d for d in docs_a["documents"]]
    assert "apple" not in [d.lower() for d in doc_names_a], f"User A leaked Apple: {doc_names_a}"

    # User B's documents (should only see Apple, NOT Tesla)
    resp = requests.get(f"{BASE}/knowledge", headers=headers_b)
    assert resp.status_code == 200, f"Docs B: {resp.status_code}"
    docs_b = resp.json()
    doc_names_b = [d for d in docs_b["documents"]]
    assert "tesla" not in [d.lower() for d in doc_names_b], f"User B leaked Tesla: {doc_names_b}"

test("6.1 Multi-tenant isolation", test_tenant_isolation)

# ============================================================
# 7. Docker Runtime
# ============================================================
def test_docker_runtime():
    result = subprocess.run(["docker", "ps", "--format", "{{.Names}} {{.Status}}"], 
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    services = result.stdout.strip().split("\n")
    required = ["financial-frontend", "financial-backend", "financial-redis", "financial-chromadb"]
    running = set()
    for line in services:
        for req in required:
            if req in line and "Up" in line:
                running.add(req)
    missing = set(required) - running
    assert len(missing) == 0, f"Missing: {missing}"

test("7.1 Docker containers healthy", test_docker_runtime)

def test_worker_heartbeat():
    result = subprocess.run(["docker", "logs", "financial-rag-assistant-worker-1"], 
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    combined = (result.stdout + result.stderr).lower()
    assert "worker runner started" in combined or "waiting for tasks" in combined or "taskworker started" in combined, \
        f"No heartbeat in logs"

test("7.2 Worker heartbeat running", test_worker_heartbeat)

# ============================================================
report()