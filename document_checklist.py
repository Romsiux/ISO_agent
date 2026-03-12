"""
document_checklist.py — ISO 27001:2022 mandatory & recommended documents,
ranked by certification priority. Renders a persistent interactive checklist.
"""
from __future__ import annotations

from typing import Dict, List

import streamlit as st

# ---------------------------------------------------------------------------
# Document definitions
# Each entry: id, tier, clause, name, description, why_needed
# ---------------------------------------------------------------------------

CHECKLIST: List[Dict] = [
    # ── TIER 1: Mandatory clauses (auditor will always ask for these) ─────────
    {
        "id": "doc_01", "tier": 1, "priority": 1,
        "clause": "Clause 4.3",
        "name": "ISMS Scope Document",
        "description": "Defines the boundaries and applicability of your ISMS — which systems, locations, and processes are covered.",
        "why": "First thing an auditor checks. Without it, nothing else can be evaluated.",
        "template_key": None,
    },
    {
        "id": "doc_02", "tier": 1, "priority": 2,
        "clause": "Clause 5.2",
        "name": "Information Security Policy",
        "description": "Top-level policy signed by top management committing the organisation to information security.",
        "why": "Demonstrates leadership commitment — mandatory for Stage 1 audit.",
        "template_key": "access_control",
    },
    {
        "id": "doc_03", "tier": 1, "priority": 3,
        "clause": "Clause 6.1.2",
        "name": "Risk Assessment Methodology",
        "description": "Documents how you identify, analyse, and evaluate information security risks — including criteria for risk acceptance.",
        "why": "ISO 27001's core requirement. All other controls are justified through risk.",
        "template_key": "risk_management",
    },
    {
        "id": "doc_04", "tier": 1, "priority": 4,
        "clause": "Clause 6.1.3",
        "name": "Statement of Applicability (SoA)",
        "description": "Lists all 93 Annex A controls, states which are applicable, which are excluded, and justifies each decision.",
        "why": "Required by name in the standard. Auditors will cross-reference every control against it.",
        "template_key": None,
    },
    {
        "id": "doc_05", "tier": 1, "priority": 5,
        "clause": "Clause 6.1.3 / 8.3",
        "name": "Risk Treatment Plan",
        "description": "Documents how each identified risk will be treated (mitigate, accept, avoid, transfer), assigns owners and timelines.",
        "why": "Proves risks are being actively managed, not just identified.",
        "template_key": None,
    },
    {
        "id": "doc_06", "tier": 1, "priority": 6,
        "clause": "Clause 6.2",
        "name": "Information Security Objectives",
        "description": "Measurable security objectives aligned with the IS policy, with plans for achieving them.",
        "why": "Demonstrates that security is being actively improved, not just maintained.",
        "template_key": None,
    },
    {
        "id": "doc_07", "tier": 1, "priority": 7,
        "clause": "Clause 8.2",
        "name": "Risk Assessment Results",
        "description": "The actual completed risk register — output of applying your risk assessment methodology.",
        "why": "Evidence that risk assessments have been performed, not just planned.",
        "template_key": None,
    },
    {
        "id": "doc_08", "tier": 1, "priority": 8,
        "clause": "Clause 9.2",
        "name": "Internal Audit Programme & Reports",
        "description": "Schedule and results of internal ISMS audits, including findings and corrective actions.",
        "why": "Mandatory for certification — proves the ISMS is being monitored internally.",
        "template_key": None,
    },
    {
        "id": "doc_09", "tier": 1, "priority": 9,
        "clause": "Clause 9.3",
        "name": "Management Review Records",
        "description": "Minutes and outcomes of management reviews of the ISMS — must happen at least annually.",
        "why": "Top management must be demonstrably engaged. Auditors look for meeting records.",
        "template_key": None,
    },
    {
        "id": "doc_10", "tier": 1, "priority": 10,
        "clause": "Clause 10.1",
        "name": "Nonconformity & Corrective Action Records",
        "description": "Log of any ISMS nonconformities found and the corrective actions taken to resolve them.",
        "why": "Shows the ISMS has a continual improvement process — required for Clause 10.",
        "template_key": None,
    },

    # ── TIER 2: Mandatory Annex A control policies ────────────────────────────
    {
        "id": "doc_11", "tier": 2, "priority": 11,
        "clause": "A.5.9 / A.5.10",
        "name": "Asset Management Policy & Inventory",
        "description": "Inventory of information assets with owners assigned and acceptable use rules defined.",
        "why": "You cannot protect what you don't know you have. Required by Annex A controls.",
        "template_key": None,
    },
    {
        "id": "doc_12", "tier": 2, "priority": 12,
        "clause": "A.5.12 / A.5.13",
        "name": "Data Classification & Handling Policy",
        "description": "Defines classification levels (e.g., Public, Internal, Confidential, Restricted) and rules for handling each.",
        "why": "Ensures sensitive data receives appropriate protection — frequently tested in audits.",
        "template_key": "data_classification",
    },
    {
        "id": "doc_13", "tier": 2, "priority": 13,
        "clause": "A.5.15 / A.8.2 / A.8.3",
        "name": "Access Control Policy",
        "description": "Rules for granting, reviewing, and revoking access to systems and data — including privileged access.",
        "why": "Access control is the #1 most-tested Annex A theme in ISO 27001 audits.",
        "template_key": "access_control",
    },
    {
        "id": "doc_14", "tier": 2, "priority": 14,
        "clause": "A.5.24 – A.5.28",
        "name": "Incident Response Procedure",
        "description": "Step-by-step procedure for detecting, reporting, classifying, responding to, and learning from security incidents.",
        "why": "NIS2 also requires this. Auditors simulate incident scenarios against this document.",
        "template_key": "incident_response",
    },
    {
        "id": "doc_15", "tier": 2, "priority": 15,
        "clause": "A.5.19 – A.5.22",
        "name": "Supplier Security Policy",
        "description": "Requirements placed on suppliers/vendors who access your information assets — including vetting and contractual obligations.",
        "why": "Supply chain attacks are a top audit focus area and NIS2 Article 21 requirement.",
        "template_key": "supplier_security",
    },
    {
        "id": "doc_16", "tier": 2, "priority": 16,
        "clause": "A.5.29 / A.5.30",
        "name": "Business Continuity Plan (BCP)",
        "description": "Plans for maintaining ISMS and critical business operations during and after a disruptive incident.",
        "why": "Required for NIS2 and heavily scrutinised in audits for critical/essential entities.",
        "template_key": None,
    },
    {
        "id": "doc_17", "tier": 2, "priority": 17,
        "clause": "A.6.1 – A.6.6",
        "name": "HR Security Procedures",
        "description": "Security screening, onboarding, role-based security responsibilities, and offboarding procedures for staff.",
        "why": "Insider threats are a top risk. Auditors check that HR processes enforce security.",
        "template_key": None,
    },
    {
        "id": "doc_18", "tier": 2, "priority": 18,
        "clause": "A.6.3",
        "name": "Security Awareness Training Records",
        "description": "Evidence that all staff receive regular information security awareness training.",
        "why": "Auditors will ask for training records and may interview staff about security practices.",
        "template_key": None,
    },
    {
        "id": "doc_19", "tier": 2, "priority": 19,
        "clause": "A.7.1 – A.7.14",
        "name": "Physical Security Policy",
        "description": "Controls for physical access to facilities — entry controls, clean desk, clear screen, equipment disposal.",
        "why": "Physical breaches can bypass all technical controls. Required Annex A theme.",
        "template_key": None,
    },
    {
        "id": "doc_20", "tier": 2, "priority": 20,
        "clause": "A.8.13",
        "name": "Backup & Recovery Policy",
        "description": "Defines backup frequency, retention, testing, and recovery procedures for critical data and systems.",
        "why": "Ransomware resilience starts here. Auditors test backups are working and tested regularly.",
        "template_key": None,
    },
    {
        "id": "doc_21", "tier": 2, "priority": 21,
        "clause": "A.8.15 / A.8.16",
        "name": "Logging & Monitoring Policy",
        "description": "Rules for what events are logged, how logs are protected, and how anomalies are detected and reviewed.",
        "why": "Required for detecting breaches. NIS2 Article 21 also requires monitoring capabilities.",
        "template_key": None,
    },
    {
        "id": "doc_22", "tier": 2, "priority": 22,
        "clause": "A.8.20 – A.8.22",
        "name": "Network Security Policy",
        "description": "Controls for network segmentation, firewall rules, remote access, and protection of network services.",
        "why": "Network security is a core technical Annex A area. Cloud users must include cloud networking.",
        "template_key": None,
    },
    {
        "id": "doc_23", "tier": 2, "priority": 23,
        "clause": "A.8.24",
        "name": "Cryptographic Policy",
        "description": "Rules for use of encryption — which data must be encrypted, key management, approved algorithms.",
        "why": "GDPR and NIS2 both require encryption of personal/sensitive data. Auditors check this.",
        "template_key": None,
    },
    {
        "id": "doc_24", "tier": 2, "priority": 24,
        "clause": "A.8.25 – A.8.32",
        "name": "Secure Development Policy",
        "description": "Security requirements for software development — secure coding, code review, testing, change management.",
        "why": "Required for any organisation that develops software. Frequently tested for tech companies.",
        "template_key": None,
    },
    {
        "id": "doc_25", "tier": 2, "priority": 25,
        "clause": "A.8.8",
        "name": "Vulnerability Management Procedure",
        "description": "Process for identifying, prioritising, and remediating technical vulnerabilities — including patch management.",
        "why": "Unpatched vulnerabilities are the #1 attack vector. Auditors look for scan evidence.",
        "template_key": None,
    },

    # ── TIER 3: Supporting / best practice documents ──────────────────────────
    {
        "id": "doc_26", "tier": 3, "priority": 26,
        "clause": "Clause 7.2",
        "name": "Competence & Training Records",
        "description": "Evidence that ISMS roles are filled by competent people — CVs, certifications, training logs.",
        "why": "Demonstrates you have qualified people managing security, not just policies on paper.",
        "template_key": None,
    },
    {
        "id": "doc_27", "tier": 3, "priority": 27,
        "clause": "A.5.36",
        "name": "Compliance Review Records",
        "description": "Records of periodic reviews to check compliance with legal, regulatory, and contractual requirements.",
        "why": "Proves ongoing compliance monitoring — important for GDPR, NIS2, and other obligations.",
        "template_key": None,
    },
    {
        "id": "doc_28", "tier": 3, "priority": 28,
        "clause": "A.5.32 / A.5.34",
        "name": "Intellectual Property & Privacy Policy",
        "description": "Policy addressing IP rights, software licensing, and personal data protection (GDPR alignment).",
        "why": "GDPR overlap — important for EU organisations. Often combined with data classification.",
        "template_key": None,
    },
    {
        "id": "doc_29", "tier": 3, "priority": 29,
        "clause": "A.6.7 / A.8.1",
        "name": "Remote Work & BYOD Policy",
        "description": "Security rules for working remotely and use of personal devices — VPN, screen lock, data transfer rules.",
        "why": "Post-pandemic essential. Auditors check remote workers are covered by the ISMS.",
        "template_key": None,
    },
    {
        "id": "doc_30", "tier": 3, "priority": 30,
        "clause": "A.5.26",
        "name": "Lessons Learned / Post-Incident Review",
        "description": "Records of post-incident reviews showing how incidents led to ISMS improvements.",
        "why": "Demonstrates continual improvement and a mature security culture.",
        "template_key": None,
    },
]

