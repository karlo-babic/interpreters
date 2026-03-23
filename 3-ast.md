---
layout: default
title: "3. ASTs & Parsing Literals"
nav_order: 4
---

# 3. Abstract Syntax Trees & Parsing Literals

In the previous chapter, we took raw source code and converted it into a flat sequence of tokens. However, programming languages are not flat; they are deeply nested. An expression like `1 + 2 * 3` implies a specific order of operations, and an expression like `1 + (2 * 3)` uses parentheses to explicitly override that order. 

A flat list of tokens like `[NUMBER, PLUS, LEFT_PAREN, NUMBER, STAR, NUMBER, RIGHT_PAREN]` does not inherently capture this nesting. To process this structure, we must move from the realm of **Lexical Analysis** to **Syntactic Analysis** (Parsing). 

In this chapter, we will define a mathematical grammar for Snek, create a tree data structure to hold that grammar in memory, and begin writing our Parser to translate tokens into trees.

## 1. Context-Free Grammars

In lexical analysis, we used a Regular Grammar (which can be represented by Regular Expressions) to group characters into tokens. Regular grammars are great for flat sequences, but they have a fatal flaw: they cannot "count", which means they cannot handle arbitrarily nested structures like parentheses.

To parse expressions, we need a more powerful tool: a **Context-Free Grammar (CFG)**. A formal grammar is a set of rules that specifies which strings of tokens are valid in a language. We use a notation called **Backus-Naur Form (BNF)** to write down these rules.

A CFG consists of a set of rules called *productions*. A rule produces a sequence of symbols. Symbols come in two varieties:
*   **Terminals:** These are the endpoints of the grammar. In our parser, the terminals are the exact tokens we get from the scanner (like `NUMBER`, `STRING`, or `FALSE`). They are "terminal" because they do not expand into anything else.
*   **Non-terminals:** These are named references to other rules in the grammar. They mean "evaluate that rule and insert whatever it produces here."

### A Grammar for Snek Expressions

Using BNF, here is a grammar that describes all of the expressions we eventually want to support in Snek:

```text
expression → primary
           | unary
           | binary ;

primary    → NUMBER | STRING | "true" | "false" | "nil" 
           | "(" expression ")" ;

unary      → ( "-" | "!" ) expression ;
binary     → expression operator expression ;
operator   → "==" | "!=" | "<" | "<=" | ">" | ">="
           | "+"  | "-"  | "*" | "/" ;
```

**How to read this notation:**
*   **The Arrow (`→`):** Means "can be expanded into".
*   **Quoted strings (`"true"`, `"("`):** Represent exact, literal lexemes. The parser must find exactly these characters.
*   **Capitalized words (`NUMBER`, `STRING`):** Represent single terminal tokens where the exact lexeme can vary (e.g., `123` and `45.67` are both `NUMBER`s).
*   **Lowercase words (`expression`, `unary`):** Represent non-terminals (references to other grammar rules).
*   **The Pipe (`|`):** Means "or". It separates different valid choices for the rule.

> **Technical Note: Ambiguity in Grammars**
>
> This grammar is a good starting point, but it has a serious problem: it is **ambiguous**. For an expression like `5 - 3 * 1`, this grammar allows two different valid syntax trees: `(5 - 3) * 1` or `5 - (3 * 1)`. It doesn't understand operator precedence (that `*` should happen before `-`).
>
> For now, this is okay. **In this chapter, we will only implement the `primary` rule.** In the next chapter, we will replace this ambiguous grammar with a more sophisticated one that precisely encodes operator precedence and associativity.

## 2. Representing the AST

Because our grammar rules refer to each other recursively, the data structure we use to represent parsed code in memory must be a tree. We call this an **Abstract Syntax Tree (AST)**. 

Imagine the expression `1 + (2 * 3)`. As an AST, it looks like this:

```text
      Binary (+)
      /        \
Literal (1)   Grouping ()
                  |
             Binary (*)
             /        \
       Literal (2)  Literal (3)
```

Each rule in our grammar will become a node class in our tree. Let us create a file named `expr.py` to hold our AST node definitions.

> **Python Toolbox: `@dataclass`**
>
> In the textbook, defining the AST requires writing a separate metaprogramming script to generate hundreds of lines of Java boilerplate just to hold data. Python provides an elegant built-in solution: `@dataclass`. 
> 
> By decorating a class with `@dataclass`, Python automatically inspects the type hints you provide and generates the `__init__`, `__repr__`, and `__eq__` methods for you. This makes defining data-heavy tree structures incredibly concise.

