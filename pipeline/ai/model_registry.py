"""Model Registry - runtime-switchable LLM models (free & premium)."""

import logging
import os
from typing import Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ModelTier(str, Enum):
    FREE = "free"
    PREMIUM = "premium"


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    COHERE = "cohere"
    GROQ = "groq"
    TOGETHER = "together"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    BEDROCK = "bedrock"
    AZURE = "azure"
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"
    LOCAL = "local"
    XAI = "xai"
    PERPLEXITY = "perplexity"
    AMAZON = "amazon"
    MICROSOFT = "microsoft"
    BYTEDANCE = "bytedance"
    NVIDIA = "nvidia"
    META = "meta"
    QWEN = "qwen"
    ZAI = "zai"
    MINIMAX = "minimax"
    MOONSHOT = "moonshot"
    STEPFUN = "stepfun"
    XIAOMI = "xiaomi"
    IBM = "ibm"
    MORPH = "morph"
    AIONLABS = "aionlabs"
    LIQUIDAI = "liquidai"
    NOUS = "nous"
    WRITER = "writer"
    UPSTAGE = "upstage"
    REKA = "reka"
    BAIDU = "baidu"
    TENCENT = "tencent"
    AI21 = "ai21"
    LIANG = "liang"


@dataclass
class ModelConfig:
    id: str
    name: str
    provider: ModelProvider
    tier: ModelTier
    description: str
    max_tokens: int = 4096
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_tools: bool = True
    supports_image: bool = False
    supports_file: bool = False
    supports_audio: bool = False
    supports_video: bool = False
    context_window: int = 128000
    api_key_env: Optional[str] = None
    default_temperature: float = 0.3
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    litellm_model: str = ""


def M(id, name, provider, tier, desc, ctx=128000, vision=False, tools=True, stream=True, key=None, cost_in=0.0, cost_out=0.0, llm="",
      image=False, file=False, audio=False, video=False):
    return ModelConfig(
        id=id, name=name, provider=provider, tier=tier, description=desc,
        context_window=ctx, supports_vision=vision, supports_tools=tools,
        supports_streaming=stream, supports_image=image or vision, supports_file=file,
        supports_audio=audio, supports_video=video, api_key_env=key,
        cost_per_1k_input=cost_in, cost_per_1k_output=cost_out,
        litellm_model=llm,
    )


FREE_MODELS = [
    M("ollama-llama3.1-8b", "Llama 3.1 8B (Local)", ModelProvider.OLLAMA, ModelTier.FREE,
      "Meta Llama 3.1 8B - fast local inference", ctx=128000, llm="ollama/llama3.1:8b"),
    M("ollama-mistral-7b", "Mistral 7B (Local)", ModelProvider.OLLAMA, ModelTier.FREE,
      "Mistral 7B - efficient local model", ctx=32000, llm="ollama/mistral:7b"),
    M("ollama-qwen2.5-7b", "Qwen 2.5 7B (Local)", ModelProvider.OLLAMA, ModelTier.FREE,
      "Qwen 2.5 7B - strong multilingual", ctx=32000, llm="ollama/qwen2.5:7b"),
    M("ollama-deepseek-r1-8b", "DeepSeek R1 8B (Local)", ModelProvider.OLLAMA, ModelTier.FREE,
      "DeepSeek R1 distilled 8B - local reasoning", ctx=64000, llm="ollama/deepseek-r1:8b"),
    M("ollama-phi-4", "Phi-4 14B (Local)", ModelProvider.OLLAMA, ModelTier.FREE,
      "Microsoft Phi-4 14B - local reasoning", ctx=128000, llm="ollama/phi-4:14b"),
    M("groq-llama3.1-8b", "Llama 3.1 8B (Groq)", ModelProvider.GROQ, ModelTier.FREE,
      "Groq-hosted Llama 3.1 8B - blazing fast", ctx=128000, key="GROQ_API_KEY",
      llm="groq/llama-3.1-8b-instant"),
    M("groq-mixtral-8x7b", "Mixtral 8x7B (Groq)", ModelProvider.GROQ, ModelTier.FREE,
      "Groq-hosted Mixtral 8x7B - fast MoE", ctx=32000, key="GROQ_API_KEY",
      llm="groq/mixtral-8x7b-32768"),
    M("groq-gemma2-9b", "Gemma 2 9B (Groq)", ModelProvider.GROQ, ModelTier.FREE,
      "Google Gemma 2 9B on Groq", ctx=8192, key="GROQ_API_KEY",
      llm="groq/gemma2-9b-it"),
    M("groq-llama3.2-3b", "Llama 3.2 3B (Groq)", ModelProvider.GROQ, ModelTier.FREE,
      "Meta Llama 3.2 3B - tiny & fast", ctx=128000, key="GROQ_API_KEY",
      llm="groq/llama-3.2-3b-preview"),
    M("groq-qwen2.5-32b", "Qwen 2.5 32B (Groq)", ModelProvider.GROQ, ModelTier.FREE,
      "Qwen 2.5 32B on Groq", ctx=128000, key="GROQ_API_KEY",
      llm="groq/qwen-2.5-32b"),
    M("together-llama3.1-8b", "Llama 3.1 8B (Together)", ModelProvider.TOGETHER, ModelTier.FREE,
      "Together-hosted Llama 3.1 8B", ctx=128000, key="TOGETHER_API_KEY",
      llm="together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"),
    M("huggingface-mistral-7b", "Mistral 7B (HuggingFace)", ModelProvider.HUGGINGFACE, ModelTier.FREE,
      "HuggingFace Inference API - Mistral 7B", ctx=32000, key="HUGGINGFACE_API_KEY",
      llm="huggingface/mistralai/Mistral-7B-Instruct-v0.3"),
    M("deepseek-chat-free", "DeepSeek Chat (Free)", ModelProvider.DEEPSEEK, ModelTier.FREE,
      "DeepSeek Chat V3 - free tier", ctx=64000, key="DEEPSEEK_API_KEY",
      llm="deepseek/deepseek-chat"),
    M("gemini-flash-free", "Gemini 2.0 Flash (Free)", ModelProvider.GOOGLE, ModelTier.FREE,
      "Google Gemini 2.0 Flash - free tier, 60 req/min", ctx=1000000, vision=True,
      file=True, audio=True, video=True,
      key="GEMINI_API_KEY", llm="gemini/gemini-2.0-flash-exp"),
    M("ollama-llama3.2-3b", "Llama 3.2 3B (Local)", ModelProvider.OLLAMA, ModelTier.FREE,
      "Meta Llama 3.2 3B - tiny local model", ctx=128000, llm="ollama/llama3.2:3b"),
    M("ollama-llama3.2-1b", "Llama 3.2 1B (Local)", ModelProvider.OLLAMA, ModelTier.FREE,
      "Meta Llama 3.2 1B - mobile/local ultra-light", ctx=128000, llm="ollama/llama3.2:1b"),
    M("ollama-gemma2-2b", "Gemma 2 2B (Local)", ModelProvider.OLLAMA, ModelTier.FREE,
      "Google Gemma 2 2B - tiny local model", ctx=8192, llm="ollama/gemma2:2b"),
    M("ollama-qwen2.5-1.5b", "Qwen 2.5 1.5B (Local)", ModelProvider.OLLAMA, ModelTier.FREE,
      "Qwen 2.5 1.5B - ultra-light mobile model", ctx=32768, llm="ollama/qwen2.5:1.5b"),
    M("ollama-qwen2.5-0.5b", "Qwen 2.5 0.5B (Local)", ModelProvider.OLLAMA, ModelTier.FREE,
      "Qwen 2.5 0.5B - smallest local model", ctx=32768, llm="ollama/qwen2.5:0.5b"),
    M("ollama-phi3.5-mini", "Phi-3.5 Mini (Local)", ModelProvider.OLLAMA, ModelTier.FREE,
      "Microsoft Phi-3.5 Mini 3.8B - local", ctx=128000, llm="ollama/phi3.5:3.8b"),
    M("ollama-mistral-7b-v2", "Mistral 7B v2 (Local)", ModelProvider.OLLAMA, ModelTier.FREE,
      "Mistral 7B v0.2 - updated local model", ctx=32000, llm="ollama/mistral:7b-v2"),
]

