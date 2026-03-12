"""
Compliance Tools
================
Four LangChain tools the agent can invoke:

  1. search_documents       — RAG search over uploaded documents
  2. calculate_risk_score   — ISO 27001 risk matrix calculator
  3. analyze_compliance_gaps — Gap analysis against all 93 Annex A controls
  4. generate_policy_template — Structured policy template generator
  5. map_iso_to_nis2        — ISO 27001 control ↔ NIS2 Article mapper
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from langchain_core.tools import tool
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# ISO 27001:2022 Annex A — all 93 controls
# ---------------------------------------------------------------------------

ISO_CONTROLS: list[dict] = [
    # ── Theme 5: Organizational ──────────────────────────────────────────────
    {"id": "5.1",  "theme": "Organizational", "name": "Policies for information security", "priority": "Critical"},
    {"id": "5.2",  "theme": "Organizational", "name": "Information security roles and responsibilities", "priority": "Critical"},
    {"id": "5.3",  "theme": "Organizational", "name": "Segregation of duties", "priority": "High"},
    {"id": "5.4",  "theme": "Organizational", "name": "Management responsibilities", "priority": "Critical"},
    {"id": "5.5",  "theme": "Organizational", "name": "Contact with authorities", "priority": "Medium"},
    {"id": "5.6",  "theme": "Organizational", "name": "Contact with special interest groups", "priority": "Low"},
    {"id": "5.7",  "theme": "Organizational", "name": "Threat intelligence", "priority": "High"},
    {"id": "5.8",  "theme": "Organizational", "name": "Information security in project management", "priority": "Medium"},
    {"id": "5.9",  "theme": "Organizational", "name": "Inventory of information and other associated assets", "priority": "Critical"},
    {"id": "5.10", "theme": "Organizational", "name": "Acceptable use of information and other associated assets", "priority": "High"},
    {"id": "5.11", "theme": "Organizational", "name": "Return of assets", "priority": "Medium"},
    {"id": "5.12", "theme": "Organizational", "name": "Classification of information", "priority": "Critical"},
    {"id": "5.13", "theme": "Organizational", "name": "Labelling of information", "priority": "High"},
    {"id": "5.14", "theme": "Organizational", "name": "Information transfer", "priority": "High"},
    {"id": "5.15", "theme": "Organizational", "name": "Access control", "priority": "Critical"},
    {"id": "5.16", "theme": "Organizational", "name": "Identity management", "priority": "Critical"},
    {"id": "5.17", "theme": "Organizational", "name": "Authentication information", "priority": "Critical"},
    {"id": "5.18", "theme": "Organizational", "name": "Access rights", "priority": "Critical"},
    {"id": "5.19", "theme": "Organizational", "name": "Information security in supplier relationships", "priority": "High"},
    {"id": "5.20", "theme": "Organizational", "name": "Addressing information security within supplier agreements", "priority": "High"},
    {"id": "5.21", "theme": "Organizational", "name": "Managing information security in the ICT supply chain", "priority": "High"},
    {"id": "5.22", "theme": "Organizational", "name": "Monitoring, review and change management of supplier services", "priority": "Medium"},
    {"id": "5.23", "theme": "Organizational", "name": "Information security for use of cloud services", "priority": "High"},
    {"id": "5.24", "theme": "Organizational", "name": "Information security incident management planning and preparation", "priority": "Critical"},
    {"id": "5.25", "theme": "Organizational", "name": "Assessment and decision on information security events", "priority": "High"},
    {"id": "5.26", "theme": "Organizational", "name": "Response to information security incidents", "priority": "Critical"},
    {"id": "5.27", "theme": "Organizational", "name": "Learning from information security incidents", "priority": "Medium"},
    {"id": "5.28", "theme": "Organizational", "name": "Collection of evidence", "priority": "Medium"},
    {"id": "5.29", "theme": "Organizational", "name": "Information security during disruption", "priority": "High"},
    {"id": "5.30", "theme": "Organizational", "name": "ICT readiness for business continuity", "priority": "High"},
    {"id": "5.31", "theme": "Organizational", "name": "Legal, statutory, regulatory and contractual requirements", "priority": "Critical"},
    {"id": "5.32", "theme": "Organizational", "name": "Intellectual property rights", "priority": "Medium"},
    {"id": "5.33", "theme": "Organizational", "name": "Protection of records", "priority": "High"},
    {"id": "5.34", "theme": "Organizational", "name": "Privacy and protection of personally identifiable information", "priority": "Critical"},
    {"id": "5.35", "theme": "Organizational", "name": "Independent review of information security", "priority": "High"},
    {"id": "5.36", "theme": "Organizational", "name": "Compliance with policies, rules and standards for information security", "priority": "High"},
    {"id": "5.37", "theme": "Organizational", "name": "Documented operating procedures", "priority": "Medium"},
    # ── Theme 6: People ──────────────────────────────────────────────────────
    {"id": "6.1",  "theme": "People", "name": "Screening", "priority": "High"},
    {"id": "6.2",  "theme": "People", "name": "Terms and conditions of employment", "priority": "High"},
    {"id": "6.3",  "theme": "People", "name": "Information security awareness, education and training", "priority": "Critical"},
    {"id": "6.4",  "theme": "People", "name": "Disciplinary process", "priority": "Medium"},
    {"id": "6.5",  "theme": "People", "name": "Responsibilities after termination or change of employment", "priority": "High"},
    {"id": "6.6",  "theme": "People", "name": "Confidentiality or non-disclosure agreements", "priority": "High"},
    {"id": "6.7",  "theme": "People", "name": "Remote working", "priority": "High"},
    {"id": "6.8",  "theme": "People", "name": "Information security event reporting", "priority": "High"},
    # ── Theme 7: Physical ────────────────────────────────────────────────────
    {"id": "7.1",  "theme": "Physical", "name": "Physical security perimeters", "priority": "Critical"},
    {"id": "7.2",  "theme": "Physical", "name": "Physical entry", "priority": "Critical"},
    {"id": "7.3",  "theme": "Physical", "name": "Securing offices, rooms and facilities", "priority": "High"},
    {"id": "7.4",  "theme": "Physical", "name": "Physical security monitoring", "priority": "High"},
    {"id": "7.5",  "theme": "Physical", "name": "Protecting against physical and environmental threats", "priority": "High"},
    {"id": "7.6",  "theme": "Physical", "name": "Working in secure areas", "priority": "Medium"},
    {"id": "7.7",  "theme": "Physical", "name": "Clear desk and clear screen", "priority": "Medium"},
    {"id": "7.8",  "theme": "Physical", "name": "Equipment siting and protection", "priority": "High"},
    {"id": "7.9",  "theme": "Physical", "name": "Security of assets off-premises", "priority": "High"},
    {"id": "7.10", "theme": "Physical", "name": "Storage media", "priority": "High"},
    {"id": "7.11", "theme": "Physical", "name": "Supporting utilities", "priority": "Critical"},
    {"id": "7.12", "theme": "Physical", "name": "Cabling security", "priority": "Medium"},
    {"id": "7.13", "theme": "Physical", "name": "Equipment maintenance", "priority": "Medium"},
    {"id": "7.14", "theme": "Physical", "name": "Secure disposal or re-use of equipment", "priority": "High"},
    # ── Theme 8: Technological ───────────────────────────────────────────────
    {"id": "8.1",  "theme": "Technological", "name": "User endpoint devices", "priority": "High"},
    {"id": "8.2",  "theme": "Technological", "name": "Privileged access rights", "priority": "Critical"},
    {"id": "8.3",  "theme": "Technological", "name": "Information access restriction", "priority": "Critical"},
    {"id": "8.4",  "theme": "Technological", "name": "Access to source code", "priority": "High"},
    {"id": "8.5",  "theme": "Technological", "name": "Secure authentication", "priority": "Critical"},
    {"id": "8.6",  "theme": "Technological", "name": "Capacity management", "priority": "Medium"},
    {"id": "8.7",  "theme": "Technological", "name": "Protection against malware", "priority": "Critical"},
    {"id": "8.8",  "theme": "Technological", "name": "Management of technical vulnerabilities", "priority": "Critical"},
    {"id": "8.9",  "theme": "Technological", "name": "Configuration management", "priority": "High"},
    {"id": "8.10", "theme": "Technological", "name": "Information deletion", "priority": "High"},
    {"id": "8.11", "theme": "Technological", "name": "Data masking", "priority": "High"},
    {"id": "8.12", "theme": "Technological", "name": "Data leakage prevention", "priority": "High"},
    {"id": "8.13", "theme": "Technological", "name": "Information backup", "priority": "Critical"},
    {"id": "8.14", "theme": "Technological", "name": "Redundancy of information processing facilities", "priority": "High"},
    {"id": "8.15", "theme": "Technological", "name": "Logging", "priority": "Critical"},
    {"id": "8.16", "theme": "Technological", "name": "Monitoring activities", "priority": "High"},
    {"id": "8.17", "theme": "Technological", "name": "Clock synchronisation", "priority": "Medium"},
    {"id": "8.18", "theme": "Technological", "name": "Use of privileged utility programs", "priority": "High"},
    {"id": "8.19", "theme": "Technological", "name": "Installation of software on operational systems", "priority": "High"},
    {"id": "8.20", "theme": "Technological", "name": "Networks security", "priority": "Critical"},
    {"id": "8.21", "theme": "Technological", "name": "Security of network services", "priority": "High"},
    {"id": "8.22", "theme": "Technological", "name": "Segregation of networks", "priority": "High"},
    {"id": "8.23", "theme": "Technological", "name": "Web filtering", "priority": "Medium"},
    {"id": "8.24", "theme": "Technological", "name": "Use of cryptography", "priority": "Critical"},
    {"id": "8.25", "theme": "Technological", "name": "Secure development life cycle", "priority": "High"},
    {"id": "8.26", "theme": "Technological", "name": "Application security requirements", "priority": "High"},
    {"id": "8.27", "theme": "Technological", "name": "Secure system architecture and engineering principles", "priority": "High"},
    {"id": "8.28", "theme": "Technological", "name": "Secure coding", "priority": "High"},
    {"id": "8.29", "theme": "Technological", "name": "Security testing in development and acceptance", "priority": "High"},
    {"id": "8.30", "theme": "Technological", "name": "Outsourced development", "priority": "Medium"},
    {"id": "8.31", "theme": "Technological", "name": "Separation of development, test and production environments", "priority": "High"},
    {"id": "8.32", "theme": "Technological", "name": "Change management", "priority": "High"},
    {"id": "8.33", "theme": "Technological", "name": "Test information", "priority": "Medium"},
    {"id": "8.34", "theme": "Technological", "name": "Protection of information systems during audit testing", "priority": "Medium"},
]

# ---------------------------------------------------------------------------
# NIS2 ↔ ISO 27001 mapping
# Each NIS2 measure maps to a list of ISO control IDs most closely related
# ---------------------------------------------------------------------------

NIS2_TO_ISO: dict[str, dict] = {
    "Art.21(a)": {
        "title": "Risk analysis and information system security policies",
        "iso_controls": ["5.1", "5.2", "5.4", "5.9", "5.31"],
    },
    "Art.21(b)": {
        "title": "Incident handling",
        "iso_controls": ["5.24", "5.25", "5.26", "5.27", "5.28", "6.8"],
    },
    "Art.21(c)": {
        "title": "Business continuity and disaster recovery",
        "iso_controls": ["5.29", "5.30", "8.13", "8.14"],
    },
    "Art.21(d)": {
        "title": "Supply chain security",
        "iso_controls": ["5.19", "5.20", "5.21", "5.22"],
    },
    "Art.21(e)": {
        "title": "Security in network and information system acquisition, development and maintenance",
        "iso_controls": ["8.25", "8.26", "8.27", "8.28", "8.29", "8.30", "8.31", "8.32"],
    },
    "Art.21(f)": {
        "title": "Policies and procedures to assess effectiveness of cybersecurity measures",
        "iso_controls": ["5.35", "5.36", "5.7"],
    },
    "Art.21(g)": {
        "title": "Basic cyber hygiene practices and cybersecurity training",
        "iso_controls": ["6.3", "8.7", "8.8", "8.9"],
    },
    "Art.21(h)": {
        "title": "Policies and procedures regarding use of cryptography",
        "iso_controls": ["8.24"],
    },
    "Art.21(i)": {
        "title": "Human resources security, access control policies and asset management",
        "iso_controls": ["5.15", "5.16", "5.17", "5.18", "6.1", "6.2", "6.5", "8.2", "8.3", "8.5"],
    },
    "Art.21(j)": {
        "title": "Multi-factor authentication or continuous authentication solutions",
        "iso_controls": ["5.17", "8.5"],
    },
    "Art.23": {
        "title": "Reporting obligations for significant incidents",
        "iso_controls": ["5.24", "5.25", "5.26", "6.8"],
    },
}

# Reverse index: ISO control → list of NIS2 articles
ISO_TO_NIS2: dict[str, list[str]] = {}
for article, data in NIS2_TO_ISO.items():
    for ctrl_id in data["iso_controls"]:
        ISO_TO_NIS2.setdefault(ctrl_id, []).append(article)


# ---------------------------------------------------------------------------
# Policy templates
# ---------------------------------------------------------------------------

POLICY_TEMPLATES: dict[str, str] = {
    "access_control": """# Access Control Policy
