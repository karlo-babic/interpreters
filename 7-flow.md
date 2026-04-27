---
layout: default
title: "7. Blocks & Control Flow"
nav_order: 8
---

# 7. Blocks, Local Scope, & Control Flow

At the end of the previous chapter, our interpreter gained memory. It can now store and recall variables. However, all variables reside in a single, global environment. Furthermore, our scripts execute strictly from top to bottom, one statement at a time. 

To elevate our language from a calculator to a Turing-complete programming language, we must introduce conditional execution (branching) and repetition (looping). We also need to introduce block scoping to ensure our programs can scale without global variable collisions.

## 1. Local Scope and Environments

Lexical scope defines a region in the source code where a variable name maps to a specific value. In most modern C-family languages, scope is controlled by curly-braced blocks (`{ ... }`). 

When a block introduces a local variable with the same name as a global variable, the local variable "shadows" the global one. The inner code sees the local variable, but once the block ends, the global variable becomes visible again. 

To implement this, we need to chain environments together. When we enter a new block, we create a new environment for the local scope and point its "enclosing" reference to the outer scope. When looking up a variable, we search the innermost environment first. If it is not found, we walk up the chain.

Open `environment.py` and modify the `Environment` class:

```python
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
```

Notice that `define()` always operates on the innermost `self.values` dictionary. We never "re-define" variables in outer scopes; we only create them locally. However, `assign()` and `get()` walk the `self.enclosing` chain recursively until they find the variable.

## 2. Blocks

With the environment chain ready, we can add the syntax for blocks. Here are our new grammar rules:

```text
statement  → exprStmt
           | printStmt
           | block ;

block      → "{" declaration* "}" ;
```

First, add the new AST node to `stmt.py`:
```python
@dataclass
class Block(Stmt):
    statements: list[Stmt]
```

Next, update `parser.py` to recognize and parse blocks. Update your `statement()` method:

```python
    def statement(self) -> stmt.Stmt:
        if self.match(TokenType.PRINT):
            return self.print_statement()
        if self.match(TokenType.LEFT_BRACE):
            return stmt.Block(self.block())
        
        return self.expression_statement()
```

Then, implement the `block()` helper. Notice that we return a list of statements rather than the `Block` node directly. We will reuse this raw list parser when we implement function bodies in a future chapter.

```python
    def block(self) -> list[stmt.Stmt]:
        statements = []

        while not self.check(TokenType.RIGHT_BRACE) and not self.is_at_end():
            decl = self.declaration()
            if decl is not None:
                statements.append(decl)

        self.consume(TokenType.RIGHT_BRACE, "Expect '}' after block.")
        return statements
```

Finally, we must interpret the block. Open `interpreter.py` and add a new helper method:

```python
    def execute_block(self, statements: list[stmt.Stmt], environment: Environment):
        previous = self.environment

        try:
            self.environment = environment
            for statement in statements:
                self.execute(statement)
        finally:
            self.environment = previous
```

> **Python Toolbox: `try...finally`**
>
> When executing a block, we temporarily replace the interpreter's current environment with a new local one. Once the block finishes, we *must* restore the previous environment. 
> 
> If a runtime error occurs inside the block, an exception is thrown. If we did not use a `finally` clause, the exception would bypass the restoration code, permanently trapping the interpreter in the local scope. The `finally` block guarantees that the cleanup code runs regardless of whether the block succeeds or raises an exception.

Now, add the `case` to the `match statement:` block in your `execute()` method:

```python
            case stmt.Block(statements):
                self.execute_block(statements, Environment(self.environment))
```

### Test it out

Create a script file (e.g., `test.snek`) to test lexical scoping and shadowing:

```c
var a = "global";
{
  var a = "local";
  print a; 
}
print a;
```

Run it using `python snek.py test.snek`. It should print `local`, then `global`. Your environment chain works perfectly.

*(Note: If you want to test this in the REPL, you must type the entire block on a single line so the parser receives the closing brace before execution: `{ var a = "local"; print a; }`)*

## 3. Logical Operators (`and` / `or`)

Before we add branching, we need logical operators. Unlike standard arithmetic operators, logical operators **short-circuit**. If evaluating the left operand provides enough information to determine the final result, the right operand is completely ignored. 

This is crucial for safe code patterns like:
`if (obj != nil and obj.is_valid()) print "OK";`

