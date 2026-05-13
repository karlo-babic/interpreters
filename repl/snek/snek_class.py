from snek_callable import SnekCallable
from snek_instance import SnekInstance

class SnekClass(SnekCallable):
    def __init__(self, name: str, methods: dict[str, 'SnekFunction'], static_methods: dict[str, 'SnekFunction']):
        self.name = name
        self.methods = methods
        self.static_methods = static_methods
        
    def find_method(self, name: str) -> 'SnekFunction | None':
        return self.methods.get(name)

    def find_static_method(self, name: str) -> 'SnekFunction | None':
        return self.static_methods.get(name)

    def arity(self) -> int:
        initializer = self.find_method("init")
        if initializer is not None:
            return initializer.arity()
        return 0

    def call(self, interpreter, arguments: list[object]) -> object:
        instance = SnekInstance(self)
        
        initializer = self.find_method("init")
        if initializer is not None:
            initializer.bind(instance).call(interpreter, arguments)
            
        return instance

    def __str__(self):
        return self.name