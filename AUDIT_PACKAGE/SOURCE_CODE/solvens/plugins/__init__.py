"""Provider plugins for SOLVENS CORE.

Each plugin implements the ProviderClient interface for a specific AI provider.

Available plugins:
- openai: OpenAI GPT models
- anthropic: Anthropic Claude models
- ollama: Local LLM inference
"""

# Plugin metadata for discovery
PLUGIN_METADATA = {
    "name": "solvens-providers",
    "version": "0.1.0",
    "description": "Provider plugins for SOLVENS CORE",
    "entry_point": "solvens.plugins",
}