PREMIUM_MODELS = [
    # ══════════════════════════════════════════
    # OpenAI
    # ══════════════════════════════════════════
    M("openai-gpt-4o", "GPT-4o", ModelProvider.OPENAI, ModelTier.PREMIUM,
      "OpenAI GPT-4o - best all-rounder", ctx=128000, vision=True,
      file=True, audio=True, key="OPENAI_API_KEY",
      cost_in=0.0025, cost_out=0.01, llm="openai/gpt-4o"),
    M("openai-gpt-4o-mini", "GPT-4o Mini", ModelProvider.OPENAI, ModelTier.PREMIUM,
      "OpenAI GPT-4o Mini - fast & cheap", ctx=128000, vision=True,
      file=True, key="OPENAI_API_KEY",
      cost_in=0.00015, cost_out=0.0006, llm="openai/gpt-4o-mini"),
    M("openai-o1", "OpenAI o1", ModelProvider.OPENAI, ModelTier.PREMIUM,
      "OpenAI o1 - advanced reasoning", ctx=200000, vision=True,
      file=True, key="OPENAI_API_KEY",
      cost_in=0.015, cost_out=0.06, llm="openai/o1-preview"),
    M("openai-o1-mini", "OpenAI o1-mini", ModelProvider.OPENAI, ModelTier.PREMIUM,
      "OpenAI o1-mini - fast reasoning", ctx=128000, key="OPENAI_API_KEY",
      cost_in=0.003, cost_out=0.012, llm="openai/o1-mini"),
    M("openai-o3-mini", "OpenAI o3-mini", ModelProvider.OPENAI, ModelTier.PREMIUM,
      "OpenAI o3-mini - latest reasoning", ctx=200000, key="OPENAI_API_KEY",
      cost_in=0.0011, cost_out=0.0044, llm="openai/o3-mini"),
    M("openai-o4-mini", "OpenAI o4-mini", ModelProvider.OPENAI, ModelTier.PREMIUM,
      "OpenAI o4-mini - newest reasoning model", ctx=200000, vision=True,
      file=True, key="OPENAI_API_KEY",
      cost_in=0.0011, cost_out=0.0044, llm="openai/o4-mini"),
    M("openai-gpt-4.1", "GPT-4.1", ModelProvider.OPENAI, ModelTier.PREMIUM,
      "OpenAI GPT-4.1 - latest flagship", ctx=1000000, vision=True,
      file=True, key="OPENAI_API_KEY",
      cost_in=0.002, cost_out=0.008, llm="openai/gpt-4.1"),
    M("openai-gpt-4.1-mini", "GPT-4.1 Mini", ModelProvider.OPENAI, ModelTier.PREMIUM,
      "OpenAI GPT-4.1 Mini - cheap & capable", ctx=1000000, vision=True,
      file=True, key="OPENAI_API_KEY",
      cost_in=0.0004, cost_out=0.0016, llm="openai/gpt-4.1-mini"),

    # ══════════════════════════════════════════
    # Anthropic
    # ══════════════════════════════════════════
    M("anthropic-claude-sonnet-4", "Claude Sonnet 4", ModelProvider.ANTHROPIC, ModelTier.PREMIUM,
      "Anthropic Claude Sonnet 4 - balanced best", ctx=200000, vision=True,
      file=True, key="ANTHROPIC_API_KEY",
      cost_in=0.003, cost_out=0.015, llm="anthropic/claude-sonnet-4-20250514"),
    M("anthropic-claude-haiku-3.5", "Claude Haiku 3.5", ModelProvider.ANTHROPIC, ModelTier.PREMIUM,
      "Anthropic Claude Haiku 3.5 - fast & cheap", ctx=200000, vision=True,
      file=True, key="ANTHROPIC_API_KEY",
      cost_in=0.0008, cost_out=0.004, llm="anthropic/claude-3-5-haiku-20241022"),
    M("anthropic-claude-opus-4", "Claude Opus 4", ModelProvider.ANTHROPIC, ModelTier.PREMIUM,
      "Anthropic Claude Opus 4 - most capable", ctx=200000, vision=True,
      file=True, key="ANTHROPIC_API_KEY",
      cost_in=0.015, cost_out=0.075, llm="anthropic/claude-opus-4-20250514"),
    M("anthropic-claude-3.5-sonnet", "Claude 3.5 Sonnet", ModelProvider.ANTHROPIC, ModelTier.PREMIUM,
      "Anthropic Claude 3.5 Sonnet - legacy flagship", ctx=200000, vision=True,
      file=True, key="ANTHROPIC_API_KEY",
      cost_in=0.003, cost_out=0.015, llm="anthropic/claude-3-5-sonnet-20241022"),

    # ══════════════════════════════════════════
    # Google
    # ══════════════════════════════════════════
    M("google-gemini-2.0-flash", "Gemini 2.0 Flash", ModelProvider.GOOGLE, ModelTier.PREMIUM,
      "Google Gemini 2.0 Flash - fast multimodal", ctx=1000000, vision=True,
      file=True, audio=True, video=True, key="GEMINI_API_KEY",
      cost_in=0.0001, cost_out=0.0004, llm="gemini/gemini-2.0-flash-exp"),
    M("google-gemini-2.5-flash", "Gemini 2.5 Flash", ModelProvider.GOOGLE, ModelTier.PREMIUM,
      "Google Gemini 2.5 Flash - newest speed/quality", ctx=1000000, vision=True,
      file=True, audio=True, video=True, key="GEMINI_API_KEY",
      cost_in=0.00015, cost_out=0.0006, llm="gemini/gemini-2.5-flash-preview-05-06"),
    M("google-gemini-2.5-pro", "Gemini 2.5 Pro", ModelProvider.GOOGLE, ModelTier.PREMIUM,
      "Google Gemini 2.5 Pro - best for code", ctx=1000000, vision=True,
      file=True, audio=True, video=True, key="GEMINI_API_KEY",
      cost_in=0.00125, cost_out=0.005, llm="gemini/gemini-2.5-pro-preview-05-06"),
    M("google-gemini-1.5-pro", "Gemini 1.5 Pro", ModelProvider.GOOGLE, ModelTier.PREMIUM,
      "Google Gemini 1.5 Pro - legacy flagship", ctx=2000000, vision=True,
      file=True, audio=True, video=True, key="GEMINI_API_KEY",
      cost_in=0.00125, cost_out=0.005, llm="gemini/gemini-1.5-pro"),

    # ══════════════════════════════════════════
    # DeepSeek
    # ══════════════════════════════════════════
    M("deepseek-r1", "DeepSeek R1", ModelProvider.DEEPSEEK, ModelTier.PREMIUM,
      "DeepSeek R1 - advanced reasoning", ctx=128000, cost_in=0.0005, cost_out=0.002,
      key="DEEPSEEK_API_KEY", llm="deepseek/deepseek-reasoner"),
    M("deepseek-v3", "DeepSeek V3", ModelProvider.DEEPSEEK, ModelTier.PREMIUM,
      "DeepSeek V3 - latest flagship", ctx=128000, cost_in=0.0005, cost_out=0.002,
      key="DEEPSEEK_API_KEY", llm="deepseek/deepseek-chat"),

    # ══════════════════════════════════════════
    # Mistral
    # ══════════════════════════════════════════
    M("mistral-large-2", "Mistral Large 2", ModelProvider.MISTRAL, ModelTier.PREMIUM,
      "Mistral Large 2 - best multilingual", ctx=128000, vision=True, key="MISTRAL_API_KEY",
      cost_in=0.002, cost_out=0.006, llm="mistral/mistral-large-2411"),
    M("mistral-small-3", "Mistral Small 3", ModelProvider.MISTRAL, ModelTier.PREMIUM,
      "Mistral Small 3 - fast & efficient", ctx=32000, key="MISTRAL_API_KEY",
      cost_in=0.001, cost_out=0.003, llm="mistral/mistral-small-2501"),
    M("mistral-codestral", "Codestral", ModelProvider.MISTRAL, ModelTier.PREMIUM,
      "Mistral Codestral - code generation", ctx=256000, key="MISTRAL_API_KEY",
      cost_in=0.001, cost_out=0.003, llm="mistral/codestral-2501"),
    M("mistral-nemo", "Mistral Nemo", ModelProvider.MISTRAL, ModelTier.PREMIUM,
      "Mistral Nemo 12B - efficient open model", ctx=128000, key="MISTRAL_API_KEY",
      cost_in=0.0001, cost_out=0.0001, llm="mistral/mistral-nemo"),

    # ══════════════════════════════════════════
    # Cohere
    # ══════════════════════════════════════════
    M("cohere-command-r7b", "Command R7B", ModelProvider.COHERE, ModelTier.PREMIUM,
      "Cohere Command R7B - RAG optimized", ctx=128000, key="COHERE_API_KEY",
      cost_in=0.0005, cost_out=0.0015, llm="cohere/command-r7b-12-2024"),
    M("cohere-command-r-plus", "Command R+", ModelProvider.COHERE, ModelTier.PREMIUM,
      "Cohere Command R+ - best for RAG", ctx=128000, key="COHERE_API_KEY",
      cost_in=0.003, cost_out=0.015, llm="cohere/command-r-plus-08-2024"),

    # ══════════════════════════════════════════
    # Meta / Llama (via OpenRouter)
    # ══════════════════════════════════════════
    M("openrouter-llama-4-scout", "Llama 4 Scout 17B", ModelProvider.META, ModelTier.PREMIUM,
      "Meta Llama 4 Scout - efficient flagship", ctx=1000000, vision=True, key="OPENROUTER_API_KEY",
      cost_in=0.0002, cost_out=0.0002, llm="openrouter/meta-llama/llama-4-scout-17b-16e-instruct"),
    M("openrouter-llama-4-maverick", "Llama 4 Maverick 17B", ModelProvider.META, ModelTier.PREMIUM,
      "Meta Llama 4 Maverick - best quality MoE", ctx=1000000, vision=True, key="OPENROUTER_API_KEY",
      cost_in=0.0002, cost_out=0.0002, llm="openrouter/meta-llama/llama-4-maverick-17b-128e-instruct"),
    M("openrouter-llama-3.3-70b", "Llama 3.3 70B", ModelProvider.META, ModelTier.PREMIUM,
      "Meta Llama 3.3 70B - instruction tuned", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0003, cost_out=0.0004, llm="openrouter/meta-llama/llama-3.3-70b-instruct"),
    M("openrouter-llama-3.1-405b", "Llama 3.1 405B", ModelProvider.META, ModelTier.PREMIUM,
      "Meta Llama 3.1 405B - largest open model", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.001, cost_out=0.001, llm="openrouter/meta-llama/llama-3.1-405b-instruct"),
    M("openrouter-llama-3.1-70b", "Llama 3.1 70B", ModelProvider.META, ModelTier.PREMIUM,
      "Meta Llama 3.1 70B - strong open model", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0003, cost_out=0.0004, llm="openrouter/meta-llama/llama-3.1-70b-instruct"),
    M("openrouter-llama-3.2-90b-vision", "Llama 3.2 90B Vision", ModelProvider.META, ModelTier.PREMIUM,
      "Meta Llama 3.2 90B - vision + text", ctx=128000, vision=True, key="OPENROUTER_API_KEY",
      cost_in=0.0005, cost_out=0.0007, llm="openrouter/meta-llama/llama-3.2-90b-vision-instruct"),

    # ══════════════════════════════════════════
    # Qwen (via OpenRouter)
    # ══════════════════════════════════════════
    M("openrouter-qwen-2.5-72b", "Qwen 2.5 72B", ModelProvider.QWEN, ModelTier.PREMIUM,
      "Qwen 2.5 72B - multilingual flagship", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0003, cost_out=0.0004, llm="openrouter/qwen/qwen-2.5-72b-instruct"),
    M("openrouter-qwen-2.5-32b-coder", "Qwen 2.5 Coder 32B", ModelProvider.QWEN, ModelTier.PREMIUM,
      "Qwen 2.5 Coder 32B - code specialist", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0002, cost_out=0.0003, llm="openrouter/qwen/qwen-2.5-coder-32b-instruct"),
    M("openrouter-qwq-32b", "QwQ 32B", ModelProvider.QWEN, ModelTier.PREMIUM,
      "Qwen QwQ 32B - reasoning model", ctx=32000, key="OPENROUTER_API_KEY",
      cost_in=0.0002, cost_out=0.0003, llm="openrouter/qwen/qwq-32b-preview"),
    M("openrouter-qwen-2.5-vl-72b", "Qwen 2.5 VL 72B", ModelProvider.QWEN, ModelTier.PREMIUM,
      "Qwen 2.5 Vision-Language 72B", ctx=128000, vision=True, key="OPENROUTER_API_KEY",
      cost_in=0.0004, cost_out=0.0005, llm="openrouter/qwen/qwen-2.5-vl-72b-instruct"),

    # ══════════════════════════════════════════
    # xAI / Grok
    # ══════════════════════════════════════════
    M("openrouter-grok-2", "Grok 2", ModelProvider.XAI, ModelTier.PREMIUM,
      "xAI Grok 2 - latest flagship", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.002, cost_out=0.01, llm="openrouter/xai/grok-2-1212"),
    M("openrouter-grok-2-vision", "Grok 2 Vision", ModelProvider.XAI, ModelTier.PREMIUM,
      "xAI Grok 2 Vision - multimodal", ctx=128000, vision=True, key="OPENROUTER_API_KEY",
      cost_in=0.002, cost_out=0.01, llm="openrouter/xai/grok-2-vision-1212"),
    M("openrouter-grok-3", "Grok 3", ModelProvider.XAI, ModelTier.PREMIUM,
      "xAI Grok 3 - next-gen reasoning", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.003, cost_out=0.015, llm="openrouter/xai/grok-3"),
    M("openrouter-grok-3-mini", "Grok 3 Mini", ModelProvider.XAI, ModelTier.PREMIUM,
      "xAI Grok 3 Mini - fast reasoning", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0003, cost_out=0.0005, llm="openrouter/xai/grok-3-mini"),

    # ══════════════════════════════════════════
    # Perplexity
    # ══════════════════════════════════════════
    M("openrouter-sonar-pro", "Sonar Pro", ModelProvider.PERPLEXITY, ModelTier.PREMIUM,
      "Perplexity Sonar Pro - search augmented", ctx=200000, key="OPENROUTER_API_KEY",
      cost_in=0.005, cost_out=0.015, llm="openrouter/perplexity/sonar-pro"),
    M("openrouter-sonar-reasoning", "Sonar Reasoning", ModelProvider.PERPLEXITY, ModelTier.PREMIUM,
      "Perplexity Sonar Reasoning - deep reasoning", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.002, cost_out=0.008, llm="openrouter/perplexity/sonar-reasoning"),
    M("openrouter-sonar", "Sonar", ModelProvider.PERPLEXITY, ModelTier.PREMIUM,
      "Perplexity Sonar - lightweight search", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.001, cost_out=0.001, llm="openrouter/perplexity/sonar"),

    # ══════════════════════════════════════════
    # Amazon / AWS
    # ══════════════════════════════════════════
    M("openrouter-nova-pro", "Nova Pro", ModelProvider.AMAZON, ModelTier.PREMIUM,
      "Amazon Nova Pro - flagship AWS model", ctx=128000, vision=True, key="OPENROUTER_API_KEY",
      cost_in=0.0008, cost_out=0.0032, llm="openrouter/amazon/nova-pro-v1"),
    M("openrouter-nova-lite", "Nova Lite", ModelProvider.AMAZON, ModelTier.PREMIUM,
      "Amazon Nova Lite - fast & cheap", ctx=128000, vision=True, key="OPENROUTER_API_KEY",
      cost_in=0.0001, cost_out=0.0004, llm="openrouter/amazon/nova-lite-v1"),
    M("openrouter-nova-micro", "Nova Micro", ModelProvider.AMAZON, ModelTier.PREMIUM,
      "Amazon Nova Micro - minimal cost", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.00005, cost_out=0.0002, llm="openrouter/amazon/nova-micro-v1"),

    # ══════════════════════════════════════════
    # Microsoft / Phi
    # ══════════════════════════════════════════
    M("openrouter-phi-4", "Phi-4 14B", ModelProvider.MICROSOFT, ModelTier.PREMIUM,
      "Microsoft Phi-4 14B - small & capable", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0001, cost_out=0.0001, llm="openrouter/microsoft/phi-4"),
    M("openrouter-phi-3.5-mini", "Phi-3.5 Mini", ModelProvider.MICROSOFT, ModelTier.PREMIUM,
      "Microsoft Phi-3.5 Mini 3.8B", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.00005, cost_out=0.00005, llm="openrouter/microsoft/phi-3.5-mini-128k"),

    # ══════════════════════════════════════════
    # NVIDIA
    # ══════════════════════════════════════════
    M("openrouter-nemotron-70b", "Nemotron 70B", ModelProvider.NVIDIA, ModelTier.PREMIUM,
      "NVIDIA Llama-Nemotron 70B - reasoning", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0003, cost_out=0.0004, llm="openrouter/nvidia/llama-3.1-nemotron-70b-instruct"),
    M("openrouter-nvidia-llama-3.3-70b", "Llama 3.3 Nemotron 70B", ModelProvider.NVIDIA, ModelTier.PREMIUM,
      "NVIDIA Llama 3.3 Nemotron 70B - latest", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0003, cost_out=0.0004, llm="openrouter/nvidia/llama-3.3-nemotron-70b-instruct"),

    # ══════════════════════════════════════════
    # ByteDance
    # ══════════════════════════════════════════
    M("openrouter-doubao-pro", "Doubao Pro", ModelProvider.BYTEDANCE, ModelTier.PREMIUM,
      "ByteDance Doubao Pro - flagship", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0005, cost_out=0.001, llm="openrouter/bytedance/doubao-pro-32k"),

    # ══════════════════════════════════════════
    # Z.ai
    # ══════════════════════════════════════════
    M("openrouter-zai-llama-70b", "Z.ai Llama 70B", ModelProvider.ZAI, ModelTier.PREMIUM,
      "Z.ai hosted Llama 3.1 70B", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0002, cost_out=0.0002, llm="openrouter/z-ai/llama-3.1-70b"),

    # ══════════════════════════════════════════
    # MiniMax
    # ══════════════════════════════════════════
    M("openrouter-minimax-01", "MiniMax 01", ModelProvider.MINIMAX, ModelTier.PREMIUM,
      "MiniMax 01 - very long context", ctx=1000000, key="OPENROUTER_API_KEY",
      cost_in=0.0002, cost_out=0.0002, llm="openrouter/minimax/minimax-01"),
    M("openrouter-minimax-text-01", "MiniMax Text 01", ModelProvider.MINIMAX, ModelTier.PREMIUM,
      "MiniMax Text 01 - text optimized", ctx=1000000, key="OPENROUTER_API_KEY",
      cost_in=0.0002, cost_out=0.0002, llm="openrouter/minimax/minimax-text-01"),

    # ══════════════════════════════════════════
    # Moonshot / Kimi
    # ══════════════════════════════════════════
    M("openrouter-moonshot-128k", "Moonshot 128K", ModelProvider.MOONSHOT, ModelTier.PREMIUM,
      "Moonshot AI Kimi - long context", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0003, cost_out=0.0006, llm="openrouter/moonshot/moonshot-v1-128k"),
    M("openrouter-moonshot-32k", "Moonshot 32K", ModelProvider.MOONSHOT, ModelTier.PREMIUM,
      "Moonshot AI Kimi - balanced", ctx=32000, key="OPENROUTER_API_KEY",
      cost_in=0.0002, cost_out=0.0004, llm="openrouter/moonshot/moonshot-v1-32k"),

    # ══════════════════════════════════════════
    # StepFun
    # ══════════════════════════════════════════
    M("openrouter-step-2", "Step 2", ModelProvider.STEPFUN, ModelTier.PREMIUM,
      "StepFun Step 2 - 16K context", ctx=16000, key="OPENROUTER_API_KEY",
      cost_in=0.0002, cost_out=0.0004, llm="openrouter/stepfun/step-2-16k"),

    # ══════════════════════════════════════════
    # Xiaomi
    # ══════════════════════════════════════════
    M("openrouter-xiaomi-spark", "Xiaomi Spark", ModelProvider.XIAOMI, ModelTier.PREMIUM,
      "Xiaomi Spark - lightweight model", ctx=32000, key="OPENROUTER_API_KEY",
      cost_in=0.0001, cost_out=0.0002, llm="openrouter/xiaomi/xiaomi-spark"),

    # ══════════════════════════════════════════
    # IBM / Granite
    # ══════════════════════════════════════════
    M("openrouter-granite-34b-code", "Granite 34B Code", ModelProvider.IBM, ModelTier.PREMIUM,
      "IBM Granite 34B Code - enterprise code AI", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0002, cost_out=0.0002, llm="openrouter/ibm/granite-34b-code-instruct"),
    M("openrouter-granite-20b-code", "Granite 20B Code", ModelProvider.IBM, ModelTier.PREMIUM,
      "IBM Granite 20B Code - efficient enterprise", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0001, cost_out=0.0001, llm="openrouter/ibm/granite-20b-code-instruct"),

    # ══════════════════════════════════════════
    # Morph
    # ══════════════════════════════════════════
    M("openrouter-morph-pro", "Morph Pro", ModelProvider.MORPH, ModelTier.PREMIUM,
      "Morph Pro - optimized inference", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0003, cost_out=0.001, llm="openrouter/morph/morph-pro"),

    # ══════════════════════════════════════════
    # Aion Labs
    # ══════════════════════════════════════════
    M("openrouter-aion-1.0", "Aion 1.0", ModelProvider.AIONLABS, ModelTier.PREMIUM,
      "Aion Labs 1.0 - biomedical AI", ctx=32000, key="OPENROUTER_API_KEY",
      cost_in=0.0002, cost_out=0.0004, llm="openrouter/aionlabs/aion-1.0"),

    # ══════════════════════════════════════════
    # Liquid AI
    # ══════════════════════════════════════════
    M("openrouter-liquid-lfm-40b", "LFM 40B", ModelProvider.LIQUIDAI, ModelTier.PREMIUM,
      "Liquid AI LFM 40B - liquid foundation model", ctx=32000, key="OPENROUTER_API_KEY",
      cost_in=0.0002, cost_out=0.0002, llm="openrouter/liquid/lfm-40b"),
    M("openrouter-liquid-lfm-7b", "LFM 7B", ModelProvider.LIQUIDAI, ModelTier.PREMIUM,
      "Liquid AI LFM 7B - efficient liquid model", ctx=32000, key="OPENROUTER_API_KEY",
      cost_in=0.00005, cost_out=0.00005, llm="openrouter/liquid/lfm-7b"),

    # ══════════════════════════════════════════
    # Nous Research
    # ══════════════════════════════════════════
    M("openrouter-hermes-3-405b", "Hermes 3 405B", ModelProvider.NOUS, ModelTier.PREMIUM,
      "Nous Hermes 3 405B - highest quality open", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.001, cost_out=0.001, llm="openrouter/nousresearch/hermes-3-llama-3.1-405b"),
    M("openrouter-hermes-3-70b", "Hermes 3 70B", ModelProvider.NOUS, ModelTier.PREMIUM,
      "Nous Hermes 3 70B - balanced open model", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0003, cost_out=0.0004, llm="openrouter/nousresearch/hermes-3-llama-3.1-70b"),

    # ══════════════════════════════════════════
    # Writer / Palmyra
    # ══════════════════════════════════════════
    M("openrouter-palmyra-x-128k", "Palmyra X 128K", ModelProvider.WRITER, ModelTier.PREMIUM,
      "Writer Palmyra X 128K - long context enterprise", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.001, cost_out=0.003, llm="openrouter/writer/palmyra-x-128k"),

    # ══════════════════════════════════════════
    # Upstage / Solar
    # ══════════════════════════════════════════
    M("openrouter-solar-pro", "Solar Pro", ModelProvider.UPSTAGE, ModelTier.PREMIUM,
      "Upstage Solar Pro - enterprise LLM", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0005, cost_out=0.0015, llm="openrouter/upstage/solar-pro"),

    # ══════════════════════════════════════════
    # Reka
    # ══════════════════════════════════════════
    M("openrouter-reka-core", "Reka Core", ModelProvider.REKA, ModelTier.PREMIUM,
      "Reka Core - multimodal flagship", ctx=128000, vision=True, file=True, key="OPENROUTER_API_KEY",
      cost_in=0.003, cost_out=0.015, llm="openrouter/reka/reka-core-20240501"),

    # ══════════════════════════════════════════
    # Baidu / ERNIE
    # ══════════════════════════════════════════
    M("openrouter-ernie-4.0", "ERNIE 4.0", ModelProvider.BAIDU, ModelTier.PREMIUM,
      "Baidu ERNIE 4.0 - Chinese LLM flagship", ctx=8000, key="OPENROUTER_API_KEY",
      cost_in=0.001, cost_out=0.002, llm="openrouter/baidu/ernie-4.0-8k"),
    M("openrouter-ernie-3.5", "ERNIE 3.5", ModelProvider.BAIDU, ModelTier.PREMIUM,
      "Baidu ERNIE 3.5 - efficient Chinese LLM", ctx=8000, key="OPENROUTER_API_KEY",
      cost_in=0.0005, cost_out=0.001, llm="openrouter/baidu/ernie-3.5-8k"),

    # ══════════════════════════════════════════
    # Tencent / Hunyuan
    # ══════════════════════════════════════════
    M("openrouter-hunyuan-large", "Hunyuan Large", ModelProvider.TENCENT, ModelTier.PREMIUM,
      "Tencent Hunyuan - large Chinese LLM", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.001, cost_out=0.002, llm="openrouter/tencent/hunyuan-large"),

    # ══════════════════════════════════════════
    # AI21 / Jamba
    # ══════════════════════════════════════════
    M("openrouter-jamba-1.5-large", "Jamba 1.5 Large", ModelProvider.AI21, ModelTier.PREMIUM,
      "AI21 Jamba 1.5 Large - hybrid SSM-transformer", ctx=256000, key="OPENROUTER_API_KEY",
      cost_in=0.002, cost_out=0.008, llm="openrouter/ai21/jamba-1.5-large"),
    M("openrouter-jamba-1.5-mini", "Jamba 1.5 Mini", ModelProvider.AI21, ModelTier.PREMIUM,
      "AI21 Jamba 1.5 Mini - efficient hybrid", ctx=256000, key="OPENROUTER_API_KEY",
      cost_in=0.0002, cost_out=0.0008, llm="openrouter/ai21/jamba-1.5-mini"),

    # ══════════════════════════════════════════
    # LIANG
    # ══════════════════════════════════════════
    M("openrouter-liang-2.0", "Liang 2.0", ModelProvider.LIANG, ModelTier.PREMIUM,
      "Liang 2.0 - optimized Asian language model", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0003, cost_out=0.0006, llm="openrouter/liang/liang-2.0"),

    # ══════════════════════════════════════════
    # Claude Code & Claude 3 (via OpenRouter)
    # ══════════════════════════════════════════
    M("openrouter-claude-code", "Claude Code", ModelProvider.ANTHROPIC, ModelTier.PREMIUM,
      "Anthropic Claude Code - coding agent with tool use", ctx=200000, vision=True,
      file=True, key="OPENROUTER_API_KEY",
      cost_in=0.003, cost_out=0.015, llm="openrouter/anthropic/claude-code"),
    M("openrouter-claude-3-opus", "Claude 3 Opus", ModelProvider.ANTHROPIC, ModelTier.PREMIUM,
      "Anthropic Claude 3 Opus - most powerful Claude 3", ctx=200000, vision=True,
      file=True, key="OPENROUTER_API_KEY",
      cost_in=0.015, cost_out=0.075, llm="openrouter/anthropic/claude-3-opus-20240229"),
    M("openrouter-claude-3-sonnet", "Claude 3 Sonnet", ModelProvider.ANTHROPIC, ModelTier.PREMIUM,
      "Anthropic Claude 3 Sonnet - balanced Claude 3", ctx=200000, vision=True,
      file=True, key="OPENROUTER_API_KEY",
      cost_in=0.003, cost_out=0.015, llm="openrouter/anthropic/claude-3-sonnet-20240229"),
    M("openrouter-claude-3-haiku", "Claude 3 Haiku", ModelProvider.ANTHROPIC, ModelTier.PREMIUM,
      "Anthropic Claude 3 Haiku - fastest Claude 3", ctx=200000, vision=True,
      file=True, key="OPENROUTER_API_KEY",
      cost_in=0.00025, cost_out=0.00125, llm="openrouter/anthropic/claude-3-haiku-20240307"),
    M("openrouter-claude-2.1", "Claude 2.1", ModelProvider.ANTHROPIC, ModelTier.PREMIUM,
      "Anthropic Claude 2.1 - legacy long-context", ctx=200000, key="OPENROUTER_API_KEY",
      cost_in=0.008, cost_out=0.024, llm="openrouter/anthropic/claude-2.1"),

    # ══════════════════════════════════════════
    # More DeepSeek models (via OpenRouter)
    # ══════════════════════════════════════════
    M("openrouter-deepseek-coder-v2", "DeepSeek Coder V2", ModelProvider.DEEPSEEK, ModelTier.PREMIUM,
      "DeepSeek Coder V2 - specialized code model", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0005, cost_out=0.002, llm="openrouter/deepseek/deepseek-coder-v2"),
    M("openrouter-deepseek-v2", "DeepSeek V2", ModelProvider.DEEPSEEK, ModelTier.PREMIUM,
      "DeepSeek V2 - efficient flagship", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0005, cost_out=0.002, llm="openrouter/deepseek/deepseek-v2"),
    M("openrouter-deepseek-r1-distill-llama-70b", "DeepSeek R1 Distill Llama 70B", ModelProvider.DEEPSEEK, ModelTier.PREMIUM,
      "DeepSeek R1 distilled into Llama 3.3 70B", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0003, cost_out=0.0004, llm="openrouter/deepseek/deepseek-r1-distill-llama-70b"),
    M("openrouter-deepseek-r1-distill-qwen-32b", "DeepSeek R1 Distill Qwen 32B", ModelProvider.DEEPSEEK, ModelTier.PREMIUM,
      "DeepSeek R1 distilled into Qwen 2.5 32B", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0002, cost_out=0.0003, llm="openrouter/deepseek/deepseek-r1-distill-qwen-32b"),

    # ══════════════════════════════════════════
    # More NVIDIA / Nemotron
    # ══════════════════════════════════════════
    M("openrouter-nvidia-minitron-8b", "Minitron 8B", ModelProvider.NVIDIA, ModelTier.PREMIUM,
      "NVIDIA Minitron 8B - efficient small model", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0001, cost_out=0.0001, llm="openrouter/nvidia/minitron-8b"),
    M("openrouter-nvidia-nemotron-4-340b", "Nemotron 4 340B", ModelProvider.NVIDIA, ModelTier.PREMIUM,
      "NVIDIA Nemotron 4 340B - largest Nemotron", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.004, cost_out=0.004, llm="openrouter/nvidia/nemotron-4-340b-reward"),

    # ══════════════════════════════════════════
    # More Google models (via OpenRouter)
    # ══════════════════════════════════════════
    M("openrouter-gemini-1.5-flash", "Gemini 1.5 Flash", ModelProvider.GOOGLE, ModelTier.PREMIUM,
      "Google Gemini 1.5 Flash - fast & cheap legacy", ctx=1000000, vision=True,
      file=True, audio=True, video=True, key="OPENROUTER_API_KEY",
      cost_in=0.0001, cost_out=0.0004, llm="openrouter/google/gemini-1.5-flash"),
    M("openrouter-gemini-2.0-flash-lite", "Gemini 2.0 Flash Lite", ModelProvider.GOOGLE, ModelTier.PREMIUM,
      "Google Gemini 2.0 Flash Lite - fastest & cheapest", ctx=1000000, vision=True,
      file=True, key="OPENROUTER_API_KEY",
      cost_in=0.00005, cost_out=0.0002, llm="openrouter/google/gemini-2.0-flash-lite-preview"),

    # ══════════════════════════════════════════
    # More Mistral models (via OpenRouter)
    # ══════════════════════════════════════════
    M("openrouter-mistral-7b", "Mistral 7B", ModelProvider.MISTRAL, ModelTier.PREMIUM,
      "Mistral 7B Instruct - lightweight open model", ctx=32000, key="OPENROUTER_API_KEY",
      cost_in=0.00005, cost_out=0.00005, llm="openrouter/mistral/mistral-7b-instruct"),
    M("openrouter-mixtral-8x7b", "Mixtral 8x7B", ModelProvider.MISTRAL, ModelTier.PREMIUM,
      "Mistral Mixtral 8x7B - strong MoE model", ctx=32000, key="OPENROUTER_API_KEY",
      cost_in=0.0005, cost_out=0.0005, llm="openrouter/mistral/mixtral-8x7b-instruct"),
    M("openrouter-mistral-large-2407", "Mistral Large 2407", ModelProvider.MISTRAL, ModelTier.PREMIUM,
      "Mistral Large (July 2024) - legacy large model", ctx=128000, vision=True,
      file=True, key="OPENROUTER_API_KEY",
      cost_in=0.002, cost_out=0.006, llm="openrouter/mistral/mistral-large-2407"),

    # ══════════════════════════════════════════
    # Mobile-friendly / Small models (via OpenRouter)
    # ══════════════════════════════════════════
    M("openrouter-phi-3.5-mini-4k", "Phi-3.5 Mini 4K", ModelProvider.MICROSOFT, ModelTier.PREMIUM,
      "Microsoft Phi-3.5 Mini 3.8B - mobile-friendly", ctx=4096, key="OPENROUTER_API_KEY",
      cost_in=0.00005, cost_out=0.00005, llm="openrouter/microsoft/phi-3.5-mini-instruct"),
    M("openrouter-gemma-2-2b", "Gemma 2 2B", ModelProvider.GOOGLE, ModelTier.PREMIUM,
      "Google Gemma 2 2B - tiny & fast", ctx=8192, key="OPENROUTER_API_KEY",
      cost_in=0.00005, cost_out=0.00005, llm="openrouter/google/gemma-2-2b-it"),
    M("openrouter-gemma-2-9b", "Gemma 2 9B", ModelProvider.GOOGLE, ModelTier.PREMIUM,
      "Google Gemma 2 9B - efficient small model", ctx=8192, key="OPENROUTER_API_KEY",
      cost_in=0.00005, cost_out=0.00005, llm="openrouter/google/gemma-2-9b-it"),
    M("openrouter-qwen-2.5-1.5b", "Qwen 2.5 1.5B", ModelProvider.QWEN, ModelTier.PREMIUM,
      "Qwen 2.5 1.5B - ultra-lightweight", ctx=32768, key="OPENROUTER_API_KEY",
      cost_in=0.00002, cost_out=0.00002, llm="openrouter/qwen/qwen-2.5-1.5b-instruct"),
    M("openrouter-qwen-2.5-0.5b", "Qwen 2.5 0.5B", ModelProvider.QWEN, ModelTier.PREMIUM,
      "Qwen 2.5 0.5B - smallest Qwen model", ctx=32768, key="OPENROUTER_API_KEY",
      cost_in=0.00001, cost_out=0.00001, llm="openrouter/qwen/qwen-2.5-0.5b-instruct"),
    M("openrouter-llama-3.2-1b", "Llama 3.2 1B", ModelProvider.META, ModelTier.PREMIUM,
      "Meta Llama 3.2 1B - mobile-optimized", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.00002, cost_out=0.00002, llm="openrouter/meta-llama/llama-3.2-1b-instruct"),
    M("openrouter-llama-3.2-3b", "Llama 3.2 3B (OpenRouter)", ModelProvider.META, ModelTier.PREMIUM,
      "Meta Llama 3.2 3B - tiny instruction model", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.00003, cost_out=0.00003, llm="openrouter/meta-llama/llama-3.2-3b-instruct"),

    # ══════════════════════════════════════════
    # More Cohere models (via OpenRouter)
    # ══════════════════════════════════════════
    M("openrouter-command-r", "Command R", ModelProvider.COHERE, ModelTier.PREMIUM,
      "Cohere Command R - efficient RAG model", ctx=128000, key="OPENROUTER_API_KEY",
      cost_in=0.0005, cost_out=0.0015, llm="openrouter/cohere/command-r"),

    # ══════════════════════════════════════════
    # Upstage Solar Mini
    # ══════════════════════════════════════════
    M("openrouter-solar-mini", "Solar Mini", ModelProvider.UPSTAGE, ModelTier.PREMIUM,
      "Upstage Solar Mini - compact enterprise LLM", ctx=32768, key="OPENROUTER_API_KEY",
      cost_in=0.0001, cost_out=0.0003, llm="openrouter/upstage/solar-mini"),

    # ══════════════════════════════════════════
    # Bedrock (AWS)
    # ══════════════════════════════════════════
    M("bedrock-claude-sonnet-4", "Claude Sonnet 4 (Bedrock)", ModelProvider.BEDROCK, ModelTier.PREMIUM,
      "AWS Bedrock Claude Sonnet 4", ctx=200000, vision=True, file=True,
      key="AWS_ACCESS_KEY_ID",
      cost_in=0.003, cost_out=0.015, llm="bedrock/anthropic.claude-sonnet-4-20250514"),

    # ══════════════════════════════════════════
    # DeepSeek (via OpenRouter)
    # ══════════════════════════════════════════
    M("openrouter-deepseek-r1", "DeepSeek R1 (OpenRouter)", ModelProvider.DEEPSEEK, ModelTier.PREMIUM,
      "DeepSeek R1 via OpenRouter", ctx=128000, key="OPENROUTER_API_KEY",
      file=True,
      cost_in=0.0005, cost_out=0.002, llm="openrouter/deepseek/deepseek-r1"),

    # ══════════════════════════════════════════
    # Mistral (via OpenRouter)
    # ══════════════════════════════════════════
    M("openrouter-mistral-large-2", "Mistral Large 2 (OpenRouter)", ModelProvider.MISTRAL, ModelTier.PREMIUM,
      "Mistral Large 2 via OpenRouter", ctx=128000, vision=True, file=True, key="OPENROUTER_API_KEY",
      cost_in=0.002, cost_out=0.006, llm="openrouter/mistral/mistral-large-2411"),
    M("openrouter-mixtral-8x22b", "Mixtral 8x22B (OpenRouter)", ModelProvider.MISTRAL, ModelTier.PREMIUM,
      "Mistral Mixtral 8x22B via OpenRouter", ctx=64000, key="OPENROUTER_API_KEY",
      cost_in=0.0009, cost_out=0.0009, llm="openrouter/mistral/mixtral-8x22b-instruct"),

    # ══════════════════════════════════════════
    # Google (via OpenRouter)
    # ══════════════════════════════════════════
    M("openrouter-gemini-2.5-pro", "Gemini 2.5 Pro (OpenRouter)", ModelProvider.GOOGLE, ModelTier.PREMIUM,
      "Google Gemini 2.5 Pro via OpenRouter", ctx=1000000, vision=True,
      file=True, audio=True, video=True, key="OPENROUTER_API_KEY",
      cost_in=0.00125, cost_out=0.005, llm="openrouter/google/gemini-2.5-pro-preview-05-06"),
    M("openrouter-gemini-2.5-flash", "Gemini 2.5 Flash (OpenRouter)", ModelProvider.GOOGLE, ModelTier.PREMIUM,
      "Google Gemini 2.5 Flash via OpenRouter", ctx=1000000, vision=True,
      file=True, audio=True, video=True, key="OPENROUTER_API_KEY",
      cost_in=0.00015, cost_out=0.0006, llm="openrouter/google/gemini-2.5-flash-preview-05-06"),

    # ══════════════════════════════════════════
    # OpenAI (via OpenRouter)
    # ══════════════════════════════════════════
    M("openrouter-gpt-4o", "GPT-4o (OpenRouter)", ModelProvider.OPENAI, ModelTier.PREMIUM,
      "OpenAI GPT-4o via OpenRouter", ctx=128000, vision=True,
      file=True, audio=True, key="OPENROUTER_API_KEY",
      cost_in=0.0025, cost_out=0.01, llm="openrouter/openai/gpt-4o"),
    M("openrouter-gpt-4o-mini", "GPT-4o Mini (OpenRouter)", ModelProvider.OPENAI, ModelTier.PREMIUM,
      "OpenAI GPT-4o Mini via OpenRouter", ctx=128000, vision=True,
      file=True, key="OPENROUTER_API_KEY",
      cost_in=0.00015, cost_out=0.0006, llm="openrouter/openai/gpt-4o-mini"),

    # ══════════════════════════════════════════
    # Anthropic (via OpenRouter)
    # ══════════════════════════════════════════
    M("openrouter-claude-sonnet-4", "Claude Sonnet 4 (OpenRouter)", ModelProvider.ANTHROPIC, ModelTier.PREMIUM,
      "Anthropic Claude Sonnet 4 via OpenRouter", ctx=200000, vision=True,
      file=True, key="OPENROUTER_API_KEY",
      cost_in=0.003, cost_out=0.015, llm="openrouter/anthropic/claude-sonnet-4-20250514"),
    M("openrouter-claude-haiku-3.5", "Claude Haiku 3.5 (OpenRouter)", ModelProvider.ANTHROPIC, ModelTier.PREMIUM,
      "Anthropic Claude Haiku 3.5 via OpenRouter", ctx=200000, vision=True,
      file=True, key="OPENROUTER_API_KEY",
      cost_in=0.0008, cost_out=0.004, llm="openrouter/anthropic/claude-3-5-haiku-20241022"),

    # ═══════════════════════════════════════════════════════════
    # HuggingFace — Llama Family
    # ═══════════════════════════════════════════════════════════
    M("hf-llama-3.1-8b", "Llama 3.1 8B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Meta Llama 3.1 8B via HuggingFace", ctx=128000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/meta-llama/Meta-Llama-3.1-8B-Instruct"),
    M("hf-llama-3.1-70b", "Llama 3.1 70B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Meta Llama 3.1 70B via HuggingFace", ctx=128000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/meta-llama/Meta-Llama-3.1-70B-Instruct"),
    M("hf-llama-3.1-405b", "Llama 3.1 405B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Meta Llama 3.1 405B via HuggingFace", ctx=128000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/meta-llama/Meta-Llama-3.1-405B-Instruct"),
    M("hf-llama-3.2-3b", "Llama 3.2 3B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Meta Llama 3.2 3B via HuggingFace", ctx=128000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/meta-llama/Llama-3.2-3B-Instruct"),
    M("hf-llama-3.2-1b", "Llama 3.2 1B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Meta Llama 3.2 1B via HuggingFace", ctx=128000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/meta-llama/Llama-3.2-1B-Instruct"),
    M("hf-llama-3.3-70b", "Llama 3.3 70B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Meta Llama 3.3 70B via HuggingFace", ctx=128000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/meta-llama/Llama-3.3-70B-Instruct"),

    # ═══════════════════════════════════════════════════════════
    # HuggingFace — Mistral Family
    # ═══════════════════════════════════════════════════════════
    M("hf-mistral-7b-v03", "Mistral 7B v0.3 (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Mistral 7B v0.3 via HuggingFace", ctx=32000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/mistralai/Mistral-7B-Instruct-v0.3"),
    M("hf-mixtral-8x7b", "Mixtral 8x7B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Mistral Mixtral 8x7B via HuggingFace", ctx=32000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/mistralai/Mixtral-8x7B-Instruct-v0.1"),
    M("hf-mixtral-8x22b", "Mixtral 8x22B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Mistral Mixtral 8x22B via HuggingFace", ctx=64000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/mistralai/Mixtral-8x22B-Instruct-v0.1"),
    M("hf-mistral-nemo", "Mistral Nemo (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Mistral Nemo 12B via HuggingFace", ctx=128000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/mistralai/Mistral-Nemo-Instruct-2407"),
    M("hf-mistral-small", "Mistral Small (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Mistral Small 22B via HuggingFace", ctx=32000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/mistralai/Mistral-Small-Instruct-2409"),
    M("hf-codestral", "Codestral (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Mistral Codestral 22B via HuggingFace", ctx=32000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/mistralai/Codestral-22B-v0.1"),

    # ═══════════════════════════════════════════════════════════
    # HuggingFace — Qwen Family
    # ═══════════════════════════════════════════════════════════
    M("hf-qwen-2.5-7b", "Qwen 2.5 7B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Qwen 2.5 7B via HuggingFace", ctx=32768, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/Qwen/Qwen2.5-7B-Instruct"),
    M("hf-qwen-2.5-14b", "Qwen 2.5 14B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Qwen 2.5 14B via HuggingFace", ctx=32768, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/Qwen/Qwen2.5-14B-Instruct"),
    M("hf-qwen-2.5-32b", "Qwen 2.5 32B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Qwen 2.5 32B via HuggingFace", ctx=32768, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/Qwen/Qwen2.5-32B-Instruct"),
    M("hf-qwen-2.5-72b", "Qwen 2.5 72B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Qwen 2.5 72B via HuggingFace", ctx=32768, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/Qwen/Qwen2.5-72B-Instruct"),
    M("hf-qwen-2.5-coder-7b", "Qwen 2.5 Coder 7B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Qwen 2.5 Coder 7B via HuggingFace", ctx=32768, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/Qwen/Qwen2.5-Coder-7B-Instruct"),
    M("hf-qwen-2.5-coder-14b", "Qwen 2.5 Coder 14B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Qwen 2.5 Coder 14B via HuggingFace", ctx=32768, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/Qwen/Qwen2.5-Coder-14B-Instruct"),
    M("hf-qwen-2.5-coder-32b", "Qwen 2.5 Coder 32B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Qwen 2.5 Coder 32B via HuggingFace", ctx=32768, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/Qwen/Qwen2.5-Coder-32B-Instruct"),
    M("hf-qwq-32b", "QwQ 32B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Qwen QwQ 32B reasoning via HuggingFace", ctx=32768, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/Qwen/QwQ-32B-Preview"),

    # ═══════════════════════════════════════════════════════════
    # HuggingFace — Google Gemma Family
    # ═══════════════════════════════════════════════════════════
    M("hf-gemma-2-2b", "Gemma 2 2B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Google Gemma 2 2B via HuggingFace", ctx=8192, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/google/gemma-2-2b-it"),
    M("hf-gemma-2-9b", "Gemma 2 9B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Google Gemma 2 9B via HuggingFace", ctx=8192, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/google/gemma-2-9b-it"),
    M("hf-gemma-2-27b", "Gemma 2 27B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Google Gemma 2 27B via HuggingFace", ctx=8192, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/google/gemma-2-27b-it"),

    # ═══════════════════════════════════════════════════════════
    # HuggingFace — Microsoft Phi Family
    # ═══════════════════════════════════════════════════════════
    M("hf-phi-4", "Phi-4 14B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Microsoft Phi-4 14B via HuggingFace", ctx=128000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/microsoft/Phi-4-mini-instruct"),
    M("hf-phi-3.5-mini", "Phi-3.5 Mini (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Microsoft Phi-3.5 Mini 3.8B via HuggingFace", ctx=128000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/microsoft/Phi-3.5-mini-instruct"),
    M("hf-phi-3.5-moe", "Phi-3.5 MoE (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Microsoft Phi-3.5 MoE 6.6B via HuggingFace", ctx=128000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/microsoft/Phi-3.5-MoE-instruct"),

    # ═══════════════════════════════════════════════════════════
    # HuggingFace — DeepSeek Family
    # ═══════════════════════════════════════════════════════════
    M("hf-deepseek-v3", "DeepSeek V3 (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "DeepSeek V3 via HuggingFace", ctx=128000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/deepseek-ai/DeepSeek-V3"),
    M("hf-deepseek-r1", "DeepSeek R1 (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "DeepSeek R1 via HuggingFace", ctx=128000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/deepseek-ai/DeepSeek-R1"),
    M("hf-deepseek-r1-distill-llama-8b", "DeepSeek R1 Distill Llama 8B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "DeepSeek R1 distilled into Llama 3.1 8B via HuggingFace", ctx=128000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/deepseek-ai/DeepSeek-R1-Distill-Llama-8B"),
    M("hf-deepseek-r1-distill-qwen-7b", "DeepSeek R1 Distill Qwen 7B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "DeepSeek R1 distilled into Qwen 2.5 7B via HuggingFace", ctx=32768, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"),
    M("hf-deepseek-r1-distill-qwen-14b", "DeepSeek R1 Distill Qwen 14B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "DeepSeek R1 distilled into Qwen 2.5 14B via HuggingFace", ctx=32768, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"),
    M("hf-deepseek-r1-distill-qwen-32b", "DeepSeek R1 Distill Qwen 32B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "DeepSeek R1 distilled into Qwen 2.5 32B via HuggingFace", ctx=32768, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"),
    M("hf-deepseek-coder-v2", "DeepSeek Coder V2 (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "DeepSeek Coder V2 16B via HuggingFace", ctx=128000, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/deepseek-ai/DeepSeek-Coder-V2-Instruct"),

    # ═══════════════════════════════════════════════════════════
    # HuggingFace — Code Models (CodeLlama, StarCoder)
    # ═══════════════════════════════════════════════════════════
    M("hf-codellama-7b", "CodeLlama 7B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Meta CodeLlama 7B via HuggingFace", ctx=16384, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/codellama/CodeLlama-7b-Instruct-hf"),
    M("hf-codellama-13b", "CodeLlama 13B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Meta CodeLlama 13B via HuggingFace", ctx=16384, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/codellama/CodeLlama-13b-Instruct-hf"),
    M("hf-codellama-34b", "CodeLlama 34B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Meta CodeLlama 34B via HuggingFace", ctx=16384, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/codellama/CodeLlama-34b-Instruct-hf"),
    M("hf-starcoder2-7b", "StarCoder2 7B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "StarCoder2 7B via HuggingFace", ctx=16384, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/bigcode/starcoder2-7b-instruct-v0.1"),
    M("hf-starcoder2-15b", "StarCoder2 15B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "StarCoder2 15B via HuggingFace", ctx=16384, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/bigcode/starcoder2-15b-instruct-v0.1"),

    # ═══════════════════════════════════════════════════════════
    # HuggingFace — Math & Reasoning
    # ═══════════════════════════════════════════════════════════
    M("hf-qwen2.5-math-7b", "Qwen 2.5 Math 7B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Qwen 2.5 Math 7B via HuggingFace", ctx=32768, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/Qwen/Qwen2.5-Math-7B-Instruct"),
    M("hf-qwen2.5-math-72b", "Qwen 2.5 Math 72B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Qwen 2.5 Math 72B via HuggingFace", ctx=32768, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/Qwen/Qwen2.5-Math-72B-Instruct"),

    # ═══════════════════════════════════════════════════════════
    # HuggingFace — Multilingual / Small
    # ═══════════════════════════════════════════════════════════
    M("hf-aya-23-8b", "Aya 23 8B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Cohere Aya 23 8B multilingual via HuggingFace", ctx=8192, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/CohereForAI/aya-23-8B"),
    M("hf-aya-23-35b", "Aya 23 35B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "Cohere Aya 23 35B multilingual via HuggingFace", ctx=8192, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/CohereForAI/aya-23-35B"),
    M("hf-bloom-7b", "BLOOM 7B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "BigScience BLOOM 7B multilingual via HuggingFace", ctx=2048, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/bigscience/bloom-7b1"),
    M("hf-tinyllama-1.1b", "TinyLlama 1.1B (HF)", ModelProvider.HUGGINGFACE, ModelTier.PREMIUM,
      "TinyLlama 1.1B small model via HuggingFace", ctx=2048, key="HUGGINGFACE_API_KEY",
      cost_in=0.0, cost_out=0.0, llm="huggingface/TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
]

ALL_MODELS: list[ModelConfig] = FREE_MODELS + PREMIUM_MODELS
MODELS_BY_ID: dict[str, ModelConfig] = {m.id: m for m in ALL_MODELS}


class ModelRegistry:
    """Runtime-switchable model registry with LiteLLM backend."""

    def __init__(self):
        self._active_model_id: str = self._get_default_model()
        self._active_tier: ModelTier = ModelTier.FREE
        self._available_models: dict[str, ModelConfig] = dict(MODELS_BY_ID)
        logger.info(f"ModelRegistry initialized with {len(self._available_models)} models")

    def _get_default_model(self) -> str:
        for model_id in ["groq-llama3.1-8b", "openai-gpt-4o-mini", "ollama-llama3.1-8b"]:
            mc = MODELS_BY_ID.get(model_id)
            if mc and self._check_api_key(mc):
                return model_id
        return "ollama-llama3.1-8b"

    def _check_api_key(self, mc: ModelConfig) -> bool:
        if mc.api_key_env:
            return bool(os.environ.get(mc.api_key_env))
        return mc.provider == ModelProvider.OLLAMA

    def get_active_model(self) -> ModelConfig:
        return self._available_models.get(self._active_model_id, MODELS_BY_ID["ollama-llama3.1-8b"])

    def set_active_model(self, model_id: str) -> bool:
        if model_id in self._available_models:
            self._active_model_id = model_id
            mc = self._available_models[model_id]
            self._active_tier = mc.tier
            logger.info(f"Active model switched to: {mc.name} ({mc.provider.value})")
            return True
        logger.warning(f"Model {model_id} not found")
        return False

    def set_active_tier(self, tier: ModelTier) -> None:
        if isinstance(tier, str):
            tier = ModelTier(tier.lower())
        self._active_tier = tier
        models = FREE_MODELS if tier == ModelTier.FREE else PREMIUM_MODELS
        if models:
            self._active_model_id = models[0].id
            logger.info(f"Switched to {tier.value} tier: {models[0].name}")

    def get_models_by_tier(self, tier: ModelTier) -> list[ModelConfig]:
        if isinstance(tier, str):
            tier = ModelTier(tier.lower())
        return [m for m in ALL_MODELS if m.tier == tier]

    def get_all_models(self) -> list[ModelConfig]:
        return list(ALL_MODELS)

    def get_available_models(self) -> list[ModelConfig]:
        return [m for m in ALL_MODELS if self._check_api_key(m)]

    def get_active_tier(self) -> ModelTier:
        return self._active_tier


_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