If `and` evaluated both sides eagerly like a standard `Binary` expression, the right side would throw an error when `obj` is `nil`. Because of this behavioral difference, we need a new AST node.

Add this to `expr.py`:

```python
@dataclass
class Logical(Expr):
    left: Expr
    operator: Token
    right: Expr
```

In `parser.py`, we must update the precedence ladder. `or` has the lowest precedence, followed by `and`. 

```text
expression → assignment ;
assignment → IDENTIFIER "=" assignment
           | logic_or ;
logic_or   → logic_and ( "or" logic_and )* ;
logic_and  → equality ( "and" equality )* ;
```

Depending on whether you implemented the **Ternary Operator** challenge in the previous chapters, the entry point into this new precedence chain will differ:

**Option A: No Ternary**
Modify your `assignment()` method to call the new `logic_or()` method instead of `equality()`:
```python
    def assignment(self) -> expr.Expr:
        # assignment -> logic_or
        expr_node = self.logic_or() 
        # ... rest of assignment ...
```

**Option B: With Ternary**
Leave your `assignment()` calling `self.ternary()`, but update your `ternary()` method to call the new `logic_or()` instead of `equality()` so that `and`/`or` bind tighter than the ternary operator:
```python
    def ternary(self) -> expr.Expr:
        e = self.logic_or()

        if self.match(TokenType.QUESTION):
        # ... rest of ternary ...
```

Now, implement the two new parsing methods. Both tracks will use the exact same code here. Notice that `logic_and()` falls through to `equality()`, properly grounding the logical operations to standard math and comparisons.

```python
    def logic_or(self) -> expr.Expr:
        expr_node = self.logic_and()

        while self.match(TokenType.OR):
            operator = self.previous()
            right = self.logic_and()
            expr_node = expr.Logical(expr_node, operator, right)

        return expr_node

    def logic_and(self) -> expr.Expr:
        expr_node = self.equality()

        while self.match(TokenType.AND):
            operator = self.previous()
            right = self.equality()
            expr_node = expr.Logical(expr_node, operator, right)

        return expr_node
```

In `interpreter.py`, add the evaluation logic to your `evaluate()` `match` block:

```python
            case expr.Logical(left_expr, operator, right_expr):
                left = self.evaluate(left_expr)

                if operator.type == TokenType.OR:
                    if self.is_truthy(left):
                        return left
                else: # TokenType.AND
                    if not self.is_truthy(left):
                        return left

                return self.evaluate(right_expr)
```

Notice that we return the *actual value* of the operand, not `True` or `False`. For example, `print "hello" or "world";` will print `hello`.

**Why do we do this?** 
In dynamically typed languages (like Python, JavaScript, Ruby, and Snek), returning the operand's actual value is a powerful feature. Because control flow statements like `if` and `while` only care if a condition is *truthy* or *falsey*, logical operators don't need to strictly return boolean types. 

By returning the underlying value, we allow developers to use logical operators for concise data fallbacks, such as setting default values:
```c
var user_name = nil;
// If user_name is falsey, it falls through and returns "Guest"
var display_name = user_name or "Guest";
```

### Test it out
Create a script (or type in the REPL) to test your logical operators. We can use assignment expressions to prove that short-circuiting works and prevents the right side from executing!

```c
print "hi" or 2; // "hi"
print nil or "yes"; // "yes"

var a = 1;
// 'a = 2' is an assignment expression, but it will be skipped
false and (a = 2); 
print a; // 1
```

## 4. Conditional Execution (`if`)

With logical operations ready, we can implement `if` statements. Here is the grammar rule:

```text
statement  → exprStmt
           | ifStmt
           | printStmt
           | block ;

ifStmt     → "if" "(" expression ")" statement
           ( "else" statement )? ;
```

Add the AST node to `stmt.py`:

```python
@dataclass
class If(Stmt):
    condition: expr.Expr
    then_branch: Stmt
    else_branch: Stmt | None
```

In `parser.py`, add to `statement()`:

```python
        if self.match(TokenType.IF):
            return self.if_statement()
```

And implement `if_statement()`:

