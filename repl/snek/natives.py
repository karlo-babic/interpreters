import time
from snek_callable import SnekCallable

class ClockCallable(SnekCallable):
    def arity(self) -> int:
        return 0
        
    def call(self, interpreter, arguments: list[object]) -> object:
        return time.time()
        
    def __str__(self):
        return "<native fn>"

class InputCallable(SnekCallable):
    def arity(self) -> int:
        return -1 # -1 signifies variable arity
        
    def call(self, interpreter, arguments: list[object]) -> object:
        prompt = ""
        if len(arguments) > 0:
            prompt = interpreter.stringify(arguments[0])
            
        try:
            return input(prompt)
        except EOFError:
            return None
            
    def __str__(self):
        return "<native fn>"

class ToNumberCallable(SnekCallable):
    def arity(self) -> int:
        return 1
        
    def call(self, interpreter, arguments: list[object]) -> object:
        value = arguments[0]
        try:
            return float(value)
        except (ValueError, TypeError):
            # We can either return None, or raise a runtime error.
            # Returning None allows the Snek programmer to check if the cast failed.
            return None
            
    def __str__(self):
        return "<native fn>"

class ToStringCallable(SnekCallable):
    def arity(self) -> int:
        return 1
        
    def call(self, interpreter, arguments: list[object]) -> object:
        value = arguments[0]
        try:
            return str(value)
        except (ValueError, TypeError):
            # We can either return None, or raise a runtime error.
            # Returning None allows the Snek programmer to check if the cast failed.
            return None
            
    def __str__(self):
        return "<native fn>"