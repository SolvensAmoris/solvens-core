# Cosmos Language Server

LSP (Language Server Protocol) implementation for Cosmos DSL.

## Features

- **Syntax Highlighting** - Full Cosmos DSL highlighting
- **Auto-completion** - Keywords and type suggestions
- **Diagnostics** - Real-time E401 error detection
- **Hover Docs** - Documentation on hover
- **Go-to Definition** - Navigate your cosmos files
- **Document Symbols** - Outline view support

## Installation

```bash
pip install cosmos-language
```

## VSCode

Install from VSCode Marketplace or manually:

```json
{
  "languages": [{
    "id": "cosmos",
    "extensions": [".cosmos"]
  }],
  "languageServer": "cosmos-language-server"
}
```

## Neovim

```lua
-- Using nvim-lspconfig
require('lspconfig').cosmos_language_server.setup({})
```

## Usage

```bash
# Start the language server
cosmos-language-server

# Or use with VSCode
# Install the Cosmos DSL VSCode extension
```

## Cosmos DSL Example

```cosmos
universe production {
  planet web_server {
    region: us-east-1
    start_on: 2026-01-01
    end_on: 2026-12-31
  }
  
  planet database {
    region: us-east-1
    depends_on: web_server
  }
  
  light deploy -> web_server, database
}
```

## License

Apache 2.0

## Author

**Luis Alberto Burciaga Miker**  
luis@solvens.amoris
