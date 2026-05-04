---
layout: default
title: "8. Functions and Closures"
nav_order: 9
---

# 8. Functions and Closures

Our interpreter has grown from a simple calculator into a sequential script execution engine. It has variables, memory, and control flow. But it is missing the most fundamental tool for abstraction: functions. Right now, to repeat a complex operation, you have to copy and paste the code. 

In this chapter, we will introduce first-class functions. We will implement function calls, parameter binding, return statements, and the crowning achievement of lexical scope: closures.

## 1. Function Calls

Before we can define our own functions, we need a way to call them. You are familiar with C-style function call syntax, but its placement in the grammar is more subtle than you might expect.

Typically, we call named functions like `average(1, 2);`. However, the name of the function is not actually part of the call syntax. The thing being called (the callee) can be *any* expression that evaluates to a function. For example: `get_callback()();`. 

Because of this, we treat a function call as a postfix operator that starts with a `(`. It has the highest precedence, binding even tighter than unary operators. We slot it into the parser by redirecting the `unary` rule to a new `call` rule.

```text
unary          → ( "!" | "-" ) unary | call ;
call           → primary ( "(" arguments? ")" )* ;
arguments      → expression ( "," expression )* ;
```

Notice the `*` at the end of the `call` rule. This allows matching a series of chained calls like `fn(1)(2)(3)`.

### 1.1 The Call AST Node

First, add the new AST node to `expr.py`.

```python
@dataclass
class Call(Expr):
    callee: Expr
    paren: Token
    arguments: list[Expr]
```

We store the `callee` expression, the list of evaluated `arguments`, and the closing parenthesis token (`paren`). We keep the parenthesis token so we can use its line number if a runtime error occurs during the call.

### 1.2 Parsing Calls

Open `parser.py`. Right now, the `unary()` method falls through to `primary()`. Change it to fall through to `call()` instead.

```python
    def unary(self) -> expr.Expr:
        if self.match(TokenType.BANG, TokenType.MINUS):
            operator = self.previous()
            right = self.unary()
            return expr.Unary(operator, right)

        return self.call()
```

Now implement the `call()` method. It parses the left operand (the primary expression), and then enters a loop to see if the resulting expression is called.

```python
    def call(self) -> expr.Expr:
        expr_node = self.primary()

        while True:
            if self.match(TokenType.LEFT_PAREN):
                expr_node = self.finish_call(expr_node)
            else:
                break

        return expr_node
```

The loop handles chaining. We rely on a helper method `finish_call()` to parse the argument list.

```python
    def finish_call(self, callee: expr.Expr) -> expr.Expr:
        arguments = []
        if not self.check(TokenType.RIGHT_PAREN):
            while True:
                if len(arguments) >= 255:
                    self.error(self.peek(), "Can't have more than 255 arguments.")
                arguments.append(self.expression())
                if not self.match(TokenType.COMMA):
                    break

        paren = self.consume(TokenType.RIGHT_PAREN, "Expect ')' after arguments.")
        return expr.Call(callee, paren, arguments)
```

> **Technical Note: Maximum Argument Counts**
>
> We validate that the argument list does not exceed 255 items. The C standard dictates that a conforming implementation must support *at least* 127 arguments, and Java caps methods at 255. Our Python tree-walk interpreter does not strictly need this limit. Note that we `error()` but do not `raise ParseError`, so the parser logs the mistake and continues without entering panic mode.

### 1.3 Interpreting Calls

We need to add execution logic for `expr.Call`. But what exactly are we calling? We need a representation for callable objects in our Python host environment. 

Create a new file named `snek_callable.py` to define an interface for anything that behaves like a function.

```python
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
```

Now, open `interpreter.py`, add `from snek_callable import SnekCallable` at the top, and add the evaluation logic to your `evaluate` method.

