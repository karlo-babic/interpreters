---
layout: default
title: "9. Semantic Analysis & Resolving"
nav_order: 10
---

# 9. Semantic Analysis and Resolving

In the previous chapters, we introduced variables, blocks, and closures. Our interpreter dynamically creates environments to represent scopes and chains them together. Most of the time, this dynamic approach perfectly mirrors the lexical scope of the source code. 

However, our dynamic environments have a critical flaw when they interact with closures. Because our interpreter resolves variables dynamically at the moment they are executed, a closure can sometimes "forget" the scope it was created in if an inner block re-declares a variable.

In this chapter, we will transition our interpreter from purely dynamic evaluation to static analysis. We will write a semantic analysis pass that resolves variables before any code is run, ensuring our closures behave exactly as lexical scoping dictates.

## 1. The Closure Bug

To understand the problem, we must see it in action. In most modern languages (like Python, C, or JavaScript), variable scope is *lexical* (or static). This means scope is determined strictly by the text of the program. A variable usage always refers to the preceding declaration with the same name in the innermost enclosing scope.

Let us look at an example that highlights the difference between how Snek currently behaves, and how it *should* behave:

```c
var a = "global";

{
  fun showA() {
    print a;
  }

  showA();
  var a = "block";
  showA();
}
```

**How it *should* work (Lexical Scoping):**
When `showA()` is declared, the only `a` textually in scope is the global one. Therefore, the `a` inside `showA()` is permanently bound to the global `a`. Even though a new local variable `a` is declared later in the block, `showA()` should be blind to it. If we run this in a modern lexically-scoped language, it will print `global` both times.

**How it *currently* works in Snek (The Bug):**
If we run this in our current interpreter, the first call to `showA()` correctly prints `global`. But the second call prints `block`. Why?

When `showA` is defined, it captures a reference to the current environment in its `closure` field. However, environments in our interpreter are mutable Python dictionaries. When the statement `var a = "block";` is executed, it modifies that *exact same* environment dictionary, adding the new local variable to it. 

When `showA()` is called the second time, it dynamically walks the environment chain, looks in the captured block environment, and finds the newly created `a`. By deferring the variable resolution to runtime, our interpreter accidentally allowed the dynamic state of the dictionary to override the static lexical structure of the code.

To fix this and enforce true lexical scope, we need to resolve variables statically *before* the code runs.

## 2. The Resolver Pass

Instead of dynamically searching the environment chain every time a variable is accessed, we will calculate the exact location of the variable statically. This solves two major problems:
1. **Correctness (The Closure Bug):** It ensures variables bind strictly to the textual scope where they were declared, ignoring dynamic runtime mutations.
2. **Performance:** Currently, accessing a global or closure variable requires an *O(N)* string lookup through a chain of dictionaries. If a variable access is inside a `while` loop running 10,000 times, the interpreter performs that expensive, multi-dictionary string search 10,000 times. By resolving the distance statically, we calculate the hops exactly once and change the runtime access to a fast, direct *O(1)* array-like jump.

This process is our first foray into **Semantic Analysis**. While a parser only checks if code is grammatically correct (syntax), semantic analysis figures out what the code actually *means*. In statically typed languages (like C++ or Java), this phase is where type checking occurs. Compilers also use semantic analysis to detect unreachable code, warn about unused variables, prevent invalid returns, and gather data for performance optimizations.

For Snek, our semantic analysis pass will resolve variable bindings by calculating exactly how many environment "hops" away every local variable is. Taking advantage of this static pass, we will also implement checks to catch specific errors before the code ever runs: 
*   Returning a value outside of a function body.
*   Re-declaring two local variables with the identical name in the exact same scope.
*   Reading a local variable inside its own initializer (e.g., `var a = a;`).

We will write a new tree-walking module called the `Resolver`. Unlike the `Interpreter`, it does not execute control flow or produce side effects. It simply traverses every node in the AST exactly once.

Create a new file named `resolver.py`:

```python
import expr
import stmt
import error

class Resolver:
    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.scopes: list[dict[str, bool]] = []

    def resolve_statements(self, statements: list[stmt.Stmt]):
        for statement in statements:
            self.resolve(statement)

    def resolve(self, node: stmt.Stmt | expr.Expr):
        """Dispatches to the appropriate resolution logic based on node type."""
        pass
```

> **Python Toolbox: Lists as Stacks**
>
> To track the current lexical scope, the `Resolver` uses a stack of dictionaries, represented by `self.scopes: list[dict[str, bool]]`. Python lists make excellent stacks. We can push a new scope using `self.scopes.append(...)`, pop it using `self.scopes.pop()`, and peek at the current innermost scope using `self.scopes[-1]`.

