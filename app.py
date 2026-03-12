"""
ISO 27001 / NIS2 Compliance Assistant
Streamlit application — main entry point.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import os
import tempfile
import time
from typing import Dict, List

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config (must be first Streamlit call) ─────────────────────────────
st.set_page_config(
    page_title="ISO 27001 / NIS2 Compliance Assistant",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #0f1b2d;
    }
    [data-testid="stSidebar"] * {
        color: #e8edf3 !important;
    }
    /* Token stats box */
    .token-box {
        background: #1a2940;
        border: 1px solid #2d4a6e;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 0.85rem;
    }
    /* Source citation block */
    .citation-block {
        background: #f0f4f8;
        border-left: 4px solid #2563eb;
        border-radius: 4px;
        padding: 10px 14px;
        margin: 4px 0;
        font-size: 0.82rem;
        color: #1e3a5f;
    }
    /* Quick action buttons */
    .stButton > button {
        border-radius: 20px;
        font-size: 0.8rem;
        padding: 4px 12px;
    }
    /* Chat input */
    .stChatInput textarea {
        border-radius: 12px;
    }
    /* Tool call indicator */
    .tool-pill {
        display: inline-block;
        background: #dbeafe;
        color: #1d4ed8;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.75rem;
        margin: 2px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Lazy imports (only after page config) ─────────────────────────────────
from agent import ComplianceAgent, messages_to_langchain
from config import AVAILABLE_MODELS, COMPANY_INDUSTRY, COMPANY_NAME, DEFAULT_MODEL, OPENAI_API_KEY
from docx_exporter import policy_to_docx
from document_checklist import CHECKLIST, render_checklist
from persistence import (
    delete_profile, get_last_used_id, list_profiles,
    save_profile, set_last_used, update_doc_checked,
    load_session, save_session,
)
from rag_engine import RAGEngine

# ── Session state initialisation ───────────────────────────────────────────

def _init_state() -> None:
    # ── Load persisted profiles ───────────────────────────────────────────────
    profiles = list_profiles()
    last_id = get_last_used_id()

    defaults: Dict = {
        "messages": [],
        "rag_engine": None,
        "agent": None,
        "api_key": OPENAI_API_KEY,
        "company_name": COMPANY_NAME,
        "company_industry": COMPANY_INDUSTRY,
        "selected_model": DEFAULT_MODEL,
        "_show_form": None,
        # Company selector screen — show if any profiles exist
        "show_company_selector": len(profiles) > 0,
        "onboarding_complete": False,
        "company_profile": {},
        "current_profile_id": None,
        "doc_checked": {d["id"]: False for d in CHECKLIST},
        # Token counters
        "total_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_cost": 0.0,
        "kb_chunks": 0,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()


# ===========================================================================
# COMPANY SELECTOR  (shown at startup when saved profiles exist)
# ===========================================================================

def _load_profile_into_session(profile: Dict) -> None:
    """Apply a saved profile dict to session state."""
    st.session_state.company_name = profile.get("company_name", "")
    st.session_state.company_industry = profile.get("company_industry", "")
    st.session_state.company_profile = profile.get("company_profile", {})
    st.session_state.doc_checked = profile.get("doc_checked", {d["id"]: False for d in CHECKLIST})
    st.session_state.current_profile_id = profile.get("id")
    st.session_state.onboarding_complete = True
    st.session_state.show_company_selector = False
    st.session_state.messages = []
    st.session_state.agent = None
    set_last_used(profile["id"])


def show_company_selector() -> None:
    """Startup screen: select an existing company or create a new one."""
    st.markdown("""
    <style>
    .selector-header {
        background: linear-gradient(135deg, #1a2940 0%, #2563eb 100%);
        border-radius: 12px;
        padding: 28px 32px;
        margin-bottom: 28px;
        color: white;
    }
    .company-card {
        background: white;
        border: 2px solid #e2e8f0;
        border-radius: 10px;
        padding: 18px 20px;
        margin: 8px 0;
        cursor: pointer;
        transition: border-color 0.2s;
    }
    .company-card:hover { border-color: #2563eb; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="selector-header">
        <h2 style="color:white;margin:0">🔒 ISO 27001 / NIS2 Compliance Assistant</h2>
        <p style="color:#93c5fd;margin:8px 0 0 0">Select a company profile to continue or create a new one.</p>
    </div>
    """, unsafe_allow_html=True)

    profiles = list_profiles()

    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        st.markdown("### 🏢 Saved Companies")
        if not profiles:
            st.info("No saved companies yet.")
        else:
            for p in profiles:
                profile_data = p.get("company_profile", {})
                cert_status = profile_data.get("cert_status", "—")
                industry = p.get("company_industry", "—")
                # Count checklist progress
                checked = p.get("doc_checked", {})
                done = sum(1 for v in checked.values() if v)
                total = len(CHECKLIST)

                with st.container(border=True):
                    col_info, col_btns = st.columns([4, 2])
                    with col_info:
                        st.markdown(f"**{p['company_name']}**")
                        st.caption(f"🏭 {industry}   |   📋 {cert_status}")
                        st.caption(f"📄 Documents: {done}/{total} ready")
                    with col_btns:
                        if st.button("▶ Select", key=f"sel_{p['id']}", type="primary", use_container_width=True):
                            _load_profile_into_session(p)
                            st.rerun()
                        if st.button("🗑 Delete", key=f"del_{p['id']}", use_container_width=True):
                            delete_profile(p["id"])
                            st.rerun()

    with col_right:
        st.markdown("### ➕ New Company")
        st.markdown(
            "Set up a fresh profile for a different company "
            "or a new certification project."
        )
        if st.button("🚀 Create New Company Profile", type="primary", use_container_width=True):
            # Reset state and go to onboarding
            st.session_state.onboarding_complete = False
            st.session_state.show_company_selector = False
            st.session_state.company_profile = {}
            st.session_state.current_profile_id = None
            st.session_state.doc_checked = {d["id"]: False for d in CHECKLIST}
            st.session_state.wizard_step = 1
            st.session_state.wizard_data = {}
            st.session_state.messages = []
            st.session_state.agent = None
            st.rerun()


# ── Gate 1: Show company selector if profiles exist ───────────────────────
if st.session_state.show_company_selector:
    show_company_selector()
    st.stop()


# ===========================================================================
# ONBOARDING WIZARD  (shown once before the main app)
# ===========================================================================

def _build_system_context(profile: Dict) -> str:
    """Convert company profile dict into a rich system context string."""
    lines = ["## Company Profile for ISO 27001 / NIS2 Assessment\n"]
    mapping = {
        "company_name":        "Company name",
        "industry":            "Industry",
        "company_size":        "Company size",
        "country":             "Country / jurisdiction",
        "isms_scope":          "ISMS scope",
        "cert_status":         "Current certification status",
        "asset_types":         "Key information assets",
        "data_types":          "Types of data processed",
        "regulatory":          "Regulatory requirements",
        "cloud_usage":         "Cloud / hosting model",
        "remote_work":         "Remote work policy",
        "existing_controls":   "Existing security controls",
        "maturity_level":      "Security maturity level",
        "top_risks":           "Top perceived risks",
        "cert_timeline":       "Target certification timeline",
        "extra_context":       "Additional context",
    }
    for key, label in mapping.items():
        val = profile.get(key)
        if val:
            if isinstance(val, list):
                val = ", ".join(val)
            lines.append(f"- **{label}:** {val}")
    return "\n".join(lines)


def show_onboarding() -> None:
    """
    Multi-step onboarding wizard that collects ISO-relevant company context.
    Sets st.session_state.onboarding_complete = True when done.
    """
    # Extra CSS for the wizard
    st.markdown("""
    <style>
    .wizard-header {
        background: linear-gradient(135deg, #1a2940 0%, #2563eb 100%);
        border-radius: 12px;
        padding: 28px 32px;
        margin-bottom: 24px;
        color: white;
    }
    .step-indicator {
        background: #f0f4f8;
        border-radius: 8px;
        padding: 10px 16px;
        margin-bottom: 20px;
        font-size: 0.85rem;
        color: #374151;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="wizard-header">
        <h2 style="color:white; margin:0">🔒 ISO 27001 / NIS2 Compliance Assistant</h2>
        <p style="color:#93c5fd; margin:8px 0 0 0">
        Let's set up your company profile so I can give you precise, 
        personalised compliance guidance.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Track wizard step
    if "wizard_step" not in st.session_state:
        st.session_state.wizard_step = 1
    if "wizard_data" not in st.session_state:
        st.session_state.wizard_data = {}

    step = st.session_state.wizard_step
    total_steps = 4

    # Step indicator
    progress = step / total_steps
    st.progress(progress)
    st.markdown(
        f'<div class="step-indicator">Step {step} of {total_steps} — '
        f'{"Company basics" if step == 1 else "Scope & assets" if step == 2 else "Security posture" if step == 3 else "Goals & timeline"}'
        f"</div>",
        unsafe_allow_html=True,
    )

    d = st.session_state.wizard_data  # shorthand

    # ── Step 1: Company basics ─────────────────────────────────────────────
    if step == 1:
        st.markdown("### 🏢 Tell me about your company")

        col1, col2 = st.columns(2)
        with col1:
            d["company_name"] = st.text_input(
                "Company name *",
                value=d.get("company_name", ""),
                placeholder="Acme Corp",
            )
        with col2:
            d["country"] = st.text_input(
                "Country / jurisdiction *",
                value=d.get("country", ""),
                placeholder="e.g. Lithuania, Germany, EU",
            )

        d["industry"] = st.selectbox(
            "Industry sector *",
            options=[
                "Technology / Software",
                "Finance / Banking",
                "Healthcare",
                "Manufacturing",
                "Retail / E-commerce",
                "Government / Public sector",
                "Energy / Utilities",
                "Telecommunications",
                "Legal / Professional services",
                "Education",
                "Other",
            ],
            index=["Technology / Software","Finance / Banking","Healthcare",
                   "Manufacturing","Retail / E-commerce","Government / Public sector",
                   "Energy / Utilities","Telecommunications","Legal / Professional services",
                   "Education","Other"].index(d.get("industry", "Technology / Software")),
        )

        d["company_size"] = st.select_slider(
            "Company size (number of employees)",
            options=["1–10", "11–50", "51–200", "201–500", "501–1000", "1000+"],
            value=d.get("company_size", "11–50"),
        )

        d["cert_status"] = st.radio(
            "Current ISO 27001 certification status",
            options=[
                "Not started yet",
                "Just beginning preparation",
                "Gap analysis in progress",
                "Implementing controls",
                "Ready for audit",
                "Already certified — maintaining/renewing",
            ],
            index=["Not started yet","Just beginning preparation","Gap analysis in progress",
                   "Implementing controls","Ready for audit",
                   "Already certified — maintaining/renewing"].index(
                       d.get("cert_status", "Not started yet")),
            horizontal=False,
        )

        st.markdown("")
        if st.button("Next →", type="primary", use_container_width=False):
            if not d.get("company_name") or not d.get("country"):
                st.warning("Please fill in company name and country.")
            else:
                st.session_state.wizard_step = 2
                st.rerun()

    # ── Step 2: Scope & assets ─────────────────────────────────────────────
    elif step == 2:
        st.markdown("### 🗂️ Scope of your Information Security Management System")

        d["isms_scope"] = st.text_area(
            "Describe what your ISMS should cover (ISO 27001 Clause 4.3) *",
            value=d.get("isms_scope", ""),
            placeholder=(
                "e.g. 'All IT systems and processes supporting our SaaS product, "
                "including development, operations, and customer support at our Vilnius office.'"
            ),
            height=100,
        )

        st.markdown("**What types of information assets does your organisation hold?**")
        asset_options = [
            "Customer personal data (PII)",
            "Employee records",
            "Financial data",
            "Intellectual property / source code",
            "Health / medical records",
            "Payment card data (PCI)",
            "Trade secrets / business strategy",
            "Operational / OT systems data",
            "Third-party / supplier data",
        ]
        d["asset_types"] = st.multiselect(
            "Select all that apply",
            options=asset_options,
            default=d.get("asset_types", []),
        )

        d["cloud_usage"] = st.selectbox(
            "Infrastructure / hosting model",
            options=[
                "On-premises only",
                "Mostly on-premises, some cloud",
                "Hybrid (mixed on-prem and cloud)",
                "Mostly cloud",
                "Cloud-only (AWS / Azure / GCP)",
                "Multi-cloud",
            ],
            index=["On-premises only","Mostly on-premises, some cloud","Hybrid (mixed on-prem and cloud)",
                   "Mostly cloud","Cloud-only (AWS / Azure / GCP)","Multi-cloud"].index(
                       d.get("cloud_usage", "Hybrid (mixed on-prem and cloud)")),
        )

        d["remote_work"] = st.selectbox(
            "Remote work situation",
            options=[
                "All office-based",
                "Mostly office, occasional remote",
                "Hybrid (regular remote + office)",
                "Mostly remote",
                "Fully remote",
            ],
            index=["All office-based","Mostly office, occasional remote",
                   "Hybrid (regular remote + office)","Mostly remote","Fully remote"].index(
                       d.get("remote_work", "Hybrid (regular remote + office)")),
        )

        col_back, col_next = st.columns([1, 5])
        with col_back:
            if st.button("← Back"):
                st.session_state.wizard_step = 1
                st.rerun()
        with col_next:
            if st.button("Next →", type="primary"):
                if not d.get("isms_scope") or not d.get("asset_types"):
                    st.warning("Please fill in ISMS scope and select at least one asset type.")
                else:
                    st.session_state.wizard_step = 3
                    st.rerun()

    # ── Step 3: Security posture ───────────────────────────────────────────
    elif step == 3:
        st.markdown("### 🛡️ Current security posture")

        d["maturity_level"] = st.select_slider(
            "How would you rate your current information security maturity?",
            options=[
                "1 — Ad hoc (no formal processes)",
                "2 — Basic (some policies exist)",
                "3 — Defined (documented processes)",
                "4 — Managed (measured and monitored)",
                "5 — Optimised (continuously improving)",
            ],
            value=d.get("maturity_level", "2 — Basic (some policies exist)"),
        )

        st.markdown("**Which controls does your organisation already have in place?**")
        control_options = [
            "Written information security policy",
            "Access control / IAM system",
            "Multi-factor authentication (MFA)",
            "Antivirus / endpoint protection",
            "Firewall / network segmentation",
            "Data backup and recovery",
            "Encryption (data at rest and/or in transit)",
            "Security awareness training",
            "Incident response procedure",
            "Supplier / vendor security assessments",
            "Vulnerability scanning",
            "SIEM / security monitoring",
            "Business continuity plan",
            "Risk register",
            "Data classification scheme",
        ]
        d["existing_controls"] = st.multiselect(
            "Select all that apply",
            options=control_options,
            default=d.get("existing_controls", []),
        )

        st.markdown("**Regulatory and compliance requirements applicable to your organisation:**")
        reg_options = [
            "GDPR (EU data protection)",
            "NIS2 Directive",
            "PCI DSS (payment cards)",
            "HIPAA (US healthcare)",
            "SOC 2",
            "ISO 27001 (our goal)",
            "Local national cybersecurity law",
            "Sector-specific regulation",
            "None / unsure",
        ]
        d["regulatory"] = st.multiselect(
            "Select all applicable",
            options=reg_options,
            default=d.get("regulatory", ["GDPR (EU data protection)", "NIS2 Directive"]),
        )

        col_back, col_next = st.columns([1, 5])
        with col_back:
            if st.button("← Back"):
                st.session_state.wizard_step = 2
                st.rerun()
        with col_next:
            if st.button("Next →", type="primary"):
                st.session_state.wizard_step = 4
                st.rerun()

    # ── Step 4: Goals & timeline ───────────────────────────────────────────
    elif step == 4:
        st.markdown("### 🎯 Goals & timeline")

        d["cert_timeline"] = st.selectbox(
            "Target ISO 27001 certification timeline",
            options=[
                "As soon as possible (< 3 months)",
                "3–6 months",
                "6–12 months",
                "12–18 months",
                "No fixed deadline — just improving",
                "Already certified",
            ],
            index=["As soon as possible (< 3 months)","3–6 months","6–12 months",
                   "12–18 months","No fixed deadline — just improving","Already certified"].index(
                       d.get("cert_timeline", "6–12 months")),
        )

        st.markdown("**What are your top 3 perceived information security risks?**")
        risk_options = [
            "Ransomware / malware attack",
            "Phishing / social engineering",
            "Insider threat (employee misconduct)",
            "Data breach / leak",
            "Supply chain / third-party compromise",
            "Cloud misconfiguration",
            "Unpatched vulnerabilities",
            "Physical security breach",
            "Business disruption / outage",
            "Regulatory fine / non-compliance",
        ]
        d["top_risks"] = st.multiselect(
            "Select up to 3",
            options=risk_options,
            default=d.get("top_risks", []),
            max_selections=3,
        )

        d["extra_context"] = st.text_area(
            "Anything else the assistant should know? (optional)",
            value=d.get("extra_context", ""),
            placeholder=(
                "e.g. 'We recently had a security incident', "
                "'Our biggest customer requires ISO 27001', "
                "'We are a startup with a small IT team of 2 people'…"
            ),
            height=90,
        )

        st.markdown("---")
        col_back, _, col_start = st.columns([1, 3, 2])
        with col_back:
            if st.button("← Back"):
                st.session_state.wizard_step = 3
                st.rerun()
        with col_start:
            if st.button("🚀 Start the assistant", type="primary", use_container_width=True):
                # Save profile to session state
                st.session_state.company_profile = dict(d)
                st.session_state.company_name = d.get("company_name", "Your Company")
                st.session_state.company_industry = d.get("industry", "Technology")
                st.session_state.onboarding_complete = True

                # Save as a new profile (or update existing)
                pid = save_profile(
                    company_name=st.session_state.company_name,
                    company_industry=st.session_state.company_industry,
                    company_profile=dict(d),
                    doc_checked=st.session_state.get("doc_checked", {ch["id"]: False for ch in CHECKLIST}),
                    profile_id=st.session_state.get("current_profile_id"),
                )
                st.session_state.current_profile_id = pid

                # Build a rich opening message from the assistant
                profile_summary = _build_system_context(d)
                welcome = (
                    f"👋 Welcome, **{d.get('company_name', 'your company')}**!\n\n"
                    f"I've saved your profile. Here's a quick summary of what I know:\n\n"
                    f"{profile_summary}\n\n"
                    f"---\n"
                    f"Based on your profile, here's where I'd suggest we start:\n\n"
                )
                # Add personalised suggestions
                suggestions = []
                status = d.get("cert_status", "")
                if "Not started" in status or "beginning" in status:
                    suggestions.append("1. **Run a full Gap Analysis** to see which of the 93 ISO 27001 controls you're missing")
                    suggestions.append("2. **Generate a Risk Management Policy** to establish your risk assessment process (required by Clause 6.1)")
                    suggestions.append("3. Ask me to explain **ISO 27001 Clause 4** (context of the organisation) — the first step")
                elif "Gap analysis" in status or "Implementing" in status:
                    suggestions.append("1. Use **Gap Analysis** to check your current control implementation progress")
                    suggestions.append("2. **Generate policy templates** for any controls you haven't documented yet")
                    suggestions.append("3. Run **Risk Assessments** on your key assets")
                else:
                    suggestions.append("1. Ask me any specific compliance question")
                    suggestions.append("2. Generate or review **policy templates**")
                    suggestions.append("3. Check **ISO 27001 ↔ NIS2 control mappings** for dual compliance")

                if "NIS2 Directive" in d.get("regulatory", []):
                    suggestions.append("4. ⚠️ **NIS2 is applicable to you** — I'll flag NIS2 obligations alongside ISO 27001 controls")

                welcome += "\n".join(suggestions)
                welcome += "\n\n💬 Type a question below or use the **Quick Actions** buttons to get started."

                st.session_state.messages = [{"role": "assistant", "content": welcome}]
                st.rerun()


# ── Gate: show onboarding if not complete ─────────────────────────────────
if not st.session_state.onboarding_complete:
    show_onboarding()
    st.stop()

# Build context string from saved profile (injected into agent calls)
_profile_context = _build_system_context(st.session_state.company_profile)


def _get_rag() -> RAGEngine:
    if st.session_state.rag_engine is None:
        if not st.session_state.api_key:
            st.error("⚠️ Please enter your OpenAI API key in the sidebar.")
            st.stop()
        st.session_state.rag_engine = RAGEngine(st.session_state.api_key)
        st.session_state.kb_chunks = st.session_state.rag_engine.get_chunk_count()
    return st.session_state.rag_engine


def _get_agent() -> ComplianceAgent:
    if st.session_state.agent is None:
        rag = _get_rag()
        st.session_state.agent = ComplianceAgent(rag, model_label=st.session_state.selected_model)
    return st.session_state.agent


# ===========================================================================
# SIDEBAR
# ===========================================================================

with st.sidebar:
    # Logo / title
    st.markdown("## 🔒 ISO Compliance\n### Assistant")
    st.markdown("---")

    # ── API Key ──────────────────────────────────────────────────────────────
    st.markdown("### ⚙️ Configuration")
    api_key_input = st.text_input(
        "OpenAI API Key",
        value=st.session_state.api_key,
        type="password",
        help="Your OpenAI API key. Never shared or stored.",
    )
    if api_key_input != st.session_state.api_key:
        st.session_state.api_key = api_key_input
        # Reset so they're rebuilt with the new key
        st.session_state.rag_engine = None
        st.session_state.agent = None
        os.environ["OPENAI_API_KEY"] = api_key_input

    col1, col2 = st.columns(2)
    with col1:
        company_name = st.text_input("Company", value=st.session_state.company_name)
        if company_name != st.session_state.company_name:
            st.session_state.company_name = company_name
    with col2:
        industry = st.text_input("Industry", value=st.session_state.company_industry)
        if industry != st.session_state.company_industry:
            st.session_state.company_industry = industry

    st.markdown("---")

    # ── Model selector ────────────────────────────────────────────────────────
    st.markdown("### 🤖 AI Model")
    selected_model = st.selectbox(
        "Main agent model",
        options=list(AVAILABLE_MODELS.keys()),
        index=list(AVAILABLE_MODELS.keys()).index(st.session_state.selected_model),
        help="Policy Generator always uses Claude regardless of this setting.",
    )
    if selected_model != st.session_state.selected_model:
        st.session_state.selected_model = selected_model
        st.session_state.agent = None  # Force rebuild with new model

    st.caption("📋 Policy Generator always uses Claude ✨")

    # Show extra API key field based on selected model
    provider = AVAILABLE_MODELS.get(selected_model, {}).get("provider", "openai")
    if provider == "anthropic":
        ak = st.text_input("Anthropic API Key", value=os.getenv("ANTHROPIC_API_KEY", ""), type="password")
        if ak:
            os.environ["ANTHROPIC_API_KEY"] = ak
    elif provider == "google":
        gk = st.text_input("Google API Key", value=os.getenv("GOOGLE_API_KEY", ""), type="password")
        if gk:
            os.environ["GOOGLE_API_KEY"] = gk

    # Always show Anthropic key for the policy tool (even when using GPT/Gemini)
    if provider != "anthropic":
        with st.expander("🔑 Anthropic key (for Policy Generator)"):
            ak2 = st.text_input("Anthropic API Key", value=os.getenv("ANTHROPIC_API_KEY", ""), type="password", key="ak_policy")
            if ak2:
                os.environ["ANTHROPIC_API_KEY"] = ak2

    st.markdown("---")

    # ── Knowledge Base ────────────────────────────────────────────────────────
    st.markdown("### 📚 Knowledge Base")

    chunks = st.session_state.kb_chunks
    if chunks > 0:
        st.success(f"✅ {chunks:,} chunks indexed")
    else:
        st.info("No documents indexed yet")

    uploaded_files = st.file_uploader(
        "Upload Documents",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        help="Upload ISO 27001 PDFs, NIS2 docs, company policies, etc.",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        index_btn = st.button("📥 Index Docs", use_container_width=True, type="primary")
    with col_b:
        clear_btn = st.button("🗑️ Clear KB", use_container_width=True)

    if index_btn and uploaded_files:
        rag = _get_rag()
        with st.spinner("Indexing documents…"):
            tmp_paths: List[str] = []
            try:
                for uf in uploaded_files:
                    suffix = "." + uf.name.split(".")[-1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uf.read())
                        tmp_paths.append(tmp.name)

                count, errors = rag.load_documents(tmp_paths)
                st.session_state.kb_chunks = rag.get_chunk_count()
                # Rebuild agent so the search tool uses the updated store
                st.session_state.agent = None

                if errors:
                    for err in errors:
                        st.warning(err)
                if count > 0:
                    st.success(f"✅ Indexed {count} chunks from {len(uploaded_files)} file(s)")
                    st.rerun()
                else:
                    st.error("No chunks were created. Check file formats.")
            finally:
                for p in tmp_paths:
                    try:
                        os.unlink(p)
                    except OSError:
                        pass
    elif index_btn:
        st.warning("Please upload files first.")

    if clear_btn:
        rag = _get_rag()
        rag.clear()
        st.session_state.kb_chunks = 0
        st.session_state.agent = None
        st.success("Knowledge base cleared.")
        st.rerun()

    st.markdown("---")

    # ── Token Usage ───────────────────────────────────────────────────────────
    st.markdown("### 📊 Token Usage (Session)")
    st.markdown(
        f"""
        <div class="token-box">
        🔡 <b>Total tokens:</b> {st.session_state.total_tokens:,}<br>
        ↑ <b>Prompt:</b> {st.session_state.prompt_tokens:,}<br>
        ↓ <b>Completion:</b> {st.session_state.completion_tokens:,}<br>
        💰 <b>Est. cost:</b> ${st.session_state.total_cost:.4f}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Company profile summary ───────────────────────────────────────────────
    profile = st.session_state.company_profile
    if profile:
        st.markdown("### 🏢 Company Profile")
        st.markdown(
            f"""
            <div class="token-box">
            🏢 <b>{profile.get('company_name', '—')}</b><br>
            🏭 {profile.get('industry', '—')}<br>
            👥 {profile.get('company_size', '—')} employees<br>
            🌍 {profile.get('country', '—')}<br>
            📋 {profile.get('cert_status', '—')}<br>
            ⏱️ {profile.get('cert_timeline', '—')}
            </div>
            """,
            unsafe_allow_html=True,
        )
    if st.button("🧹 Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    if st.button("🔄 Switch Company", use_container_width=True):
        st.session_state.show_company_selector = True
        st.session_state.onboarding_complete = False
        st.session_state.messages = []
        st.session_state.agent = None
        st.rerun()

    if st.button("✏️ Edit Company Profile", use_container_width=True):
        st.session_state.onboarding_complete = False
        st.session_state.show_company_selector = False
        st.session_state.wizard_step = 1
        st.rerun()

    st.markdown(
        "<small style='color:#6b8cae'>Built with LangChain · ChromaDB · GPT-4o</small>",
        unsafe_allow_html=True,
    )


# ===========================================================================
# MAIN PANEL
# ===========================================================================

st.markdown("# 🔒 ISO 27001 / NIS2 Compliance Assistant")
st.markdown(
    "Upload your ISO standards, company policies, or NIS2 documentation, "
    "then ask any compliance question. I can assess risks, identify gaps, "
    "generate policies, and map controls between standards."
)

# ── Main tabs ──────────────────────────────────────────────────────────────
tab_chat, tab_docs = st.tabs(["💬 Chat", "📄 Document Checklist"])

with tab_docs:
    st.markdown("### 📄 ISO 27001 Required Documents")
    st.markdown(
        "Track which mandatory and recommended documents you have prepared. "
        "**Check off each document as you complete it** — progress is saved automatically "
        "and will be here next time you open the app."
    )

    def _save_checklist(checked: Dict) -> None:
        st.session_state.doc_checked = checked
        if st.session_state.current_profile_id:
            update_doc_checked(st.session_state.current_profile_id, checked)
        else:
            save_session({
                "company_name": st.session_state.company_name,
                "company_industry": st.session_state.company_industry,
                "company_profile": st.session_state.company_profile,
                "doc_checked": checked,
            })

    st.session_state.doc_checked = render_checklist(
        st.session_state.doc_checked,
        on_change_callback=_save_checklist,
    )

with tab_chat:
    # ── Quick-action buttons ─────────────────────────────────────────────────
    st.markdown("**Quick Actions:**")
    qa_cols = st.columns(6)

    with qa_cols[0]:
        if st.button("🎯 Gap Analysis", use_container_width=True):
            st.session_state._show_form = "gap"
    with qa_cols[1]:
        if st.button("⚠️ Risk Calc", use_container_width=True):
            st.session_state._show_form = "risk"
    with qa_cols[2]:
        if st.button("📋 Policy Generator", use_container_width=True):
            st.session_state._show_form = "policy"
            st.session_state._policy_requested = False  # reset until form submitted
    with qa_cols[3]:
        if st.button("🇪🇺 NIS2 Guide", use_container_width=True):
            st.session_state._show_form = "nis2"
    with qa_cols[4]:
        if st.button("🏅 ISO 27001 Guide", use_container_width=True):
            st.session_state._show_form = "iso"
    with qa_cols[5]:
        if st.button("🧠 Test Knowledge", use_container_width=True):
            st.session_state._show_form = "quiz"

    # ── Interactive forms ────────────────────────────────────────────────────
    active_form = st.session_state.get("_show_form")

    if active_form == "gap":
        with st.container(border=True):
            st.markdown("#### 🎯 Compliance Gap Analysis")
            st.caption("List the ISO 27001:2022 Annex A control IDs your company has already implemented.")
            controls_input = st.text_area(
                "Implemented controls (comma-separated)",
                placeholder="e.g. 5.1, 5.2, 5.4, 6.3, 8.5, 8.7, 8.13",
                help="Use IDs from 5.1–5.37, 6.1–6.8, 7.1–7.14, 8.1–8.34. Leave blank if none yet.",
            )
            col_run, col_cancel = st.columns([1, 4])
            with col_run:
                if st.button("▶ Analyse", type="primary"):
                    if controls_input.strip():
                        st.session_state._quick_prompt = f"Analyze my compliance gaps. I have implemented these controls: {controls_input}"
                    else:
                        st.session_state._quick_prompt = "Analyze my compliance gaps. I have not implemented any controls yet. Show me all critical gaps."
                    st.session_state._show_form = None
                    st.rerun()
            with col_cancel:
                if st.button("✕ Cancel"):
                    st.session_state._show_form = None
                    st.rerun()

    elif active_form == "risk":
        with st.container(border=True):
            st.markdown("#### ⚠️ Risk Assessment")
            st.caption("Fill in details about the asset you want to assess.")
            asset_name = st.text_input("Asset name", placeholder="e.g. Customer database, Employee laptops, VPN server")
            col1, col2, col3 = st.columns(3)
            with col1:
                asset_value = st.slider("Asset value", 1, 5, 3, help="How critical is this asset to your business? (1=low, 5=critical)")
            with col2:
                likelihood = st.slider("Threat likelihood", 1, 5, 2, help="How likely is a threat to exploit this? (1=rare, 5=almost certain)")
            with col3:
                vulnerability = st.slider("Vulnerability level", 1, 5, 2, help="How exposed/vulnerable is this asset? (1=minimal, 5=severe)")
            existing_controls = st.text_input("Existing controls", placeholder="e.g. Firewall, antivirus, MFA — or leave blank if none")
            col_run, col_cancel = st.columns([1, 4])
            with col_run:
                if st.button("▶ Calculate", type="primary"):
                    if asset_name.strip():
                        controls_str = existing_controls.strip() or "None"
                        st.session_state._quick_prompt = (
                            f"Calculate risk for an asset: asset_name='{asset_name}', "
                            f"asset_value={asset_value}, threat_likelihood={likelihood}, "
                            f"vulnerability_level={vulnerability}, existing_controls='{controls_str}'"
                        )
                        st.session_state._show_form = None
                        st.rerun()
                    else:
                        st.warning("Please enter an asset name.")
            with col_cancel:
                if st.button("✕ Cancel"):
                    st.session_state._show_form = None
                    st.rerun()

    elif active_form == "policy":
        with st.container(border=True):
            st.markdown("#### 📋 Policy Template Generator")
            policy_type = st.selectbox(
                "Which policy do you need?",
                options=["access_control", "incident_response", "risk_management", "data_classification", "supplier_security"],
                format_func=lambda x: {
                    "access_control": "Access Control Policy",
                    "incident_response": "Incident Response Policy",
                    "risk_management": "Risk Management Policy",
                    "data_classification": "Data Classification Policy",
                    "supplier_security": "Supplier Security Policy",
                }[x],
            )
            company = st.text_input("Company name", value=st.session_state.company_name)
            domain = st.text_input("Company email domain", placeholder="e.g. mycompany.com")
            col_run, col_cancel = st.columns([1, 4])
            with col_run:
                if st.button("▶ Generate", type="primary"):
                    domain_str = domain.strip() or "company.com"
                    st.session_state._quick_prompt = (
                        f"Generate a {policy_type} policy template for company_name='{company}', "
                        f"company_domain='{domain_str}'"
                    )
                    st.session_state._policy_requested = True
                    st.session_state._show_form = None
                    st.rerun()
            with col_cancel:
                if st.button("✕ Cancel"):
                    st.session_state._show_form = None
                    st.rerun()

    elif active_form == "nis2":
        with st.container(border=True):
            st.markdown("#### 📖 NIS2 Directive Guide")

            # Summary banner
            st.markdown("""
            <div style="background:#eff6ff;border-left:4px solid #2563eb;border-radius:6px;
                        padding:12px 16px;margin-bottom:14px;font-size:0.9rem;color:#1e3a5f">
            <b>NIS2 (Network and Information Security Directive 2)</b> is the EU's updated 
            cybersecurity law effective from <b>October 2024</b>. It expands the scope of NIS1, 
            tightens security requirements, and introduces significant fines (up to 
            <b>€10M or 2% of global turnover</b>). It closely overlaps with ISO 27001 — 
            organisations already certified save significant compliance effort.
            </div>
            """, unsafe_allow_html=True)

            st.markdown("**Choose a topic to explore:**")

            # Row 1
            r1c1, r1c2, r1c3 = st.columns(3)
            with r1c1:
                if st.button("🏢 Does my organisation need to comply?",
                             use_container_width=True, key="nis2_q1"):
                    industry = st.session_state.company_profile.get("industry", "")
                    size = st.session_state.company_profile.get("company_size", "")
                    country = st.session_state.company_profile.get("country", "")
                    st.session_state._quick_prompt = (
                        f"Does my organisation need to comply with NIS2? "
                        f"We are a {size}-employee company in the {industry} sector, based in {country}. "
                        f"Explain the NIS2 entity categories (essential vs important), which sectors are covered, "
                        f"size thresholds, and give a clear yes/no recommendation for our profile."
                    )
                    st.session_state._show_form = None
                    st.rerun()
            with r1c2:
                if st.button("📋 What are the Article 21 requirements?",
                             use_container_width=True, key="nis2_q2"):
                    st.session_state._quick_prompt = (
                        "Give me a structured breakdown of all NIS2 Article 21 security requirements. "
                        "For each requirement, explain what it means in practice, what evidence an auditor "
                        "would look for, and which ISO 27001:2022 Annex A controls it maps to."
                    )
                    st.session_state._show_form = None
                    st.rerun()
            with r1c3:
                if st.button("⚡ What are the incident reporting obligations?",
                             use_container_width=True, key="nis2_q3"):
                    st.session_state._quick_prompt = (
                        "Explain the NIS2 Article 23 incident reporting obligations in detail. "
                        "Cover: the 24-hour early warning, 72-hour notification, and 1-month final report deadlines; "
                        "what counts as a 'significant incident'; who to report to; and how ISO 27001 "
                        "incident management controls (A.5.24–A.5.28) support compliance."
                    )
                    st.session_state._show_form = None
                    st.rerun()

            # Row 2
            r2c1, r2c2, r2c3 = st.columns(3)
            with r2c1:
                if st.button("✅ Benefits of ISO 27001 for NIS2 compliance",
                             use_container_width=True, key="nis2_q4"):
                    cert = st.session_state.company_profile.get("cert_status", "not yet certified")
                    st.session_state._quick_prompt = (
                        f"We are {cert} with ISO 27001. "
                        f"Explain in detail how ISO 27001 certification helps with NIS2 compliance. "
                        f"Which NIS2 Article 21 requirements does ISO 27001 already satisfy? "
                        f"What gaps remain even with ISO 27001 certification? "
                        f"Give us a practical dual-compliance roadmap."
                    )
                    st.session_state._show_form = None
                    st.rerun()
            with r2c2:
                if st.button("❌ Most common NIS2 compliance mistakes",
                             use_container_width=True, key="nis2_q5"):
                    st.session_state._quick_prompt = (
                        "What are the most common mistakes organisations make when preparing for NIS2 compliance? "
                        "Cover: scope assessment errors, supply chain oversights, incident reporting gaps, "
                        "management accountability failures, and technical control weaknesses. "
                        "For each mistake explain how to avoid it and which controls to implement."
                    )
                    st.session_state._show_form = None
                    st.rerun()
            with r2c3:
                if st.button("💰 What are the NIS2 fines & penalties?",
                             use_container_width=True, key="nis2_q6"):
                    st.session_state._quick_prompt = (
                        "Explain the NIS2 enforcement, fines, and penalty regime. "
                        "Cover: maximum fine amounts for essential vs important entities, "
                        "management personal liability provisions, suspension of certifications, "
                        "and how enforcement differs by EU member state. "
                        "Compare to GDPR enforcement for context."
                    )
                    st.session_state._show_form = None
                    st.rerun()

            # Row 3
            r3c1, r3c2, r3c3 = st.columns(3)
            with r3c1:
                if st.button("🗺️ NIS2 vs ISO 27001 full control mapping",
                             use_container_width=True, key="nis2_q7"):
                    st.session_state._quick_prompt = (
                        "Provide a complete mapping between all NIS2 Article 21 requirements and "
                        "ISO 27001:2022 Annex A controls. Show it as a structured table with: "
                        "NIS2 requirement, description, mapped ISO 27001 controls, and any gaps "
                        "not covered by ISO 27001."
                    )
                    st.session_state._show_form = None
                    st.rerun()
            with r3c2:
                if st.button("🏗️ How to build a NIS2 compliance programme",
                             use_container_width=True, key="nis2_q8"):
                    company = st.session_state.company_name
                    timeline = st.session_state.company_profile.get("cert_timeline", "12 months")
                    st.session_state._quick_prompt = (
                        f"Create a practical step-by-step NIS2 compliance programme for {company}. "
                        f"We want to achieve compliance within {timeline}. "
                        f"Include: governance setup, risk assessment, technical controls, supplier management, "
                        f"incident response, staff training, and ongoing monitoring. "
                        f"Structure it as a phased roadmap with milestones."
                    )
                    st.session_state._show_form = None
                    st.rerun()
            with r3c3:
                if st.button("🔗 Supply chain & third-party obligations",
                             use_container_width=True, key="nis2_q9"):
                    st.session_state._quick_prompt = (
                        "Explain the NIS2 supply chain and third-party security obligations under Article 21(d). "
                        "What must organisations do to vet suppliers? What contractual requirements must be in place? "
                        "How does this relate to ISO 27001 Annex A controls A.5.19–A.5.22? "
                        "Give practical guidance on building a supplier security programme."
                    )
                    st.session_state._show_form = None
                    st.rerun()

            st.markdown("")
            if st.button("✕ Close", key="nis2_close"):
                st.session_state._show_form = None
                st.rerun()

    elif active_form == "iso":
        with st.container(border=True):
            st.markdown("#### 🏅 ISO 27001 Guide")

            st.markdown("""
            <div style="background:#f0fdf4;border-left:4px solid #16a34a;border-radius:6px;
                        padding:12px 16px;margin-bottom:14px;font-size:0.9rem;color:#14532d">
            <b>ISO 27001:2022</b> is the international standard for Information Security Management Systems (ISMS).
            Certification demonstrates to customers, regulators, and partners that your organisation 
            systematically manages information security risks. The 2022 revision introduced 
            <b>11 new controls</b> and reorganised Annex A into <b>4 themes</b> with <b>93 controls</b> total.
            </div>
            """, unsafe_allow_html=True)

            st.markdown("**Choose a topic to explore:**")

            r1c1, r1c2, r1c3 = st.columns(3)
            with r1c1:
                if st.button("🚀 How do I get certified? Step-by-step",
                             use_container_width=True, key="iso_q1"):
                    company = st.session_state.company_name
                    status = st.session_state.company_profile.get("cert_status", "not started")
                    timeline = st.session_state.company_profile.get("cert_timeline", "12 months")
                    st.session_state._quick_prompt = (
                        f"Give {company} a step-by-step ISO 27001 certification roadmap. "
                        f"Our current status is: {status}. Target timeline: {timeline}. "
                        f"Cover all phases: gap analysis, ISMS design, risk assessment, control implementation, "
                        f"internal audit, management review, Stage 1 audit, Stage 2 audit, and surveillance audits. "
                        f"Include realistic time estimates for each phase."
                    )
                    st.session_state._show_form = None
                    st.rerun()
            with r1c2:
                if st.button("📐 What is the ISMS scope and why does it matter?",
                             use_container_width=True, key="iso_q2"):
                    scope = st.session_state.company_profile.get("isms_scope", "")
                    company = st.session_state.company_name
                    st.session_state._quick_prompt = (
                        f"Explain ISO 27001 Clause 4.3 ISMS scope in depth for {company}. "
                        f"Our current scope description is: '{scope}'. "
                        f"Review this scope, identify any weaknesses or gaps, and suggest improvements. "
                        f"Explain the consequences of a scope that is too narrow or too broad for certification."
                    )
                    st.session_state._show_form = None
                    st.rerun()
            with r1c3:
                if st.button("⚖️ What are the 93 Annex A controls?",
                             use_container_width=True, key="iso_q3"):
                    st.session_state._quick_prompt = (
                        "Give me a structured overview of all 93 ISO 27001:2022 Annex A controls "
                        "organised by the 4 themes: Organisational (5.x), People (6.x), "
                        "Physical (7.x), and Technological (8.x). "
                        "For each theme summarise the key controls, highlight the 11 new controls "
                        "added in the 2022 revision, and flag the ones most commonly failed in audits."
                    )
                    st.session_state._show_form = None
                    st.rerun()

            r2c1, r2c2, r2c3 = st.columns(3)
            with r2c1:
                if st.button("📊 How does risk assessment work?",
                             use_container_width=True, key="iso_q4"):
                    maturity = st.session_state.company_profile.get("maturity_level", "")
                    assets = st.session_state.company_profile.get("asset_types", [])
                    st.session_state._quick_prompt = (
                        f"Explain the ISO 27001 risk assessment and treatment process (Clauses 6.1.2 and 6.1.3) "
                        f"in practical detail. Our maturity level is {maturity} and our key assets include: "
                        f"{', '.join(assets) if assets else 'various information assets'}. "
                        f"Walk through: defining risk criteria, asset identification, threat/vulnerability analysis, "
                        f"risk evaluation, risk treatment options, and producing the Risk Treatment Plan and SoA. "
                        f"Include a worked example relevant to our asset types."
                    )
                    st.session_state._show_form = None
                    st.rerun()
            with r2c2:
                if st.button("📝 What is the Statement of Applicability (SoA)?",
                             use_container_width=True, key="iso_q5"):
                    st.session_state._quick_prompt = (
                        "Explain the ISO 27001 Statement of Applicability (SoA) in depth. "
                        "What must it contain? How do you decide which of the 93 controls to include or exclude? "
                        "What are valid justifications for exclusion? "
                        "Show me an example SoA entry structure and explain how auditors use the SoA during certification."
                    )
                    st.session_state._show_form = None
                    st.rerun()
            with r2c3:
                if st.button("🔍 What do auditors check in Stage 1 vs Stage 2?",
                             use_container_width=True, key="iso_q6"):
                    st.session_state._quick_prompt = (
                        "Explain what ISO 27001 certification auditors look for in the Stage 1 (documentation review) "
                        "and Stage 2 (implementation audit) audits. "
                        "What documents must be ready for Stage 1? What evidence do they test in Stage 2? "
                        "What are the most common reasons organisations fail or receive major nonconformities? "
                        "How should we prepare our team for auditor interviews?"
                    )
                    st.session_state._show_form = None
                    st.rerun()

            r3c1, r3c2, r3c3 = st.columns(3)
            with r3c1:
                if st.button("🔄 ISO 27001:2022 — what changed from 2013?",
                             use_container_width=True, key="iso_q7"):
                    existing = st.session_state.company_profile.get("existing_controls", [])
                    st.session_state._quick_prompt = (
                        "What are the key differences between ISO 27001:2013 and ISO 27001:2022? "
                        "List all 11 new controls added in 2022 and explain what each one requires. "
                        "What did organisations certified under 2013 need to do to transition? "
                        "Are there any controls that were removed or significantly changed?"
                    )
                    st.session_state._show_form = None
                    st.rerun()
            with r3c2:
                if st.button("💡 What are the most common audit failures?",
                             use_container_width=True, key="iso_q8"):
                    controls = st.session_state.company_profile.get("existing_controls", [])
                    st.session_state._quick_prompt = (
                        "What are the most common reasons organisations fail ISO 27001 audits or receive "
                        "major nonconformities? "
                        f"We currently have these controls in place: {', '.join(controls) if controls else 'none yet'}. "
                        f"For each common failure area, explain what went wrong, what auditors found, "
                        f"and specifically what we should check in our own ISMS to avoid the same issue."
                    )
                    st.session_state._show_form = None
                    st.rerun()
            with r3c3:
                if st.button("💰 What does ISO 27001 certification cost?",
                             use_container_width=True, key="iso_q9"):
                    size = st.session_state.company_profile.get("company_size", "")
                    country = st.session_state.company_profile.get("country", "")
                    st.session_state._quick_prompt = (
                        f"Give a realistic cost breakdown for ISO 27001 certification for a "
                        f"{size}-employee company in {country}. "
                        f"Include: certification body (CB) fees, consultancy costs, staff time, "
                        f"tooling/software, training, and ongoing surveillance audit costs. "
                        f"Also explain how to reduce costs — e.g. internal vs external consultants, "
                        f"choosing the right CB, scope decisions."
                    )
                    st.session_state._show_form = None
                    st.rerun()

            st.markdown("")
            if st.button("✕ Close", key="iso_close"):
                st.session_state._show_form = None
                st.rerun()

    elif active_form == "quiz":
        with st.container(border=True):
            st.markdown("#### 🧠 Test Your ISO 27001 & NIS2 Knowledge")
            st.markdown("""
            <div style="background:#faf5ff;border-left:4px solid #7c3aed;border-radius:6px;
                        padding:12px 16px;margin-bottom:14px;font-size:0.9rem;color:#3b0764">
            Select a quiz format below. The AI will generate questions, wait for your answers,
            then score and explain each one. Great for preparing your team for audits.
            </div>
            """, unsafe_allow_html=True)

            st.markdown("**Difficulty:**")
            difficulty = st.select_slider(
                "difficulty",
                options=["Beginner", "Intermediate", "Advanced", "Auditor-level"],
                value="Intermediate",
                label_visibility="collapsed",
            )

            st.markdown("**Topic focus:**")
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🔀 Mixed ISO 27001 + NIS2", use_container_width=True, key="quiz_mixed"):
                    st.session_state._quick_prompt = (
                        f"You are a certified ISO 27001 lead auditor running a knowledge quiz. "
                        f"Generate a {difficulty}-level quiz of 8 questions covering both ISO 27001:2022 and NIS2. "
                        f"Mix question types: multiple choice (show options A/B/C/D), true/false, and short answer. "
                        f"Cover: Annex A controls, clauses, NIS2 Article 21 requirements, risk assessment, SoA, incident reporting. "
                        f"After presenting ALL 8 questions, wait for the user's answers before scoring. "
                        f"Number each question clearly. At the end offer to explain any wrong answers in detail."
                    )
                    st.session_state._show_form = None
                    st.rerun()
            with c2:
                if st.button("🏅 ISO 27001 only", use_container_width=True, key="quiz_iso"):
                    st.session_state._quick_prompt = (
                        f"You are a certified ISO 27001 lead auditor running a knowledge quiz. "
                        f"Generate a {difficulty}-level quiz of 8 questions focused exclusively on ISO 27001:2022. "
                        f"Mix question types: multiple choice (show options A/B/C/D), true/false, and scenario-based. "
                        f"Cover: the 10 clauses, all 4 Annex A themes, the 11 new 2022 controls, risk methodology, SoA, audit process. "
                        f"After presenting ALL 8 questions, wait for the user's answers before scoring. "
                        f"Number each question clearly."
                    )
                    st.session_state._show_form = None
                    st.rerun()
            with c3:
                if st.button("🇪🇺 NIS2 only", use_container_width=True, key="quiz_nis2"):
                    st.session_state._quick_prompt = (
                        f"You are a NIS2 compliance expert running a knowledge quiz. "
                        f"Generate a {difficulty}-level quiz of 8 questions focused exclusively on NIS2. "
                        f"Mix question types: multiple choice (show options A/B/C/D), true/false, and scenario-based. "
                        f"Cover: entity categories, Article 21 security measures, Article 23 incident reporting, "
                        f"scope/thresholds, enforcement and fines, member state obligations, supply chain requirements. "
                        f"After presenting ALL 8 questions, wait for the user's answers before scoring. "
                        f"Number each question clearly."
                    )
                    st.session_state._show_form = None
                    st.rerun()

            st.markdown("**Scenario-based:**")
            c4, c5 = st.columns(2)
            with c4:
                if st.button("🚨 Incident response scenario", use_container_width=True, key="quiz_incident"):
                    company = st.session_state.company_name
                    st.session_state._quick_prompt = (
                        f"You are running a {difficulty}-level incident response tabletop exercise for {company}. "
                        f"Present a realistic scenario: a ransomware attack encrypts the company's customer database at 2am on a Friday. "
                        f"Then ask 6 sequential questions testing knowledge of: "
                        f"ISO 27001 incident classification (A.5.24), NIS2 Article 23 reporting timelines, "
                        f"who to notify (internal + regulators), evidence preservation, business continuity activation, "
                        f"and post-incident review requirements. "
                        f"Wait for each answer before asking the next question. Score at the end."
                    )
                    st.session_state._show_form = None
                    st.rerun()
            with c5:
                if st.button("🔍 Audit preparation quiz", use_container_width=True, key="quiz_audit"):
                    cert_status = st.session_state.company_profile.get("cert_status", "preparing for audit")
                    st.session_state._quick_prompt = (
                        f"You are a {difficulty}-level ISO 27001 certification auditor. "
                        f"Simulate Stage 2 audit interview questions for a company that is {cert_status}. "
                        f"Ask 8 questions an auditor would actually ask during an on-site audit — "
                        f"covering ISMS scope, risk treatment decisions, control evidence, "
                        f"management review outcomes, internal audit findings, and continual improvement. "
                        f"After each answer, give brief auditor-style feedback (pass/observation/nonconformity) "
                        f"before moving to the next question."
                    )
                    st.session_state._show_form = None
                    st.rerun()

            st.markdown("")
            if st.button("✕ Close", key="quiz_close"):
                st.session_state._show_form = None
                st.rerun()

    # ── Render chat history ──────────────────────────────────────────────────
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            if msg.get("sources"):
                with st.expander("📎 Sources used", expanded=False):
                    for src in msg["sources"]:
                        st.markdown(
                            f'<div class="citation-block">📄 <b>{src["file"]}</b>'
                            f'{"  |  Page " + str(src["page"]) if src.get("page") else ""}'
                            f"</div>",
                            unsafe_allow_html=True,
                        )

            if msg.get("tools_used"):
                tool_html = " ".join(
                    f'<span class="tool-pill">🔧 {t}</span>'
                    for t in msg["tools_used"]
                )
                st.markdown(tool_html, unsafe_allow_html=True)

            if msg.get("usage"):
                u = msg["usage"]
                st.caption(
                    f"🤖 {st.session_state.selected_model}  |  "
                    f"🔡 {u['total_tokens']:,} tokens  |  💰 ${u['cost_usd']:.4f}"
                )

            if msg.get("is_policy"):
                import re as _re
                first_heading = _re.search(r"^# (.+)$", msg["content"], _re.MULTILINE)
                filename = (
                    first_heading.group(1).strip().replace(" ", "_").replace("/", "-") + ".docx"
                    if first_heading else "policy_document.docx"
                )
                try:
                    docx_bytes = policy_to_docx(msg["content"], st.session_state.company_name)
                    st.download_button(
                        label="📥 Download as Word Document (.docx)",
                        data=docx_bytes,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"hist_docx_{st.session_state.messages.index(msg)}",
                    )
                except Exception:
                    pass

    # ── Chat input ───────────────────────────────────────────────────────────
    initial_value = ""
    if hasattr(st.session_state, "_quick_prompt"):
        initial_value = st.session_state._quick_prompt
        del st.session_state._quick_prompt

    user_input = st.chat_input(
        "Ask about ISO 27001, NIS2, risk assessment, policy templates…",
    )

    if not user_input and initial_value:
        user_input = initial_value

    # ── Process message ──────────────────────────────────────────────────────
    if user_input:
        if not st.session_state.api_key:
            st.error("⚠️ Please enter your OpenAI API key in the sidebar.")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                agent = _get_agent()
                lc_history = messages_to_langchain(st.session_state.messages[:-1])

                try:
                    response, usage = agent.run(
                        user_input=user_input,
                        chat_history=lc_history,
                        company_name=st.session_state.company_name,
                        company_industry=st.session_state.company_industry + "\n\n" + _profile_context,
                    )
                except Exception as exc:
                    response = (
                        f"❌ An error occurred: {exc}\n\n"
                        "Please check your API key and try again."
                    )
                    usage = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0}

            st.markdown(response)

            sources: List[Dict] = []
            if "[Source" in response:
                import re
                for match in re.finditer(
                    r"\[Source \d+: ([^\|]+)\s*\|?\s*Page ([^\]]*)\]", response
                ):
                    file_name = match.group(1).strip()
                    page = match.group(2).strip() if match.group(2).strip() else None
                    if file_name and not any(s["file"] == file_name for s in sources):
                        sources.append({"file": file_name, "page": page})

            if sources:
                with st.expander("📎 Sources used", expanded=False):
                    for src in sources:
                        st.markdown(
                            f'<div class="citation-block">📄 <b>{src["file"]}</b>'
                            f'{"  |  Page " + str(src["page"]) if src.get("page") else ""}'
                            f"</div>",
                            unsafe_allow_html=True,
                        )

            tools_used: List[str] = []
            tool_keywords = {
                "Risk Score": "calculate_risk_score",
                "Gap Analysis": "analyze_compliance_gaps",
                "Policy": "generate_policy_template",
                "NIS2 →": "map_iso_nis2_controls",
                "ISO 27001 Control": "map_iso_nis2_controls",
                "Source 1:": "search_documents",
                "No relevant documents": "search_documents",
            }
            for keyword, tool_name in tool_keywords.items():
                if keyword in response and tool_name not in tools_used:
                    tools_used.append(tool_name)

            if tools_used:
                tool_html = " ".join(
                    f'<span class="tool-pill">🔧 {t}</span>' for t in tools_used
                )
                st.markdown(tool_html, unsafe_allow_html=True)

            is_policy = st.session_state.pop("_policy_requested", False)
            if is_policy:
                try:
                    docx_bytes = policy_to_docx(response, st.session_state.company_name)
                    import re as _re
                    first_heading = _re.search(r"^# (.+)$", response, _re.MULTILINE)
                    filename = (
                        first_heading.group(1).strip().replace(" ", "_").replace("/", "-") + ".docx"
                        if first_heading else "policy_document.docx"
                    )
                    st.download_button(
                        label="📥 Download as Word Document (.docx)",
                        data=docx_bytes,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"docx_{len(st.session_state.messages)}",
                    )
                except Exception as e:
                    st.caption(f"⚠️ Could not generate .docx: {e}")

            st.caption(
                f"🤖 {st.session_state.selected_model}  |  "
                f"🔡 {usage['total_tokens']:,} tokens  |  💰 ${usage['cost_usd']:.4f}"
            )

        st.session_state.total_tokens += usage["total_tokens"]
        st.session_state.prompt_tokens += usage["prompt_tokens"]
        st.session_state.completion_tokens += usage["completion_tokens"]
        st.session_state.total_cost += usage["cost_usd"]

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response,
                "sources": sources,
                "tools_used": tools_used,
                "usage": usage,
                "is_policy": is_policy,
            }
        )

    # ── Welcome message when chat is empty ───────────────────────────────────
    if not st.session_state.messages:
        st.markdown(
            """
            <div style="text-align:center; padding: 40px 20px; color: #6b7280;">
            <h3>👋 Welcome!</h3>
            <p>I'm your ISO 27001 & NIS2 compliance expert.<br>
            Here's how to get started:</p>
            <ol style="text-align:left; display:inline-block;">
            <li>Enter your <b>OpenAI API key</b> in the sidebar</li>
            <li><b>Upload</b> ISO 27001 PDFs, NIS2 docs, or company policies</li>
            <li>Click <b>Index Docs</b> to build your knowledge base</li>
            <li>Ask any compliance question or use the <b>Quick Actions</b> above</li>
            </ol>
            <br>
            <p><i>💡 You can also use me without uploading documents —
            I have built-in knowledge of ISO 27001:2022 and NIS2.</i></p>
            </div>
            """,
            unsafe_allow_html=True,
        )