```python
            case expr.Call(callee_expr, paren, arguments_exprs):
                callee = self.evaluate(callee_expr)

                arguments = []
                for arg in arguments_exprs:
                    arguments.append(self.evaluate(arg))

                if not isinstance(callee, SnekCallable):
                    raise error.SnekRuntimeError(paren, "Can only call functions and classes.")

                if len(arguments) != callee.arity():
                    raise error.SnekRuntimeError(paren, 
                        f"Expected {callee.arity()} arguments but got {len(arguments)}.")

                return callee.call(self, arguments)
```

We evaluate the callee and all of its arguments. Then, we check two critical things:
1. Is the object actually callable? If the user types `"string"();`, we intercept it and raise a `SnekRuntimeError` instead of letting Python crash.
2. Does the argument count match the function's arity? Unlike JavaScript (which silently ignores extra arguments) we follow Python's stricter approach and raise an error if the counts mismatch.

### 1.4 Native Functions

Our interpreter knows how to call functions, but we have not implemented function declarations yet. How can we test this? We can inject "Native Functions" directly into the global environment. Native functions are provided by the interpreter and implemented in the host language (Python).

Let us add a `clock()` function that returns the current time. This will be useful later for benchmarking.

To keep our architecture clean and separate host-language implementations from our core interpreter logic, create a new file named `natives.py`:

```python
import time
from snek_callable import SnekCallable

class ClockCallable(SnekCallable):
    def arity(self) -> int:
        return 0
        
    def call(self, interpreter, arguments: list[object]) -> object:
        return time.time()
        
    def __str__(self):
        return "<native fn>"
```

Now, open `interpreter.py`. We will add a `self.globals` field to our `Interpreter` class. We want native functions to reside in the outermost global scope, regardless of how deeply nested the current `self.environment` is. 

Add `import natives` to the top of the file, and update the `__init__` method:

```python
import natives

class Interpreter:
    def __init__(self):
        self.globals = Environment()
        self.environment = self.globals
        
        # Define native functions
        self.globals.define("clock", natives.ClockCallable())
```

**Test it out:**
Run your REPL and type `print clock();`. You should see a large Unix timestamp print out. Our call machinery is officially working.

## 2. Function Declarations

Now we give users the power to define their own functions. A function declaration binds a name to a block of code and a list of parameters. 

```text
declaration    → funDecl | varDecl | statement ;
funDecl        → "fun" function ;
function       → IDENTIFIER "(" parameters? ")" block ;
parameters     → IDENTIFIER ( "," IDENTIFIER )* ;
```

In `stmt.py`, add the AST node:

```python
@dataclass
class Function(Stmt):
    name: Token
    params: list[Token]
    body: list[Stmt]
```

In `parser.py`, update `declaration()` to check for the `fun` keyword:

```python
    def declaration(self) -> stmt.Stmt | None:
        try:
            if self.match(TokenType.FUN):
                return self.function("function")
            if self.match(TokenType.VAR):
                return self.var_declaration()
            return self.statement()
        except ParseError:
            self.synchronize()
            return None
```

We delegate to a new `function(kind)` method. We pass `"function"` as a string because later, we will reuse this exact same method to parse methods inside classes, and we want our error messages to reflect what is currently being parsed.

```python
    def function(self, kind: str) -> stmt.Stmt:
        name = self.consume(TokenType.IDENTIFIER, f"Expect {kind} name.")
        self.consume(TokenType.LEFT_PAREN, f"Expect '(' after {kind} name.")

        parameters = []
        if not self.check(TokenType.RIGHT_PAREN):
            while True:
                if len(parameters) >= 255:
                    self.error(self.peek(), "Can't have more than 255 parameters.")
                parameters.append(self.consume(TokenType.IDENTIFIER, "Expect parameter name."))
                if not self.match(TokenType.COMMA):
                    break
        
        self.consume(TokenType.RIGHT_PAREN, "Expect ')' after parameters.")
        self.consume(TokenType.LEFT_BRACE, f"Expect '{{' before {kind} body.")
        
        body = self.block()
        return stmt.Function(name, parameters, body)
```

## 3. Function Objects

A parsed `stmt.Function` is just an AST node. We need a runtime representation of it that implements our `SnekCallable` interface. Create a new file called `snek_function.py`.