```python
from dataclasses import dataclass
from token_class import Token

class Expr:
    """Base class for all expression nodes."""
    pass

@dataclass
class Binary(Expr):
    left: Expr
    operator: Token
    right: Expr

@dataclass
class Grouping(Expr):
    expression: Expr

@dataclass
class Literal(Expr):
    value: object

@dataclass
class Unary(Expr):
    operator: Token
    right: Expr
```

This single, clean file replaces all the AST generation logic from the Java implementation.

## 3. Traversing the Tree

Eventually, we will need to evaluate these syntax trees. The logic to evaluate a `Binary` expression (which requires doing math on a left and right child) is very different from the logic to evaluate a `Literal` (which just returns a value). How do we write a function that takes an `Expr` and executes the correct behavior based on its specific subclass?

> **Architecture Shift: Pattern Matching vs. The Visitor Pattern**
>
> To solve this problem in an Object-Oriented language like Java, the book introduces the **Visitor Pattern**. This is a complex architectural workaround used to separate operations (like printing or evaluating) from the data structures they operate on.
>
> In Python 3.10+, we have a much better tool: **Structural Pattern Matching** (`match` / `case`). This allows us to inspect an object's type and structure directly, extracting its fields in a highly readable, functional style. By using `@dataclass`, Python automatically enables this unpacking behavior.

To prove our AST works, let us write an AST Printer. This will traverse a tree and produce an unambiguous string representation of it. For example, it will translate a tree representing the math expression `-123 * (45.67 + 8)` into the explicit, Lisp-style string `(* (- 123) (group (+ 45.67 8)))`. Seeing the nesting written out like this is immensely helpful for debugging our parser.

As an AST, it looks like this:

```text
              Binary (*)
              /        \
        Unary (-)    Grouping ()
           |             |
      Literal (123)   Binary (+)
                      /        \
               Literal (45.67) Literal (8)
```

Create `ast_printer.py`:

```python
import expr

class AstPrinter:
    def print_ast(self, expression: expr.Expr) -> str:
        """Traverses the AST and returns a Lisp-style string."""
        match expression:
            # If expression is a Binary node, unpack its fields into variables
            case expr.Binary(left, operator, right):
                return self.parenthesize(operator.lexeme, left, right)
            case expr.Grouping(inner_expr):
                return self.parenthesize("group", inner_expr)
            case expr.Literal(value):
                if value is None: return "nil"
                # Python stringifies True as "True", but Snek expects "true"
                if isinstance(value, bool): return str(value).lower()
                return str(value)
            case expr.Unary(operator, right):
                return self.parenthesize(operator.lexeme, right)
            case _:
                return "Unknown Expression"

    def parenthesize(self, name: str, *exprs: expr.Expr) -> str:
        """Helper to format nested expressions."""
        builder = [f"({name}"]
        for e in exprs:
            builder.append(f" {self.print_ast(e)}")
        builder.append(")")
        return "".join(builder)
```

### Test it out

Open `snek.py`. Let us manually create an AST and print it to prove our architecture works before we attempt to parse anything automatically. Add these imports at the top:

```python
from token_class import Token
from token_type import TokenType
import expr
from ast_printer import AstPrinter
```

Modify your `run` method to instantiate a tree and print it:

```python
    @staticmethod
    def run(source):
        # For this test, ignore the source input and build a manual AST:
        # Represents: -123 * (45.67 + 8)
        expression = expr.Binary(
            expr.Unary(
                Token(TokenType.MINUS, "-", None, 1),
                expr.Literal(123)
            ),
            Token(TokenType.STAR, "*", None, 1),
            expr.Grouping(
                expr.Binary(
                    expr.Literal(45.67),
                    Token(TokenType.PLUS, "+", None, 1),
                    expr.Literal(8)
                )
            )
        )

        printer = AstPrinter()
        print(printer.print_ast(expression))
```

Run your interpreter (and press enter). You should see `(* (- 123) (group (+ 45.67 8)))`. If so, your AST classes and Pattern Matching logic are working. You can now delete this manual tree code and added imports.

## 4. The Parser Shell

Now we will write the code that automatically generates these trees from our tokens. We will use a technique called **Recursive Descent Parsing**. 

A recursive descent parser is a literal translation of the grammar's rules straight into imperative code. 
*   Each grammar rule becomes a method.
*   A terminal (a specific token) translates to code that matches and consumes that token.
*   A non-terminal (a reference to another rule) translates to a function call to that rule's method.

