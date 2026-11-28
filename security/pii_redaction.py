"""
SOLVENS Security - PII Detection and Redaction

Automatically detect and redact Personally Identifiable Information
before sending to external LLM providers.
"""

import re
from dataclasses import dataclass
from typing import Optional, Callable
from enum import Enum


class PIICategory(str, Enum):
    """Categories of PII."""
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    EMAIL = "email"
    PHONE = "phone"
    IP_ADDRESS = "ip_address"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    DATE_OF_BIRTH = "dob"
    ADDRESS = "address"
    NAME = "name"  # Simple name detection
    API_KEY = "api_key"
    SECRET = "secret"
    PASSWORD = "password"


@dataclass
class PIIMatch:
    """A detected PII match."""
    category: PIICategory
    value: str
    start: int
    end: int
    confidence: float  # 0.0 - 1.0


class PIIRedactor:
    """
    Detect and redact PII from text.
    
    Usage:
        redactor = PIIRedactor()
        redacted, matches = redactor.redact("My SSN is 123-45-6789")
        # redacted = "My SSN is [REDACTED:SSN]"
        # matches = [PIIMatch(PIICategory.SSN, "123-45-6789", ...)]
    """
    
    REDACTED_TEMPLATE = "[REDACTED:{category}]"
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize PII Redactor.
        
        Args:
            strict_mode: If True, raise exception on PII detection failure
        """
        self.strict_mode = strict_mode
        self._patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> dict[PIICategory, tuple[re.Pattern, float]]:
        """Compile regex patterns for each PII type."""
        return {
            # Social Security Number (US)
            PIICategory.SSN: (
                re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
                0.95
            ),
            
            # Credit Card (Visa, MasterCard, Amex, Discover)
            PIICategory.CREDIT_CARD: (
                re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{15,16}\b'),
                0.90
            ),
            
            # Email Address
            PIICategory.EMAIL: (
                re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
                0.95
            ),
            
            # Phone Number (US formats)
            PIICategory.PHONE: (
                re.compile(r'\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
                0.85
            ),
            
            # IP Address (IPv4)
            PIICategory.IP_ADDRESS: (
                re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
                0.90
            ),
            
            # Passport Number (generic pattern)
            PIICategory.PASSPORT: (
                re.compile(r'\b[A-Z]{1,2}\d{6,9}\b'),
                0.70
            ),
            
            # Driver License (US - various formats)
            PIICategory.DRIVER_LICENSE: (
                re.compile(r'\b[A-Z]\d{7,14}\b'),
                0.60
            ),
            
            # Date of Birth (various formats)
            PIICategory.DATE_OF_BIRTH: (
                re.compile(r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b'),
                0.75
            ),
            
            # Generic API key patterns
            PIICategory.API_KEY: (
                re.compile(r'\b(?:(?:sk|api|key|token)[_-]?(?:live|test)?[_-]?[a-zA-Z0-9]{20,}|(?:AKIA|A3T|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16})\b', re.IGNORECASE),
                0.85
            ),
            
            # Generic secrets
            PIICategory.SECRET: (
                re.compile(r'\b(?:password|passwd|pwd|secret|token|auth)[_-]?(?:key)?\s*[=:]\s*["\']?[^\s"\']+["\']?', re.IGNORECASE),
                0.90
            ),
            
            # AWS access key IDs are included in the same API-key matcher.
            # Keep one dictionary entry per category to avoid overwriting patterns.

        }
    
    def detect(self, text: str) -> list[PIIMatch]:
        """
        Detect PII in text without redacting.
        
        Returns:
            List of PIIMatch objects
        """
        matches = []
        
        for category, (pattern, confidence) in self._patterns.items():
            for match in pattern.finditer(text):
                matches.append(PIIMatch(
                    category=category,
                    value=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=confidence,
                ))
        
        # Sort by position in text
        matches.sort(key=lambda m: m.start)
        return matches
    
    def redact(self, text: str, custom_replacer: Optional[Callable[[str], str]] = None) -> tuple[str, list[PIIMatch]]:
        """
        Detect and redact PII from text.
        
        Args:
            text: Input text
            custom_replacer: Optional function to generate replacement text
        
        Returns:
            Tuple of (redacted_text, list_of_matches)
        
        Raises:
            PIIValidationError: If strict_mode and PII detected
        """
        matches = self.detect(text)
        
        if not matches:
            return text, []
        
        if self.strict_mode:
            raise PIIValidationError(
                f"PII detected in strict mode: {[m.category.value for m in matches]}"
            )
        
        # Redact from end to start to preserve positions
        redacted = text
        offset = 0
        
        for match in matches:
            if custom_replacer:
                replacement = custom_replacer(match.category.value)
            else:
                replacement = self.REDACTED_TEMPLATE.format(category=match.category.value.upper())
            
            start = match.start + offset
            end = match.end + offset
            redacted = redacted[:start] + replacement + redacted[end:]
            offset += len(replacement) - (match.end - match.start)
        
        return redacted, matches
    
    def redact_dict(self, data: dict, path: str = "") -> tuple[dict, list[PIIMatch]]:
        """
        Recursively redact PII from a dictionary.
        
        Returns:
            Tuple of (redacted_dict, all_matches)
        """
        import json
        
        redacted = {}
        all_matches = []
        
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, str):
                redacted_value, matches = self.redact(value)
                redacted[key] = redacted_value
                for m in matches:
                    all_matches.append(m)
            elif isinstance(value, dict):
                redacted[key], nested_matches = self.redact_dict(value, current_path)
                all_matches.extend(nested_matches)
            elif isinstance(value, list):
                redacted_list = []
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        redacted_item, matches = self.redact(item)
                        redacted_list.append(redacted_item)
                        for m in matches:
                            all_matches.append(m)
                    elif isinstance(item, (dict, list)):
                        redacted_item, nested_matches = self._redact_nested(item)
                        redacted_list.append(redacted_item)
                        all_matches.extend(nested_matches)
                    else:
                        redacted_list.append(item)
                redacted[key] = redacted_list
            else:
                redacted[key] = value
        
        return redacted, all_matches
    
    def _redact_nested(self, value):
        """Recursively redact strings inside nested dict/list structures."""
        if isinstance(value, str):
            return self.redact(value)
        if isinstance(value, dict):
            output, matches = {}, []
            for key, item in value.items():
                output[key], found = self._redact_nested(item)
                matches.extend(found)
            return output, matches
        if isinstance(value, list):
            output, matches = [], []
            for item in value:
                redacted_item, found = self._redact_nested(item)
                output.append(redacted_item)
                matches.extend(found)
            return output, matches
        return value, []

    def summary(self, matches: list[PIIMatch]) -> dict:
        """
        Generate a summary of detected PII.
        
        Returns:
            Dict with counts per category
        """
        summary = {}
        for match in matches:
            category = match.category.value
            if category not in summary:
                summary[category] = {"count": 0, "confidence_avg": 0, "instances": []}
            summary[category]["count"] += 1
            summary[category]["instances"].append(match.value[:4] + "..." if len(match.value) > 4 else match.value)
        
        # Calculate average confidence
        for category, data in summary.items():
            category_matches = [m for m in matches if m.category.value == category]
            data["confidence_avg"] = sum(m.confidence for m in category_matches) / len(category_matches)
        
        return summary


class PIIValidationError(Exception):
    """Raised when PII is detected in strict mode."""
    pass


class PIIAwareLLMWrapper:
    """Redact PII recursively from user and tool message payloads before dispatch."""

    def __init__(self, llm_provider, strict_mode: bool = False):
        self.llm = llm_provider
        self.redactor = PIIRedactor(strict_mode=strict_mode)

    def _redact_value(self, value):
        if isinstance(value, str):
            return self.redactor.redact(value)[0]
        if isinstance(value, dict):
            return {key: self._redact_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._redact_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._redact_value(item) for item in value)
        return value

    def _redact_messages(self, messages: list[dict]) -> list[dict]:
        redacted = []
        for message in messages:
            # Redact every untrusted/provider-bound field regardless of role.
            # Keep only the role label intact; content, metadata, tool arguments,
            # names, and multimodal payloads may all carry secrets or PII.
            msg = {
                key: (value if key == "role" else self._redact_value(value))
                for key, value in message.items()
            }
            redacted.append(msg)
        return redacted

    async def chat(self, messages: list[dict]) -> dict:
        return await self.llm.chat(self._redact_messages(messages))

    def chat_sync(self, messages: list[dict]) -> dict:
        return self.llm.chat_sync(self._redact_messages(messages))