The keys in our scope dictionaries will be variable names. The boolean values will indicate whether a variable has finished its initializer (to prevent invalid edge cases like `var a = a;`).

Let us add the scope management helpers to the `Resolver`:

```python
    def begin_scope(self):
        self.scopes.append({})

    def end_scope(self):
        self.scopes.pop()
```

## 3. Declaring and Defining

When we resolve a block, we push a new scope, resolve the block's statements, and pop the scope. 

Add the `match` statement inside `resolve()`, and start implementing the node logic:

```python
    def resolve(self, node: stmt.Stmt | expr.Expr):
        """Dispatches to the appropriate resolution logic based on node type."""
        match node:
            case stmt.Block(statements):
                self.begin_scope()
                self.resolve_statements(statements)
                self.end_scope()
```

Next, we handle variable declarations. Adding a variable to the scope requires two-steps: declaring it, then defining it.

```python
            case stmt.Var(name, initializer):
                self.declare(name)
                if initializer is not None:
                    self.resolve(initializer)
                self.define(name)
```

We split binding into two steps to handle funny edge cases like `var a = a;`. If we define the variable immediately, the right-hand `a` would resolve to the currently uninitialized `a`, leading to a confusing `nil` value. Instead, we want it to be an error to read a variable in its own initializer.

Add these helper methods to `Resolver`:

```python
    def declare(self, name: 'Token'):
        if not self.scopes:
            return
        
        scope = self.scopes[-1]
        scope[name.lexeme] = False

    def define(self, name: 'Token'):
        if not self.scopes:
            return
            
        scope = self.scopes[-1]
        scope[name.lexeme] = True
```

When we declare a variable, we mark it `False` in the scope dictionary, meaning "it exists, but it is not ready yet." Once the initializer is fully resolved, we call `define()`, marking it `True`.

**Why do we check `if not self.scopes: return`?**
Notice that both methods immediately bail out if the `self.scopes` stack is empty. This is how we handle **global variables**. 

In our `Resolver`, the `self.scopes` stack is only used to track *local* scopes (like inside a `{}` block or a function body). When you declare a variable at the very top level of a Snek script, you are not inside any block, so the `self.scopes` stack is completely empty. 

By returning immediately, the resolver essentially says: *"I am at the global scope. I don't need to resolve this statically."* Global variables in Snek are left completely dynamic. Later, if the `Interpreter` evaluates a variable and doesn't find a static distance mapped to it, it will simply fall back to looking it up by its string name in the `self.globals` environment.

## 4. Resolving Variables and Assignments

Now we handle reading and assigning to variables.

```python
            case expr.Variable(name):
                if self.scopes and self.scopes[-1].get(name.lexeme) is False:
                    error.error(name.line, "Can't read local variable in its own initializer.")
                
                self.resolve_local(node, name)

            case expr.Assign(name, value):
                self.resolve(value)
                self.resolve_local(node, name)
```

When resolving a variable, if the variable is found in the current scope but its value is `False`, we report our static error. Otherwise, we calculate the variable's distance using `resolve_local`. Assignment is identical, except we resolve the value expression first.

Here is the core logic that calculates the environment distance:

```python
    def resolve_local(self, expr_node: expr.Expr, name: 'Token'):
        # Iterate through the scopes backwards (innermost to outermost)
        for i in range(len(self.scopes) - 1, -1, -1):
            if name.lexeme in self.scopes[i]:
                # Calculate the number of hops to the target scope
                distance = len(self.scopes) - 1 - i
                self.interpreter.resolve(expr_node, distance)
                return
        
        # If not found, assume it is global.
```

We use Python's `range()` to walk backwards through the scope list, starting from the innermost scope. When we find the variable's name, we calculate the number of "hops" from the current scope to the scope where the variable lives. A distance of `0` means it is in the current block, `1` means it is one block outward, and so on.

Once we have that hop count, we pass both the AST node and the distance to `self.interpreter.resolve()`. We haven't actually written that method in the `Interpreter` yet! We will add it in a few steps. It will act as the bridge between our static analysis and the runtime, storing this integer so the interpreter can completely skip the slow dynamic dictionary lookups later.

## 5. Resolving Functions and Control Flow

Functions both bind a name and introduce a new scope. Add these cases to your `match` statement:

```python
            case stmt.Function(name, params, body):
                self.declare(name)
                self.define(name)
                self.resolve_function(params, body)

            case expr.AnonymousFunction(keyword, params, body):
                self.resolve_function(params, body)
```

Notice that we declare and define the function's name *before* resolving its body. This is important: it allows a function to recursively refer to itself inside its own body. 

