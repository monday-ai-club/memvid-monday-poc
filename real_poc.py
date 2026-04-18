#!/usr/bin/env python3
"""
Real Memvid POC for monday.com — Radar, April 15 2026
Tests: encode, search (keyword + NL), latency, incremental update, multi-source
"""

import time
import os
import tempfile
import json

# Suppress cv2 / Qt warnings
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["DISPLAY"] = ""

from memvid import MemvidEncoder, MemvidRetriever

# ── 1. Realistic monday.com workspace data ─────────────────────────────────────
MONDAY_ITEMS = [
    # Sprint notes
    "Sprint 42 planning: decided to migrate authentication service from JWT to OAuth 2.0. Owner: Tal Ben-David. ETA: end of Q2.",
    "Sprint 43 retro: OAuth migration blocked by legacy API gateway. Decision: defer to Q3, keep JWT for now. Action item: file ADR.",
    "Sprint 44: database migration from PostgreSQL 13 to 16 greenlit. DBA team lead: Noa Shapira. Parallel run starts week 3.",
    "Sprint 45 goal: ship the AI widget feature to 10% of enterprise customers. Requires ML pipeline finalization.",
    "Sprint 46 planning: AI widget held due to latency issues on mobile (p99 > 400ms). Investigating model quantization.",

    # Architecture Decision Records
    "ADR-001: Chose Kafka over RabbitMQ for event streaming. Rationale: better partition tolerance, existing team expertise.",
    "ADR-002: API versioning strategy — URL path versioning (/v1/, /v2/) over header versioning. Agreed by platform team.",
    "ADR-003: Frontend monorepo using Nx. Rejected Turborepo due to lack of Go plugin ecosystem support.",
    "ADR-004: Caching layer: Redis Cluster for session data, CDN for static assets. Postgres for persistent state only.",
    "ADR-005: Authentication: move to PKCE-based OAuth 2.0 for all new integrations. Legacy SAML supported until end of 2026.",

    # Customer escalations
    "Customer Acme Corp (Enterprise) escalation: bulk CSV import fails for files >50k rows. Reproducible. Priority: P1. Owner: Yael Levy.",
    "Customer Globex Inc: reporting incorrect row counts in Dashboard aggregations when using timezone offset filters. P2.",
    "Customer Initech escalation: SSO login broken after their IdP migrated to PingFederate. Workaround sent. Fix in progress.",
    "Customer FutureTech Ltd: requesting SCIM 2.0 provisioning support. Currently in roadmap for Q4 2026.",
    "Acme Corp follow-up: root cause identified — CSV parser silently truncates at 65535 rows (int16 overflow). Fix deployed.",

    # Bug reports
    "BUG-4421: Billing page crashes on Safari 16 when switching between monthly/annual plan views. Reproducible 100%. Owner: Dev.",
    "BUG-4532: Notification emails sent in wrong timezone for users with non-UTC calendar settings. Low impact, backlog.",
    "BUG-4601: Board filter state not preserved on page reload when using custom URL scheme. Medium priority.",
    "BUG-4712: Race condition in column reorder causing data loss under high-concurrency writes. P0. Hotfix shipped Apr 10.",
    "BUG-4801: OAuth callback URL whitelist not enforced for subdomain wildcards — security issue. Patched Apr 12.",

    # KPIs and OKRs
    "Q1 2026 KPI: MAU hit 18.4M (+23% YoY). Enterprise tier grew 41%. Churn held below 2.1% target.",
    "Q2 2026 OKR: Ship AI Columns to 100% of pro users. Key result: p99 inference latency <200ms.",
    "Q2 2026 OKR: Reduce support ticket MTTR from 18h to 12h. On track as of April 1.",
    "Q3 2026 OKR: Launch monday Work OS for SMB segment. Requires simplified onboarding flow.",

    # Meeting notes
    "All-hands April 2026: CEO announced strategic partnership with Salesforce for CRM data sync integration.",
    "Engineering weekly Apr 7: discussed adopting Temporal for durable workflow orchestration. Pilot in payments team.",
    "Product review Apr 9: AI Columns feature approved for GA, pending legal review of data retention policy.",
    "Design sync Apr 11: decided to redesign the item view sidebar. New information architecture by end of Q2.",

    # Team-specific context
    "ML Platform team: switched from PyTorch 2.1 to 2.3 for training pipeline. CUDA 12.4 required on all GPU instances.",
    "Data team: migrated analytics pipeline to dbt + DuckDB. Airflow DAGs now generate dbt models automatically.",
    "Platform team: Kubernetes upgrade to 1.32 scheduled for May 15. All teams must pin pod disruption budgets.",
    "Security team: mandatory MFA rollout for all employees complete. SSO enforced for all internal tools.",
    "Frontend team: migrated from Webpack 4 to Vite 6. Build times dropped from 4.2min to 38 seconds.",
    "Infrastructure: moved from AWS us-east-1 to multi-region active-active (us-east-1 + eu-west-1). Latency -40ms for EU.",
]

