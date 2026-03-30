---
layout: default
title: "5. Evaluating Expressions"
nav_order: 6
---

# 5. Evaluating Expressions (The Interpreter)

In the previous chapters, we transformed raw source code into a structured Abstract Syntax Tree (AST). Now, it is time to bring that tree to life. Our parser guarantees that the code is grammatically correct; our interpreter will execute the semantics of that code to produce a result.

In this chapter, we will build a tree-walking interpreter. It will recursively traverse the AST nodes we defined, evaluate their underlying mathematical or logical operations, and handle runtime errors gracefully.

## 1. Representing Values

Snek is a dynamically typed language. A variable can hold a number, and later hold a string. We must bridge the gap between Snek's dynamic types and our host language, Python. 

Because Python is also dynamically typed, this mapping is straightforward. We do not need to create custom wrapper classes for our values. We can map Snek types directly to Python's primitive types:

| Snek Type | Python Representation |
| :--- | :--- |
| `nil` | `None` |
| Booleans (`true` / `false`) | `bool` (`True` / `False`) |
| Numbers | `float` |
| Strings | `str` |

> **Python Toolbox: Dynamic Typing**
>
> In the textbook's Java implementation, the author must use the base `Object` class to represent Snek values, relying on Java's `instanceof` to determine the type at runtime. In Python, variables do not have static types, only the values they hold do. We can simply return standard Python objects from our evaluation methods and use Python's built-in `isinstance()` function when we need to enforce type constraints.

## 2. The Interpreter Core

Create a new file named `interpreter.py`. We will start by defining the core evaluation method. 

Thanks to Python's structural pattern matching, we do not need the complex Visitor pattern used in the Java implementation. We can directly match on the structure of our AST nodes.

```python
from token_type import TokenType
from token_class import Token
import expr

class Interpreter:
    def evaluate(self, expression: expr.Expr) -> object:
        """Recursively evaluates an AST node and returns a Python object."""
        match expression:
            case expr.Literal(value):
                return value
            
            case expr.Grouping(inner_expr):
                return self.evaluate(inner_expr)
```

The base cases are simple:
*   A `Literal` evaluates to its underlying value (which we already converted to a Python `float`, `str`, `bool`, or `None` during the scanning phase).
*   A `Grouping` evaluates the expression inside the parentheses and returns that result.

## 2.1 Wiring It Up (First Test Run)

Before we add complex operators, let's connect our new Interpreter to the main pipeline so we can test it as we build. 

First, we need to convert Python objects back into Snek syntax before printing them to the user. For example, Python's `None` should display as `"nil"`, and integers (which we store as floats) should print without the `.0` suffix.

Add this helper method to your `Interpreter` class:

```python
    def stringify(self, obj: object) -> str:
        if obj is None:
            return "nil"
        
        if isinstance(obj, bool):
            return str(obj).lower()
        
        if isinstance(obj, float):
            text = str(obj)
            if text.endswith(".0"):
                text = text[:-2]
            return text
            
        return str(obj)
```

Now, open `snek.py`. Add the import at the top:

```python
from interpreter import Interpreter
```

Then, update your `run` method. We will replace the `AstPrinter` logic with our actual `Interpreter`:

```python
    @staticmethod
    def run(source):
        # Scan the text into tokens
        scanner = Scanner(source)
        tokens = scanner.scan_tokens()

        # Parse the tokens into an AST
        parser = Parser(tokens)
        expression = parser.parse()

        # Stop if there was a syntax error.
        if error.had_error or expression is None:
            return

        # Interpret the AST
        interpreter = Interpreter()
        result = interpreter.evaluate(expression)
        print(interpreter.stringify(result))
```

### Test it out
Run your REPL (`python snek.py`).
Type `123;` and `(45.67);`. Your interpreter should evaluate the AST and print `123` and `45.67`.

## 3. Unary Operators and "Truthiness"

Next, we handle expressions with a single operand. Add the `Unary` case to your `match` statement:

```python
            case expr.Unary(operator, right_expr):
                right = self.evaluate(right_expr)
                
                if operator.type == TokenType.MINUS:
                    return -float(right)
                elif operator.type == TokenType.BANG:
                    return not self.is_truthy(right)
```

First, we evaluate the operand recursively. Then, we apply the operator. 
*   For the `MINUS` operator, we cast the value to a float and negate it. (We will add strict type checking for this soon to prevent users from negating strings).
*   For the `BANG` (logical NOT) operator, we rely on a concept called "truthiness".

### Truthiness

What happens when a user uses `!` on something that is not a boolean? For example, `!nil` or `!"hello"`. Most dynamically typed languages partition the universe of values into two sets: "truthy" and "falsey". 

Add this helper method to your `Interpreter` class:

```python
    def is_truthy(self, obj: object) -> bool:
        if obj is None:
            return False
        if isinstance(obj, bool):
            return obj
        return True
```

> **Technical Note: Explicit Truthiness**
>
> Why did we write our own `is_truthy` function instead of just using Python's `bool(right)`? 
>
> Host languages and guest languages often have conflicting semantics. In Python, the number `0` and the empty string `""` evaluate to `False`. However, Snek follows Ruby's simpler rule: **only `nil` and `false` are falsey**. Everything else, including `0` and `""`, is truthy. If we relied on Python's implicit conversion, our interpreter would behave incorrectly according to the Snek specification.

### Test it out
Because your interpreter is already wired up, you can test this immediately!
Run the REPL and try:
*   `-123;` (Should print `-123`)
*   `!true;` (Should print `false`)
*   `!nil;` (Should print `true` because nil is falsey)

## 4. Binary Operators

Binary operators require evaluating two operands. Add this case to your `evaluate` method:

```python
            case expr.Binary(left_expr, operator, right_expr):
                left = self.evaluate(left_expr)
                right = self.evaluate(right_expr)
                
                if operator.type == TokenType.MINUS:
                    return float(left) - float(right)
                elif operator.type == TokenType.SLASH:
                    return float(left) / float(right)
                elif operator.type == TokenType.STAR:
                    return float(left) * float(right)
                
                elif operator.type == TokenType.PLUS:
                    if isinstance(left, float) and isinstance(right, float):
                        return float(left) + float(right)
                    if isinstance(left, str) and isinstance(right, str):
                        return str(left) + str(right)
                    # We will handle the error case for this shortly.
                    return None
                
                elif operator.type == TokenType.GREATER:
                    return float(left) > float(right)
                elif operator.type == TokenType.GREATER_EQUAL:
                    return float(left) >= float(right)
                elif operator.type == TokenType.LESS:
                    return float(left) < float(right)
                elif operator.type == TokenType.LESS_EQUAL:
                    return float(left) <= float(right)
                
                elif operator.type == TokenType.BANG_EQUAL:
                    return not self.is_equal(left, right)
                elif operator.type == TokenType.EQUAL_EQUAL:
                    return self.is_equal(left, right)
```

Notice that the `PLUS` operator is overloaded. If both operands are numbers, it performs addition. If both are strings, it performs concatenation.

We also need a helper for equality. Add this to your `Interpreter` class:

```python
    def is_equal(self, a: object, b: object) -> bool:
        if a is None and b is None:
            return True
        if a is None:
            return False
        return a == b
```

### Test it out
Run the REPL again. Your interpreter is now a fully functional calculator:
*   `2 + 3 * 4;` (Should print `14`)
*   `"hello " + "world";` (Should print `hello world`)
*   `1 == 2;` (Should print `false`)

## 5. Runtime Errors

Our code currently has a dangerous flaw. If the user evaluates `"muffin" - 5`, Python will throw a `ValueError` when trying to execute `float("muffin")`. This will generate a massive Python stack trace and crash the interpreter entirely.

A runtime error is a failure that the language semantics demand we detect and report while the program is running. We must intercept these invalid operations, report them in Snek's terminology, and handle them without crashing the host process.

Create a new custom exception. You can place this at the top of `interpreter.py`:

```python
class SnekRuntimeError(Exception):
    def __init__(self, token: Token, message: str):
        super().__init__(message)
        self.token = token
```

Next, add type-checking helpers to your `Interpreter` class:

```python
    def check_number_operand(self, operator: Token, operand: object):
        if isinstance(operand, float):
            return
        raise SnekRuntimeError(operator, "Operand must be a number.")

    def check_number_operands(self, operator: Token, left: object, right: object):
        if isinstance(left, float) and isinstance(right, float):
            return
        raise SnekRuntimeError(operator, "Operands must be numbers.")
```

Now, we need to go back and update our `Unary` and `Binary` cases in the `evaluate` method to use these checks before attempting to execute Python math operations. 

Replace your previous `Unary` and `Binary` cases with this complete, type-checked version:

