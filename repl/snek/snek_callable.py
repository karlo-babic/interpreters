from abc import ABC, abstractmethod

class SnekCallable(ABC):
    @abstractmethod
    def arity(self) -> int:
        """Returns the number of arguments the function expects."""
        pass

    @abstractmethod
    def call(self, interpreter, arguments: list[object]) -> object:
        """Executes the function body and returns a value."""
        pass
