from snek_callable import SnekCallable
import stmt
from environment import Environment
from return_class import ReturnException
import expr

class SnekFunction(SnekCallable):
    def __init__(self, declaration: stmt.Function | expr.AnonymousFunction, closure: Environment, is_initializer: bool = False):
        self.declaration = declaration
        self.closure = closure
        self.is_initializer = is_initializer

    def arity(self) -> int:
        return len(self.declaration.params)

    def call(self, interpreter, arguments: list[object]) -> object:
        environment = Environment(self.closure)
        for i in range(len(self.declaration.params)):
            environment.define(self.declaration.params[i].lexeme, arguments[i])

        try:
            interpreter.execute_block(self.declaration.body, environment)
        except ReturnException as return_value:
            if self.is_initializer:
                return self.closure.get_at(0, "this")
            return return_value.value
            
        if self.is_initializer:
            return self.closure.get_at(0, "this")
        return None

    def bind(self, instance: 'SnekInstance') -> 'SnekFunction':
        environment = Environment(self.closure)
        environment.define("this", instance)
        return SnekFunction(self.declaration, environment, self.is_initializer)

    def __str__(self):
        if isinstance(self.declaration, stmt.Function):
            return f"<fn {self.declaration.name.lexeme}>"
        return "<fn anonymous>"