```python
from snek_callable import SnekCallable
import stmt
from environment import Environment

class SnekFunction(SnekCallable):
    def __init__(self, declaration: stmt.Function):
        self.declaration = declaration

    def arity(self) -> int:
        return len(self.declaration.params)

    def call(self, interpreter, arguments: list[object]) -> object:
        # Create a new environment for the function call
        environment = Environment(interpreter.globals)

        # Bind the arguments to the parameters
        for i in range(len(self.declaration.params)):
            environment.define(self.declaration.params[i].lexeme, arguments[i])

        # Execute the function body
        interpreter.execute_block(self.declaration.body, environment)
        
        return None

    def __str__(self):
        return f"<fn {self.declaration.name.lexeme}>"
```

This is the core of how functions operate. When a function is called:
1. We create a *brand new* `Environment`. This prevents recursive calls from overwriting each other's variables.
2. We link this new environment to the `globals` environment. 
3. We bind the passed arguments to the parameter names.
4. We instruct the interpreter to execute the body block inside this new environment.

Finally, we need to interpret the declaration itself. In `interpreter.py`, add `from snek_function import SnekFunction`, and add the logic to your `execute()` method:

```python
            case stmt.Function(name, params, body):
                function = SnekFunction(statement)
                self.environment.define(name.lexeme, function)
```

**Test it out:**
```c
fun sayHi(first, last) {
  print "Hi, " + first + " " + last + "!";
}
sayHi("Dear", "Reader");
```
Your interpreter can now define and execute functions!

## 4. Return Statements

We can pass data *into* functions, but we have no way to get data *out*. Since Snek's function bodies are blocks of statements (which do not evaluate to values), we need a dedicated `return` statement. 

```text
statement      → exprStmt | forStmt | ifStmt | printStmt | returnStmt | whileStmt | block ;
returnStmt     → "return" expression? ";" ;
```

Add the AST node to `stmt.py`:
```python
@dataclass
class Return(Stmt):
    keyword: Token
    value: Expr | None
```

In `parser.py`, update `statement()` to match it:
```python
        if self.match(TokenType.RETURN):
            return self.return_statement()
```

And parse it:
```python
    def return_statement(self) -> stmt.Stmt:
        keyword = self.previous()
        value = None
        if not self.check(TokenType.SEMICOLON):
            value = self.expression()

        self.consume(TokenType.SEMICOLON, "Expect ';' after return value.")
        return stmt.Return(keyword, value)
```

### 4.1 Stack Unwinding

Interpreting a `return` statement is uniquely difficult in a tree-walk interpreter. You can return from anywhere within a function, even deeply nested inside an `if` statement that is inside a `while` loop. 

When the `return` is executed, the interpreter must instantly stop executing the current block, jump all the way out of all enclosing blocks, and hand the value back to the `SnekFunction.call()` method. 

> **Python Toolbox: Exceptions for Control Flow**
>
> In Python, the cleanest way to immediately abort a deep call stack is to raise an Exception. We will throw a custom `ReturnException` containing the return value, and catch it at the top level of the function call. 

Create a new exception class in a file named `return_class.py` (to avoid clashing with the `stmt.Return` node):

```python
class ReturnException(Exception):
    def __init__(self, value: object):
        super().__init__()
        self.value = value
```

In `interpreter.py`, add `from return_class import ReturnException`, and add the execution logic to `execute()`:

```python
            case stmt.Return(keyword, value_expr):
                value = None
                if value_expr is not None:
                    value = self.evaluate(value_expr)
                raise ReturnException(value)
```

Finally, we catch this exception in `snek_function.py`. Update your `call()` method:

```python
from return_class import ReturnException

    def call(self, interpreter, arguments: list[object]) -> object:
        environment = Environment(interpreter.globals)
        for i in range(len(self.declaration.params)):
            environment.define(self.declaration.params[i].lexeme, arguments[i])

        try:
            interpreter.execute_block(self.declaration.body, environment)
        except ReturnException as return_value:
            return return_value.value
            
        return None
```

