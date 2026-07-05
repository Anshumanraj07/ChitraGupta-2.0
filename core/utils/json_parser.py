"""
ChitraGupta 2.0 — JSON Parser
Robust JSON parsing with fallback for LLM outputs.
"""

import json
import logging
import re
from typing import Any, Optional, Dict, List

logger = logging.getLogger("chitragupta.json_parser")


def parse_json_robust(text: str, default: Any = None) -> Any:
    """
    Robustly parse JSON from text that may contain extra content.
    Handles: markdown code blocks, partial JSON, trailing commas, etc.
    """
    if not text or not text.strip():
        return default
    
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract from markdown code blocks
    code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object in text
    json_match = re.search(r'(\{.*\})', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to fix common issues
    fixed = _fix_common_json_issues(text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    
    logger.warning(f"Failed to parse JSON from: {text[:200]}")
    return default


def _fix_common_json_issues(text: str) -> str:
    """Fix common JSON formatting issues."""
    # Remove trailing commas
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    # Fix single quotes to double quotes (naive)
    # Only for keys and simple values
    text = re.sub(r"'([^']*)':", r'"\1":', text)
    text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
    
    # Fix unquoted keys
    text = re.sub(r'(\w+):', r'"\1":', text)
    
    return text


def parse_json_array(text: str, default: List = None) -> List:
    """Parse JSON array from text."""
    if default is None:
        default = []
    
    result = parse_json_robust(text, default)
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        return [result]
    return default


def parse_json_object(text: str, default: Dict = None) -> Dict:
    """Parse JSON object from text."""
    if default is None:
        default = {}
    
    result = parse_json_robust(text, default)
    if isinstance(result, dict):
        return result
    return default


def extract_json_fields(text: str, fields: List[str]) -> Dict[str, Any]:
    """Extract specific fields from JSON in text."""
    result = {}
    parsed = parse_json_robust(text, {})
    
    if isinstance(parsed, dict):
        for field in fields:
            if field in parsed:
                result[field] = parsed[field]
    
    return result


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """Safely serialize to JSON with default handling."""
    def default_serializer(o):
        if hasattr(o, 'model_dump'):
            return o.model_dump()
        if hasattr(o, '__dict__'):
            return o.__dict__
        if hasattr(o, 'isoformat'):
            return o.isoformat()
        return str(o)
    
    return json.dumps(obj, default=default_serializer, **kwargs)


# Backward compatibility functions for engine_shifter
def extract_and_validate_json(text: str, schema: Any = None, default: Any = None) -> Any:
    """
    Extract and validate JSON from text.
    Backward compatible with engine_shifter expectations.
    """
    return parse_json_robust(text, default)


def build_retry_prompt(original_prompt: str, error: str, attempt: int = 1) -> str:
    """Build a retry prompt for failed JSON parsing."""
    return f"""The previous response could not be parsed as valid JSON.

Error: {error}
Attempt: {attempt}

Please provide a valid JSON response only, following the exact schema specified.

Original prompt:
{original_prompt}"""


def build_json_instruction(schema: Any = None) -> str:
    """Build JSON instruction for LLM prompts."""
    if schema:
        return f"Respond with valid JSON matching this schema: {schema}"
    return "Respond with valid JSON only."