Add the `resolve_function` helper:

```python
    def resolve_function(self, params: list['Token'], body: list[stmt.Stmt]):
        self.begin_scope()
        for param in params:
            self.declare(param)
            self.define(param)
        
        self.resolve_statements(body)
        self.end_scope()
```

### 5.1 Traversing the Rest of the Tree

The resolver must touch every node in the AST. Even if a node doesn't bind variables (like a math expression), it might have children that do. If we don't provide a `case` for these nodes, the resolver will stop and "dead-end," missing any variables nested inside.

Add these "pass-through" cases to complete the `match` statement in `resolve()`:

```python
            # --- Other Statements ---
            case stmt.Expression(expression):
                self.resolve(expression)
                
            case stmt.If(condition, then_branch, else_branch):
                self.resolve(condition)
                self.resolve(then_branch)
                if else_branch is not None:
                    self.resolve(else_branch)
                    
            case stmt.Print(expression):
                self.resolve(expression)
                
            case stmt.Return(keyword, value):
                if value is not None:
                    self.resolve(value)
                    
            case stmt.While(condition, body):
                self.resolve(condition)
                self.resolve(body)

            # --- Other Expressions ---
            case expr.Binary(left, operator, right):
                self.resolve(left)
                self.resolve(right)
                
            case expr.Call(callee, paren, arguments):
                self.resolve(callee)
                for arg in arguments:
                    self.resolve(arg)
                    
            case expr.Grouping(expression):
                self.resolve(expression)
                
            case expr.Literal(value):
                pass # Nothing to do
                
            case expr.Logical(left, operator, right):
                self.resolve(left)
                self.resolve(right)
                
            case expr.Unary(operator, right):
                self.resolve(right)
                
            case expr.Ternary(condition, then_branch, else_branch):
                self.resolve(condition)
                self.resolve(then_branch)
                self.resolve(else_branch)
```

Notice how a static analysis differs from dynamic execution. In an `If` statement, the `Interpreter` only evaluates one branch. The `Resolver` explores *both* branches, because it analyzes the structure of the code, not the runtime flow.

## 6. Wiring up the Interpreter

The `Resolver` calculates the distance integers, but the `Interpreter` needs to store them for execution. Open `interpreter.py`.

```python
class Interpreter:
    def __init__(self):
        self.globals = Environment()
        self.environment = self.globals
        self.locals: dict[int, int] = {} # AST node ID to distance mapping
        
        # ... natives ...
```

We need a method to receive the distance from the resolver:

```python
    def resolve(self, expr_node: expr.Expr, depth: int):
        self.locals[id(expr_node)] = depth
```

> **Technical Note: AST Node Identity and Hashing**
>
> In Java, objects are automatically hashable by their memory reference, allowing you to use object instances as dictionary keys effortlessly.
>
> In Python, our AST classes use `@dataclass`. By default, Python `@dataclass` are mutable and unhashable. Even if we forced them to be hashable (using `frozen=True`), they evaluate equality based on their *contents*. Two separate `Literal(5)` nodes would hash to the exact same key, causing their resolution data to overwrite each other. 
> 
> To perfectly emulate Java's reference-based hashing, we use Python's built-in `id()` function. `id(expr_node)` returns a unique integer identifying the object in memory, providing a perfect, collision-free dictionary key for our side-table data.

### 6.1 Environment Hopping

Now we must update `Environment` to support distance-based lookups. Open `environment.py`:

```python
    def ancestor(self, distance: int) -> 'Environment':
        environment = self
        for _ in range(distance):
            environment = environment.enclosing
        return environment

    def get_at(self, distance: int, name: str) -> object:
        return self.ancestor(distance).values.get(name)

    def assign_at(self, distance: int, name: Token, value: object):
        self.ancestor(distance).values[name.lexeme] = value
```

Because the `Resolver` already validated the variable's existence statically, `get_at` and `assign_at` do not need to throw runtime errors. They know exactly where the variable lives.

### 6.2 Executing Resolved Variables

Return to `interpreter.py` and replace your `expr.Variable` evaluation logic in `evaluate()`:

```python
            case expr.Variable(name):
                return self.look_up_variable(name, expression)
```

Which uses this new helper method:

```python
    def look_up_variable(self, name: Token, expr_node: expr.Expr) -> object:
        distance = self.locals.get(id(expr_node))
        if distance is not None:
            return self.environment.get_at(distance, name.lexeme)
        else:
            return self.globals.get(name)
```

If the node ID is found in the `locals` dictionary, we jump directly to the target environment. If not, it must be a global variable, so we dynamically look it up in `self.globals`.

Update the `expr.Assign` logic to do the same:

```python
            case expr.Assign(name, value_expr):
                value = self.evaluate(value_expr)
                
                distance = self.locals.get(id(expression))
                if distance is not None:
                    self.environment.assign_at(distance, name, value)
                else:
                    self.globals.assign(name, value)
                    
                return value
```

## 7. Static Error Detection

Since we are analyzing the code before running it, we can help the user by detecting obvious bugs. 

**Bug 1: Returning outside a function.**
A `return` statement at the top-level of a script is invalid. Add an `Enum` to `resolver.py`:

```python
from enum import Enum, auto

class FunctionType(Enum):
    NONE = auto()
    FUNCTION = auto()
```

Initialize `self.current_function = FunctionType.NONE` in the `Resolver`'s `__init__`.

Update `resolve_function` to track that the resolver is now inside a function body:

```python
    def resolve_function(self, params: list['Token'], body: list[stmt.Stmt]):
        enclosing_function = self.current_function
        self.current_function = FunctionType.FUNCTION
        
        self.begin_scope()
        for param in params:
            self.declare(param)
            self.define(param)
        
        self.resolve_statements(body)
        self.end_scope()
        
        self.current_function = enclosing_function
```

Finally, check it inside the `stmt.Return` case:

```python
            case stmt.Return(keyword, value):
                if self.current_function == FunctionType.NONE:
                    error.error(keyword.line, "Can't return from top-level code.")
                    
                if value is not None:
                    self.resolve(value)
```

**Bug 2: Duplicate Local Variables.**
It is an error to declare two variables with the exact same name in the exact same local scope. Update the `declare()` method in `resolver.py`:

```python
    def declare(self, name: 'Token'):
        if not self.scopes:
            return
        
        scope = self.scopes[-1]
        if name.lexeme in scope:
            error.error(name.line, "Already a variable with this name in this scope.")
            
        scope[name.lexeme] = False
```

## 8. Connecting the Pipeline

All the machinery is in place. The final step is to insert the `Resolver` pass into our main pipeline. Open `snek.py`. Add the import:

```python
from resolver import Resolver
```

Then, insert it in the `run()` method right after parsing:

```python
    @staticmethod
    def run(source, repl_mode=False):
        # ... scanner and parser logic ...

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
        # ...
```

### Test it out

Run the initial pathological script that broke our interpreter:

```c
var a = "global";
{
  fun showA() {
    print a;
  }

  showA();
  var a = "block";
  showA();
}
```

It should now print `global` and `global`. Our closures perfectly capture and enforce static lexical scope! Furthermore, try returning a value outside a function or re-declaring a local variable, and verify that your static errors are safely reported.

---

## 9. Challenges

### 1. Python's Scope Rules

In Snek, we distinguish between **creating** a variable and **updating** an existing one using the `var` keyword. Python does not have a `var` keyword, which leads to a design conflict. Consider this comparison:

**Snek (Explicit Intent):**
```c
var x = "global";

fun f() {
  x = "local"; // No 'var', so Snek updates the existing global variable.
  print x;
}

f();      // Prints "local"
print x;  // Prints "local"
```

**Equivalent Python (Ambiguous Intent):**
```python
x = "global"

def f():
    # Python sees an assignment. Lacking a 'var' keyword, 
    # it defaults to creating a brand new LOCAL variable.
    x = "local" 
    print(x)

f()        # Prints "local"
print(x)   # Prints "global"
```

To update the global variable in Python, you must use the `global` keyword inside the function: `global x`.

Research the "Implicit Variable Declaration" problem. Why does Python's design force you to use explicit keywords like `global` (and `nonlocal`) to mutate variables in outer scopes, while Snek, JavaScript, and C allow it to happen automatically? What are the safety trade-offs of Snek's approach versus Python's?

### 2. Semantic Extension: Unused Variables

Compilers and IDEs often warn you if you define a local variable but never read its value. This helps you find potential typos and clean up dead code.

Extend the `Resolver` to track whether a local variable is ever used. 

<details>
<summary>Implementation Hints</summary>

1.  Currently, our scope dictionaries map a name to a simple `bool`. To solve this, you will need to store more metadata. Consider mapping names to a dictionary like `{"defined": bool, "used": bool, "line": int}`.
2.  Update `declare()` to initialize the new dictionary with `"used": False`.
3.  Inside `resolve_local()`, whenever you successfully find a variable in a local scope, set its `"used"` flag to `True`.
4.  In `end_scope()`, iterate through the dictionary you are about to discard. If any variable has `"used": False`, emit a warning using `sys.stderr`: `print(f"[line {state['line']}] Warning: Local variable '{name}' is not used.", file=sys.stderr)`.
</details>