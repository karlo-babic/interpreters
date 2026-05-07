from dataclasses import dataclass
from token_class import Token

class Expr:
    """Base class for all expression nodes."""
    pass

@dataclass
class Binary(Expr):
    left: Expr
    operator: Token
    right: Expr

@dataclass
class Grouping(Expr):
    expression: Expr

@dataclass
class Literal(Expr):
    value: object

@dataclass
class Unary(Expr):
    operator: Token
    right: Expr

@dataclass
class Ternary(Expr):
    condition: Expr
    then_branch: Expr
    else_branch: Expr

@dataclass
class Variable(Expr):
    name: Token

@dataclass
class Assign(Expr):
    name: Token
    value: Expr

@dataclass
class Logical(Expr):
    left: Expr
    operator: Token
    right: Expr

@dataclass
class Call(Expr):
    callee: Expr
    paren: Token
    arguments: list[Expr]

@dataclass
class AnonymousFunction(Expr):
    keyword: Token
    params: list[Token]
    body: list['stmt.Stmt'] # Forward reference to Stmt