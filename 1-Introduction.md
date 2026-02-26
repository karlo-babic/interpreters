---
layout: default
title: "1. Introduction"
nav_order: 2
---

# 1. Introduction

In this course, we will build an interpreter for a programming language called **Snek**. While Snek is a small language, it is not a toy; it features dynamic typing, garbage collection, closures, and object-oriented programming.

We will implement Snek using **Python**. In interpreter terminology, Python is our **Host Language** (the language we write the interpreter in) and Snek is our **Guest Language** (the language our interpreter executes).

## 1. The Snek Language

Snek syntax is derived from the C-family (C, Java, JavaScript), making it familiar to most programmers.

Here is an example of what valid Snek code looks like:

```c
// A function declaration
fun fib(n) {
  if (n < 2) return n;
  return fib(n - 1) + fib(n - 2);
}

// A class declaration
class Greeter {
  init(name) {
    this.name = name;
  }

  sayHello() {
    print "Hello, " + this.name + "!";
  }
}

var start = clock();
print fib(10);
print clock() - start;
```

Our goal is to write a Python program that can read this text and execute it.

## 2. Architecture

An interpreter is a pipeline. It takes raw source code in one end and processes it through several distinct stages.

### A. Scanning (Lexical Analysis)
The first step is to group the raw characters of the source code into meaningful chunks called **tokens**. This is similar to how we group letters into words when reading English.
*   **Input:** `var score = 10;`
*   **Output:** `[VAR, IDENTIFIER("score"), EQUAL, NUMBER(10), SEMICOLON]`

### B. Parsing
The next step is to impose grammatical structure on the tokens. We organize them into a tree structure called an **Abstract Syntax Tree (AST)**. This tree represents the nesting and hierarchy of the code.
*   **Input:** The list of tokens from the Scanner.
*   **Output:** A tree structure representing the statement.
    ```text
    VariableDeclaration
    ├── name: "score"
    └── initializer: Literal
        └── value: 10
    ```

### C. Static Analysis
Before running the code, we do a pass over the AST to check for logical errors and resolve variable scopes. This ensures that variables refer to the correct declarations.

### D. Interpretation
Finally, we traverse the AST and execute the logic. This is where the code actually "runs."

## 3. Project Setup

Create a directory for your project. Inside, we will create a main entry point file named `snek.py`.

**Requirements:**
*   You must use **Python 3.10** or newer. We will use the `match` / `case` syntax introduced in 3.10 for pattern matching in later chapters.

## 4. The Main Entry Point

Our first task is to build the shell of the interpreter. This script will handle input from the user and error reporting.

The interpreter supports two modes of operation:
1.  **Script Mode:** If you provide a filename argument, it reads and executes that file.
2.  **REPL (Read-Eval-Print Loop):** If you provide no arguments, it opens an interactive prompt where you can type code and execute it line-by-line.

### Implementation

Create `snek.py` and add the following code structure. 

**A note on Python style:** You might wonder why we are using a `Snek` class filled with `@staticmethod`s instead of standard top-level Python functions. The book uses Java, which requires all code to reside inside a class. The author uses `static` methods and variables to manage the global state of the interpreter (like whether a syntax error has occurred). 

While we could use global variables in Python, using a class as a "namespace" to group our interpreter's state and main functions keeps our architecture cleanly encapsulated and closely aligned with the book's structure.

```python
import sys

class Snek:
    had_error = False

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
            if Snek.had_error:
                sys.exit(1)
        except FileNotFoundError:
            print(f"Could not find file: {path}")
            sys.exit(1)

    @staticmethod
    def run_prompt():
        """Runs the interactive REPL."""
        print("Snek REPL (Type 'exit' to quit)")
        while True:
            try:
                line = input("> ")
                # Check for explicit exit command
                if line.strip() == "exit":
                    break
                Snek.run(line)
                # We reset the error flag in the REPL so one mistake 
                # doesn't kill the entire session.
                Snek.had_error = False
            except (EOFError, KeyboardInterrupt):
                # Catches Ctrl+D (Unix) or Ctrl+Z+Enter (Windows)
                print("\nExiting...")
                break

    @staticmethod
    def run(source):
        """The core execution logic."""
        # For now, we just print the code to prove we received it.
        # Later, this will connect to the Scanner and Parser.
        print(f"DEBUG: Received {len(source)} characters.")

    @staticmethod
    def error(line, message):
        """Reports an error to the user."""
        Snek.report(line, "", message)

    @staticmethod
    def report(line, where, message):
        print(f"[line {line}] Error{where}: {message}", file=sys.stderr)
        Snek.had_error = True

if __name__ == "__main__":
    Snek.main()
```

### Error Handling

Robust error handling is critical for a language. Note the `had_error` flag.
*   In **Script Mode**, if an error occurs, we must ensure the process exits with a failure code so that other scripts or build tools know it failed.
*   In **REPL Mode**, we report the error but reset the flag. We do not want to crash the interpreter just because the user made a typo.

## 5. Exercise

1.  Create the `snek.py` file with the code above.
2.  **Test the REPL:**
    *   Run `python3 snek.py`.
    *   Type some text and press Enter. You should see the debug message.
    *   Exit using `Ctrl+D` (Linux/Mac) or `Ctrl+Z` (Windows).
3.  **Test Script Mode:**
    *   Create a dummy file named `hello.snek` with some text inside.
    *   Run `python3 snek.py hello.snek`.
    *   Ensure it reads the file and prints the debug message.