**Version:** 1.0  |  **Date:** {date}  |  **Owner:** CISO / IT Security

## 1. Purpose
This policy establishes rules governing access to information assets at {company_name} to protect confidentiality, integrity, and availability (ISO 27001 Control 5.15).

## 2. Scope
Applies to all employees, contractors, and third parties accessing {company_name} systems and data.

## 3. Access Control Principles
- **Least privilege:** Users receive only the access required for their role.
- **Need-to-know:** Access to sensitive data is granted only when justified.
- **Segregation of duties:** Critical functions require more than one person.

## 4. User Access Management (ISO 5.16, 5.18)
- [ ] Formal user registration and de-registration process
- [ ] Access provisioning approval workflow
- [ ] Quarterly access rights review
- [ ] Immediate revocation upon termination (same-day)

## 5. Authentication (ISO 5.17, 8.5)
- Passwords: minimum 12 characters, complexity requirements
- Multi-factor authentication (MFA) required for: VPN, admin accounts, cloud services
- Password manager usage encouraged

## 6. Privileged Access (ISO 8.2)
- Separate privileged accounts for administrative tasks
- Privileged sessions logged and reviewed
- Just-in-time (JIT) access for production environments

## 7. Review and Compliance
Policy reviewed annually. Violations may result in disciplinary action.

