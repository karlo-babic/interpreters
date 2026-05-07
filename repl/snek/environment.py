from token_class import Token
from error import SnekRuntimeError

class Environment:
    # Use quotes for forward reference to the class itself
    def __init__(self, enclosing: 'Environment | None' = None):
        self.values: dict[str, object] = {}
        self.enclosing = enclosing

    def define(self, name: str, value: object):
        """Binds a new name to a value in the current scope."""
        self.values[name] = value

    def get(self, name: Token) -> object:
        """Looks up a variable, walking the scope chain if necessary."""
        if name.lexeme in self.values:
            return self.values[name.lexeme]

        if self.enclosing is not None:
            return self.enclosing.get(name)

        raise SnekRuntimeError(name, f"Undefined variable '{name.lexeme}'.")

    def assign(self, name: Token, value: object):
        """Assigns a new value to an existing variable, walking the chain."""
        if name.lexeme in self.values:
            self.values[name.lexeme] = value
            return

        if self.enclosing is not None:
            self.enclosing.assign(name, value)
            return

        raise SnekRuntimeError(name, f"Undefined variable '{name.lexeme}'.")

    def ancestor(self, distance: int) -> 'Environment':
        environment = self
        for _ in range(distance):
            environment = environment.enclosing
        return environment

    def get_at(self, distance: int, name: str) -> object:
        return self.ancestor(distance).values.get(name)

    def assign_at(self, distance: int, name: Token, value: object):
        self.ancestor(distance).values[name.lexeme] = value