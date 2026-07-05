"""
ChitraGupta 2.0 — EngineShifter Utility
Multi-provider LLM routing with automatic failover.

Provider order (per role):
  CHAT:    Groq → OpenRouter → Cloudflare → Gemini
  MEMORY:  OpenRouter → Groq → Gemini
  SHADOW:  Cerebras → Groq → OpenRouter
  PROFILER: Mistral → Groq → OpenRouter
  FALLBACK: Cloudflare → Groq → OpenRouter
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Type

from pydantic import BaseModel

# --- Load .env with override so file values win over stale env vars ---
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from core.utils.json_parser import extract_and_validate_json, build_retry_prompt

# ---------------------------------------------------------------------------
# LangChain provider imports (graceful — missing packages log, don't crash)
# ---------------------------------------------------------------------------

_langchain_providers: dict[str, Any] = {}

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    _langchain_providers["google"] = ChatGoogleGenerativeAI
except ImportError:
    pass

try:
    from langchain_groq import ChatGroq
    _langchain_providers["groq"] = ChatGroq
except ImportError:
    pass

try:
    from langchain_mistralai import ChatMistralAI
    _langchain_providers["mistral"] = ChatMistralAI
except ImportError:
    pass

try:
    from langchain_openai import ChatOpenAI
    _langchain_providers["openai"] = ChatOpenAI
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("chitragupta.engine_shifter")

# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------


class AllProvidersExhaustedError(Exception):
    """Raised when every provider in the fallback chain has failed."""
    pass


# ---------------------------------------------------------------------------
# Role Enum
# ---------------------------------------------------------------------------


class ProviderRole(str, Enum):
    PROFILER = "profiler"
    MEMORY = "memory"
    CHAT = "chat"
    SHADOW = "shadow"
    FALLBACK = "fallback"


# ---------------------------------------------------------------------------
# Provider Config
# ---------------------------------------------------------------------------

REQUEST_TIMEOUT = 12  # seconds


class ProviderConfig:
    """Immutable configuration for a single LLM provider binding."""

    __slots__ = (
        "provider", "model", "api_key_env", "base_url",
        "temperature", "max_tokens", "timeout",
    )

    def __init__(
        self,
        provider: str,
        model: str,
        api_key_env: str,
        base_url: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = REQUEST_TIMEOUT,
    ):
        self.provider = provider
        self.model = model
        self.api_key_env = api_key_env
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def __repr__(self) -> str:
        return f"ProviderConfig({self.provider}/{self.model})"


# ---------------------------------------------------------------------------
# Provider Registry — ordered primary → fallbacks
# Only verified live model IDs.
# ---------------------------------------------------------------------------

_CLOUDFLARE_ACCOUNT_ID_DEFAULT = "8d25d8bab921d21ed4d001993fa67b11"
_CLOUDFLARE_GATEWAY_ID_DEFAULT = "8d25d8bab921d21ed4d001993fa67b11"

PROVIDER_CHAINS: dict[ProviderRole, list[ProviderConfig]] = {
    # CHAT: Groq → OpenRouter → Cloudflare → Gemini
    ProviderRole.CHAT: [
        ProviderConfig(
            provider="groq",
            model="llama-3.1-8b-instant",
            api_key_env="GROQ_API_KEY",
            temperature=0.7,
            max_tokens=2048,
        ),
        ProviderConfig(
            provider="openrouter",
            model="meta-llama/llama-3.1-8b-instruct",
            api_key_env="OPENROUTER_API_KEY",
            base_url="https://openrouter.ai/api/v1",
            temperature=0.7,
            max_tokens=2048,
        ),
        ProviderConfig(
            provider="cloudflare",
            model="@cf/meta/llama-3.3-8b-instruct",
            api_key_env="CLOUDFLARE_API_TOKEN",
            base_url=None,  # built dynamically
            temperature=0.7,
            max_tokens=2048,
        ),
        ProviderConfig(
            provider="google",
            model="gemini-2.0-flash",
            api_key_env="GOOGLE_API_KEY",
            temperature=0.7,
            max_tokens=2048,
        ),
    ],
    # MEMORY: OpenRouter → Groq → Gemini
    ProviderRole.MEMORY: [
        ProviderConfig(
            provider="openrouter",
            model="meta-llama/llama-3.1-8b-instruct",
            api_key_env="OPENROUTER_API_KEY",
            base_url="https://openrouter.ai/api/v1",
            temperature=0.2,
            max_tokens=1024,
        ),
        ProviderConfig(
            provider="groq",
            model="llama-3.1-8b-instant",
            api_key_env="GROQ_API_KEY",
            temperature=0.2,
            max_tokens=1024,
        ),
        ProviderConfig(
            provider="google",
            model="gemini-2.0-flash",
            api_key_env="GOOGLE_API_KEY",
            temperature=0.2,
            max_tokens=1024,
        ),
    ],
    # SHADOW: Cerebras → Groq → OpenRouter
    ProviderRole.SHADOW: [
    ProviderConfig(
        provider="cerebras",
        model="llama3.1-8b",
        api_key_env="CEREBRAS_API_KEY",
        base_url="https://api.cerebras.ai/v1",
        temperature=0.5,
        max_tokens=1024,
    ),
        ProviderConfig(
            provider="groq",
            model="llama-3.1-8b-instant",
            api_key_env="GROQ_API_KEY",
            temperature=0.5,
            max_tokens=1024,
        ),
        ProviderConfig(
            provider="openrouter",
            model="meta-llama/llama-3.1-8b-instruct",
            api_key_env="OPENROUTER_API_KEY",
            base_url="https://openrouter.ai/api/v1",
            temperature=0.5,
            max_tokens=1024,
        ),
    ],
    # PROFILER: Mistral → Groq → OpenRouter
    ProviderRole.PROFILER: [
        ProviderConfig(
            provider="mistral",
            model="mistral-small-latest",
            api_key_env="MISTRAL_API_KEY",
            temperature=0.3,
            max_tokens=512,
        ),
        ProviderConfig(
            provider="groq",
            model="llama-3.1-8b-instant",
            api_key_env="GROQ_API_KEY",
            temperature=0.3,
            max_tokens=512,
        ),
        ProviderConfig(
            provider="openrouter",
            model="meta-llama/llama-3.1-8b-instruct",
            api_key_env="OPENROUTER_API_KEY",
            base_url="https://openrouter.ai/api/v1",
            temperature=0.3,
            max_tokens=512,
        ),
    ],
    # FALLBACK: Cloudflare → Groq → OpenRouter
    ProviderRole.FALLBACK: [
        ProviderConfig(
            provider="cloudflare",
            model="@cf/meta/llama-3.3-8b-instruct",
            api_key_env="CLOUDFLARE_API_TOKEN",
            base_url=None,  # built dynamically
            temperature=0.5,
            max_tokens=512,
        ),
        ProviderConfig(
            provider="groq",
            model="llama-3.1-8b-instant",
            api_key_env="GROQ_API_KEY",
            temperature=0.5,
            max_tokens=512,
        ),
        ProviderConfig(
            provider="openrouter",
            model="meta-llama/llama-3.1-8b-instruct",
            api_key_env="OPENROUTER_API_KEY",
            base_url="https://openrouter.ai/api/v1",
            temperature=0.5,
            max_tokens=512,
        ),
    ],
}


# ---------------------------------------------------------------------------
# Provider Runtime Audit — per-invocation observability
# ---------------------------------------------------------------------------


def _extract_token_usage(raw_result: Any) -> dict[str, Any]:
    """Extract token usage from a LangChain LLM response (AIMessage).

    Checks multiple locations where providers embed usage metadata:
    - response_metadata.token_usage / usage
    - usage_metadata (OpenAI-compatible)
    - .usage_metadata (LangChain standard)

    Returns dict with input_tokens, output_tokens, total_tokens, estimated.
    Never crashes — returns zeros with estimated=True on any failure.
    """
    estimated = False
    input_tokens = 0
    output_tokens = 0

    try:
        # 1) Try response_metadata → token_usage (Groq, some OpenAI-compatible)
        resp_meta = getattr(raw_result, "response_metadata", None) or {}
        if isinstance(resp_meta, dict):
            # Some providers use "token_usage", others "usage"
            usage = resp_meta.get("token_usage") or resp_meta.get("usage") or {}
            if isinstance(usage, dict):
                input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
                output_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or usage.get("completion_tokens_details") or 0
                # Handle nested completion_tokens_details
                if isinstance(output_tokens, dict):
                    output_tokens = 0

        # 2) Try usage_metadata (OpenAI / LangChain standard)
        usage_meta = getattr(raw_result, "usage_metadata", None)
        if isinstance(usage_meta, dict):
            input_tokens = input_tokens or usage_meta.get("input_tokens") or 0
            output_tokens = output_tokens or usage_meta.get("output_tokens") or 0

    except Exception:
        estimated = True

    total_tokens = input_tokens + output_tokens

    # If zero tokens found, estimate from content length
    if total_tokens == 0:
        estimated = True
        # Rough estimate: ~4 chars per token
        content_str = ""
        content = getattr(raw_result, "content", None)
        if content and isinstance(content, str):
            content_str = content
        elif content and isinstance(content, list):
            # Some providers return list of content blocks
            for block in content:
                if isinstance(block, dict):
                    content_str += block.get("text", "")
                elif isinstance(block, str):
                    content_str += block
        output_tokens = max(1, len(content_str) // 4) if content_str else 0
        input_tokens = 0  # Can't estimate input without messages

    total_tokens = input_tokens + output_tokens
    if total_tokens == 0:
        estimated = True

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated": estimated,
    }


class ProviderRuntimeRecord:
    """Record of a single provider invocation for runtime audit."""

    __slots__ = (
        "role", "provider", "model", "base_url",
        "structured_output_mode", "http_status", "latency_ms",
        "finish_reason", "fallback_depth", "request_success",
        "error_type", "timestamp", "failover_chain",
        "input_tokens", "output_tokens", "total_tokens", "tokens_estimated",
    )

    def __init__(
        self,
        role: str,
        provider: str,
        model: str,
        base_url: str,
        structured_output_mode: str,
        http_status: int | None,
        latency_ms: float,
        finish_reason: str,
        fallback_depth: int,
        request_success: bool,
        error_type: str | None = None,
        failover_chain: list[str] | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        tokens_estimated: bool = False,
    ):
        self.role = role
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.structured_output_mode = structured_output_mode
        self.http_status = http_status
        self.latency_ms = latency_ms
        self.finish_reason = finish_reason
        self.fallback_depth = fallback_depth
        self.request_success = request_success
        self.error_type = error_type
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.failover_chain = failover_chain or []
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
        self.tokens_estimated = tokens_estimated

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "structured_output_mode": self.structured_output_mode,
            "http_status": self.http_status,
            "latency_ms": round(self.latency_ms, 1),
            "finish_reason": self.finish_reason,
            "fallback_depth": self.fallback_depth,
            "request_success": self.request_success,
            "error_type": self.error_type,
            "timestamp": self.timestamp,
            "failover_chain": self.failover_chain,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "tokens_estimated": self.tokens_estimated,
        }


# Per-role latest runtime record
_runtime_audit: dict[str, ProviderRuntimeRecord] = {}

# Role name mapping for display
_ROLE_DISPLAY = {
    "profiler": "PROFILER",
    "memory": "MEMORY",
    "chat": "CHAT",
    "shadow": "SHADOW",
    "fallback": "MICRO",
}


def _record_runtime(
    role: ProviderRole,
    config: ProviderConfig,
    latency_ms: float,
    is_structured: bool,
    fallback_depth: int,
    success: bool,
    http_status: int | None = None,
    error_type: str | None = None,
    failover_chain: list[str] | None = None,
    raw_result: Any = None,
) -> None:
    """Record a provider invocation result into the runtime audit."""
    provider = config.provider
    use_native = is_structured and provider in _NATIVE_JSON_MODE_PROVIDERS
    structured_mode = "native" if use_native else ("parser" if is_structured else "n/a")

    # Resolve effective base_url
    base_url = config.base_url or ""
    if provider == "cloudflare":
        account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", _CLOUDFLARE_ACCOUNT_ID_DEFAULT)
        gateway_id = os.environ.get("CLOUDFLARE_GATEWAY_ID", _CLOUDFLARE_GATEWAY_ID_DEFAULT)
        if gateway_id and gateway_id != account_id:
            base_url = f"gateway.ai.cloudflare.com/.../{gateway_id}"
        else:
            base_url = "api.cloudflare.com/.../ai/v1"

    finish_reason = "success" if success else (error_type or "error")

    # Extract token usage from raw LLM result if available
    token_info = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "estimated": True}
    if success and raw_result is not None:
        try:
            token_info = _extract_token_usage(raw_result)
        except Exception:
            token_info = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "estimated": True}

    record = ProviderRuntimeRecord(
        role=role.value,
        provider=provider,
        model=config.model,
        base_url=base_url,
        structured_output_mode=structured_mode,
        http_status=http_status if success else http_status,
        latency_ms=latency_ms,
        finish_reason=finish_reason,
        fallback_depth=fallback_depth,
        request_success=success,
        error_type=error_type,
        failover_chain=failover_chain or [],
        input_tokens=token_info["input_tokens"],
        output_tokens=token_info["output_tokens"],
        total_tokens=token_info["total_tokens"],
        tokens_estimated=token_info["estimated"],
    )
    _runtime_audit[role.value] = record

    # Print one console line after every successful invocation
    if success:
        _print_runtime_line(record)


def _print_runtime_line(record: ProviderRuntimeRecord) -> None:
    """Print ONE console line after a successful provider invocation."""
    display_role = _ROLE_DISPLAY.get(record.role, record.role.upper())
    fallback_str = "no" if record.fallback_depth == 0 else f"yes({record.provider})"
    latency_str = f"{round(record.latency_ms)}ms"
    structured_str = record.structured_output_mode.capitalize()
    est = "~" if record.tokens_estimated else ""
    tokens_str = f"{est}{record.input_tokens}/{est}{record.output_tokens}/{est}{record.total_tokens}"

    logger.info(
        f"{display_role} | {record.provider} | {record.model} | "
        f"tokens({tokens_str}) | {latency_str} | {structured_str} | fallback={fallback_str}"
    )


def get_runtime_audit() -> dict[str, dict[str, Any]]:
    """Return the latest runtime audit record per role as dicts."""
    result = {}
    for role_key in ("profiler", "memory", "chat", "shadow", "fallback"):
        record = _runtime_audit.get(role_key)
        if record:
            result[role_key] = record.to_dict()
        else:
            result[role_key] = {
                "provider": None,
                "model": None,
                "latency_ms": None,
                "structured_output": None,
                "http_status": None,
                "fallback_count": None,
                "last_error": None,
                "last_updated": None,
            }
    return result


def get_token_audit() -> dict[str, dict[str, Any]]:
    """Return per-role token usage from the latest runtime audit records."""
    result = {}
    for role_key in ("profiler", "memory", "chat", "shadow", "fallback"):
        record = _runtime_audit.get(role_key)
        if record:
            result[role_key] = {
                "provider": record.provider,
                "model": record.model,
                "structured_output_mode": record.structured_output_mode,
                "input_tokens": record.input_tokens,
                "output_tokens": record.output_tokens,
                "total_tokens": record.total_tokens,
                "estimated": record.tokens_estimated,
                "latency_ms": round(record.latency_ms, 1),
                "http_status": record.http_status,
                "fallback_depth": record.fallback_depth,
                "last_error": record.error_type,
                "last_updated": record.timestamp,
            }
        else:
            result[role_key] = {
                "provider": None,
                "model": None,
                "structured_output_mode": None,
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
                "estimated": None,
                "latency_ms": None,
                "http_status": None,
                "fallback_depth": None,
                "last_error": None,
                "last_updated": None,
            }
    return result


def print_runtime_provider_report() -> str:
    """Print a clean runtime provider table with token accounting.

    ROLE | PROVIDER | MODEL | TOKENS(IN/OUT/TOTAL) | LATENCY | MODE | FALLBACK
    """
    header = f"{'ROLE':<10s} | {'PROVIDER':<14s} | {'MODEL':<28s} | {'TOKENS(IN/OUT/TOTAL)':<22s} | {'LATENCY':<10s} | {'MODE':<8s} | {'FALLBACK'}"
    sep = "-" * len(header)
    lines = [header, sep]

    for role_key in ("profiler", "memory", "chat", "shadow", "fallback"):
        record = _runtime_audit.get(role_key)
        display_role = _ROLE_DISPLAY.get(role_key, role_key.upper())

        if record:
            provider = record.provider
            model = record.model if len(record.model) <= 27 else record.model[:24] + "..."
            est = "~" if record.tokens_estimated else ""
            tokens = f"{est}{record.input_tokens}/{est}{record.output_tokens}/{est}{record.total_tokens}"
            latency = f"{round(record.latency_ms)}ms"
            mode = record.structured_output_mode.capitalize()
            fallback = "No" if record.fallback_depth == 0 else f"Yes(depth={record.fallback_depth})"
        else:
            provider = "-"
            model = "-"
            tokens = "-"
            latency = "-"
            mode = "-"
            fallback = "-"

        lines.append(f"{display_role:<10s} | {provider:<14s} | {model:<28s} | {tokens:<22s} | {latency:<10s} | {mode:<8s} | {fallback}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Provider Health Tracking — enhanced with model, latency, HTTP, last failure
# ---------------------------------------------------------------------------

_provider_health: dict[str, dict[str, Any]] = {}


def _init_health(provider: str) -> None:
    """Initialize health entry for a provider if not present."""
    if provider not in _provider_health:
        _provider_health[provider] = {
            "status": "NOT_SELECTED",
            "model": "",
            "latency_ms": None,
            "http_status": None,
            "last_failure": None,
        }


def _record_success(provider: str, model: str, latency_ms: float) -> None:
    _init_health(provider)
    _provider_health[provider] = {
        "status": "OK",
        "model": model,
        "latency_ms": round(latency_ms, 1),
        "http_status": 200,
        "last_failure": None,
    }


def _record_failure(provider: str, model: str, status: str, http_status: Any, reason: str) -> None:
    _init_health(provider)
    prev = _provider_health[provider]
    _provider_health[provider] = {
        "status": status,
        "model": model or prev.get("model", ""),
        "latency_ms": prev.get("latency_ms"),
        "http_status": http_status,
        "last_failure": reason,
    }


def get_provider_health() -> dict[str, dict[str, Any]]:
    """Return a snapshot of provider health statuses with full diagnostics."""
    all_providers = ["groq", "google", "cerebras", "mistral", "openrouter", "cloudflare"]
    result = {}
    for p in all_providers:
        _init_health(p)
        result[p] = dict(_provider_health[p])
    return result


def print_provider_health() -> str:
    """Format provider health as a one-line-per-provider table."""
    all_providers = ["groq", "google", "cerebras", "mistral", "openrouter", "cloudflare"]
    lines = []
    for p in all_providers:
        _init_health(p)
        h = _provider_health[p]
        status = h["status"]
        model = h.get("model", "")
        latency = f"{h['latency_ms']}ms" if h.get("latency_ms") is not None else "-"
        http = str(h.get("http_status", "-"))
        fail = h.get("last_failure") or "-"
        lines.append(f"{p:12s} {status:20s} model={model:30s} latency={latency:8s} HTTP={http:5s} last_fail={fail}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM Instance Cache — initialize once, reuse across requests
# ---------------------------------------------------------------------------

_llm_cache: dict[str, Any] = {}


def _cache_key(config: ProviderConfig) -> str:
    return f"{config.provider}|{config.model}|{config.api_key_env}|{config.base_url or ''}"


# Providers that support native JSON mode via response_format
_NATIVE_JSON_MODE_PROVIDERS = {"groq", "mistral", "openrouter", "cerebras", "cloudflare"}


def _build_llm(config: ProviderConfig, json_mode: bool = False) -> Any:
    """Instantiate a LangChain chat model from a ProviderConfig. Cached.

    Parameters
    ----------
    config : ProviderConfig
        Provider configuration.
    json_mode : bool
        If True and the provider supports it, enable native JSON output mode
        (response_format={"type": "json_object"}) so the model is forced
        to emit valid JSON. Falls back to plain text if provider doesn't
        support it.
    """
    # Cache key includes json_mode flag so we don't reuse a plain LLM for JSON mode
    key = _cache_key(config) + ("|json" if json_mode else "")
    if key in _llm_cache:
        return _llm_cache[key]

    # Resolve API key — support CLOUDFLARE_API_TOKEN aliasing to CLOUDFLARE_API_KEY
    api_key = os.environ.get(config.api_key_env, "")
    if not api_key and config.api_key_env == "CLOUDFLARE_API_TOKEN":
        api_key = os.environ.get("CLOUDFLARE_API_KEY", "")
    if not api_key:
        raise ValueError(f"Missing API key: {config.api_key_env}")

    # Disable forced JSON mode to prevent Langchain warnings
    use_json_mode = False

    llm = None

    if config.provider == "google":
        cls = _langchain_providers.get("google")
        if cls is None:
            raise ImportError("langchain-google-genai not installed")
        # Google does not reliably support response_format — skip json_mode
        llm = cls(
            model=config.model,
            google_api_key=api_key,
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
            request_timeout=config.timeout,
            max_retries=0,
        )

    elif config.provider == "groq":
        cls = _langchain_providers.get("groq")
        if cls is None:
            raise ImportError("langchain-groq not installed")
        kwargs: dict[str, Any] = dict(
            model=config.model,
            groq_api_key=api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            request_timeout=config.timeout,
        )
        if use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        llm = cls(**kwargs)

    elif config.provider == "mistral":
        cls = _langchain_providers.get("mistral")
        if cls is None:
            raise ImportError("langchain-mistralai not installed")
        kwargs = dict(
            model=config.model,
            api_key=api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        if use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        llm = cls(**kwargs)

    elif config.provider == "openrouter":
        cls = _langchain_providers.get("openai")
        if cls is None:
            raise ImportError("langchain-openai not installed")
        kwargs = dict(
            model=config.model,
            openai_api_key=api_key,
            base_url=config.base_url or "https://openrouter.ai/api/v1",
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            request_timeout=config.timeout,
            default_headers={"HTTP-Referer": "https://chitragupta.ai"},
        )
        if use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        llm = cls(**kwargs)

    elif config.provider == "cerebras":
        cls = _langchain_providers.get("openai")
        if cls is None:
            raise ImportError("langchain-openai not installed")
        kwargs = dict(
            model=config.model,
            openai_api_key=api_key,
            base_url=config.base_url or "https://api.cerebras.ai/v1",
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            request_timeout=config.timeout,
        )
        if use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        llm = cls(**kwargs)

    elif config.provider == "cloudflare":
        cls = _langchain_providers.get("openai")
        if cls is None:
            raise ImportError("langchain-openai not installed")
        # Auto-detect Cloudflare IDs from env, fallback to hardcoded defaults
        account_id = os.environ.get(
            "CLOUDFLARE_ACCOUNT_ID",
            _CLOUDFLARE_ACCOUNT_ID_DEFAULT,
        )
        gateway_id = os.environ.get(
            "CLOUDFLARE_GATEWAY_ID",
            _CLOUDFLARE_GATEWAY_ID_DEFAULT,
        )
        # Auto-detect: AI Gateway only if gateway_id differs from account_id
        # Same value = not a real gateway, use Workers AI direct
        if gateway_id and gateway_id != account_id:
            cf_base_url = f"https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/workers-ai"
        else:
            # Workers AI mode (direct)
            cf_base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"
        _init_health("cloudflare")
        _provider_health["cloudflare"]["model"] = config.model
        kwargs = dict(
            model=config.model,
            openai_api_key=api_key,
            base_url=cf_base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            request_timeout=config.timeout,
        )
        if use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        llm = cls(**kwargs)

    else:
        raise ValueError(f"Unknown provider: {config.provider}")

    _llm_cache[key] = llm
    return llm


def _clear_llm_cache() -> None:
    _llm_cache.clear()


# ---------------------------------------------------------------------------
# Error Classification
# ---------------------------------------------------------------------------


def _is_skipable_error(exc: Exception) -> bool:
    """Return True for errors that should immediately skip to next provider.

    400/401/403/404/429 → skip. Also catches gRPC/Google SDK quota errors.
    ImportError for missing packages or env config → skip.
    """
    status_code = getattr(exc, "status_code", None)
    if status_code in (400, 401, 403, 404, 429):
        return True
    grpc_code = getattr(exc, "code", None)
    if grpc_code is not None and str(grpc_code) in (
        "StatusCode.RESOURCE_EXHAUSTED", "RESOURCE_EXHAUSTED", "429",
    ):
        return True
    error_str = str(exc).lower()
    if "400" in error_str or "invalid" in error_str:
        return True
    if "401" in error_str or "unauthorized" in error_str:
        return True
    if "403" in error_str or "forbidden" in error_str:
        return True
    if "404" in error_str or "not_found" in error_str or "model not found" in error_str:
        return True
    if "no endpoints found" in error_str:
        return True
    if "resource_exhausted" in error_str:
        return True
    if "queue_exceeded" in error_str:
        return True
    if "quota" in error_str and "exceeded" in error_str:
        return True
    if "limit: 0" in error_str or "limit:0" in error_str:
        return True
    if isinstance(exc, ImportError):
        return True
    return False


def _is_rate_limit_error(exc: BaseException) -> bool:
    """Check if an exception is specifically a 429 rate-limit error."""
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True
    error_str = str(exc).lower()
    return "rate_limit" in error_str or "429" in error_str or "resource_exhausted" in error_str


def _is_timeout_error(exc: BaseException) -> bool:
    """Check if an exception is a timeout error."""
    import httpx
    if isinstance(exc, (httpx.TimeoutException, TimeoutError, asyncio.TimeoutError)):
        return True
    error_str = str(exc).lower()
    return "timeout" in error_str or "timed out" in error_str


def _classify_error(exc: Exception) -> tuple[str, Any]:
    """Return (health_status, http_status) for provider health tracking."""
    http_status = getattr(exc, "status_code", None)
    if _is_rate_limit_error(exc):
        return "QUOTA", http_status or 429
    if isinstance(exc, ImportError) and "CLOUDFLARE" in str(exc):
        return "ACCOUNT_CONFIG_ERROR", None
    if isinstance(exc, ImportError) and "ACCOUNT_ID" in str(exc):
        return "ACCOUNT_ID_MISSING", None
    if _is_skipable_error(exc):
        return "SKIP", http_status
    return "ERROR", http_status


# ---------------------------------------------------------------------------
# Core Invocation with Fallback
# ---------------------------------------------------------------------------


def _is_default_result(result: BaseModel) -> bool:
    """Check if a Pydantic model instance is all-default (i.e., parse failed silently)."""
    try:
        return result == type(result)()
    except Exception:
        return False


def _single_provider_invoke(
    role: ProviderRole,
    config: ProviderConfig,
    messages: list[dict],
    json_mode: bool = False,
    **kwargs: Any,
) -> Any:
    """Invoke a single LLM provider. No retry logic here — handled by caller.

    Parameters
    ----------
    json_mode : bool
        If True, build the LLM with native JSON output mode enabled.
    """
    llm = _build_llm(config, json_mode=json_mode)
    return llm.invoke(messages, **kwargs)


def _invoke_chain(role: ProviderRole, messages: list[dict], parse_schema: Type[BaseModel] | None = None, **kwargs: Any) -> Any:
    """
    Walk the provider chain for a role. On skipable errors, fall through.
    On non-skipable errors, raise. Returns raw AIMessage or parsed BaseModel.

    Structured-output improvements:
    - For providers that support it, enable native JSON mode (response_format).
    - If parsing returns all-default (schema fallback), retry ONCE with a
      short enforcement prompt appended.
    - On retry failure, return schema defaults — never throw from parsing.

    - 400/401/403/404/429/ImportError → skip to next provider
    - timeout → retry ONCE on same provider (simple re-invoke), then skip
    - Max 1 retry per provider for timeout only
    """
    chain = PROVIDER_CHAINS.get(role, [])
    if not chain:
        raise ValueError(f"No provider chain configured for role: {role}")

    last_error: Exception | None = None
    is_structured = parse_schema is not None

    # Track failover chain for runtime audit
    _failed_providers: list[str] = []

    for i, config in enumerate(chain):
        for attempt in range(2):  # attempt 0 = primary, attempt 1 = timeout retry only
            start = time.monotonic()
            try:
                # Enable native JSON mode for structured output when provider supports it
                raw_result = _single_provider_invoke(
                    role, config, messages, json_mode=is_structured, **kwargs
                )
                latency_ms = (time.monotonic() - start) * 1000

                if is_structured:
                    result = extract_and_validate_json(raw_result, parse_schema)  # type: ignore[arg-type]

                    # If parse returned defaults (silent failure), retry ONCE
                    # with enforcement prompt before giving up on this provider
                    if _is_default_result(result):
                        logger.warning(
                            f"Role '{role.value}' {config.provider}/{config.model} "
                            f"parse returned defaults, retrying with enforcement..."
                        )
                        try:
                            retry_messages = messages + [
                                {"role": "assistant", "content": str(raw_result.content if hasattr(raw_result, "content") else raw_result)},
                                {"role": "user", "content": build_retry_prompt()},
                            ]
                            raw_retry = _single_provider_invoke(
                                role, config, retry_messages, json_mode=True, **kwargs
                            )
                            retry_result = extract_and_validate_json(raw_retry, parse_schema)  # type: ignore[arg-type]
                            # If retry also returned defaults, accept defaults — never throw
                            if _is_default_result(retry_result):
                                logger.warning(
                                    f"Role '{role.value}' {config.provider}/{config.model} "
                                    f"retry also returned defaults, accepting schema defaults"
                                )
                            _record_success(config.provider, config.model, latency_ms)
                            _record_runtime(role, config, latency_ms, is_structured, i, True,
                                            http_status=200, failover_chain=_failed_providers,
                                            raw_result=raw_retry)
                            if i > 0:
                                logger.info(f"Role '{role.value}' failover succeeded on {config.provider}/{config.model}")
                            return retry_result
                        except Exception as retry_exc:
                            logger.warning(
                                f"Role '{role.value}' {config.provider}/{config.model} "
                                f"parse-retry failed ({type(retry_exc).__name__}), accepting defaults"
                            )
                            _record_success(config.provider, config.model, latency_ms)
                            _record_runtime(role, config, latency_ms, is_structured, i, True,
                                            http_status=200, failover_chain=_failed_providers,
                                            raw_result=raw_result)
                            return result  # return the default result from first attempt
                else:
                    result = raw_result

                _record_success(config.provider, config.model, latency_ms)
                _record_runtime(role, config, latency_ms, is_structured, i, True,
                                http_status=200, failover_chain=_failed_providers,
                                raw_result=raw_result)
                if i > 0:
                    logger.info(f"Role '{role.value}' failover succeeded on {config.provider}/{config.model}")
                return result

            except Exception as exc:
                latency_ms = (time.monotonic() - start) * 1000
                last_error = exc
                health_status, http_status = _classify_error(exc)
                _record_failure(config.provider, config.model, health_status, http_status, type(exc).__name__)
                _record_runtime(role, config, latency_ms, is_structured, i, False,
                                http_status=http_status, error_type=type(exc).__name__,
                                failover_chain=_failed_providers)

                # Track failed provider for failover chain display
                if config.provider not in _failed_providers:
                    _failed_providers.append(config.provider)

                # OpenRouter health logging
                if config.provider == "openrouter":
                    logger.info(
                        f"PROVIDER_HEALTH | openrouter | {config.model} | "
                        f"HTTP={http_status or 'N/A'} | reason={type(exc).__name__}"
                    )

                if _is_skipable_error(exc):
                    logger.warning(
                        f"Role '{role.value}' {config.provider}/{config.model} "
                        f"skipable ({type(exc).__name__}), next..."
                    )
                    break  # break retry loop, go to next provider

                if _is_timeout_error(exc) and attempt == 0:
                    logger.warning(
                        f"Role '{role.value}' {config.provider}/{config.model} "
                        f"timeout, retrying once..."
                    )
                    continue  # retry once on same provider

                # All other errors or timeout retry exhausted — skip to next provider
                logger.warning(
                    f"Role '{role.value}' {config.provider}/{config.model} "
                    f"error ({type(exc).__name__}), next..."
                )
                break  # break retry loop, go to next provider

    # If all providers exhausted AND we're doing structured output, return defaults instead of raising
    if is_structured:
        logger.warning(
            f"All providers exhausted for structured role '{role.value}', "
            f"returning schema defaults. Last error: {last_error}"
        )
        return parse_schema()  # type: ignore[misc]

    raise AllProvidersExhaustedError(
        f"All providers exhausted for role '{role.value}'. Last error: {last_error}"
    )


def invoke_with_fallback(role: ProviderRole, messages: list[dict], **kwargs: Any) -> Any:
    """Invoke the primary LLM for a role with automatic failover. Returns raw AIMessage."""
    return _invoke_chain(role, messages, parse_schema=None, **kwargs)


def invoke_structured(role: ProviderRole, messages: list[dict], schema: Type[BaseModel], **kwargs: Any) -> BaseModel:
    """Invoke the LLM for a role and parse into a Pydantic schema."""
    return _invoke_chain(role, messages, parse_schema=schema, **kwargs)


# ---------------------------------------------------------------------------
# Convenience: get primary LLM instance (for direct use)
# ---------------------------------------------------------------------------


def get_llm(role: ProviderRole) -> Any:
    """Return the primary LangChain chat model for a given role (no fallback)."""
    chain = PROVIDER_CHAINS.get(role, [])
    if not chain:
        raise ValueError(f"No provider chain configured for role: {role}")
    return _build_llm(chain[0])