```python
            case expr.Unary(operator, right_expr):
                right = self.evaluate(right_expr)
                
                if operator.type == TokenType.MINUS:
                    self.check_number_operand(operator, right)
                    return -float(right)
                elif operator.type == TokenType.BANG:
                    return not self.is_truthy(right)
            
            case expr.Binary(left_expr, operator, right_expr):
                left = self.evaluate(left_expr)
                right = self.evaluate(right_expr)
                
                if operator.type == TokenType.MINUS:
                    self.check_number_operands(operator, left, right)
                    return float(left) - float(right)
                elif operator.type == TokenType.SLASH:
                    self.check_number_operands(operator, left, right)
                    return float(left) / float(right)
                elif operator.type == TokenType.STAR:
                    self.check_number_operands(operator, left, right)
                    return float(left) * float(right)
                
                elif operator.type == TokenType.PLUS:
                    if isinstance(left, float) and isinstance(right, float):
                        return float(left) + float(right)
                    if isinstance(left, str) and isinstance(right, str):
                        return str(left) + str(right)
                    raise SnekRuntimeError(operator, "Operands must be two numbers or two strings.")
                
                elif operator.type == TokenType.GREATER:
                    self.check_number_operands(operator, left, right)
                    return float(left) > float(right)
                elif operator.type == TokenType.GREATER_EQUAL:
                    self.check_number_operands(operator, left, right)
                    return float(left) >= float(right)
                elif operator.type == TokenType.LESS:
                    self.check_number_operands(operator, left, right)
                    return float(left) < float(right)
                elif operator.type == TokenType.LESS_EQUAL:
                    self.check_number_operands(operator, left, right)
                    return float(left) <= float(right)
                
                elif operator.type == TokenType.BANG_EQUAL:
                    return not self.is_equal(left, right)
                elif operator.type == TokenType.EQUAL_EQUAL:
                    return self.is_equal(left, right)
```

Finally, we need to report these errors. Open `error.py` and add this function:

```python
def runtime_error(err):
    global had_runtime_error
    print(f"{str(err)}\n[line {err.token.line}]", file=sys.stderr)
    had_runtime_error = True
```

### 5.1 Catching Errors in the REPL

We are throwing our new `SnekRuntimeError`, but our main pipeline doesn't know how to catch it yet. If a user triggers it right now, Python will still crash with an unhandled exception.

Open `snek.py`. Update your import to include the new error class:

```python
from interpreter import Interpreter, SnekRuntimeError
```

Finally, update the execution block at the bottom of your `run` method to catch the error and route it to our `error.py` module:

```python
        # Interpret the AST
        interpreter = Interpreter()
        try:
            result = interpreter.evaluate(expression)
            print(interpreter.stringify(result))
        except SnekRuntimeError as err:
            error.runtime_error(err)
```

### Test it out

Run your REPL and purposefully trigger a runtime error:
*   `"muffin" - 5;` 
    *   Instead of crashing, it should print: `Operands must be numbers. [line 1]`
    *   The REPL should safely prompt you for the next line of code without exiting.

---

## 6. Challenges

### 1. Semantic Extension: Ternary Evaluation
In the previous chapter, you added parsing support for the ternary operator (`condition ? then_branch : else_branch`). Now it is time to implement its evaluation logic.

<details>
<summary>Hints</summary>

*   Add a new case to your `evaluate` match statement to handle the `expr.Ternary` AST node.
*   The ternary operator must **short-circuit**. You must evaluate the `condition` first. If the condition is truthy, you should *only* evaluate the `then_branch`. If it is falsey, you should *only* evaluate the `else_branch`. 
*   If you evaluate both branches before checking the condition, you will introduce subtle bugs when we add side effects (like printing or variable assignment) later in the course.
</details>

### 2. Division by Zero
What happens in your current interpreter if you evaluate `1 / 0;`? 

Because we rely on Python's underlying math operations, Python raises a `ZeroDivisionError`. This exception bypasses our `SnekRuntimeError` catching logic, causing the interpreter process to crash and dump a Python stack trace to the user.

Fix this. 

<details>
<summary>Hints</summary>

*   Update the evaluation logic for `TokenType.SLASH`.
*   Check if the right operand is zero.
*   If it is, raise a `SnekRuntimeError` with a helpful message (e.g., "Division by zero."). 
</details>

### 3. String Comparisons
Currently, Snek only allows ordering comparisons (`<`, `>`, `<=`, `>=`) on numbers. If you try to evaluate `"apple" < "banana";`, the interpreter will throw a `SnekRuntimeError` because of our `check_number_operands` validation.

Extend the interpreter to support comparing strings alphabetically. 

<details>
<summary>Hints</summary>

*   You cannot simply delete the `check_number_operands` call. If you allow mixed-type comparisons (like `"apple" < 5`), Python's underlying `<` operator will crash with a `TypeError`, taking your whole interpreter down with it.
*   Create a new helper method (e.g., `check_number_or_string_operands`) that ensures *both* operands are floats, OR *both* operands are strings. 
*   If the operands are a mix of types (one string, one float), raise a `SnekRuntimeError` with a message like: `"Operands must be two numbers or two strings."`
*   Update the evaluation cases for `TokenType.GREATER`, `TokenType.LESS`, etc., to use your new helper. 
*   *Bonus:* Because Python natively supports alphabetical string comparisons using standard math operators (`"a" < "b"` evaluates to `True` in Python), once your type-checker is in place, the actual evaluation logic won't need to change at all!
</details>