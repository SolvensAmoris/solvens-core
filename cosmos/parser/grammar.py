"""
COSMOS Language Grammar (EBNF)

This defines the formal grammar for .cosmos files.

Grammar Reference:
    ::=(definition)
    ::=(sequence)
    ::=(alternative)
    [x]=(optional x)
    {x}=(zero or more x)
    x*=((zero or more x)
    x+=(one or more x)
    "x"=(terminal string)
    (x)=(grouping)

Example .cosmos file:
    task process_data {
        provider = "openai"
        depends_on = [fetch_data, validate]
        retry = 3
        timeout = 30
    }
    
    agent claude {
        model = "claude-3-sonnet"
        temperature = 0.7
    }
"""

GRAMMAR = """
/*
 * COSMOS Language Grammar (EBNF)
 * Author: Luis Alberto Burciaga Miker
 */

Program       ::= Statement*

Statement     ::= TaskDecl
               | AgentDecl
               | ProviderDecl
               | DagDecl
               | Comment

TaskDecl      ::= "task" IDENTIFIER "{" TaskBody "}"
TaskBody      ::= { TaskProperty }
TaskProperty  ::= "provider" "=" STRING
               | "depends_on" "=" "[" DependencyList "]"
               | "retry" "=" NUMBER
               | "timeout" "=" NUMBER
               | "parallel" "=" BOOLEAN
               | Comment

AgentDecl     ::= "agent" IDENTIFIER "{" AgentBody "}"
AgentBody     ::= { AgentProperty }
AgentProperty ::= IDENTIFIER "=" (STRING | NUMBER | BOOLEAN)
               | Comment

ProviderDecl  ::= "provider" IDENTIFIER "{" ProviderBody "}"
ProviderBody  ::= { ProviderProperty }
ProviderProperty ::= IDENTIFIER "=" (STRING | NUMBER | BOOLEAN)

DagDecl       ::= "dag" IDENTIFIER "{" DagBody "}"
DagBody       ::= { DagNode }
DagNode       ::= IDENTIFIER "->" IDENTIFIER

DependencyList::= IDENTIFIER { "," IDENTIFIER }

Comment       ::= "#" .*

IDENTIFIER    ::= (letter | "_") { (letter | digit | "_") }
STRING        ::= '"' .* '"'
NUMBER        ::= ["-"] digit { digit }
BOOLEAN       ::= "true" | "false"
letter        ::= "a".."z" | "A".."Z"
digit         ::= "0".."9"
"""

# Parse rules for the parser
GRAMMAR_RULES = """
TaskDecl      -> 'task' IDENTIFIER LBRACE TaskBody RBRACE
TaskBody      -> TaskProperty*
TaskProperty  -> ProviderAssign | DependsOn | RetryAssign | TimeoutAssign | Comment
ProviderAssign-> 'provider' EQUALS STRING
DependsOn     -> 'depends_on' EQUALS LBRACKET DependencyList? RBRACKET
DependencyList-> IDENTIFIER (COMMA IDENTIFIER)*
RetryAssign   -> 'retry' EQUALS NUMBER
TimeoutAssign -> 'timeout' EQUALS NUMBER

AgentDecl     -> 'agent' IDENTIFIER LBRACE AgentBody RBRACE
AgentBody     -> AgentProperty*
AgentProperty -> IDENTIFIER EQUALS (STRING | NUMBER | BOOLEAN) | Comment

ProviderDecl  -> 'provider' IDENTIFIER LBRACE ProviderBody RBRACE
ProviderBody  -> ProviderProperty*
ProviderProperty -> IDENTIFIER EQUALS (STRING | NUMBER | BOOLEAN)

DagDecl       -> 'dag' IDENTIFIER LBRACE DagBody RBRACE
DagBody       -> DagEdge*
DagEdge       -> IDENTIFIER ARROW IDENTIFIER
"""


class Grammar:
    """
    Represents the COSMOS language grammar.
    
    Use this to understand the structure of .cosmos files
    and to validate parser output.
    """
    
    @staticmethod
    def get_grammar() -> str:
        """Return the EBNF grammar definition."""
        return GRAMMAR
    
    @staticmethod
    def get_parse_rules() -> str:
        """Return the parser rules in a readable format."""
        return GRAMMAR_RULES
    
    @staticmethod
    def validate_syntax(source: str) -> bool:
        """
        Basic syntax validation without full parsing.
        Returns True if the source looks valid.
        """
        # Check balanced braces
        brace_count = source.count("{") - source.count("}")
        if brace_count != 0:
            return False
        
        # Check balanced brackets
        bracket_count = source.count("[") - source.count("]")
        if bracket_count != 0:
            return False
        
        # Check balanced parentheses
        paren_count = source.count("(") - source.count(")")
        if paren_count != 0:
            return False
        
        return True
