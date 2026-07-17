"""Default routing rules for SOLVENS CORE.

These rules determine which provider to use based on task content.
"""

from solvens.core.types import ModelCapability, ProviderType
from solvens.router.router import RoutingRule


class DefaultRoutingRules:
    """Collection of default routing rules.
    
    Rules are evaluated in priority order (highest first).
    First matching rule determines the provider.
    """
    
    @staticmethod
    def get_default_rules() -> list[RoutingRule]:
        """Get all default routing rules."""
        return [
            # === High Priority: Specific Use Cases ===
            
            # Code Generation & Analysis
            RoutingRule(
                name="code_generation",
                patterns=[
                    r"\bdef\s+\w+",           # Python function
                    r"\bfunction\s+\w+",       # JS function
                    r"\bclass\s+\w+",          # Class definition
                    r"\bimport\s+\w+",         # Import statement
                    r"\brequire\s*\(",         # CommonJS require
                    r"\bpub\s+fn",             # Rust function
                    r"\bfunc\s+\w+",           # Go/Rust function
                    r"```\w*",                # Code block
                    r"execute\s+this\s+code",
                    r"write\s+(me\s+)?a\s+function",
                    r"debug\s+this",
                    r"fix\s+(the\s+)?bug",
                ],
                capability=ModelCapability.CHAT,
                provider=ProviderType.ANTHROPIC,  # Claude excels at code
                priority=100,
                quality_weight=0.9,
                cost_weight=0.1,
            ),
            
            # Research & Analysis
            RoutingRule(
                name="research",
                patterns=[
                    r"\banalyze\s+",
                    r"\bresearch\s+",
                    r"\binvestigate\s+",
                    r"\bstudy\s+",
                    r"\bcompare\s+",
                    r"\bevaluate\s+",
                    r"\bassess\s+",
                    r"\breview\s+the\s+",
                    r"\bwhat\s+are\s+the\s+",
                    r"\blist\s+all\s+",
                ],
                capability=ModelCapability.CHAT,
                provider=ProviderType.SAKANA,
                priority=90,
                quality_weight=0.8,
                cost_weight=0.2,
            ),
            
            # Documentation Generation
            RoutingRule(
                name="documentation",
                patterns=[
                    r"\bdocument\s+",
                    r"\bdocs?\s+",
                    r"\bwrite\s+.*readme",
                    r"\bgenerate\s+.*doc",
                    r"\bapi\s+reference",
                    r"\bmarkdown\s+",
                    r"\bspecification\s+",
                    r"\buser\s+guide",
                    r"\btutorial\s+",
                    r"\bhow\s+to\s+",
                ],
                capability=ModelCapability.CHAT,
                provider=ProviderType.GOOGLE,  # Gemini for documentation
                priority=85,
                quality_weight=0.7,
                cost_weight=0.3,
            ),
            
            # Reasoning & Logic
            RoutingRule(
                name="reasoning",
                patterns=[
                    r"\blogic\s+",
                    r"\bproof\s+",
                    r"\btheorem\s+",
                    r"\bderive\s+",
                    r"\bexplain\s+why",
                    r"\breasoning\s+",
                    r"\bstep\s+by\s+step",
                    r"\bthink\s+through",
                    r"\bdebugging\s+logic",
                    r"\bmathematical\s+",
                ],
                capability=ModelCapability.CHAT,
                provider=ProviderType.OPENAI,  # GPT for reasoning
                priority=80,
                quality_weight=0.8,
                cost_weight=0.2,
            ),
            
            # Creative Writing
            RoutingRule(
                name="creative",
                patterns=[
                    r"\bstory\s+",
                    r"\bwrite\s+.*fiction",
                    r"\bpoem\s+",
                    r"\bnarrative\s+",
                    r"\bcreative\s+writing",
                    r"\bscript\s+",
                    r"\bdialogue\s+",
                    r"\bcharacter\s+",
                    r"\bplot\s+",
                ],
                capability=ModelCapability.CHAT,
                provider=ProviderType.GROK,
                priority=75,
                quality_weight=0.7,
                cost_weight=0.3,
            ),
            
            # Translation
            RoutingRule(
                name="translation",
                patterns=[
                    r"\btranslate\s+",
                    r"\btranslation\s+",
                    r"\bconvert\s+.*to\s+",
                    r"\blanguage\s+",
                    r"\bspanish\s+",
                    r"\bfrench\s+",
                    r"\bgerman\s+",
                    r"\bjapanese\s+",
                ],
                capability=ModelCapability.CHAT,
                provider=ProviderType.DEEPSEEK,
                priority=70,
                quality_weight=0.7,
                cost_weight=0.3,
            ),
            
            # Data Processing
            RoutingRule(
                name="data_processing",
                patterns=[
                    r"\bparse\s+",
                    r"\bextract\s+",
                    r"\btransform\s+",
                    r"\bcsv\s+",
                    r"\bjson\s+",
                    r"\bdata\s+",
                    r"\bregex\s+",
                    r"\bformat\s+",
                ],
                capability=ModelCapability.CHAT,
                provider=ProviderType.DEEPSEEK,
                priority=65,
                quality_weight=0.6,
                cost_weight=0.4,
            ),
            
            # Video-related tasks
            RoutingRule(
                name="video",
                patterns=[
                    r"\bvideo\s+",
                    r"\banimation\s+",
                    r"\bclip\s+",
                    r"\bmovie\s+",
                    r"\byoutube\s+",
                    r"\bframe\s+",
                ],
                capability=ModelCapability.VIDEO,
                provider=ProviderType.POLLO_AI,
                priority=60,
                quality_weight=0.8,
                cost_weight=0.2,
            ),
            
            # === Medium Priority: General Patterns ===
            
            # Questions & Answers
            RoutingRule(
                name="question_answer",
                patterns=[
                    r"^\s*what\s+",
                    r"^\s*who\s+",
                    r"^\s*where\s+",
                    r"^\s*when\s+",
                    r"^\s*why\s+",
                    r"^\s*how\s+",
                    r"^\s*can\s+",
                    r"^\s*is\s+",
                    r"^\s*are\s+",
                    r"^\s*do\s+",
                ],
                capability=ModelCapability.CHAT,
                provider=None,  # Use default
                priority=50,
                quality_weight=0.6,
                cost_weight=0.4,
            ),
            
            # Summarization
            RoutingRule(
                name="summarization",
                patterns=[
                    r"\bsummarize\s+",
                    r"\bsummary\s+",
                    r"\btl;dr",
                    r"\btoo\s+long\s+didn'?t\s+read",
                    r"\bshorten\s+",
                    r"\bcondense\s+",
                ],
                capability=ModelCapability.CHAT,
                provider=None,
                priority=45,
                quality_weight=0.5,
                cost_weight=0.5,
            ),
            
            # === Lower Priority: Fallback Rules ===
            
            # Default fallback (lowest priority)
            RoutingRule(
                name="default",
                patterns=[r".*"],  # Matches everything
                capability=ModelCapability.CHAT,
                provider=None,  # Uses configured default
                priority=0,
                quality_weight=0.5,
                cost_weight=0.5,
            ),
        ]

    @staticmethod
    def get_code_rules() -> list[RoutingRule]:
        """Get rules specifically for code-related tasks."""
        return [
            rule for rule in DefaultRoutingRules.get_default_rules()
            if "code" in rule.name.lower()
        ]

    @staticmethod
    def get_research_rules() -> list[RoutingRule]:
        """Get rules for research tasks."""
        return [
            rule for rule in DefaultRoutingRules.get_default_rules()
            if rule.name in ("research", "analysis", "review")
        ]

    @staticmethod
    def get_offline_rules() -> list[RoutingRule]:
        """Get rules that route to local/offline providers."""
        return [
            RoutingRule(
                name="offline_fallback",
                patterns=[
                    r"\boffline\s+",
                    r"\blocal\s+",
                    r"\bno\s+internet",
                    r"\bairgap\s+",
                    r"\bprivate\s+",
                ],
                provider=ProviderType.OLLAMA,
                priority=100,
                quality_weight=0.3,
                cost_weight=1.0,
            ),
        ]