**Approved by:** ________________  **Date:** ________________
""",

    "incident_response": """# Information Security Incident Response Policy
**Version:** 1.0  |  **Date:** {date}  |  **Owner:** CISO

## 1. Purpose
Define the process for detecting, reporting, and responding to information security incidents (ISO 27001 Controls 5.24–5.28, NIS2 Art.21(b), Art.23).

## 2. Incident Classification
| Severity | Definition | Response Time |
|----------|-----------|---------------|
| P1 – Critical | Data breach, ransomware, service outage | 1 hour |
| P2 – High | Suspected breach, malware detected | 4 hours |
| P3 – Medium | Policy violation, phishing attempt | 24 hours |
| P4 – Low | Minor anomaly, failed login attempts | 72 hours |

## 3. Incident Response Phases
### 3.1 Detection & Reporting
- All staff report suspected incidents to: security@{company_domain}
- SIEM/monitoring alerts routed to on-call security team
- NIS2: Significant incidents reported to national authority within **24 hours** (early warning), full report within **72 hours**

### 3.2 Containment
- Isolate affected systems
- Preserve evidence (logs, memory dumps)
- Activate business continuity plan if required

### 3.3 Eradication & Recovery
- Remove threat, patch vulnerabilities
- Restore from clean backups
- Verify system integrity before return to production

