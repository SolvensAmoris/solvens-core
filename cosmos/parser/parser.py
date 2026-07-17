"""
Parser for COSMOS Language

Parses .cosmos source files into AST nodes.
"""

from typing import Optional
from cosmos.parser.lexer import Lexer, Token, TokenType
from cosmos.ast import (
    ASTNode, Program, TaskDecl, AgentDecl, 
    ProviderDecl, DagDecl, Property
)


class ParserError(Exception):
    """Raised when a parsing error occurs."""
    pass


class Parser:
    """
    Recursive descent parser for COSMOS language.
    
    Example usage:
        source = '''
        task process_data {
            provider = "openai"
            depends_on = [fetch_data]
        }
        '''
        parser = Parser(source)
        ast = parser.parse()
    """
    
    def __init__(self, source: str):
        self.lexer = Lexer(source)
        self.tokens: list[Token] = []
        self.pos = 0
    
    def parse(self) -> Program:
        """Parse the source and return an AST."""
        self.tokens = self.lexer.tokenize()
        return self._parse_program()
    
    def _parse_program(self) -> Program:
        """Parse a complete program."""
        statements: list[ASTNode] = []
        
        while not self._is_at_end():
            self._skip_newlines()
            if self._is_at_end():
                break
            
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)
        
        return Program(statements=statements)
    
    def _parse_statement(self) -> Optional[ASTNode]:
        """Parse a single statement."""
        token = self._peek()
        
        if token.type == TokenType.TASK:
            return self._parse_task()
        elif token.type == TokenType.AGENT:
            return self._parse_agent()
        elif token.type == TokenType.PROVIDER:
            return self._parse_provider()
        elif token.type == TokenType.DAG:
            return self._parse_dag()
        elif token.type == TokenType.COMMENT:
            self._advance()
            return None
        elif token.type == TokenType.NEWLINE:
            self._advance()
            return None
        else:
            self._advance()
            return None
    
    def _parse_task(self) -> TaskDecl:
        """Parse a task declaration."""
        self._expect(TokenType.TASK)
        name = self._expect(TokenType.IDENTIFIER).value
        self._expect(TokenType.LBRACE)
        
        properties: list[Property] = []
        
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            self._skip_newlines()
            
            if self._check(TokenType.RBRACE):
                break
            
            prop = self._parse_task_property()
            if prop:
                properties.append(prop)
        
        self._expect(TokenType.RBRACE)
        
        return TaskDecl(name=name, properties=properties)
    
    def _parse_task_property(self) -> Optional[Property]:
        """Parse a task property."""
        token = self._peek()
        
        if token.type == TokenType.PROVIDER:
            self._advance()
            self._expect(TokenType.EQUALS)
            value = self._expect(TokenType.STRING).value
            return Property(name="provider", value=value)
        
        elif token.type == TokenType.DEPENDS_ON:
            self._advance()
            self._expect(TokenType.EQUALS)
            self._expect(TokenType.LBRACKET)
            
            deps: list[str] = []
            while not self._check(TokenType.RBRACKET):
                deps.append(self._expect(TokenType.IDENTIFIER).value)
                if self._check(TokenType.COMMA):
                    self._advance()
            
            self._expect(TokenType.RBRACKET)
            return Property(name="depends_on", value=deps)
        
        elif token.type == TokenType.RETRY:
            self._advance()
            self._expect(TokenType.EQUALS)
            value = self._expect(TokenType.NUMBER).value
            return Property(name="retry", value=int(value))
        
        elif token.type == TokenType.TIMEOUT:
            self._advance()
            self._expect(TokenType.EQUALS)
            value = self._expect(TokenType.NUMBER).value
            return Property(name="timeout", value=int(value))
        
        elif token.type == TokenType.COMMENT:
            self._advance()
            return None
        
        elif token.type == TokenType.NEWLINE:
            self._advance()
            return None
        
        else:
            self._advance()
            return None
    
    def _parse_agent(self) -> AgentDecl:
        """Parse an agent declaration."""
        self._expect(TokenType.AGENT)
        name = self._expect(TokenType.IDENTIFIER).value
        self._expect(TokenType.LBRACE)
        
        properties: list[Property] = []
        
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            self._skip_newlines()
            if self._check(TokenType.RBRACE):
                break
            
            token = self._peek()
            if token.type == TokenType.IDENTIFIER:
                prop_name = self._advance().value
                self._expect(TokenType.EQUALS)
                
                if self._check(TokenType.STRING):
                    value = self._expect(TokenType.STRING).value
                elif self._check(TokenType.NUMBER):
                    value = self._expect(TokenType.NUMBER).value
                else:
                    value = self._advance().value
                
                properties.append(Property(name=prop_name, value=value))
            elif token.type == TokenType.COMMENT:
                self._advance()
            else:
                self._advance()
        
        self._expect(TokenType.RBRACE)
        return AgentDecl(name=name, properties=properties)
    
    def _parse_provider(self) -> ProviderDecl:
        """Parse a provider declaration."""
        self._expect(TokenType.PROVIDER)
        name = self._expect(TokenType.IDENTIFIER).value
        self._expect(TokenType.LBRACE)
        
        properties: list[Property] = []
        
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            self._skip_newlines()
            if self._check(TokenType.RBRACE):
                break
            
            token = self._peek()
            if token.type == TokenType.IDENTIFIER:
                prop_name = self._advance().value
                self._expect(TokenType.EQUALS)
                
                if self._check(TokenType.STRING):
                    value = self._expect(TokenType.STRING).value
                elif self._check(TokenType.NUMBER):
                    value = self._expect(TokenType.NUMBER).value
                else:
                    value = self._advance().value
                
                properties.append(Property(name=prop_name, value=value))
            elif token.type == TokenType.COMMENT:
                self._advance()
            else:
                self._advance()
        
        self._expect(TokenType.RBRACE)
        return ProviderDecl(name=name, properties=properties)
    
    def _parse_dag(self) -> DagDecl:
        """Parse a DAG declaration."""
        self._expect(TokenType.DAG)
        name = self._expect(TokenType.IDENTIFIER).value
        self._expect(TokenType.LBRACE)
        
        edges: list[tuple[str, str]] = []
        
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            self._skip_newlines()
            if self._check(TokenType.RBRACE):
                break
            
            if self._check(TokenType.IDENTIFIER):
                from_node = self._advance().value
                self._expect(TokenType.ARROW)
                to_node = self._expect(TokenType.IDENTIFIER).value
                edges.append((from_node, to_node))
            elif self._check(TokenType.COMMENT):
                self._advance()
            else:
                self._advance()
        
        self._expect(TokenType.RBRACE)
        return DagDecl(name=name, edges=edges)
    
    # Helper methods
    
    def _peek(self) -> Token:
        """Look at the current token."""
        return self.tokens[self.pos]
    
    def _advance(self) -> Token:
        """Consume and return the current token."""
        if not self._is_at_end():
            self.pos += 1
        return self.tokens[self.pos - 1]
    
    def _check(self, type_: TokenType) -> bool:
        """Check if the current token is of the given type."""
        if self._is_at_end():
            return False
        return self._peek().type == type_
    
    def _expect(self, type_: TokenType) -> Token:
        """Expect a token of the given type and consume it."""
        if self._check(type_):
            return self._advance()
        raise ParserError(f"Expected {type_}, got {self._peek().type}")
    
    def _is_at_end(self) -> bool:
        """Check if we've reached the end of tokens."""
        return self._peek().type == TokenType.EOF
    
    def _skip_newlines(self) -> None:
        """Skip any newlines."""
        while self._check(TokenType.NEWLINE) or self._check(TokenType.COMMENT):
            self._advance()