TIER_LABELS = {
    1: ("🔴 Tier 1 — Mandatory Clauses", "Required by ISO 27001 clauses. An auditor will always request these."),
    2: ("🟡 Tier 2 — Annex A Policies", "Required to demonstrate control implementation. Most must exist for certification."),
    3: ("🟢 Tier 3 — Supporting Evidence", "Best-practice documents that strengthen your ISMS and satisfy auditor enquiries."),
}


# ---------------------------------------------------------------------------
# Checklist renderer
# ---------------------------------------------------------------------------

def render_checklist(checked: Dict[str, bool], on_change_callback) -> Dict[str, bool]:
    """
    Render the full ISO 27001 document checklist.
    Returns updated checked dict.
    """
    st.markdown("""
    <style>
    .tier-header {
        border-radius: 8px;
        padding: 10px 16px;
        margin: 20px 0 8px 0;
        font-weight: bold;
    }
    .tier-1 { background: #fde8e8; color: #7f1d1d; border-left: 4px solid #dc2626; }
    .tier-2 { background: #fef3c7; color: #78350f; border-left: 4px solid #f59e0b; }
    .tier-3 { background: #dcfce7; color: #14532d; border-left: 4px solid #16a34a; }
    .doc-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px 14px;
        margin: 4px 0;
    }
    .doc-card.done {
        background: #f0fdf4;
        border-color: #bbf7d0;
        opacity: 0.75;
    }
    </style>
    """, unsafe_allow_html=True)

    # Summary stats
    total = len(CHECKLIST)
    done = sum(1 for d in CHECKLIST if checked.get(d["id"], False))
    t1_total = sum(1 for d in CHECKLIST if d["tier"] == 1)
    t1_done  = sum(1 for d in CHECKLIST if d["tier"] == 1 and checked.get(d["id"], False))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Overall progress", f"{done}/{total}", f"{round(done/total*100)}%")
    with col2:
        st.metric("🔴 Mandatory (Tier 1)", f"{t1_done}/{t1_total}",
                  "✅ Complete!" if t1_done == t1_total else f"{t1_total - t1_done} remaining")
    with col3:
        cert_ready = t1_done == t1_total
        st.metric("Certification readiness",
                  "Ready for audit ✅" if cert_ready else "Not yet ready",
                  "All Tier 1 docs complete" if cert_ready else f"Complete {t1_total - t1_done} more Tier 1 docs")

    st.progress(done / total)
    st.caption(f"💡 Tip: Complete all **Tier 1** documents first — these are the minimum required for an ISO 27001 certification audit.")
    st.markdown("---")

    # Group by tier
    current_tier = None
    for doc in sorted(CHECKLIST, key=lambda x: x["priority"]):
        tier = doc["tier"]
        if tier != current_tier:
            current_tier = tier
            label, subtitle = TIER_LABELS[tier]
            tier_class = f"tier-{tier}"
            st.markdown(
                f'<div class="tier-header {tier_class}">{label}<br>'
                f'<span style="font-weight:normal;font-size:0.85rem">{subtitle}</span></div>',
                unsafe_allow_html=True,
            )

        is_done = checked.get(doc["id"], False)
        card_class = "doc-card done" if is_done else "doc-card"

        col_check, col_info = st.columns([1, 11])
        with col_check:
            new_val = st.checkbox(
                label="✓",
                value=is_done,
                key=f"chk_{doc['id']}",
                label_visibility="collapsed",
            )
            if new_val != is_done:
                checked[doc["id"]] = new_val
                on_change_callback(checked)

        with col_info:
            name_display = f"~~{doc['name']}~~" if is_done else f"**{doc['name']}**"
            st.markdown(
                f'<div class="{card_class}">'
                f'<b style="{"text-decoration:line-through;color:#6b7280" if is_done else ""}">'
                f'{doc["name"]}</b> '
                f'<code style="font-size:0.75rem;background:#e2e8f0;padding:1px 6px;border-radius:4px">'
                f'{doc["clause"]}</code><br>'
                f'<span style="font-size:0.82rem;color:#4b5563">{doc["description"]}</span><br>'
                f'<span style="font-size:0.78rem;color:#6366f1">ℹ️ {doc["why"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")
    if st.button("🔄 Reset all checkboxes", type="secondary"):
        for doc in CHECKLIST:
            checked[doc["id"]] = False
        on_change_callback(checked)
        st.rerun()

    return checked