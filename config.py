"""Central configuration for ISO Compliance Assistant."""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Read from Streamlit secrets if running on Streamlit Cloud ─────────────────
def _get(key: str, fallback: str = "") -> str:
    """Read from st.secrets first (Streamlit Cloud), then env vars, then fallback."""
    try:
        import streamlit as st
        val = st.secrets.get(key, "")
        if val:
            return val
    except Exception:
        pass
    return os.getenv(key, fallback)

# ── API Keys ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = _get("OPENAI_API_KEY")
ANTHROPIC_API_KEY: str = _get("ANTHROPIC_API_KEY")
GOOGLE_API_KEY: str = _get("GOOGLE_API_KEY")

# ── Model options ─────────────────────────────────────────────────────────────
AVAILABLE_MODELS: dict = {
    "GPT-4o (OpenAI)":              {"provider": "openai",    "model": "gpt-4o"},
    "GPT-5 (OpenAI)":               {"provider": "openai",    "model": "gpt-5"},
    "Claude Sonnet 4.6 (Anthropic)":{"provider": "anthropic", "model": "claude-sonnet-4-6"},
    "Gemini 3.1 Pro (Google)":      {"provider": "google",    "model": "gemini-3.1-pro-preview"},
}

# Default model for the main agent
DEFAULT_MODEL: str = "GPT-4o (OpenAI)"

# Policy generator always uses Claude (best for structured documents)
POLICY_MODEL: str = "claude-sonnet-4-6"
POLICY_PROVIDER: str = "anthropic"

# ── Embedding ─────────────────────────────────────────────────────────────────
# Using local HuggingFace model — no API key needed
EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

# ── Company context ───────────────────────────────────────────────────────────
COMPANY_NAME: str = _get("COMPANY_NAME", "Your Company")
COMPANY_INDUSTRY: str = _get("COMPANY_INDUSTRY", "Technology")

# ── ChromaDB ──────────────────────────────────────────────────────────────────
CHROMA_PERSIST_DIR: str = "./chroma_db"
COLLECTION_NAME: str = "iso_compliance"

# ── RAG ───────────────────────────────────────────────────────────────────────
CHUNK_SIZE: int = 1000
CHUNK_OVERLAP: int = 200
TOP_K_RESULTS: int = 6

# ── Pricing (USD per 1 000 tokens) ────────────────────────────────────────────
TOKEN_PRICES: dict = {
    "gpt-4o":                  {"input": 0.005,   "output": 0.015},
    "gpt-5":                   {"input": 0.0025,  "output": 0.010},
    "claude-sonnet-4-6":       {"input": 0.003,   "output": 0.015},
    "gemini-3.1-pro-preview":  {"input": 0.002,   "output": 0.012},
}