### 3.4 Post-Incident Review
- Root cause analysis within 5 business days
- Lessons learned documented and shared
- Policy/control updates actioned

## 4. Roles & Responsibilities
- **Incident Commander:** CISO or delegate
- **Technical Lead:** IT Security team
- **Communications Lead:** PR / Legal

**Approved by:** ________________  **Date:** ________________
""",

    "risk_management": """# Information Security Risk Management Policy
**Version:** 1.0  |  **Date:** {date}  |  **Owner:** CISO / Risk Manager

## 1. Purpose
Establish a consistent approach to identifying, assessing, and treating information security risks (ISO 27001 Clause 6.1, NIS2 Art.21(a)).

## 2. Risk Assessment Methodology
**Risk Score = Likelihood × Impact**

| Score | Likelihood | Impact |
|-------|-----------|--------|
| 1 | Rare (<1/year) | Negligible |
| 2 | Unlikely (1–3/year) | Minor |
| 3 | Possible (quarterly) | Moderate |
| 4 | Likely (monthly) | Major |
| 5 | Almost certain (weekly) | Catastrophic |

**Risk levels:** Low (1–4) | Medium (5–9) | High (10–19) | Critical (20–25)

## 3. Risk Treatment Options
- **Mitigate:** Implement controls to reduce likelihood/impact
- **Transfer:** Insurance, contractual liability
- **Accept:** Document and monitor residual risk
- **Avoid:** Discontinue the risky activity

## 4. Risk Register
All risks rated Medium or above are recorded in the Risk Register with:
- Risk owner, risk description, current controls, residual risk score
- Treatment plan with due date and responsible party

## 5. Review Cadence
- Risk register reviewed **quarterly**
- Full risk assessment **annually** or after significant change
- Risk appetite approved by Board **annually**

**Approved by:** ________________  **Date:** ________________
""",

    "data_classification": """# Data Classification Policy
**Version:** 1.0  |  **Date:** {date}  |  **Owner:** Data Protection Officer

## 1. Classification Levels (ISO 5.12, 5.13)
| Level | Label | Examples | Handling |
|-------|-------|---------|---------|
| 4 – Restricted | 🔴 RESTRICTED | Trade secrets, source code, personal health data | Encrypted at rest & transit; access log required |
| 3 – Confidential | 🟠 CONFIDENTIAL | Financial data, contracts, employee records | Encrypted; need-to-know; NDA required |
| 2 – Internal | 🟡 INTERNAL | Policies, internal reports, org charts | Internal use only; not for external sharing |
| 1 – Public | 🟢 PUBLIC | Marketing materials, published documents | No restrictions |

