"""LLM service with LiteLLM, runtime model switching, and streaming."""

import json
import logging
from typing import Optional, AsyncGenerator

from .model_registry import ModelRegistry, get_model_registry, ModelConfig

logger = logging.getLogger(__name__)


class LLMService:
    """LLM service using LiteLLM for unified multi-provider access with runtime model switching."""

    def __init__(self, registry: Optional[ModelRegistry] = None):
        self.registry = registry or get_model_registry()

    def get_active_config(self) -> ModelConfig:
        return self.registry.get_active_model()

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
        model_id: Optional[str] = None,
    ) -> str:
        model_cfg = self.registry._available_models.get(model_id) if model_id else self.registry.get_active_model()
        litellm_model = model_cfg.litellm_model
        temp = temperature if temperature is not None else model_cfg.default_temperature

        try:
            from litellm import acompletion
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await acompletion(
                model=litellm_model,
                messages=messages,
                temperature=temp,
                max_tokens=min(max_tokens, model_cfg.max_tokens),
            )
            return response.choices[0].message.content
        except ImportError:
            logger.warning("litellm not installed, falling back to direct provider")
            return await self._fallback_generate(prompt, system_prompt, temperature, max_tokens, model_cfg)
        except Exception as e:
            logger.error(f"LiteLLM generation failed: {e}")
            return f"[{model_cfg.name}] Mock response for: {prompt[:100]}..."

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
        model_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        model_cfg = self.registry._available_models.get(model_id) if model_id else self.registry.get_active_model()
        litellm_model = model_cfg.litellm_model
        temp = temperature if temperature is not None else model_cfg.default_temperature

        try:
            from litellm import acompletion
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await acompletion(
                model=litellm_model,
                messages=messages,
                temperature=temp,
                max_tokens=min(max_tokens, model_cfg.max_tokens),
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except ImportError:
            yield "LiteLLM not installed. Install with: pip install litellm"
        except Exception as e:
            logger.error(f"LiteLLM streaming failed: {e}")
            yield f"[Error] {e}"

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> dict:
        sp = (system_prompt or "") + "\nRespond ONLY with valid JSON. No explanation."
        result = await self.generate(
            prompt,
            system_prompt=sp,
            temperature=0.1,
            max_tokens=4096,
            model_id=model_id,
        )
        match = __import__("re").search(r'(\{.*\}|\[.*\])', result, __import__("re").DOTALL)
        if match and match.group(1).strip().startswith(("{", "[")):
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return {"raw": result}

    async def _fallback_generate(self, prompt, system_prompt, temperature, max_tokens, model_cfg):
        provider = model_cfg.provider.value
        if provider == "openai":
            from openai import OpenAI
            import os
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model=model_cfg.id.replace("openai-", "").replace("-", "."),
                messages=messages,
                temperature=temperature or model_cfg.default_temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        elif provider == "anthropic":
            import anthropic
            import os
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            kwargs = {
                "model": model_cfg.id.replace("anthropic-", "").replace("-", "."),
                "max_tokens": max_tokens,
                "temperature": temperature or model_cfg.default_temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                kwargs["system"] = system_prompt
            response = client.messages.create(**kwargs)
            return response.content[0].text
        else:
            return f"[{model_cfg.name}] Mock response for: {prompt[:100]}..."
