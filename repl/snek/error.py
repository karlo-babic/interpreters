import sys
from token_class import Token

class SnekRuntimeError(Exception):
    def __init__(self, token: Token, message: str):
        super().__init__(message)
        self.token = token

# Global error flags
had_error = False
had_runtime_error = False

def error(line, message):
    """Reports a syntax error to the user."""
    report(line, "", message)

def report(line, where, message):
    global had_error
    print(f"[line {line}] Error{where}: {message}", file=sys.stderr)
    had_error = True

def runtime_error(err):
    global had_runtime_error
    print(f"{str(err)}\n[line {err.token.line}]", file=sys.stderr)
    had_runtime_error = True