## 2. Labelling Requirements
- All documents must include classification label in header/footer
- Emails: include classification in subject line for Confidential/Restricted
- Files: classification in filename or metadata

## 3. GDPR / Personal Data
Personal data is classified at minimum **Confidential** and subject to GDPR/NIS2 Art.21(i).
Special category data (health, biometric) is classified **Restricted**.

## 4. Data Retention
| Classification | Retention Period | Disposal Method |
|---------------|-----------------|----------------|
| Restricted | Per legal requirement | Certified destruction |
| Confidential | 7 years | Secure shredding / crypto-erase |
| Internal | 3 years | Standard deletion |
| Public | As needed | Standard deletion |

**Approved by:** ________________  **Date:** ________________
""",

    "supplier_security": """# Supplier & Third-Party Security Policy
**Version:** 1.0  |  **Date:** {date}  |  **Owner:** Procurement / CISO

## 1. Purpose
Manage information security risks in the supply chain (ISO 5.19–5.22, NIS2 Art.21(d)).

## 2. Supplier Classification
| Tier | Criteria | Due Diligence |
|------|---------|--------------|
| Critical | Access to Restricted data or core systems | ISO 27001 cert or full audit |
| High | Access to Confidential data | Security questionnaire + contract clauses |
| Standard | No access to sensitive data | Standard contract terms |

## 3. Pre-Engagement Requirements
- [ ] Security questionnaire completed
- [ ] Data Processing Agreement (DPA) signed if personal data involved
- [ ] NDA signed for all Confidential/Restricted access
- [ ] ISO 27001 certificate or equivalent evidence provided (Tier Critical)

## 4. Contractual Requirements (ISO 5.20)
All supplier contracts must include:
- Right to audit clause
- Data breach notification obligation (within 24 hours per NIS2)
- Data return/destruction on contract termination
- Sub-processor notification and approval requirements

## 5. Ongoing Monitoring (ISO 5.22)
- Annual security review for Critical/High tier suppliers
- Review after any supplier security incident
- Monitor supplier's public security advisories

