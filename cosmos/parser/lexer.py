"""
Lexer for COSMOS Language

Tokenizes .cosmos source files into tokens for the parser.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional


class TokenType(Enum):
    """Token types for COSMOS language."""
    # Literals
    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()
    
    # Keywords
    TASK = auto()
    AGENT = auto()
    PROVIDER = auto()
    DAG = auto()
    DEPENDS_ON = auto()
    RETRY = auto()
    TIMEOUT = auto()
    PARALLEL = auto()
    SEQUENTIAL = auto()
    
    # Operators
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LPAREN = auto()
    RPAREN = auto()
    ARROW = auto()
    DOT = auto()
    COMMA = auto()
    COLON = auto()
    SEMICOLON = auto()
    AT = auto()
    EQUALS = auto()
    
    # Special
    NEWLINE = auto()
    COMMENT = auto()
    EOF = auto()
    ERROR = auto()


@dataclass
class Token:
    """Represents a token in the source code."""
    type: TokenType
    value: str
    line: int
    column: int


KEYWORDS = {
    "task": TokenType.TASK,
    "agent": TokenType.AGENT,
    "provider": TokenType.PROVIDER,
    "dag": TokenType.DAG,
    "depends_on": TokenType.DEPENDS_ON,
    "retry": TokenType.RETRY,
    "timeout": TokenType.TIMEOUT,
    "parallel": TokenType.PARALLEL,
    "sequential": TokenType.SEQUENTIAL,
}


class Lexer:
    """
    Tokenizer for COSMOS source files.
    
    Example .cosmos file:
    ```
    task process_data {
        provider = "openai"
        depends_on = [fetch_data]
        retry = 3
    }
    ```
    """
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []
    
    def tokenize(self) -> list[Token]:
        """Tokenize the entire source and return list of tokens."""
        while self.pos < len(self.source):
            self._scan_token()
        
        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return self.tokens
    
    def _scan_token(self) -> None:
        """Scan the next token."""
        char = self.source[self.pos]
        
        # Whitespace
        if char in " \t":
            self._advance()
            self.column += 1
            return
        
        # Newlines
        if char == "\n":
            self.tokens.append(Token(TokenType.NEWLINE, "\n", self.line, self.column))
            self._advance()
            self.line += 1
            self.column = 1
            return
        
        # Comments
        if char == "#":
            self._scan_comment()
            return
        
        # Operators and punctuation
        if char == "{":
            self.tokens.append(Token(TokenType.LBRACE, char, self.line, self.column))
            self._advance()
            self.column += 1
            return
        if char == "}":
            self.tokens.append(Token(TokenType.RBRACE, char, self.line, self.column))
            self._advance()
            self.column += 1
            return
        if char == "[":
            self.tokens.append(Token(TokenType.LBRACKET, char, self.line, self.column))
            self._advance()
            self.column += 1
            return
        if char == "]":
            self.tokens.append(Token(TokenType.RBRACKET, char, self.line, self.column))
            self._advance()
            self.column += 1
            return
        if char == "(":
            self.tokens.append(Token(TokenType.LPAREN, char, self.line, self.column))
            self._advance()
            self.column += 1
            return
        if char == ")":
            self.tokens.append(Token(TokenType.RPAREN, char, self.line, self.column))
            self._advance()
            self.column += 1
            return
        if char == ",":
            self.tokens.append(Token(TokenType.COMMA, char, self.line, self.column))
            self._advance()
            self.column += 1
            return
        if char == ";":
            self.tokens.append(Token(TokenType.SEMICOLON, char, self.line, self.column))
            self._advance()
            self.column += 1
            return
        if char == "@":
            self.tokens.append(Token(TokenType.AT, char, self.line, self.column))
            self._advance()
            self.column += 1
            return
        if char == ":":
            self.tokens.append(Token(TokenType.COLON, char, self.line, self.column))
            self._advance()
            self.column += 1
            return
        if char == ".":
            self.tokens.append(Token(TokenType.DOT, char, self.line, self.column))
            self._advance()
            self.column += 1
            return
        
        # Arrow operator
        if char == "-" and self._peek() == ">":
            self.tokens.append(Token(TokenType.ARROW, "->", self.line, self.column))
            self._advance()
            self._advance()
            self.column += 2
            return
        
        # Equals
        if char == "=":
            self.tokens.append(Token(TokenType.EQUALS, char, self.line, self.column))
            self._advance()
            self.column += 1
            return
        
        # String
        if char == '"':
            self._scan_string()
            return
        
        # Number
        if char.isdigit() or (char == "-" and self._peek().isdigit()):
            self._scan_number()
            return
        
        # Identifier or keyword
        if char.isalpha() or char == "_":
            self._scan_identifier()
            return
        
        # Unknown character
        self.tokens.append(Token(TokenType.ERROR, char, self.line, self.column))
        self._advance()
        self.column += 1
    
    def _scan_string(self) -> None:
        """Scan a string literal."""
        start_col = self.column
        self._advance()  # Skip opening quote
        value = ""
        
        while self.pos < len(self.source) and self.source[self.pos] != '"':
            if self.source[self.pos] == "\n":
                raise SyntaxError(f"String literal cannot span lines at {self.line}:{self.column}")
            value += self.source[self.pos]
            self._advance()
        
        if self.pos >= len(self.source):
            raise SyntaxError(f"Unterminated string at {self.line}:{start_col}")
        
        self._advance()  # Skip closing quote
        self.tokens.append(Token(TokenType.STRING, value, self.line, start_col))
        self.column += len(value) + 2
    
    def _scan_number(self) -> None:
        """Scan a number literal."""
        start_col = self.column
        value = ""
        
        if self.source[self.pos] == "-":
            value += self.source[self.pos]
            self._advance()
        
        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            value += self.source[self.pos]
            self._advance()
        
        self.tokens.append(Token(TokenType.NUMBER, value, self.line, start_col))
        self.column += len(value)
    
    def _scan_identifier(self) -> None:
        """Scan an identifier or keyword."""
        start_col = self.column
        value = ""
        
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == "_"):
            value += self.source[self.pos]
            self._advance()
        
        token_type = KEYWORDS.get(value, TokenType.IDENTIFIER)
        self.tokens.append(Token(token_type, value, self.line, start_col))
        self.column += len(value)
    
    def _scan_comment(self) -> None:
        """Scan a comment."""
        start_col = self.column
        value = ""
        
        self._advance()  # Skip #
        while self.pos < len(self.source) and self.source[self.pos] != "\n":
            value += self.source[self.pos]
            self._advance()
        
        self.tokens.append(Token(TokenType.COMMENT, value, self.line, start_col))
        self.column += len(value) + 1
    
    def _peek(self) -> str:
        """Look at the next character without consuming it."""
        if self.pos + 1 < len(self.source):
            return self.source[self.pos + 1]
        return ""
    
    def _advance(self) -> None:
        """Move to the next character."""
        self.pos += 1