**Test it out:**
You can now calculate Fibonacci numbers using recursion.
```c
fun fib(n) {
  if (n <= 1) return n;
  return fib(n - 2) + fib(n - 1);
}

for (var i = 0; i < 15; i = i + 1) {
  print fib(i);
}
```

## 5. Closures

Our functions are powerful, but they have a subtle bug. Look closely at how we initialize the `Environment` in `SnekFunction.call()`:

```python
environment = Environment(interpreter.globals)
```

We always set the parent environment to `globals`. If a variable is not found inside the function, the interpreter looks directly in the global scope. This works for top-level functions, but what about local functions nested inside other functions?

```c
fun makeCounter() {
  var i = 0;
  fun count() {
    i = i + 1;
    print i;
  }

  return count;
}

var counter = makeCounter();
counter();
```

Here, `count()` tries to use `i`, which is declared outside of itself in `makeCounter()`. `makeCounter()` returns a reference to the `count` function and then finishes. By the time `counter()` is executed at the top level, `makeCounter()` has already exited.

If you run this code right now, Snek throws an `Undefined variable 'i'` error. Because we hardcoded `interpreter.globals` as the parent environment, `count()` cannot see `i`. 

To fix this, functions must "close over" and hold onto the environment where they were declared. This data structure is called a **closure**. 

Open `snek_function.py` and modify the constructor to accept and store the active environment:

```python
class SnekFunction(SnekCallable):
    def __init__(self, declaration: stmt.Function, closure: Environment):
        self.declaration = declaration
        self.closure = closure
        
    # ...
```

Update `call()` to use this closure as the parent environment, rather than `globals`:

```python
    def call(self, interpreter, arguments: list[object]) -> object:
        environment = Environment(self.closure)
        # ... rest of the method ...
```

Finally, over in `interpreter.py`, when we execute a `stmt.Function` declaration inside our `execute()` method's `match` block, we pass the current active environment to the constructor:

```python
            case stmt.Function(name, params, body):
                function = SnekFunction(statement, self.environment)
                self.environment.define(name.lexeme, function)
```

**Test it out:**
Run the `makeCounter` example again. It should print `1`. If you call `counter()` again, it will print `2`. The `count` function successfully captured and retained its surrounding environment.

Our interpreter now supports true lexical scoping and closures. However, our reliance on purely dynamic environment chains creates a subtle performance and semantics problem. In the next chapter, we will write a static semantic analysis pass to make our closures completely bulletproof.

---

## 6. Challenges

### 1. Expanding the Standard Library (`input` and `toNumber`)
Currently, Snek can print to the console and check the time, but it cannot receive input from the user.

Your challenge is to expand Snek's standard library by adding an `input()` native function. Furthermore, make the prompt string **optional**, so both of these Snek scripts work:

**Example A:**
```c
print "What is your name?";
var name = input();
print "Hello, " + name;
```

**Example B:**
```c
var name = input("What is your name? ");
print "Hello, " + name;
```

Once you get `input` working, consider this third example.

**Example C (The Math Problem):**
```c
var age_str = input("How old are you? ");
// var future_age = age_str + 10; // This would crash.
var future_age = toNumber(age_str) + 10;
print "In ten years, you will be:";
print future_age;
```

If you try to add `10` directly to the result of `input()`, Snek will throw a runtime error. Unlike JavaScript, Snek does not implicitly cast strings to numbers during addition. 

To complete this challenge, you must also implement a second native function, `toNumber(value)`, which parses a string into a number. This will allow Example C to execute successfully.

<details>
<summary>Implementation Hints</summary>

