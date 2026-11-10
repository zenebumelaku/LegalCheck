import io
import sys
import uuid
import time
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from fastapi.testclient import TestClient

from app.main import app
from app.main import app
from app.db.session import get_session_factory
from app.db.models import User, LegalSource, LegalProvision, LegalProvisionChunk, Document
from app.core.security import hash_password
from app.services.legal_question_cache import get_legal_question_cache

def create_sample_pdf(title: str, text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 750, title)
    y = 720
    for line in text.split("\n"):
        if line.strip():
            c.drawString(100, y, line.strip())
            y -= 25
    c.save()
    buf.seek(0)
    return buf.getvalue()

def run_all_scenarios():
    print("=" * 70)
    print("LEGALCHECK ETHIOPIA — 11 RAG & REDIS SCENARIOS VERIFICATION")
    print("=" * 70)

    db = get_session_factory()()
    cache = get_legal_question_cache()
    client = TestClient(app)

    # 0. Setup test user and login
    test_email = f"scenario_tester_{uuid.uuid4().hex[:6]}@legalcheck.et"
    test_password = "SecurePassword123!"
    user = User(
        email=test_email,
        password_hash=hash_password(test_password),
        name="Scenario Tester",
        role="legal_analyst",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    login_res = client.post("/api/v1/auth/login", json={"email": test_email, "password": test_password})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[INIT] Created and authenticated test user.")

    # ----------------------------------------------------
    # SCENARIO 1: Upload a document (.pdf) via UI / API
    # ----------------------------------------------------
    print("\n--- SCENARIO 1: Upload a document (.pdf) ---")
    doc1_content = (
        "Section 1: Work Environment\n"
        "Remote staff members receive an operational stipend.\n"
        "Section 2: Internet Subsidy\n"
        "The company provides a monthly internet allowance of 1,500 ETB for all verified remote employees."
    )
    doc1_pdf = create_sample_pdf("Remote Work Policy 2026", doc1_content)
    upload1_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("remote_work_policy_2026.pdf", doc1_pdf, "application/pdf")},
        headers=headers,
    )
    assert upload1_res.status_code == 201, f"Upload failed: {upload1_res.text}"
    doc1_data = upload1_res.json()
    doc1_id = doc1_data["id"]
    print(f"✓ PASS Scenario 1: Document uploaded successfully. ID: {doc1_id}")

    # ----------------------------------------------------
    # SCENARIO 2: Confirm text is extracted
    # ----------------------------------------------------
    print("\n--- SCENARIO 2: Confirm text is extracted ---")
    extracted_chars = doc1_data.get("extracted_characters", 0)
    pages = doc1_data.get("pages", [])
    assert extracted_chars > 0, "No characters extracted"
    assert len(pages) > 0, "No pages extracted"
    print(f"✓ PASS Scenario 2: Text extracted. Pages: {len(pages)}, Characters: {extracted_chars}")

    # ----------------------------------------------------
    # SCENARIO 3: Confirm chunks and embeddings stored in SQLite
    # ----------------------------------------------------
    print("\n--- SCENARIO 3: Confirm chunks and embeddings in SQLite ---")
    chunks_created = doc1_data.get("chunks_created", 0)
    assert chunks_created > 0, "No chunks created"

    source = db.query(LegalSource).filter(LegalSource.title == "remote_work_policy_2026.pdf").first()
    assert source is not None, "LegalSource not found in DB"
    provisions = db.query(LegalProvision).filter(LegalProvision.legal_source_id == source.id).all()
    assert len(provisions) > 0, "No provisions found"
    
    chunks = db.query(LegalProvisionChunk).filter(
        LegalProvisionChunk.provision_id.in_([p.id for p in provisions])
    ).all()
    assert len(chunks) > 0, "No provision chunks found in DB"
    assert chunks[0].embedding is not None, "Dense embedding vector is missing"
    assert len(chunks[0].embedding) == 384, f"Embedding dimension mismatch: {len(chunks[0].embedding)} != 384"
    print(f"✓ PASS Scenario 3: {len(chunks)} chunks stored with 384-dim dense embeddings in SQLite vector store.")

    # ----------------------------------------------------
    # SCENARIO 4: Ask a question whose answer exists in document
    # ----------------------------------------------------
    print("\n--- SCENARIO 4: Ask question existing in document ---")
    q4 = "What is the monthly internet allowance for remote employees?"
    t0 = time.time()
    chat4_res = client.post(
        "/api/v1/legal-questions/conversations",
        json={"question": q4},
        headers=headers,
    )
    t4 = time.time() - t0
    assert chat4_res.status_code in (200, 201), f"Q&A failed: {chat4_res.text}"
    chat4_data = chat4_res.json()
    conv_id = chat4_data["conversation_id"]
    ans4 = chat4_data["answer"]
    print(f"Question: {q4}")
    print(f"Answer: {ans4['answer']}")
    print(f"Status: {ans4['status']}, Cache Hit: {ans4['cache_hit']}, Latency: {t4:.2f}s")
    assert ans4["status"] == "answered", f"Expected answered, got {ans4['status']}"
    assert "1,500" in ans4["answer"] or "1500" in ans4["answer"], "Expected 1,500 ETB in answer"
    assert ans4["cache_hit"] is False, "Expected first call to be Cache MISS"
    print("✓ PASS Scenario 4: Question answered successfully from document content.")

    # ----------------------------------------------------
    # SCENARIO 5: Verify answer uses retrieved context and cites source
    # ----------------------------------------------------
    print("\n--- SCENARIO 5: Verify citation of source ---")
    citations = ans4.get("citations", [])
    assert len(citations) > 0, "Expected at least one citation"
    citation = citations[0]
    print(f"Cited Source: {citation['source_title']}")
    print(f"Supporting Quote: {citation['supporting_quote']}")
    assert "remote_work_policy_2026.pdf" in citation["source_title"], "Citation does not match uploaded source"
    print("✓ PASS Scenario 5: Answer correctly cites uploaded document source.")

    # ----------------------------------------------------
    # SCENARIO 6: Question not in corpus -> negative response (insufficient_evidence)
    # ----------------------------------------------------
    print("\n--- SCENARIO 6: Question not in corpus (insufficient_evidence) ---")
    q6 = "What are the specific safety regulations for piloting warp drive spaceships in Ethiopian airspace?"
    chat6_res = client.post(
        "/api/v1/legal-questions/conversations",
        json={"question": q6},
        headers=headers,
    )
    assert chat6_res.status_code in (200, 201), f"Q&A failed: {chat6_res.text}"
    ans6 = chat6_res.json()["answer"]
    print(f"Question: {q6}")
    print(f"Status: {ans6['status']}")
    print(f"Answer: {ans6['answer']}")
    assert ans6["status"] == "insufficient_evidence", f"Expected insufficient_evidence, got {ans6['status']}"
    assert len(ans6["citations"]) == 0, "Expected zero citations for insufficient evidence"
    print("✓ PASS Scenario 6: System correctly returns insufficient_evidence without hallucinating citations.")

    # ----------------------------------------------------
    # SCENARIO 7: Ask the same question again -> Redis Cache HIT
    # ----------------------------------------------------
    print("\n--- SCENARIO 7: Ask same question again -> Redis Cache HIT ---")
    t0 = time.time()
    chat7_res = client.post(
        "/api/v1/legal-questions/conversations",
        json={"question": q4},
        headers=headers,
    )
    t7 = time.time() - t0
    assert chat7_res.status_code in (200, 201), f"Q&A failed: {chat7_res.text}"
    ans7 = chat7_res.json()["answer"]
    print(f"Status: {ans7['status']}, Cache Hit: {ans7['cache_hit']}, Latency: {t7*1000:.1f}ms")
    assert ans7["cache_hit"] is True, "Expected Redis Cache HIT on repeated query"
    assert ans7["answer"] == ans4["answer"], "Cached answer text mismatch"
    print(f"✓ PASS Scenario 7: Immediate Redis Cache HIT confirmed ({t7*1000:.1f}ms vs {t4:.2f}s).")

    # ----------------------------------------------------
    # SCENARIO 8: Upload a second document -> immediate retrieval
    # ----------------------------------------------------
    print("\n--- SCENARIO 8: Upload second document & retrieve immediately ---")
    doc2_content = (
        "Section 1: Hardware Equipment Reimbursement\n"
        "The company reimburses up to 25,000 ETB for specialist hardware upon presentation of valid receipts.\n"
        "Section 2: Maintenance and Upgrades\n"
        "All hardware repairs must be handled by authorized warranty service centers."
    )
    doc2_pdf = create_sample_pdf("Hardware Policy 2026", doc2_content)
    upload2_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("hardware_policy_2026.pdf", doc2_pdf, "application/pdf")},
        headers=headers,
    )
    assert upload2_res.status_code == 201, f"Upload 2 failed: {upload2_res.text}"
    doc2_data = upload2_res.json()
    doc2_id = doc2_data["id"]

    q8 = "What is the reimbursement amount for specialist hardware?"
    chat8_res = client.post(
        "/api/v1/legal-questions/conversations",
        json={"question": q8},
        headers=headers,
    )
    assert chat8_res.status_code in (200, 201), f"Q&A 8 failed: {chat8_res.text}"
    ans8 = chat8_res.json()["answer"]
    print(f"Question: {q8}")
    print(f"Answer: {ans8['answer']}")
    assert ans8["status"] == "answered", "Second document was not immediately retrievable"
    assert "25,000" in ans8["answer"] or "25000" in ans8["answer"], "Expected 25,000 in answer"
    assert any("hardware_policy_2026.pdf" in c["source_title"] for c in ans8["citations"]), "Source not cited"
    print("✓ PASS Scenario 8: Second document immediately indexed and retrievable.")

    # Verify cache HIT on q8 before deletion
    chat8_cached = client.post(
        "/api/v1/legal-questions/conversations",
        json={"question": q8},
        headers=headers,
    )
    assert chat8_cached.json()["answer"]["cache_hit"] is True, "Expected cache HIT before document deletion"
    print("✓ Confirmed Redis Cache HIT for q8 before document deletion.")

    # ----------------------------------------------------
    # SCENARIO 9: Verify cache invalidation when corpus changes
    # ----------------------------------------------------
    print("\n--- SCENARIO 9: Verify cache invalidation on corpus change ---")
    # Verify deleting document invalidates cache
    del_res = client.delete(f"/api/v1/documents/{doc2_id}", headers=headers)
    assert del_res.status_code == 204, f"Delete failed: {del_res.text}"
    print("✓ Deleted document 2 from vector store and triggered cache.invalidate_all()")

    # Subsequent query for q8 should now NOT hit cache
    chat9_res = client.post(
        "/api/v1/legal-questions/conversations",
        json={"question": q8},
        headers=headers,
    )
    assert chat9_res.status_code in (200, 201), f"Q&A 9 failed: {chat9_res.text}"
    ans9 = chat9_res.json()["answer"]
    print(f"After deletion, status: {ans9['status']}, cache_hit: {ans9['cache_hit']}")
    assert ans9["cache_hit"] is False, "Expected Cache MISS because cache was invalidated on document deletion"
    print("✓ PASS Scenario 9: Cache successfully invalidated when corpus was updated/deleted.")

    # ----------------------------------------------------
    # SCENARIO 10: Test invalid files
    # ----------------------------------------------------
    print("\n--- SCENARIO 10: Test invalid files ---")
    # 10a. Empty file
    res_empty = client.post(
        "/api/v1/documents/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers=headers,
    )
    assert res_empty.status_code == 400, f"Expected 400, got {res_empty.status_code}"
    print(f"10a Empty file rejected: HTTP {res_empty.status_code} ({res_empty.text})")

    # 10b. Unsupported file extension
    res_unsupported = client.post(
        "/api/v1/documents/upload",
        files={"file": ("script.exe", b"MZBinaryContent", "application/octet-stream")},
        headers=headers,
    )
    assert res_unsupported.status_code == 415, f"Expected 415, got {res_unsupported.status_code}"
    print(f"10b Unsupported type rejected: HTTP {res_unsupported.status_code} ({res_unsupported.text})")

    # 10c. Oversized file (> 10MB)
    huge_bytes = b"0" * (10 * 1024 * 1024 + 1024)
    res_oversize = client.post(
        "/api/v1/documents/upload",
        files={"file": ("huge.pdf", huge_bytes, "application/pdf")},
        headers=headers,
    )
    assert res_oversize.status_code in (413, 415), f"Expected 413 or 415, got {res_oversize.status_code}"
    print(f"10c Oversize file rejected: HTTP {res_oversize.status_code}")
    print("✓ PASS Scenario 10: All invalid file inputs rejected properly with appropriate HTTP error codes.")

    # ----------------------------------------------------
    # SCENARIO 11: End-to-end conversation flow
    # ----------------------------------------------------
    print("\n--- SCENARIO 11: End-to-end conversation flow ---")
    conv_list = client.get("/api/v1/legal-questions/conversations", headers=headers)
    assert conv_list.status_code == 200, f"List failed: {conv_list.text}"
    items = conv_list.json()["items"]
    assert len(items) > 0, "No conversations listed"

    conv_detail = client.get(f"/api/v1/legal-questions/conversations/{conv_id}", headers=headers)
    assert conv_detail.status_code == 200, f"Detail failed: {conv_detail.text}"
    messages = conv_detail.json()["messages"]
    assert len(messages) >= 2, "Expected user question and assistant answer messages in conversation"
    print(f"✓ PASS Scenario 11: End-to-end conversation detail retrieved with {len(messages)} messages.")

    # Cleanup
    client.delete(f"/api/v1/documents/{doc1_id}", headers=headers)
    client.delete(f"/api/v1/legal-questions/conversations/{conv_id}", headers=headers)
    db.delete(user)
    db.commit()
    db.close()

    print("\n" + "=" * 70)
    print("ALL 11 EVALUATION SCENARIOS COMPLETED AND VERIFIED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_all_scenarios()
