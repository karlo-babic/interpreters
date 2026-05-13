from token_class import Token
import error

class SnekInstance:
    def __init__(self, klass: 'SnekClass'):
        self.klass = klass
        self.fields: dict[str, object] = {}

    def get(self, name: Token) -> object:
        if name.lexeme in self.fields:
            return self.fields[name.lexeme]
            
        method = self.klass.find_method(name.lexeme)
        if method is not None:
            return method.bind(self)
            
        raise error.SnekRuntimeError(name, f"Undefined property '{name.lexeme}'.")

    def set(self, name: Token, value: object):
        self.fields[name.lexeme] = value

    def __str__(self):
        return f"{self.klass.name} instance"