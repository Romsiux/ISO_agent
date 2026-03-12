"""
Agent
=====
Builds and runs the LangChain tool-calling agent.

Supports multiple LLM providers:
  - OpenAI   (gpt-4o, gpt-4o-mini)
  - Anthropic (claude-sonnet-4-5)
  - Google    (gemini-1.5-pro)

The policy-generator tool always uses Claude internally regardless of
the main agent's selected model.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.callbacks.manager import get_openai_callback
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from compliance_tools import (
    analyze_compliance_gaps,
    calculate_risk_score,
    create_search_tool,
    generate_policy_template,
    map_iso_nis2_controls,
)
from config import (
    ANTHROPIC_API_KEY,
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    GOOGLE_API_KEY,
    OPENAI_API_KEY,
    TOKEN_PRICES,
)
from rag_engine import RAGEngine

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an expert ISO 27001:2022 and NIS2 Directive compliance consultant.

You help organisations achieve and maintain information security certification by:
• Explaining ISO 27001 clauses, controls, and implementation guidance
• Interpreting NIS2 Directive requirements and obligations
• Performing risk assessments and gap analyses
• Generating policy templates and documentation
• Mapping controls between ISO 27001 and NIS2
• Providing practical, actionable implementation advice

Available tools:
1. **search_documents** — searches the uploaded knowledge base (ISO standard PDFs, company docs)
2. **calculate_risk_score** — ISO 27001 risk matrix calculator
3. **analyze_compliance_gaps** — checks which of the 93 Annex A controls are missing
4. **generate_policy_template** — creates ready-to-use policy documents (uses Claude for best quality)
5. **map_iso_nis2_controls** — maps ISO 27001 controls ↔ NIS2 articles

Guidelines:
- Always cite specific ISO 27001 clauses or Annex A control numbers when relevant
- Reference NIS2 articles when there is overlap
- When answering from uploaded documents, note the source and page
- Be precise and practical — avoid vague advice
- For policy questions, offer to generate a template
- Proactively suggest related controls or requirements the user might not have considered

Company context: {company_name} ({company_industry} industry)
"""


def get_llm(model_label: str):
    """
    Factory — return the right LangChain LLM for *model_label*.
    Falls back to GPT-4o if the required API key is missing.
    """
    cfg = AVAILABLE_MODELS.get(model_label, AVAILABLE_MODELS[DEFAULT_MODEL])
    provider = cfg["provider"]
    model = cfg["model"]

    if provider == "anthropic":
        if not ANTHROPIC_API_KEY:
            logger.warning("No ANTHROPIC_API_KEY — falling back to GPT-4o")
            return ChatOpenAI(model="gpt-4o", temperature=0.1, openai_api_key=OPENAI_API_KEY)
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            temperature=0.1,
            anthropic_api_key=ANTHROPIC_API_KEY,
        )

    if provider == "google":
        if not GOOGLE_API_KEY:
            logger.warning("No GOOGLE_API_KEY — falling back to GPT-4o")
            return ChatOpenAI(model="gpt-4o", temperature=0.1, openai_api_key=OPENAI_API_KEY)
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=0.1,
            google_api_key=GOOGLE_API_KEY,
        )

    # Default: OpenAI
    return ChatOpenAI(
        model=model,
        temperature=0.1,
        openai_api_key=OPENAI_API_KEY,
    )


def _estimate_cost(model_label: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost in USD for the given model and token counts."""
    cfg = AVAILABLE_MODELS.get(model_label, {})
    model = cfg.get("model", "gpt-4o")
    prices = TOKEN_PRICES.get(model, TOKEN_PRICES["gpt-4o"])
    return (prompt_tokens / 1000 * prices["input"]) + (completion_tokens / 1000 * prices["output"])


def _tiktoken_count(text: str, model: str = "gpt-4o") -> int:
    """Count tokens with tiktoken; fall back to word estimate if unavailable."""
    try:
        import tiktoken
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(str(text)))
    except Exception:
        return max(1, len(str(text).split()) * 2)


class ComplianceAgent:
    """Wraps an AgentExecutor with multi-model support and token usage tracking."""

    def __init__(self, rag_engine: RAGEngine, model_label: str = DEFAULT_MODEL) -> None:
        self.rag_engine = rag_engine
        self.model_label = model_label
        self._build_agent()

    def _build_agent(self) -> None:
        llm = get_llm(self.model_label)

        tools = [
            create_search_tool(self.rag_engine),
            calculate_risk_score,
            analyze_compliance_gaps,
            generate_policy_template,
            map_iso_nis2_controls,
        ]

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
        self.executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=8,
        )

    def run(
        self,
        user_input: str,
        chat_history: List[BaseMessage],
        company_name: str = "Your Company",
        company_industry: str = "Technology",
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Run the agent and return (response_text, usage_stats).
        Uses get_openai_callback for OpenAI models; estimates cost for others.
        """
        cfg = AVAILABLE_MODELS.get(self.model_label, {})
        provider = cfg.get("provider", "openai")

        if provider == "openai":
            cfg_model = AVAILABLE_MODELS.get(self.model_label, {}).get("model", "gpt-4o")
            with get_openai_callback() as cb:
                result = self.executor.invoke({
                    "input": user_input,
                    "chat_history": chat_history,
                    "company_name": company_name,
                    "company_industry": company_industry,
                })
            output_text = result.get("output", "")

            # get_openai_callback can return 0 with newer gpt-4o API versions
            # fall back to tiktoken estimation when that happens
            if cb.total_tokens > 0:
                usage = {
                    "total_tokens": cb.total_tokens,
                    "prompt_tokens": cb.prompt_tokens,
                    "completion_tokens": cb.completion_tokens,
                    "cost_usd": cb.total_cost,
                }
            else:
                prompt_tok = _tiktoken_count(user_input, cfg_model)
                completion_tok = _tiktoken_count(output_text, cfg_model)
                usage = {
                    "total_tokens": prompt_tok + completion_tok,
                    "prompt_tokens": prompt_tok,
                    "completion_tokens": completion_tok,
                    "cost_usd": _estimate_cost(self.model_label, prompt_tok, completion_tok),
                }
            result = {"output": output_text}
        else:
            # For Anthropic/Google — run without callback, estimate cost
            result = self.executor.invoke({
                "input": user_input,
                "chat_history": chat_history,
                "company_name": company_name,
                "company_industry": company_industry,
            })
            # result["output"] may be a list of content blocks (Anthropic) — normalise to str
            output = result["output"]
            if isinstance(output, list):
                output = " ".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in output
                ).strip()
            # Use tiktoken for a reasonable estimate
            prompt_tok = _tiktoken_count(user_input)
            completion_tok = _tiktoken_count(output)
            usage = {
                "total_tokens": prompt_tok + completion_tok,
                "prompt_tokens": prompt_tok,
                "completion_tokens": completion_tok,
                "cost_usd": _estimate_cost(self.model_label, prompt_tok, completion_tok),
            }
            result = {"output": output}

        return result["output"], usage

    def rebuild(self, model_label: str | None = None) -> None:
        """Rebuild the agent, optionally switching models."""
        if model_label:
            self.model_label = model_label
        self._build_agent()


def messages_to_langchain(history: List[Dict[str, str]]) -> List[BaseMessage]:
    """Convert Streamlit chat history dicts to LangChain BaseMessage objects."""
    def _to_str(content) -> str:
        """Normalise content — may be a string or a list of Anthropic content blocks."""
        if isinstance(content, list):
            return " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            ).strip()
        return str(content)

    messages: List[BaseMessage] = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=_to_str(msg["content"])))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=_to_str(msg["content"])))
    return messages