**Approved by:** ________________  **Date:** ________________
""",
}


# ===========================================================================
# Tool 1 — Document Search (created dynamically, see agent.py)
# ===========================================================================

def create_search_tool(rag_engine):
    """
    Factory that returns a LangChain tool bound to a specific RAGEngine instance.
    Kept separate because tools cannot easily reference mutable external state
    via the @tool decorator alone.
    """
    from langchain_core.tools import tool as lc_tool

    @lc_tool
    def search_documents(query: str) -> str:
        """
        Search the compliance knowledge base for information about
        ISO 27001, NIS2, company policies, procedures, and uploaded documents.
        Use this tool whenever the user asks about specific clauses, controls,
        requirements, or content from their uploaded documents.
        """
        docs = rag_engine.retrieve(query)
        if not docs:
            return (
                "No relevant documents found in the knowledge base. "
                "Please upload ISO 27001 PDFs, NIS2 documentation, or company "
                "policy files using the sidebar, then click 'Index Documents'."
            )

        results = []
        seen_content: set[str] = set()
        for i, doc in enumerate(docs[:5], 1):
            # Deduplicate by content prefix
            prefix = doc.page_content[:80]
            if prefix in seen_content:
                continue
            seen_content.add(prefix)

            source = Path(doc.metadata.get("source", "Unknown")).name
            page = doc.metadata.get("page", "N/A")
            results.append(
                f"[Source {i}: {source} | Page {page}]\n{doc.page_content.strip()}"
            )

        return "\n\n---\n\n".join(results)

    return search_documents


# ===========================================================================
# Tool 2 — Risk Calculator
# ===========================================================================

class RiskInput(BaseModel):
    asset_name: str = Field(description="Name of the information asset being assessed")
    asset_value: int = Field(ge=1, le=5, description="Business value/importance of the asset (1=low, 5=critical)")
    threat_likelihood: int = Field(ge=1, le=5, description="Likelihood that a threat will exploit a vulnerability (1=rare, 5=almost certain)")
    vulnerability_level: int = Field(ge=1, le=5, description="Level of existing vulnerability or weakness (1=minimal, 5=severe)")
    existing_controls: str = Field(
        default="None documented",
        description="Brief description of currently implemented security controls for this asset",
    )


@tool("calculate_risk_score", args_schema=RiskInput)
def calculate_risk_score(
    asset_name: str,
    asset_value: int,
    threat_likelihood: int,
    vulnerability_level: int,
    existing_controls: str = "None documented",
) -> str:
    """
    Calculate an ISO 27001-style information security risk score using a
    likelihood × impact matrix. Returns the numeric score, risk level,
    risk treatment recommendation, and applicable ISO 27001 controls.
    """
    # ISO 27001 standard risk formula:
    #   Risk = Likelihood × Impact
    #   Impact = Asset Value (how damaging a breach would be)
    #   Vulnerability raises the effective likelihood
    #
    # Adjusted likelihood = base likelihood boosted by vulnerability
    #   - vulnerability 1-2: no boost
    #   - vulnerability 3:   +0 (neutral)
    #   - vulnerability 4:   +1
    #   - vulnerability 5:   +2
    # Capped at 5.
    vulnerability_boost = max(0, vulnerability_level - 3)
    adjusted_likelihood = min(5, threat_likelihood + vulnerability_boost)

    impact = asset_value                          # Impact IS the asset value
    raw_score = adjusted_likelihood * impact      # 1–25 scale

    if raw_score <= 4:
        level = "🟢 Low"
        treatment = "Accept – monitor and review annually."
        urgent = False
    elif raw_score <= 9:
        level = "🟡 Medium"
        treatment = "Mitigate – implement additional controls within 90 days."
        urgent = False
    elif raw_score <= 15:
        level = "🟠 High"
        treatment = "Mitigate urgently – implement controls within 30 days; escalate to management."
        urgent = True
    else:
        level = "🔴 Critical"
        treatment = "Immediate action required – escalate to CISO; implement emergency controls."
        urgent = True

    # Suggest top controls based on asset type keywords
    suggested: List[str] = []
    name_lower = asset_name.lower()
    if any(k in name_lower for k in ["server", "system", "database", "db"]):
        suggested = ["8.5 Secure authentication", "8.2 Privileged access rights", "8.15 Logging", "8.8 Vulnerability management"]
    elif any(k in name_lower for k in ["data", "record", "file", "document"]):
        suggested = ["5.12 Classification", "8.3 Access restriction", "8.24 Cryptography", "8.13 Backup"]
    elif any(k in name_lower for k in ["network", "infra", "firewall", "router"]):
        suggested = ["8.20 Network security", "8.22 Network segregation", "8.5 Secure authentication", "8.16 Monitoring"]
    elif any(k in name_lower for k in ["employee", "staff", "user", "people"]):
        suggested = ["6.3 Security training", "5.15 Access control", "6.6 NDA", "6.8 Incident reporting"]
    else:
        suggested = ["5.9 Asset inventory", "5.15 Access control", "8.7 Malware protection", "6.3 Security training"]

    lines = [
        f"## Risk Assessment: {asset_name}",
        "",
        f"| Parameter                  | Value |",
        f"|----------------------------|-------|",
        f"| Asset Value (Impact)        | {asset_value}/5 |",
        f"| Threat Likelihood (base)    | {threat_likelihood}/5 |",
        f"| Vulnerability Level         | {vulnerability_level}/5 |",
        f"| Adjusted Likelihood         | {adjusted_likelihood}/5 *(+{vulnerability_boost} from vulnerability)* |",
        f"| **Risk Score**              | **{raw_score}/25** *(Adjusted Likelihood × Asset Value)* |",
        f"| **Risk Level**              | **{level}** |",
        "",
        f"**Existing Controls:** {existing_controls}",
        "",
        f"**Recommended Treatment:** {treatment}",
        "",
        "**Suggested ISO 27001 Controls to Implement:**",
    ]
    for ctrl in suggested:
        lines.append(f"  - {ctrl}")

    if urgent:
        lines += [
            "",
            "⚠️ **Action Required:** Add this risk to your Risk Register and assign a risk owner immediately.",
        ]

    return "\n".join(lines)


# ===========================================================================
# Tool 3 — Compliance Gap Analyser
# ===========================================================================

class GapInput(BaseModel):
    implemented_controls: str = Field(
        description=(
            "Comma-separated list of ISO 27001:2022 Annex A control IDs that are "
            "currently implemented, e.g. '5.1, 5.2, 6.3, 8.5, 8.7'. "
            "Use IDs from 5.1–5.37, 6.1–6.8, 7.1–7.14, 8.1–8.34."
        )
    )


@tool("analyze_compliance_gaps", args_schema=GapInput)
def analyze_compliance_gaps(implemented_controls: str) -> str:
    """
    Analyse which ISO 27001:2022 Annex A controls are missing compared to the
    full set of 93 controls. Returns coverage percentage, prioritised gap list,
    and theme-level breakdown. Also shows which NIS2 articles may be impacted
    by missing controls.
    """
    # Parse input
    implemented = {
        c.strip()
        for c in implemented_controls.replace(";", ",").split(",")
        if c.strip()
    }

    all_ids = {ctrl["id"] for ctrl in ISO_CONTROLS}
    valid_implemented = implemented & all_ids
    invalid = implemented - all_ids

    missing = [c for c in ISO_CONTROLS if c["id"] not in valid_implemented]
    critical_missing = [c for c in missing if c["priority"] == "Critical"]
    high_missing = [c for c in missing if c["priority"] == "High"]

    coverage = round(len(valid_implemented) / len(all_ids) * 100, 1)

    # Theme breakdown
    themes: dict[str, dict] = {}
    for ctrl in ISO_CONTROLS:
        t = ctrl["theme"]
        themes.setdefault(t, {"total": 0, "implemented": 0})
        themes[t]["total"] += 1
        if ctrl["id"] in valid_implemented:
            themes[t]["implemented"] += 1

    # NIS2 impact: which articles have missing controls?
    nis2_impact: dict[str, list[str]] = {}
    for ctrl in missing:
        for article in ISO_TO_NIS2.get(ctrl["id"], []):
            nis2_impact.setdefault(article, []).append(ctrl["id"])

    lines = [
        "## ISO 27001:2022 Compliance Gap Analysis",
        "",
        f"**Controls implemented:** {len(valid_implemented)} / {len(all_ids)} ({coverage}%)",
        f"**Gaps identified:** {len(missing)} controls missing",
        "",
        "### Theme Breakdown",
        "| Theme | Implemented | Total | Coverage |",
        "|-------|------------|-------|---------|",
    ]
    for theme, data in themes.items():
        pct = round(data["implemented"] / data["total"] * 100)
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        lines.append(f"| {theme} | {data['implemented']} | {data['total']} | {bar} {pct}% |")

    if critical_missing:
        lines += ["", "### 🔴 Critical Gaps (Address Immediately)"]
        for ctrl in critical_missing[:10]:
            nis2_ref = ", ".join(ISO_TO_NIS2.get(ctrl["id"], []))
            nis2_str = f" ← NIS2: {nis2_ref}" if nis2_ref else ""
            lines.append(f"  - **{ctrl['id']}** {ctrl['name']}{nis2_str}")

    if high_missing:
        lines += ["", "### 🟠 High Priority Gaps (Address within 30–90 days)"]
        for ctrl in high_missing[:10]:
            lines.append(f"  - **{ctrl['id']}** {ctrl['name']}")

    if nis2_impact:
        lines += ["", "### NIS2 Directive Impact"]
        for article, ctrls in sorted(nis2_impact.items()):
            article_data = NIS2_TO_ISO.get(article, {})
            title = article_data.get("title", "")
            lines.append(f"  - **{article}** ({title}): missing controls {', '.join(ctrls)}")

    if invalid:
        lines += [
            "",
            f"⚠️ Note: The following IDs were not recognised and were ignored: {', '.join(sorted(invalid))}",
        ]

    lines += [
        "",
        "---",
        f"💡 **Next step:** Focus on the {len(critical_missing)} critical gaps first. "
        "Ask me to generate a policy template for any specific control area.",
    ]

    return "\n".join(lines)


# ===========================================================================
# Tool 4 — Policy Template Generator
# ===========================================================================

class PolicyInput(BaseModel):
    policy_type: str = Field(
        description=(
            "Type of policy to generate. Choose from: "
            "'access_control', 'incident_response', 'risk_management', "
            "'data_classification', 'supplier_security'"
        )
    )
    company_name: str = Field(default="Your Company", description="Name of the company")
    company_domain: str = Field(default="company.com", description="Company email domain")


@tool("generate_policy_template", args_schema=PolicyInput)
def generate_policy_template(
    policy_type: str,
    company_name: str = "Your Company",
    company_domain: str = "company.com",
) -> str:
    """
    Generate a structured, ISO 27001-compliant policy template using Claude
    for the highest quality document output. Falls back to a built-in template
    if no Anthropic API key is configured.
    Available templates: access_control, incident_response, risk_management,
    data_classification, supplier_security.
    Returns a ready-to-customise Markdown document.
    """
    import os
    from datetime import date

    key = policy_type.lower().replace(" ", "_").replace("-", "_")
    base_template = POLICY_TEMPLATES.get(key)

    if base_template is None:
        available = ", ".join(POLICY_TEMPLATES.keys())
        return (
            f"Template '{policy_type}' not found. "
            f"Available templates: {available}. "
            "Ask me to generate one of those, or I can help you draft a custom policy."
        )

    today = date.today().strftime("%d %B %Y")
    filled = base_template.format(
        date=today,
        company_name=company_name,
        company_domain=company_domain,
    )

    # ── Enhance with Claude (auto-selected for best document quality) ─────────
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": (
                        f"You are an ISO 27001:2022 compliance expert. "
                        f"Enhance and complete the following policy template for {company_name} "
                        f"({company_domain}). Keep all section headings, improve the wording to be "
                        f"more professional and specific, add any missing implementation details, "
                        f"and ensure it references the correct ISO 27001:2022 and NIS2 controls. "
                        f"Return ONLY the completed policy document in Markdown format, "
                        f"no preamble or explanation.\n\n{filled}"
                    )
                }]
            )
            enhanced = message.content[0].text
            return f"*[Generated by Claude Sonnet — enhanced document quality]*\n\n{enhanced}"
        except Exception:
            pass  # Silently fall back to base template

    return filled


# ===========================================================================
# Tool 5 — ISO 27001 ↔ NIS2 Control Mapper
# ===========================================================================

class MapInput(BaseModel):
    control_reference: str = Field(
        description=(
            "ISO 27001 control ID (e.g. '8.5', '5.24') OR "
            "NIS2 article reference (e.g. 'Art.21(b)', 'Art.23')"
        )
    )


@tool("map_iso_nis2_controls", args_schema=MapInput)
def map_iso_nis2_controls(control_reference: str) -> str:
    """
    Map an ISO 27001:2022 control to its related NIS2 Directive articles,
    or map a NIS2 article to related ISO 27001 Annex A controls.
    Useful for dual compliance planning.
    """
    ref = control_reference.strip()

    # Try NIS2 article lookup first
    if ref.upper().startswith("ART") or "21" in ref or "23" in ref:
        # Normalise: "art.21b" → "Art.21(b)"
        normalised = ref.replace("art.", "Art.").replace("ART.", "Art.")
        match = NIS2_TO_ISO.get(normalised) or NIS2_TO_ISO.get(normalised.replace("Art.21", "Art.21"))

        # Try fuzzy match
        if not match:
            for key in NIS2_TO_ISO:
                if ref.lower().replace(" ", "") in key.lower().replace(" ", ""):
                    match = NIS2_TO_ISO[key]
                    normalised = key
                    break

        if not match:
            available = ", ".join(NIS2_TO_ISO.keys())
            return f"NIS2 reference '{ref}' not found. Available: {available}"

        ctrl_details = []
        for cid in match["iso_controls"]:
            ctrl = next((c for c in ISO_CONTROLS if c["id"] == cid), None)
            if ctrl:
                ctrl_details.append(f"  - **{cid}** {ctrl['name']} ({ctrl['priority']} priority)")

        lines = [
            f"## NIS2 {normalised} → ISO 27001:2022 Controls",
            f"**NIS2 Requirement:** {match['title']}",
            "",
            "**Related ISO 27001 Annex A Controls:**",
        ] + ctrl_details

        return "\n".join(lines)

    # ISO 27001 control lookup
    ctrl = next((c for c in ISO_CONTROLS if c["id"] == ref), None)
    if ctrl is None:
        # Try prefix match
        ctrl = next((c for c in ISO_CONTROLS if c["id"].startswith(ref)), None)

    if ctrl is None:
        return (
            f"Control ID '{ref}' not found. "
            "Use format like '5.1', '8.5', '7.2' (ISO 27001) "
            "or 'Art.21(b)', 'Art.23' (NIS2)."
        )

    articles = ISO_TO_NIS2.get(ctrl["id"], [])
    if not articles:
        return (
            f"**ISO 27001 Control {ctrl['id']}:** {ctrl['name']} ({ctrl['theme']} theme, {ctrl['priority']} priority)\n\n"
            "This control does not have a direct NIS2 mapping but still contributes to overall compliance posture."
        )

    article_details = []
    for art in articles:
        art_data = NIS2_TO_ISO[art]
        article_details.append(f"  - **{art}** {art_data['title']}")

    lines = [
        f"## ISO 27001 Control {ctrl['id']} → NIS2 Articles",
        f"**Control:** {ctrl['name']}",
        f"**Theme:** {ctrl['theme']}  |  **Priority:** {ctrl['priority']}",
        "",
        "**Related NIS2 Articles:**",
    ] + article_details + [
        "",
        "💡 Implementing this control helps satisfy the NIS2 articles listed above.",
    ]

    return "\n".join(lines)