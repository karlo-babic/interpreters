from dataclasses import dataclass
import expr
from token_class import Token

class Stmt:
    """Base class for all statement nodes."""
    pass

@dataclass
class Expression(Stmt):
    expression: expr.Expr

@dataclass
class Print(Stmt):
    expression: expr.Expr

@dataclass
class Var(Stmt):
    name: Token
    initializer: expr.Expr | None

@dataclass
class Block(Stmt):
    statements: list[Stmt]

@dataclass
class If(Stmt):
    condition: expr.Expr
    then_branch: Stmt
    else_branch: Stmt | None

@dataclass
class While(Stmt):
    condition: expr.Expr
    body: Stmt

@dataclass
class Function(Stmt):
    name: Token
    params: list[Token]
    body: list[Stmt]

@dataclass
class Return(Stmt):
    keyword: Token
    value: expr.Expr | None