Create `parser.py`. We will start with the basic navigation shell, which is very similar to how the Scanner moved through characters.

```python
from token_type import TokenType
from token_class import Token
import expr
import error

class ParseError(Exception):
    """A sentinel exception used to unwind the parser on an error."""
    pass

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0

    # --- Navigation Helpers ---

    def peek(self) -> Token:
        return self.tokens[self.current]

    def is_at_end(self) -> bool:
        return self.peek().type == TokenType.EOF

    def previous(self) -> Token:
        return self.tokens[self.current - 1]

    def advance(self) -> Token:
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def check(self, token_type: TokenType) -> bool:
        if self.is_at_end():
            return False
        return self.peek().type == token_type

    def match(self, *types: TokenType) -> bool:
        for token_type in types:
            if self.check(token_type):
                self.advance()
                return True
        return False
```

These helper methods are the "eyes and hands" of our parser. They are very similar to the ones we wrote for the Scanner, but instead of operating on a string of characters, they operate on a list of `Token` objects:
*   **`peek()`** looks at the current token we have yet to consume.
*   **`advance()`** consumes the current token and returns it.
*   **`check(token_type)`** looks at the current token to see if it is of the given type, but *does not* consume it.
*   **`match(*types)`** is our primary tool for branching. It checks if the current token has any of the given types. If it does, it consumes the token and returns `True`. Otherwise, it leaves the token alone and returns `False`.

## 5. Parsing Literals (and Grouping)