def banner(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print('='*60)

def run_poc():
    tmpdir = tempfile.mkdtemp()
    video_path = os.path.join(tmpdir, "monday_memory.mp4")
    index_path = os.path.join(tmpdir, "monday_memory.json")

    results = {}

    # ── 2. Encode ──────────────────────────────────────────────────────────────
    banner("STEP 1: Encoding 34 monday.com workspace items")
    enc = MemvidEncoder()
    t0 = time.perf_counter()
    for item in MONDAY_ITEMS:
        enc.add_text(item)
    enc.build_video(video_path, index_path)
    encode_time = (time.perf_counter() - t0) * 1000
    print(f"✅ Encoded {len(MONDAY_ITEMS)} items → {video_path}")
    print(f"   Encode time: {encode_time:.0f}ms")
    print(f"   File size: {os.path.getsize(video_path) / 1024:.1f} KB (video)")
    print(f"   Index size: {os.path.getsize(index_path) / 1024:.1f} KB (JSON)")
    results['encode_ms'] = round(encode_time)
    results['video_kb'] = round(os.path.getsize(video_path) / 1024, 1)

    # ── 3. Load retriever ─────────────────────────────────────────────────────
    banner("STEP 2: Loading retriever")
    ret = MemvidRetriever(video_path, index_path)
    print("✅ Retriever loaded")

    # ── 4. Natural Language queries ───────────────────────────────────────────
    banner("STEP 3: Natural Language Queries (the critical test)")
    nl_queries = [
        ("What did we decide about the database?", "PostgreSQL / DB migration decision"),
        ("What is the status of the AI widget feature?", "AI widget / AI Columns feature"),
        ("What authentication changes are planned?", "OAuth / JWT / PKCE migration"),
        ("What is Acme Corp asking for?", "Acme Corp CSV bulk import issue"),
        ("Who is working on OAuth?", "Tal Ben-David / OAuth owner"),
        ("What were the Q2 priorities?", "OKR / AI Columns / MTTR"),
        ("What engineering decisions were made about Kafka?", "ADR-001 Kafka vs RabbitMQ"),
        ("What frontend tooling changes happened recently?", "Vite / Webpack migration"),
    ]

    nl_results = []
    for query, expected in nl_queries:
        t_q = time.perf_counter()
        hits = ret.search(query, top_k=3)
        latency = (time.perf_counter() - t_q) * 1000
        hit_count = len(hits)
        # Check if best hit is relevant (simple substring check on expected keywords)
        relevant = any(
            any(kw.lower() in h.lower() for kw in expected.split("/"))
            for h in hits
        )
        status = "✅" if relevant else "⚠️ "
        print(f"\n  Query: \"{query}\"")
        print(f"  {status} {hit_count} results, {latency:.1f}ms — relevant: {relevant}")
        if hits:
            print(f"  Top hit: {hits[0][:120]}...")
        nl_results.append({
            "query": query,
            "hits": hit_count,
            "relevant": relevant,
            "latency_ms": round(latency, 1)
        })
    results['nl_queries'] = nl_results
    nl_pass = sum(1 for r in nl_results if r['relevant'])
    print(f"\n  NL Score: {nl_pass}/{len(nl_queries)} queries returned relevant results")

    # ── 5. Keyword queries ────────────────────────────────────────────────────
    banner("STEP 4: Keyword Queries")
    kw_queries = [
        "Acme Corp", "OAuth", "Kafka", "billing bug", "AI Columns", "DuckDB"
    ]
    kw_results = []
    for query in kw_queries:
        t_q = time.perf_counter()
        hits = ret.search(query, top_k=3)
        latency = (time.perf_counter() - t_q) * 1000
        hit_count = len(hits)
        relevant = hit_count > 0 and query.lower() in hits[0].lower()
        status = "✅" if relevant else "⚠️ "
        print(f"  {status} \"{query}\" → {hit_count} hits, {latency:.1f}ms")
        kw_results.append({"query": query, "hits": hit_count, "relevant": relevant, "latency_ms": round(latency, 1)})
    results['kw_queries'] = kw_results

    # ── 6. Latency benchmark ──────────────────────────────────────────────────
    banner("STEP 5: Latency Benchmark (50 queries)")
    bench_queries = [
        "database migration", "customer escalation", "authentication", "sprint planning",
        "engineering decision", "AI feature", "billing", "security patch",
    ] * 7  # 56 queries, take first 50
    bench_queries = bench_queries[:50]
    latencies = []
    for q in bench_queries:
        t_q = time.perf_counter()
        ret.search(q, top_k=3)
        latencies.append((time.perf_counter() - t_q) * 1000)
    latencies.sort()
    p50 = latencies[24]
    p99 = latencies[49]
    print(f"  p50 latency: {p50:.2f}ms")
    print(f"  p99 latency: {p99:.2f}ms")
    results['bench'] = {"p50_ms": round(p50, 2), "p99_ms": round(p99, 2)}

    # ── 7. Incremental update ─────────────────────────────────────────────────
    banner("STEP 6: Incremental Update Test")
    new_item = "Emergency incident Apr 15: payment processing API down for 12 minutes due to expired TLS cert. Postmortem scheduled."
    enc2 = MemvidEncoder()
    for item in MONDAY_ITEMS:
        enc2.add_text(item)
    enc2.add_text(new_item)
    video_path2 = os.path.join(tmpdir, "monday_memory_v2.mp4")
    index_path2 = os.path.join(tmpdir, "monday_memory_v2.json")
    t_update = time.perf_counter()
    enc2.build_video(video_path2, index_path2)
    update_time = (time.perf_counter() - t_update) * 1000
    ret2 = MemvidRetriever(video_path2, index_path2)
    hits = ret2.search("payment processing incident", top_k=3)
    found = any("TLS" in h or "payment" in h or "incident" in h for h in hits)
    print(f"  Update time (rebuild): {update_time:.0f}ms")
    print(f"  New item retrievable: {'✅ YES' if found else '❌ NO'}")
    if hits:
        print(f"  Top hit: {hits[0][:120]}...")
    results['incremental'] = {"rebuild_ms": round(update_time), "new_item_found": found}

    # ── 8. Summary ────────────────────────────────────────────────────────────
    banner("SUMMARY")
    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    run_poc()
