import sys
import error
import stmt
from scanner import Scanner
from parser import Parser
from ast_printer import AstPrinter
from interpreter import Interpreter
from resolver import Resolver

class Snek:
    interpreter = Interpreter()

    @staticmethod
    def main():
        """Main entry point for the interpreter."""
        args = sys.argv[1:]
        
        if len(args) > 1:
            print("Usage: python snek.py [script]")
            sys.exit(1)
        elif len(args) == 1:
            Snek.run_file(args[0])
        else:
            Snek.run_prompt()

    @staticmethod
    def run_file(path):
        """Executes a script from a file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                script = f.read()
            Snek.run(script)
            
            # If there was an error during execution, exit with an error code.
            if error.had_error:
                sys.exit(1)
            if error.had_runtime_error:
                sys.exit(1)
        except FileNotFoundError:
            print(f"Could not find file: {path}")
            sys.exit(1)

    @staticmethod
    def run_prompt():
        """Runs the interactive REPL."""
        print("Snek REPL (Type 'exit' or Ctrl+D/Ctrl+C to quit)")
        while True:
            try:
                line = input("> ")
                # Check for explicit exit command
                if line.strip() == "exit":
                    break
                Snek.run(line, repl_mode=True)
                # We reset the error flag in the REPL so one mistake 
                # doesn't kill the entire session.
                error.had_error = False
            except (EOFError, KeyboardInterrupt):
                # Catches Ctrl+D (Unix) or Ctrl+C (Windows)
                print("\nExiting...")
                break

    @staticmethod
    def run(source, repl_mode=False):
        # Scan the text into tokens
        scanner = Scanner(source)
        tokens = scanner.scan_tokens()

        # Parse the tokens into an AST
        parser = Parser(tokens)
        statements = parser.parse()

        # Stop if there was a syntax error.
        if error.had_error:
            return

        # Run the Semantic Analysis pass
        resolver = Resolver(Snek.interpreter)
        resolver.resolve_statements(statements)

        # Stop if there was a resolution error.
        if error.had_error:
            return

        # Interpret the AST
        if repl_mode and len(statements) == 1 and isinstance(statements[0], stmt.Expression):
            # Intercept raw expressions in the REPL
            try:
                result = Snek.interpreter.evaluate(statements[0].expression)
                print(Snek.interpreter.stringify(result))
            except error.SnekRuntimeError as err:
                error.runtime_error(err)
        else:
            Snek.interpreter.interpret(statements)

if __name__ == "__main__":
    Snek.main()
