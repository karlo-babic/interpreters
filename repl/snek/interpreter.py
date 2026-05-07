from token_type import TokenType
from token_class import Token
from environment import Environment
from snek_function import SnekFunction
from return_class import ReturnException
from snek_callable import SnekCallable
import error
import expr
import stmt
import natives

class Interpreter:
    def __init__(self):
        self.globals = Environment()
        self.environment = self.globals
        self.locals: dict[int, int] = {} # AST node ID to distance mapping
        
        # Define native functions
        self.globals.define("clock", natives.ClockCallable())
        self.globals.define("input", natives.InputCallable())
        self.globals.define("toNumber", natives.ToNumberCallable())
        self.globals.define("toString", natives.ToStringCallable())

    def resolve(self, expr_node: expr.Expr, depth: int):
        self.locals[id(expr_node)] = depth

    def interpret(self, statements: list[stmt.Stmt]):
        try:
            for statement in statements:
                self.execute(statement)
        except error.SnekRuntimeError as err:
            error.runtime_error(err)

    def execute(self, statement: stmt.Stmt):
        match statement:
            case stmt.Print(expression):
                value = self.evaluate(expression)
                print(self.stringify(value))
                
            case stmt.Expression(expression):
                self.evaluate(expression)

            case stmt.Var(name, initializer):
                value = None
                if initializer is not None:
                    value = self.evaluate(initializer)
                self.environment.define(name.lexeme, value)

            case stmt.Block(statements):
                self.execute_block(statements, Environment(self.environment))

            case stmt.If(condition, then_branch, else_branch):
                if self.is_truthy(self.evaluate(condition)):
                    self.execute(then_branch)
                elif else_branch is not None:
                    self.execute(else_branch)

            case stmt.While(condition, body):
                while self.is_truthy(self.evaluate(condition)):
                    self.execute(body)

            case stmt.Function(name, params, body):
                function = SnekFunction(statement, self.environment)
                self.environment.define(name.lexeme, function)

            case stmt.Return(keyword, value_expr):
                value = None
                if value_expr is not None:
                    value = self.evaluate(value_expr)
                raise ReturnException(value)

    def execute_block(self, statements: list[stmt.Stmt], environment: Environment):
        previous = self.environment

        try:
            self.environment = environment
            for statement in statements:
                self.execute(statement)
        finally:
            self.environment = previous

    def evaluate(self, expression: expr.Expr) -> object:
        """Recursively evaluates an AST node and returns a Python object."""
        match expression:
            case expr.Literal(value):
                return value
            
            case expr.Grouping(inner_expr):
                return self.evaluate(inner_expr)
            
            case expr.Unary(operator, right_expr):
                right = self.evaluate(right_expr)
                
                if operator.type == TokenType.MINUS:
                    self.check_number_operand(operator, right)
                    return -float(right)
                elif operator.type == TokenType.BANG:
                    return not self.is_truthy(right)
            
            case expr.Binary(left_expr, operator, right_expr):
                left = self.evaluate(left_expr)
                right = self.evaluate(right_expr)
                
                if operator.type == TokenType.MINUS:
                    self.check_number_operands(operator, left, right)
                    return float(left) - float(right)
                elif operator.type == TokenType.SLASH:
                    self.check_number_operands(operator, left, right)
                    if float(right) == 0.0:
                        raise error.SnekRuntimeError(operator, "Division by zero.")
                    return float(left) / float(right)
                elif operator.type == TokenType.STAR:
                    self.check_number_operands(operator, left, right)
                    return float(left) * float(right)
                
                elif operator.type == TokenType.PLUS:
                    if isinstance(left, float) and isinstance(right, float):
                        return float(left) + float(right)
                    if isinstance(left, str) and isinstance(right, str):
                        return str(left) + str(right)
                    raise error.SnekRuntimeError(operator, "Operands must be two numbers or two strings.")
                
                elif operator.type == TokenType.GREATER:
                    self.check_number_or_string_operands(operator, left, right)
                    return left > right
                elif operator.type == TokenType.GREATER_EQUAL:
                    self.check_number_or_string_operands(operator, left, right)
                    return left >= right
                elif operator.type == TokenType.LESS:
                    self.check_number_or_string_operands(operator, left, right)
                    return left < right
                elif operator.type == TokenType.LESS_EQUAL:
                    self.check_number_or_string_operands(operator, left, right)
                    return left <= right
                
                elif operator.type == TokenType.BANG_EQUAL:
                    return not self.is_equal(left, right)
                elif operator.type == TokenType.EQUAL_EQUAL:
                    return self.is_equal(left, right)

            case expr.Ternary(condition_expr, then_expr, else_expr):
                cond_val = self.evaluate(condition_expr)
                if self.is_truthy(cond_val):
                    return self.evaluate(then_expr)
                else:
                    return self.evaluate(else_expr)

            case expr.Variable(name):
                distance = self.locals.get(id(expression))
                if distance is not None:
                    return self.environment.get_at(distance, name.lexeme)
                else:
                    return self.globals.get(name)
            
            case expr.Assign(name, value_expr):
                value = self.evaluate(value_expr)
                
                distance = self.locals.get(id(expression))
                if distance is not None:
                    self.environment.assign_at(distance, name, value)
                else:
                    self.globals.assign(name, value)
                    
                return value

            case expr.Logical(left_expr, operator, right_expr):
                left = self.evaluate(left_expr)

                if operator.type == TokenType.OR:
                    if self.is_truthy(left):
                        return left
                else: # TokenType.AND
                    if not self.is_truthy(left):
                        return left

                return self.evaluate(right_expr)

            case expr.Call(callee_expr, paren, arguments_exprs):
                callee = self.evaluate(callee_expr)

                arguments = []
                for arg in arguments_exprs:
                    arguments.append(self.evaluate(arg))

                if not isinstance(callee, SnekCallable):
                    raise error.SnekRuntimeError(paren, "Can only call functions and classes.")

                expected_arity = callee.arity()
                if expected_arity != -1 and len(arguments) != expected_arity:
                    raise error.SnekRuntimeError(paren, 
                        f"Expected {callee.arity()} arguments but got {len(arguments)}.")

                return callee.call(self, arguments)

            case expr.AnonymousFunction():
                return SnekFunction(expression, self.environment)

    def is_truthy(self, obj: object) -> bool:
        if obj is None:
            return False
        if isinstance(obj, bool):
            return obj
        return True

    def is_equal(self, a: object, b: object) -> bool:
        if a is None and b is None:
            return True
        if a is None:
            return False
        return a == b

    def check_number_operand(self, operator: Token, operand: object):
        if isinstance(operand, float):
            return
        raise error.SnekRuntimeError(operator, "Operand must be a number.")

    def check_number_operands(self, operator: Token, left: object, right: object):
        if isinstance(left, float) and isinstance(right, float):
            return
        raise error.SnekRuntimeError(operator, "Operands must be numbers.")

    def check_number_or_string_operands(self, operator: Token, left: object, right: object):
        if isinstance(left, float) and isinstance(right, float):
            return
        if isinstance(left, str) and isinstance(right, str):
            return
        raise error.SnekRuntimeError(operator, "Operands must be two numbers or two strings.")

    def stringify(self, obj: object) -> str:
        if obj is None:
            return "nil"
        
        if isinstance(obj, bool):
            return str(obj).lower()
        
        if isinstance(obj, float):
            text = str(obj)
            if text.endswith(".0"):
                text = text[:-2]
            return text
            
        return str(obj)
