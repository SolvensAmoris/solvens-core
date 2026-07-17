"""
Cosmos Language Server
=======================

LSP (Language Server Protocol) implementation for Cosmos DSL.
Provides IDE integration for VSCode, Neovim, Emacs, and other LSP clients.

Features:
- Syntax highlighting
- Auto-completion
- Diagnostics (E401 detection)
- Hover documentation
- Go-to definition
- Document symbols

Author: Luis Alberto Burciaga Miker
Version: 1.0.0
License: Apache 2.0
"""

__version__ = "1.0.0"
__author__ = "Luis Alberto Burciaga Miker"
__email__ = "luis@solvens.amoris"

from .server import CosmosLanguageServer

__all__ = ["CosmosLanguageServer", "__version__"]