```python
    def if_statement(self) -> stmt.Stmt:
        self.consume(TokenType.LEFT_PAREN, "Expect '(' after 'if'.")
        condition = self.expression()
        self.consume(TokenType.RIGHT_PAREN, "Expect ')' after if condition.")

        then_branch = self.statement()
        else_branch = None
        if self.match(TokenType.ELSE):
            else_branch = self.statement()

        return stmt.If(condition, then_branch, else_branch)
```

> **Technical Note: The Dangling Else Problem**
>
> Consider the code: `if (a) if (b) do_b(); else do_a();`
> Which `if` does the `else` belong to? This is a famous ambiguity in programming language grammars known as the "Dangling Else" problem.
> 
> Our recursive descent parser resolves this automatically. Because `if_statement()` eagerly calls `self.match(TokenType.ELSE)` immediately after parsing the `then_branch`, the inner `if` will aggressively consume the `else` token before returning to the outer `if`. Thus, `else` is always bound to the nearest preceding `if`, which is exactly what C, Java, and Python do.

In `interpreter.py`, add the execution logic to `execute()`:

```python
            case stmt.If(condition, then_branch, else_branch):
                if self.is_truthy(self.evaluate(condition)):
                    self.execute(then_branch)
                elif else_branch is not None:
                    self.execute(else_branch)
```

### Test it out
Let's make sure our branching logic and truthiness evaluation are working properly.

```c
var condition = true;

if (condition) {
    print "This should print.";
}

if (nil) {
    print "This should not.";
} else {
    print "But this should.";
}
```
If your interpreter outputs the correct strings, your `if` and `else` statements are wired up correctly.

## 5. While Loops

Looping is what gives programming languages their power. A `while` loop behaves exactly like an `if` statement, but repeats as long as the condition is truthy.

```text
statement  → exprStmt
           | ifStmt
           | printStmt
           | whileStmt
           | block ;

whileStmt  → "while" "(" expression ")" statement ;
```

Add the AST node to `stmt.py`:

```python
@dataclass
class While(Stmt):
    condition: expr.Expr
    body: Stmt
```

Update `parser.py`'s `statement()` to check for `TokenType.WHILE`:

```python
        if self.match(TokenType.WHILE):
            return self.while_statement()
```

Then, add the parsing method:
```python
    def while_statement(self) -> stmt.Stmt:
        self.consume(TokenType.LEFT_PAREN, "Expect '(' after 'while'.")
        condition = self.expression()
        self.consume(TokenType.RIGHT_PAREN, "Expect ')' after condition.")
        body = self.statement()

        return stmt.While(condition, body)
```

In `interpreter.py`'s `execute()` method:

```python
            case stmt.While(condition, body):
                while self.is_truthy(self.evaluate(condition)):
                    self.execute(body)
```

### Test it out
Before we move on to `for` loops, let's make sure our basic iteration works. 

```c
var count = 0;
while (count < 3) {
  print count;
  count = count + 1;
}
```
Run this script. If it prints `0`, `1`, and `2`, your interpreter successfully handles repetition.

## 6. For Loops and Desugaring

We have one final control flow construct: the C-style `for` loop. 
`for (var i = 0; i < 10; i = i + 1) print i;`

Here is the grammar:

```text
statement  → exprStmt
           | forStmt
           | ifStmt
           | printStmt
           | whileStmt
           | block ;

forStmt    → "for" "(" ( varDecl | exprStmt | ";" )
             expression? ";"
             expression? ")" statement ;
```

We *could* define a new `stmt.For` AST node and write interpreter logic for it. But notice that a `for` loop is just a very specific arrangement of a `while` loop, an initializer, and an increment expression. 

```c
{
  var i = 0;
  while (i < 10) {
    print i;
    i = i + 1;
  }
}
```

This translation process is called **Desugaring**. We take "Syntactic Sugar" (the `for` loop) and translate it down to a more primitive representation (blocks and `while` loops) before the interpreter ever sees it. This keeps our interpreter backend small and fast.

We do this entirely in `parser.py`. There is **no new AST node**. 

First, hook it up in your `statement()` method:

```python
        if self.match(TokenType.FOR):
            return self.for_statement()
```

