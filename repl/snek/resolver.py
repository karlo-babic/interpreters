import expr
import stmt
import error
from enum import Enum, auto

class FunctionType(Enum):
    NONE = auto()
    FUNCTION = auto()
    INITIALIZER = auto()
    METHOD = auto()
    STATIC_METHOD = auto()

class ClassType(Enum):
    NONE = auto()
    CLASS = auto()

class Resolver:
    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.scopes: list[dict[str, bool]] = []
        self.current_function = FunctionType.NONE
        self.current_class = ClassType.NONE

    def resolve_statements(self, statements: list[stmt.Stmt]):
        for statement in statements:
            self.resolve(statement)

    def resolve(self, node: stmt.Stmt | expr.Expr):
        """Dispatches to the appropriate resolution logic based on node type."""
        match node:
            case stmt.Block(statements):
                self.begin_scope()
                self.resolve_statements(statements)
                self.end_scope()

            case stmt.Var(name, initializer):
                self.declare(name)
                if initializer is not None:
                    self.resolve(initializer)
                self.define(name)

            case expr.Variable(name):
                if self.scopes and name.lexeme in self.scopes[-1]:
                    if self.scopes[-1][name.lexeme]["defined"] is False:
                        error.error(name.line, "Can't read local variable in its own initializer.")
                
                self.resolve_local(node, name)

            case expr.Assign(name, value):
                self.resolve(value)
                self.resolve_local(node, name)

            case stmt.Function(name, params, body):
                self.declare(name)
                self.define(name)
                self.resolve_function(params, body, FunctionType.FUNCTION)

            case expr.AnonymousFunction(keyword, params, body):
                self.resolve_function(params, body, FunctionType.FUNCTION)

            case stmt.Class(name, methods):
                enclosing_class = self.current_class
                self.current_class = ClassType.CLASS
                
                self.declare(name)
                self.define(name)
                
                self.begin_scope()
                self.scopes[-1]["this"] = {"defined": True, "used": True, "line": name.line}
                
                for method in methods:
                    declaration = FunctionType.METHOD
                    if method.name.lexeme == "init":
                        declaration = FunctionType.INITIALIZER
                    if method.is_static:
                        declaration = FunctionType.STATIC_METHOD

                    self.resolve_function(method.params, method.body, declaration)
                    
                self.end_scope()
                self.current_class = enclosing_class

            case expr.This(keyword):
                if self.current_class == ClassType.NONE:
                    error.error(keyword.line, "Can't use 'this' outside of a class.")
                    return
                elif self.current_function == FunctionType.STATIC_METHOD:
                    error.error(keyword.line, "Can't use 'this' inside a static method.")
                    return
                
                self.resolve_local(node, keyword)

            # --- Other Statements ---
            case stmt.Expression(expression):
                self.resolve(expression)
                
            case stmt.If(condition, then_branch, else_branch):
                self.resolve(condition)
                self.resolve(then_branch)
                if else_branch is not None:
                    self.resolve(else_branch)
                    
            case stmt.Print(expression):
                self.resolve(expression)
                
            case stmt.Return(keyword, value):
                if self.current_function == FunctionType.NONE:
                    error.error(keyword.line, "Can't return from top-level code.")
                elif self.current_function == FunctionType.INITIALIZER and value is not None:
                    error.error(keyword.line, "Can't return a value from an initializer.")
                    
                if value is not None:
                    self.resolve(value)
                    
            case stmt.While(condition, body):
                self.resolve(condition)
                self.resolve(body)

            # --- Other Expressions ---
            case expr.Binary(left, operator, right):
                self.resolve(left)
                self.resolve(right)
                
            case expr.Call(callee, paren, arguments):
                self.resolve(callee)
                for arg in arguments:
                    self.resolve(arg)
                    
            case expr.Grouping(expression):
                self.resolve(expression)
                
            case expr.Literal(value):
                pass # Nothing to do
                
            case expr.Logical(left, operator, right):
                self.resolve(left)
                self.resolve(right)
                
            case expr.Unary(operator, right):
                self.resolve(right)
                
            case expr.Ternary(condition, then_branch, else_branch):
                self.resolve(condition)
                self.resolve(then_branch)
                self.resolve(else_branch)
            
            case expr.Get(object_expr, name):
                self.resolve(object_expr)
                
            case expr.Set(object_expr, name, value_expr):
                self.resolve(value_expr)
                self.resolve(object_expr)

    def begin_scope(self):
        self.scopes.append({})

    def end_scope(self):
        scope = self.scopes.pop()
        
        import sys
        for name, state in scope.items():
            if not state["used"]:
                print(f"[line {state['line']}] Warning: Local variable '{name}' is not used.", file=sys.stderr)

    def declare(self, name: 'Token'):
        if not self.scopes:
            return
        
        scope = self.scopes[-1]
        if name.lexeme in scope:
            error.error(name.line, "Already a variable with this name in this scope.")

        scope[name.lexeme] = {
            "defined": False, 
            "used": False, 
            "line": name.line
        }

    def define(self, name: 'Token'):
        if not self.scopes:
            return
            
        scope = self.scopes[-1]
        scope[name.lexeme]["defined"] = True

    def resolve_local(self, expr_node: expr.Expr, name: 'Token'):
        # Iterate through the scopes backwards (innermost to outermost)
        for i in range(len(self.scopes) - 1, -1, -1):
            if name.lexeme in self.scopes[i]:
                self.scopes[i][name.lexeme]["used"] = True
                # Calculate the number of hops to the target scope
                distance = len(self.scopes) - 1 - i
                self.interpreter.resolve(expr_node, distance)
                return
        
        # If not found, assume it is global.

    def resolve_function(self, params: list['Token'], body: list[stmt.Stmt], function_type: FunctionType):
        enclosing_function = self.current_function
        self.current_function = function_type
        
        self.begin_scope()
        for param in params:
            self.declare(param)
            self.define(param)
        
        self.resolve_statements(body)
        self.end_scope()
        
        self.current_function = enclosing_function