1. **Variable Arity:** Snek's current `SnekCallable` interface assumes every function has an exact, fixed number of arguments. Because `input` can take 0 or 1 arguments, you will need to modify your interpreter to support variable arity. A simple workaround is to have `arity()` return `-1`. Then, update your `interpreter.py` to skip the strict `len(arguments) != callee.arity()` check if the expected arity is `-1`.
2. **The Input Native Function:** Open `natives.py` and create an `InputCallable` class. Inside `call()`, check the length of `arguments`. If an argument was provided, convert it to a string using `interpreter.stringify()` and pass it to Python's built-in `input(prompt)` function.
3. **The ToNumber Native Function:** Create a `ToNumberCallable` class with an arity of 1. Inside `call()`, attempt to pass the argument to Python's `float()` function. If the string is invalid and Python raises a `ValueError` (for example, if the user typed "hello"), catch it and return `None` (which represents `nil` in Snek) or raise a `SnekRuntimeError`.
4. **Registration:** Open `interpreter.py` and register both new functions in the `__init__` method using `self.globals.define(...)`.
</details>

### 2. Semantic Extension: Anonymous Functions (Lambdas)
Snek's function declaration syntax creates a function and binds it to a name simultaneously. In functional programming, it is common to create a function and pass it directly to another function without naming it.

Add anonymous function syntax to Snek so the following code works:
```c
fun thrice(fn) {
  for (var i = 1; i <= 3; i = i + 1)
    fn(i);
}

thrice(fun (x) { print x*x; });
```

<details>
<summary>Implementation Hints</summary>

This exercise reinforces the difference between **Statements** (which do not evaluate to values) and **Expressions** (which do). An anonymous function evaluates to a callable object, so it must be parsed as an expression.

**1. The AST (`expr.py`)**
Add a new node (`AnonymousFunction`) to `expr.py`. Notice it does *not* have a `name` field, because anonymous functions do not have names! You should include the `keyword` token (the `fun` token itself) so you can report accurate line numbers if a runtime error occurs inside the function.

**2. The Parser (`parser.py`)**
You will need to intercept the `fun` keyword inside the `primary()` expression parser. To avoid cluttering `primary()`, it is best to delegate to a helper method.

```python
    def primary(self) -> expr.Expr:
        # ... [existing literal checks] ...

        if self.match(TokenType.FUN):
            return self.anonymous_function()
            
        # ... [rest of primary] ...
```

In your `anonymous_function()` helper, you will parse the parameter list and the body block. This logic will look almost identical to your existing `function()` statement parser, just without expecting an identifier name at the beginning. Once parsed, return your new `expr.AnonymousFunction` node.

**3. The Interpreter (`interpreter.py` and `snek_function.py`)**
In the `evaluate()` method, we handle the `expr.AnonymousFunction` node. We need to instantiate and return a `SnekFunction` object:
```python
            case expr.AnonymousFunction():
                return SnekFunction(expression, self.environment)
```

However, `SnekFunction` currently expects a `stmt.Function` declaration. We need to refactor `SnekFunction` to accept `expr.AnonymousFunction` as well.

*   Open `snek_function.py`.
*   Update the `__init__` method's type hint so `declaration` can be either a `stmt.Function` or an `expr.AnonymousFunction`.
*   Because both AST nodes have `.params` and `.body` fields, your `call()` method and `arity()` method will continue to work perfectly without any changes.
*   The only method you need to update is `__str__()`. Check which type of node `self.declaration` is. If it is a `stmt.Function`, return `<fn name>`. Otherwise (if it is an anonymous expression) return `<fn anonymous>`.
</details>

### 3. Trace-it: The Closure Chain
Given the following Snek code, draw or explain the exact chain of `Environment` objects starting from the innermost scope at the moment `print a + b + c;` is executed.

```c
var a = "global";
fun outer() {
  var b = "outer";
  fun inner() {
    var c = "inner";
    print a + b + c;
  }
  return inner;
}
var fn = outer();
fn();
```

<details>
<summary>Answer</summary>

1. **Innermost Environment:** Created dynamically when `fn()` (which is `inner`) is called. Contains `{ "c": "inner" }`. Its enclosing parent is...
2. **Closure Environment:** Captured when `inner` was declared inside `outer`. Contains `{ "b": "outer", "inner": <fn inner> }`. Its enclosing parent is...
3. **Global Environment:** Contains `{ "a": "global", "outer": <fn outer>, "fn": <fn inner> }`.
</details>