Then, implement desugaring:
```python
    def for_statement(self) -> stmt.Stmt:
        self.consume(TokenType.LEFT_PAREN, "Expect '(' after 'for'.")

        # 1. Parse Initializer
        if self.match(TokenType.SEMICOLON):
            initializer = None
        elif self.match(TokenType.VAR):
            initializer = self.var_declaration()
        else:
            initializer = self.expression_statement()

        # 2. Parse Condition
        condition = None
        if not self.check(TokenType.SEMICOLON):
            condition = self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after loop condition.")

        # 3. Parse Increment
        increment = None
        if not self.check(TokenType.RIGHT_PAREN):
            increment = self.expression()
        self.consume(TokenType.RIGHT_PAREN, "Expect ')' after for clauses.")

        # 4. Parse Body
        body = self.statement()

        # 5. Desugar into a While loop
        if increment is not None:
            # Append the increment to execute after the body
            body = stmt.Block([body, stmt.Expression(increment)])

        if condition is None:
            # If no condition is provided, it's an infinite loop
            condition = expr.Literal(True)
        
        body = stmt.While(condition, body)

        if initializer is not None:
            # Execute the initializer once before the loop
            body = stmt.Block([initializer, body])

        return body
```

### Test it out

Our language is now Turing-complete! You can calculate the Fibonacci sequence in Snek. Run your REPL or execute a script file with this code:

```c
var a = 0;
var temp;

for (var b = 1; a < 10000; b = temp + b) {
  print a;
  temp = a;
  a = b;
}
```

If it prints the sequence up to 6765, congratulations. You have successfully implemented control flow.

---

## 7. Challenges

### 1. Trace-it
Given the following Snek code, draw or explain the chain of `Environment` objects at the exact moment the `print c;` statement is evaluated. How many scopes must the interpreter walk up to find `a` versus `c`?

```c
var a = 1;
{
    var b = 2;
    var a = 3;
    {
        var c = 4;
        print c;
    }
}
```

<details>
<summary>Answer</summary>

At the moment `print c;` evaluates, there are three environments in the chain:
1. **Innermost Environment:** Contains `{ "c": 4 }`. Its `enclosing` pointer points to the middle environment.
2. **Middle Environment:** Contains `{ "b": 2, "a": 3 }`. Its `enclosing` pointer points to the global environment.
3. **Global Environment:** Contains `{ "a": 1 }`.

To resolve `c`, the interpreter looks in the innermost environment and finds it immediately (0 hops up the chain). If it needed to find `a`, it would fail to find it in the innermost environment, step up to the middle environment, and find the value `3` (1 hop up the chain). The global `a` is shadowed and ignored.
</details>

### 2. Feature Addition: `else if`
Most languages allow you to chain conditional branches together using `else if` (or `elif`). 
Right now, our Snek grammar only explicitly supports `if` and `else`. 

Your challenge is to add `else if` support to Snek so that the following code works:
```c
var age = 15;

if (age < 13) {
    print "Child";
} else if (age < 18) {
    print "Teenager";
} else {
    print "Adult";
}
```
Think about what new AST nodes you need to create, how to update the parser to look for the `else if` token combination, and how to update the interpreter's `execute()` method. 

Once you have a plan, try running the script above in your *current*, unmodified Snek interpreter.

<details>
<summary>¯\_(ツ)_/¯</summary>

Look closely at our grammar rule for the `else` branch: it accepts any `statement`. 
An `if` statement *is* a statement. 

Therefore, `else if (condition) ...` is not a special language feature. It is literally just an `else` branch whose inner statement happens to be a standard `if` statement. The Snek parser naturally parses it as a deeply nested tree of standard `stmt.If` nodes. 

This is exactly how C, Java, and JavaScript handle `else if` under the hood.
</details>

### 3. "If-less" Programming
We implemented `and` and `or` as logical operators. However, because they short-circuit, they are fundamentally control flow constructs just like `if` and `while`.

To prove this, try to write a Snek script that assigns a value to a variable based on a condition, but **you are not allowed to use the `if` keyword.** 

**The Challenge:**
Given a variable `age`, write an expression that assigns the string `"Allowed"` to a variable named `status` when `age > 18`, but assigns `"Denied"` to `status` when `age <= 18`.
You can chain `and` and `or` together to build a working conditional expression.

**The Mechanics of Short-Circuiting:**
*   `A and B`: Evaluates `A`. If `A` is falsey, it stops and returns `A` immediately. If `A` is truthy, it evaluates and returns `B`.
*   `A or B`: Evaluates `A`. If `A` is truthy, it stops and returns `A` immediately. If `A` is falsey, it evaluates and returns `B`.