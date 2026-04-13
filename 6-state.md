---
layout: default
title: "6. Statements and Global State"
nav_order: 7
---

# 6. Statements and Global State

The interpreter we have built so far feels less like a programming language and more like a desktop calculator. We can parse and evaluate complex mathematical and logical expressions, but a program is currently limited to a single line of execution. Furthermore, we cannot bind a name to data, making it impossible to compose software out of reusable pieces.

In this chapter, we will give our interpreter a memory. We will transition from evaluating isolated expressions to executing a top-down list of commands. We will define statements that produce output (`print`), create state (`var`), and modify that state (assignment). 

By the end of this chapter, your interpreter will be able to run multi-line scripts. 

## 1. Expressions vs. Statements

Up to this point, everything we have parsed has been an **expression**. An expression's primary job is to be evaluated to produce a value. `1 + 2` produces `3`. `"hello" == "world"` produces `false`. 

**Statements**, on the other hand, do not produce values. Their primary job is to produce an effect. Because they evaluate to nothing, to be useful, they must change the world in some way. This is called a **side effect**. Side effects include producing user-visible output or modifying the internal state of the interpreter.

We will start by adding the two simplest kinds of statements to Snek:
1.  **Expression Statements:** This allows you to place an expression where a statement is expected. You see this constantly in C or Java when you call a function and put a semicolon after it. 
2.  **Print Statements:** This evaluates an expression and displays the result to the user. We are baking `print` into the language as a statement rather than a library function so we can see the results of our interpreter working before we have to implement full function declarations.

Our new grammar rules for the top level of a Snek script are:

```text
program        → statement* EOF ;
statement      → exprStmt | printStmt ;
exprStmt       → expression ";" ;
printStmt      → "print" expression ";" ;
```

## 2. Representing Statements (AST)

Because expressions and statements serve fundamentally different roles, we do not mix them in the same class hierarchy. Operands of a `+` operator must be expressions, never statements. The body of a `while` loop must be a statement, never a raw expression. By separating them into two base classes, we leverage Python's type hints to catch architectural mistakes early.

Create a new file named `stmt.py` to hold our statement nodes:

```python
from dataclasses import dataclass
import expr

class Stmt:
    """Base class for all statement nodes."""
    pass

@dataclass
class Expression(Stmt):
    expression: expr.Expr

@dataclass
class Print(Stmt):
    expression: expr.Expr
```

> **Architecture Note:**
> Just like our `Expr` classes, these are pure data structures. They hold the data parsed from the source code, but they do not contain the logic for executing themselves.

## 3. Parsing Statements

Now we must update the Parser to produce a list of statements instead of a single expression. Open `parser.py` and add the new import at the top:

```python
import stmt
```

Next, rewrite your `parse` method. It is now the entry point for the `program` grammar rule. It will loop and parse statements until it hits the end of the file.

```python
    def parse(self) -> list[stmt.Stmt]:
        statements = []
        while not self.is_at_end():
            statements.append(self.statement())
        return statements
```

Now we implement `statement()`. We look at the current token to decide which statement rule to follow. If we see a `print` keyword, we parse a print statement. If not, we assume it is an expression statement.

```python
    def statement(self) -> stmt.Stmt:
        if self.match(TokenType.PRINT):
            return self.print_statement()
        
        return self.expression_statement()

    def print_statement(self) -> stmt.Stmt:
        value = self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after value.")
        return stmt.Print(value)

    def expression_statement(self) -> stmt.Stmt:
        expr_node = self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after expression.")
        return stmt.Expression(expr_node)
```

Notice how strictly we enforce the `;` token using `self.consume()`. In Snek, the semicolon is mandatory. 

## 4. Executing Statements

With our parser producing `Stmt` nodes, the interpreter must be updated to consume them. Open `interpreter.py` and add the imports:

```python
import stmt
import error
```

We need a new method to execute statements. This is the statement-equivalent of our existing `evaluate` method. It takes a `Stmt` node and uses Python's structural pattern matching to execute the appropriate side effect.

Add this `execute` method to your `Interpreter` class:

```python
    def execute(self, statement: stmt.Stmt):
        match statement:
            case stmt.Print(expression):
                value = self.evaluate(expression)
                print(self.stringify(value))
                
            case stmt.Expression(expression):
                self.evaluate(expression)
```

For a `Print` statement, we evaluate the inner expression, convert it to a string using our `stringify` helper, and output it to the console.
For an `Expression` statement, we evaluate the inner expression and entirely discard the result. The evaluation itself is the point (in case it does something like assign a variable later).

Finally, we need a public entry point for the interpreter that accepts a list of statements and executes them sequentially. Add this to your `Interpreter` class:

```python
    def interpret(self, statements: list[stmt.Stmt]):
        try:
            for statement in statements:
                self.execute(statement)
        except error.SnekRuntimeError as err:
            error.runtime_error(err)
```

### 4.1 Wiring it up

Open `snek.py`. We need to instantiate the `Interpreter` once and reuse it across multiple calls to `run()`, so that global variables persist throughout a REPL session. Add it as a class attribute:

```python
class Snek:
    interpreter = Interpreter()

    @staticmethod
    def main():
```

Then, replace the old single-expression execution logic at the bottom of the `run` method with the new statement list logic:

```python
    @staticmethod
    def run(source):
        # Scan the text into tokens
        scanner = Scanner(source)
        tokens = scanner.scan_tokens()

        # Parse the tokens into an AST
        parser = Parser(tokens)
        statements = parser.parse()

        # Stop if there was a syntax error.
        if error.had_error:
            return

        # Interpret the AST
        Snek.interpreter.interpret(statements)
```

**Test it out:**
Run your REPL and type the following:
`print 1 + 2;`
`print 3 * 4;`
Your interpreter should evaluate and print the results sequentially. Notice that if you just type `1 + 2;` without the `print` keyword, nothing prints. It is correctly parsed as an expression statement, evaluated, and the result is silently discarded.

## 5. Global State (The Environment)

Now that we have statements, we can introduce state. The bindings that associate variable names to values need to be stored somewhere in memory. This data structure is called an **Environment**.

We will start with the easiest kind of variables: global variables. To implement global state, we just need a data structure that can map string names to Python objects. A Python dictionary is perfect for this.

Create a new file named `environment.py`:

```python
from token_class import Token
from error import SnekRuntimeError

class Environment:
    def __init__(self):
        self.values: dict[str, object] = {}

    def define(self, name: str, value: object):
        """Binds a new name to a value."""
        self.values[name] = value

    def get(self, name: Token) -> object:
        """Looks up a variable by its token name."""
        if name.lexeme in self.values:
            return self.values[name.lexeme]

        raise SnekRuntimeError(name, f"Undefined variable '{name.lexeme}'.")
```

> **Python Toolbox: Encapsulation**
> Why create an `Environment` class instead of just using a raw `dict` inside the interpreter? 
> First, it encapsulates our specific error handling logic. If a variable is not found, we want to throw our custom `SnekRuntimeError` complete with the specific token for line number reporting. 
> Second, in the next chapter, we will implement local scoping by chaining multiple environments together. Having a dedicated class makes that transition seamless.

## 6. Variable Declarations and Access

To define and use variables, we add two new rules to our grammar. 

First, we separate statements into two tiers. A `varDecl` creates a binding. We allow declarations at the top level, but we do not allow them inside single-statement control flow branches (like `if (true) var a = 1;`).

```text
declaration    → varDecl | statement ;
varDecl        → "var" IDENTIFIER ( "=" expression )? ";" ;
```

Second, we add variable access to the bottom of the expression precedence ladder:

```text
primary        → NUMBER | STRING | "true" | "false" | "nil" 
               | "(" expression ")" 
               | IDENTIFIER ;
```

### 6.1 Syntax Trees

In `stmt.py`, add the variable declaration node. Notice that the initializer is optional.

```python
from token_class import Token

# ... existing code ...

@dataclass
class Var(Stmt):
    name: Token
    initializer: expr.Expr | None
```

In `expr.py`, add the variable access node:

```python
@dataclass
class Variable(Expr):
    name: Token
```

### 6.2 Parsing Variables

Open `parser.py`. We need to update our entry point to parse `declaration` instead of `statement`. This is also the exact moment we finally hook up our Panic Mode error recovery from Chapter 4.

Change `parse()` to call `declaration()`:

```python
    def parse(self) -> list[stmt.Stmt]:
        statements = []
        while not self.is_at_end():
            decl = self.declaration()
            if decl is not None:
                statements.append(decl)
        return statements
```

Now implement `declaration()`. If it catches a `ParseError`, it triggers synchronization.

```python
    def declaration(self) -> stmt.Stmt | None:
        try:
            if self.match(TokenType.VAR):
                return self.var_declaration()
            return self.statement()
        except ParseError:
            self.synchronize()
            return None
```

Next, implement `var_declaration()` to handle the identifier and optional initializer.

```python
    def var_declaration(self) -> stmt.Stmt:
        name = self.consume(TokenType.IDENTIFIER, "Expect variable name.")

        initializer = None
        if self.match(TokenType.EQUAL):
            initializer = self.expression()

        self.consume(TokenType.SEMICOLON, "Expect ';' after variable declaration.")
        return stmt.Var(name, initializer)
```

Finally, update `primary()` to recognize the `IDENTIFIER` token and create the variable access node. Add this right before the `LEFT_PAREN` check:

```python
        if self.match(TokenType.IDENTIFIER):
            return expr.Variable(self.previous())
```

### 6.3 Interpreting Variables

Open `interpreter.py`. We need to give our interpreter an instance of our new `Environment` to hold its memory. Add the import at the top:

```python
from environment import Environment
```

And initialize it inside the `Interpreter` class:

```python
class Interpreter:
    def __init__(self):
        self.environment = Environment()
        
    # ... existing code ...
```

Next, update the `match` block in `execute()` to handle the new `stmt.Var` node:

```python
            case stmt.Var(name, initializer):
                value = None
                if initializer is not None:
                    value = self.evaluate(initializer)
                self.environment.define(name.lexeme, value)
```

If the variable is declared without an initializer (e.g., `var a;`), it defaults to `None` (which Snek prints as `nil`).

Finally, update the `match` block in `evaluate()` to handle the `expr.Variable` node by looking it up in the environment:

```python
            case expr.Variable(name):
                return self.environment.get(name)
```

**Test it out:**
Your interpreter now has memory. Run your REPL and try:
```c
var a = 10;
var b = 20;
print a + b;
```
It should correctly print `30`.

## 7. Assignment

We can create new variables and access them, but we cannot modify them. Lox allows mutation, so we need assignment.

Assignment uses the `=` operator. It is the lowest precedence expression form, slotting just before `equality` (or `ternary`, if you implemented the challenge in Chapter 4).

```text
expression     → assignment ;
assignment     → IDENTIFIER "=" assignment | ternary ;
```

Because assignment is an expression, it evaluates to the assigned value. This allows chaining, like `a = b = 5;`. 

First, add the AST node to `expr.py`:

```python
@dataclass
class Assign(Expr):
    name: Token
    value: Expr
```

### 7.1 Parsing Assignment

Parsing assignment is uniquely tricky. A recursive descent parser with a single token of lookahead cannot tell that it is parsing an assignment until *after* it has parsed the entire left side and finally stumbled onto the `=` sign. 

We solve this by parsing the left side as if it were a normal expression. If we subsequently see an `=`, we look at the expression we just parsed and strictly validate that it is a valid assignment target (an l-value). If it is a `Variable` expression, we extract its token and convert it into an `Assign` node.

Update `parser.py`. Change your `expression()` method to call a new `assignment()` method instead of `equality()` (or instead of `ternary()` if you implemented the challenge in Chapter 4):

```python
    def expression(self) -> expr.Expr:
        return self.assignment()

    def assignment(self) -> expr.Expr:
        # Parse the left hand side as a normal expression
        expr_node = self.ternary() 

        if self.match(TokenType.EQUAL):
            equals = self.previous()
            # Recursively parse the right hand side
            value = self.assignment()

            # Validate the left hand side is an l-value
            if isinstance(expr_node, expr.Variable):
                name = expr_node.name
                return expr.Assign(name, value)

            # We report an error, but we do not throw ParseError because 
            # we aren't in a confused state that requires panic mode synchronization.
            self.error(equals, "Invalid assignment target.")

        return expr_node
```

### 7.2 Interpreting Assignment

An assignment modifies an existing variable. It is not allowed to create a new one. Let's add an `assign` method to our `Environment` in `environment.py` to enforce this rule:

```python
    def assign(self, name: Token, value: object):
        """Assigns a new value to an existing variable."""
        if name.lexeme in self.values:
            self.values[name.lexeme] = value
            return

        raise SnekRuntimeError(name, f"Undefined variable '{name.lexeme}'.")
```

Finally, update the `match` block in `evaluate()` in `interpreter.py` to execute the assignment:

```python
            case expr.Assign(name, value_expr):
                value = self.evaluate(value_expr)
                self.environment.assign(name, value)
                return value
```

We evaluate the right-hand side, assign it in the environment, and then return the value.

**Test it out:**
Run your interpreter and verify that state mutation works:
```c
var volume = 11;
print volume;
volume = 0;
print volume;
```

We have successfully transitioned our interpreter from a stateless calculator into a sequential script execution engine. In the next chapter, we will introduce blocks and local scoping to encapsulate state properly.

---

## 8. Challenges

### 1. REPL Usability
Currently, the REPL forces users to type `print 1 + 2;` just to see a mathematical result. This is tedious. Most REPLs (like Python's) automatically display the result if you type a raw expression, but remain silent if you type a statement.

Modify `snek.py` or your parser so that if the user types a raw expression in the interactive REPL (e.g., `1 + 2;`), it implicitly prints the value, but in script mode (when reading from a file) it behaves normally and discards the result.

<details>
<summary>Hint</summary>

There are a few ways to solve this. One approach is to catch raw `Expression` statements at the top level of the interpreter execution loop in `snek.py` (specifically only when in the `run_prompt` mode) and explicitly `print(interpreter.stringify(interpreter.evaluate(stmt.expression)))` instead of executing them.
</details>

### 2. Language Lawyer: Uninitialized Variables
Snek implicitly initializes variables to `nil` if an initializer is omitted (`var a;`). Research how three other languages handle uninitialized variables (e.g., Python, Go, C). 

What are the safety and usability trade-offs of Snek's approach? Could this design choice mask user errors? How would you modify Snek's `Environment` to throw a runtime error if a user attempted to read an unassigned variable?

### 3. Trace-it: Invalid Assignment
Assume a user inputs the following invalid code into Snek:
`a + b = c;`

Write out the step-by-step trace of exactly what the `assignment()` parsing does. At what point does it evaluate `a + b`, when does it find the `=`, and how does the `isinstance` validation check ultimately catch the error?