With our navigation helpers ready, we can translate our grammar rules directly into Python methods. We will start with the `primary` rule, which is the rule for the highest-precedence expressions (those that don't involve operators, like literals and groupings).

Add this method to your `Parser` class:

```python
    # --- Grammar Rules ---

    def primary(self) -> expr.Expr:
        if self.match(TokenType.FALSE): return expr.Literal(False)
        if self.match(TokenType.TRUE): return expr.Literal(True)
        if self.match(TokenType.NIL): return expr.Literal(None)

        if self.match(TokenType.NUMBER, TokenType.STRING):
            return expr.Literal(self.previous().literal)

        if self.match(TokenType.LEFT_PAREN):
            e = self.expression()
            self.consume(TokenType.RIGHT_PAREN, "Expect ')' after expression.")
            return expr.Grouping(e)

        raise self.error(self.peek(), "Expect expression.")
```

Look at how this maps to our BNF grammar: `primary → NUMBER | STRING | "true" | "false" | "nil" | "(" expression ")"`. We use a series of `if self.match(...)` calls to check for each possible starting token, which implements the `|` (or) part of the grammar rule.

When we encounter a left parenthesis, we recursively call `self.expression()` (which we will define shortly) to parse the inside of the grouping, and then we strictly require a closing right parenthesis.

Let's break down how this Python code directly implements our grammar rules:
*   **Booleans and Nil:** If we match a `FALSE`, `TRUE`, or `NIL` token, we instantly return a corresponding `Literal` AST node.
*   **Numbers and Strings:** We check for both types at once. Because `match()` advances the parser, the token we just matched is now the *previous* token. We use `self.previous().literal` to grab the actual Python `float` or `str` value that our Scanner parsed for us earlier, and wrap it in a `Literal` node.
*   **Parentheses (Grouping):** If we hit a `(`, we know we are starting a grouped expression. We recursively call `self.expression()` to parse whatever is inside the parentheses. Once the inner expression is parsed, the grammar dictates we *must* find a `)`. We use `self.consume()` to enforce this.

### Error Handling

What happens if the parser expects a `)` but finds a `;`? Or what if it hits a `+` where it expects a literal number? We need to report a syntax error.

Add these two methods to `Parser`:

```python
    # --- Error Handling ---

    def consume(self, token_type: TokenType, message: str) -> Token:
        """Requires the next token to be of a specific type, otherwise throws an error."""
        if self.check(token_type):
            return self.advance()
        raise self.error(self.peek(), message)

    def error(self, token: Token, message: str) -> ParseError:
        """Reports the error to the user and returns a ParseError."""
        if token.type == TokenType.EOF:
            error.report(token.line, " at end", message)
        else:
            error.report(token.line, f" at '{token.lexeme}'", message)
        return ParseError()
```

> **Technical Note: Why use Exceptions for Parsing Errors?**
>
> Parsing is deeply recursive. If a syntax error occurs ten function calls deep inside a grouped expression, returning `None` or an error code all the way back up the call stack would be a nightmare of `if error_occurred: return` checks. 
>
> By raising a `ParseError`, we utilize Python's exception handling to instantly unwind the call stack to a safe place where we can recover and continue parsing. We do not crash the interpreter; we catch the exception at the top level.

Notice the difference between `match()` and `consume()`:
*   We use **`match()`** when we are trying to figure out what kind of syntax we are looking at (e.g., "Is this a number or a string?"). 
*   We use **`consume()`** when the grammar absolutely dictates what token must come next. If we just parsed a `(`, and then parsed an expression, the next token *must* be a `)`. If it isn't, the user's source code is invalid, and we throw an error.

### The Entry Point

A recursive descent parser handles operator precedence by chaining methods together. Each method handles one level of precedence and calls the next level "up" until finally reaching `primary()`. 

Since we don’t have operators yet, our chain is very short: `expression()` simply calls `primary()` directly. We will add the intermediate steps for arithmetic and logic in the next chapter.

Add this to `Parser`:

```python
    # --- Parser Entry Point ---

    def expression(self) -> expr.Expr:
        # For now, our grammar is: expression → primary ;
        # In the next chapter, we will expand this to handle operators.
        return self.primary()

    def parse(self) -> expr.Expr | None:
        try:
            return self.expression()
        except ParseError:
            return None
```

## 6. Wiring it up

We have a complete, runnable pipeline for evaluating simple literals and groupings. Let us connect the Scanner, the Parser, and the AST Printer together in `snek.py`.

Open `snek.py` and add these imports at the top of the file, with the others:

```python
from parser import Parser
from ast_printer import AstPrinter
```

Update your `run` method in `snek.py`:

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

        # Print the AST
        printer = AstPrinter()
        print(printer.print_ast(expression))
```

### Test it out

Now that the entire pipeline is connected, run your interpreter (`python snek.py`) and test it on real input.

1.  Type `123;` and press Enter. The parser should create a `Literal` node, and the `AstPrinter` should print its value: `123.0`. *(Note: Because we haven't implemented statement parsing yet, the parser simply grabs the first valid expression it finds and silently ignores the trailing `;` token).*
2.  Type `((( "hello" )));` and press Enter. The parser should generate a deeply nested tree, and the printer should show you the structure: `(group (group (group hello)))`.
3.  Type `(123;` and press Enter. Your error handling should kick in and report the missing parenthesis: `[line 1] Error at ';': Expect ')' after expression.`

In the next chapter, we will build out the rest of the precedence ladder to support the full range of arithmetic operators.

---

## 7. Challenges

### Trace-it
Given the following AST output generated by an <code>AstPrinter</code>, write the exact Python <code>Expr</code> constructor code that generated it. <br><code>(* (- 5) (group 10))</code>

<details>
<summary>Answer</summary>

```python
expression = expr.Binary(
    expr.Unary(
        Token(TokenType.MINUS, "-", None, 1),
        expr.Literal(5)
    ),
    Token(TokenType.STAR, "*", None, 1),
    expr.Grouping(
        expr.Literal(10)
    )
)
```
</details>

### Add Unary Expressions
The parser currently only understands literals (e.g., `123`, `"hi"`, `true`) and groupings (`(...)`). In this exercise, you will extend it to support unary expressions like `-5` or `!true`. This is a preview of the recursive descent techniques we will use heavily in the next chapter.

Your goal is to implement the following grammar rules:

```text
expression → unary ;
unary      → ( "!" | "-" ) unary | primary ;
```

This means that `expression` should now call `unary`, and `unary` will either be a `!` or `-` followed by *another* unary expression (to handle cases like `!!true`), or it will fall through to `primary` if no operator is found.

<details>
<summary>Implementation Hint</summary>

1.  Create a new method `unary(self) -> expr.Expr` in your `Parser` class.
2.  Inside `unary()`, check if the current token is a `BANG` or `MINUS`.
    *   If it is, consume the operator token. Then, **recursively call `unary()`** to parse the right-hand operand.
    *   Construct and return a `expr.Unary` node.
3.  If the current token is *not* a unary operator, simply call and return `self.primary()`.
4.  Finally, update your `expression()` method to call `self.unary()` instead of `self.primary()`.
</details>

Once complete, you should be able to run your REPL and test both simple and nested unary expressions. Typing `!false` should result in `(! false)`, while a more complex input like `!!-123` should produce `(! (! (- 123.0)))`, proving that your parser correctly handles recursive operators.