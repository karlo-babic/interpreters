---
layout: default
title: "4. Parsing Expressions"
nav_order: 5
---

# 4. Parsing Expressions (Recursive Descent)

In the previous chapter, we built the foundation of our parser and successfully parsed primary expressions: literals and groupings. However, programming languages are mostly composed of operations combining these primary expressions.

In this chapter, we will implement the rest of our expression grammar. We will deal with operator precedence and associativity, rewrite our grammar to be unambiguous, and implement a full Recursive Descent parser. Finally, we will add robust error recovery so our parser does not crash at the first sign of invalid code.

## 1. Ambiguity and the Parsing Game

At the end of Chapter 3, we looked at a simple grammar for expressions. It looked something like this:

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

This grammar is **ambiguous**. Consider the expression `5 + 3 * 2`. If we play the "parsing game" with these rules, we could generate two entirely different Abstract Syntax Trees (ASTs):

```text
  Wrong Tree (Ignores Precedence)        Right Tree (Follows Precedence)

               *                                       +
              / \                                     / \
             +   2                                   5   *
            / \                                         / \
           5   3                                       3   2

   Evaluates to: (5 + 3) * 2 = 16          Evaluates to: 5 + (3 * 2) = 11
```

Math dictates that multiplication has higher precedence than addition, so the second tree is the correct one. However, our flat grammar has no way of knowing this. To fix this, we must define rules for precedence and associativity.

*   **Precedence** determines which operator binds tighter. Higher precedence operators (like `*`) are evaluated first, meaning they appear *lower* in the syntax tree.
*   **Associativity** determines the evaluation order for a series of the same operator. Left-associative operators evaluate left-to-right (`5 - 3 - 1` becomes `(5 - 3) - 1`). Right-associative operators evaluate right-to-left.

### The Stratified Grammar

We fix ambiguity by stratifying our grammar. We define a separate rule for each precedence level. Each rule only matches expressions at its precedence level or higher.

Notice that in our new grammar, the generic `binary` and `operator` rules from the previous chapter have been completely eliminated. Instead of one ambiguous catch-all rule, we split the binary operations up into four distinct rules (`equality`, `comparison`, `term`, and `factor`), one for each level of precedence.

Here is the unambiguous, stratified grammar for Snek expressions, ordered from lowest to highest precedence:

```text
expression → equality ;
equality   → comparison ( ( "!=" | "==" ) comparison )* ;
comparison → term ( ( ">" | ">=" | "<" | "<=" ) term )* ;
term       → factor ( ( "-" | "+" ) factor )* ;
factor     → unary ( ( "/" | "*" ) unary )* ;
unary      → ( "!" | "-" ) unary | primary ;
primary    → NUMBER | STRING | "true" | "false" | "nil" | "(" expression ")" ;
```

Notice how `expression` simply routes to `equality`. Then `equality` looks for `==` or `!=`, but its operands must be `comparison` expressions (or higher). This forces the parser to descend to the bottom of the precedence ladder before it can match a lower-precedence operator, perfectly mirroring mathematical rules.

## 2. Top-Down Recursive Descent

A recursive descent parser translates these grammar rules directly into code. We start at the top (`expression`) and work our way down to the leaves (`primary`).

Let us update our entry point. Open `parser.py` and modify the `expression()` method:

```python
    # --- Parser Entry Point ---

    def expression(self) -> expr.Expr:
        return self.equality()
```

Now, we just need to implement the missing methods down the chain.

## 3. Parsing Binary Operators

We will start with `equality()`. Look at the grammar rule:
`equality → comparison ( ( "!=" | "==" ) comparison )* ;`

The `*` in BNF means "zero or more times". In imperative code, a repeating sequence translates perfectly to a `while` loop. Add this method to your `Parser` class (above `primary()`):

```python
    def equality(self) -> expr.Expr:
        e = self.comparison()

        while self.match(TokenType.BANG_EQUAL, TokenType.EQUAL_EQUAL):
            operator = self.previous()
            right = self.comparison()
            e = expr.Binary(e, operator, right)

        return e
```

> **Technical Note: Left-Associativity**
>
> The `while` loop is the secret to left-associativity. Consider parsing the expression `1 + 2 + 3`. We want the AST to lean to the left, representing `(1 + 2) + 3`. Here is how the `while` loop builds it step-by-step:
> 
> 1. We parse the first operand (`e = self.factor()`). `e` is now `Literal(1)`.
> 2. We enter the `while` loop because we see a `+`. We parse the right operand (`Literal(2)`).
> 3. We construct a new `Binary` node and assign it *back* to `e`.
> 4. The loop runs again because we see the second `+`. We parse the right operand (`Literal(3)`).
> 5. We construct another `Binary` node, using our *entire existing tree* (`e`) as the new left operand.
> 
> ```text
>   Step 1:         Step 2 (First Loop):        Step 3 (Second Loop):
> 
>      1                     +                            +
>                           / \                          / \
>                          1   2                        +   3
>                                                      / \
>                                                     1   2
> ```
> 
> Because the old `e` constantly gets pushed down to become the left child of the new node, the tree naturally grows up and to the right, leaving the leftmost operations at the bottom to be evaluated first.

The remaining binary operators follow the exact same pattern. Implement `comparison()`, `term()`, and `factor()`:

```python
    def comparison(self) -> expr.Expr:
        e = self.term()

        while self.match(TokenType.GREATER, TokenType.GREATER_EQUAL, TokenType.LESS, TokenType.LESS_EQUAL):
            operator = self.previous()
            right = self.term()
            e = expr.Binary(e, operator, right)

        return e

    def term(self) -> expr.Expr:
        e = self.factor()

        while self.match(TokenType.MINUS, TokenType.PLUS):
            operator = self.previous()
            right = self.factor()
            e = expr.Binary(e, operator, right)

        return e

    def factor(self) -> expr.Expr:
        e = self.unary()

        while self.match(TokenType.SLASH, TokenType.STAR):
            operator = self.previous()
            right = self.unary()
            e = expr.Binary(e, operator, right)

        return e
```

You might notice that these four methods look nearly identical. In a recursive descent parser, this repetition is standard. It keeps the precedence explicitly mapped to the call stack, making the parser robust and easy to read.

## 4. Parsing Unary Operators

Next, we reach the `unary` rule:
`unary → ( "!" | "-" ) unary | primary ;`

If you completed the challenge at the end of the previous chapter, you might already have this! Notice that `unary` calls *itself* on the right side of the operator. Add this method:

```python
    def unary(self) -> expr.Expr:
        if self.match(TokenType.BANG, TokenType.MINUS):
            operator = self.previous()
            right = self.unary()
            return expr.Unary(operator, right)

        return self.primary()
```

Because `unary()` calls `self.unary()` to parse its operand, it evaluates right-to-left. If you type `!!true`, it parses the first `!`, then recursively calls `unary()` to parse the second `!`, making the second one the child of the first. This naturally creates right-associativity.

If the current token is not a `!` or `-`, we simply fall through to `self.primary()`, completing the chain.

## 5. Syntax Errors and Synchronization

Our parser can now build complex trees. However, we must consider what happens when the user types invalid code. 

A parser has two main jobs:
1. Produce an AST for valid code.
2. Detect errors, report them, and recover quickly so it can find subsequent errors.

If we encounter a syntax error, we raise a `ParseError`. But if we simply let the exception crash the program, the user only sees one error at a time. We want to catch that error, realign our parser's internal state, and keep going. This technique is called **Panic Mode** recovery.

When a parser goes into panic mode, it knows its state is corrupted. It must discard tokens until it finds a boundary where it knows it can safely resume parsing. In C-like languages, statement boundaries are marked by semicolons or keywords that begin a new statement (like `class`, `fun`, `var`, or `if`).

Add the following `synchronize()` method to your `Parser` class under the Error Handling section:

```python
    def synchronize(self):
        """Discards tokens until a statement boundary is found."""
        self.advance()

        while not self.is_at_end():
            if self.previous().type == TokenType.SEMICOLON:
                return

            # If the next token is a keyword that starts a statement, we are safe.
            next_type = self.peek().type
            if next_type in (TokenType.CLASS, TokenType.FUN, TokenType.VAR, 
                             TokenType.FOR, TokenType.IF, TokenType.WHILE, 
                             TokenType.PRINT, TokenType.RETURN):
                return

            self.advance()
```

> **Technical Note: Exception Unwinding**
>
> Right now, we catch the `ParseError` in our top-level `parse()` method and simply return `None`. Because we only parse single expressions at this stage, we have no statement boundaries to synchronize to.
> 
> In Chapter 7, when we add statements and blocks, we will update `parse()` to catch `ParseError`, call `self.synchronize()`, and continue parsing the next line. We write this method now to lay down the correct architectural foundation.

## 6. Wiring it Up

Your parser is now fully capable of handling mathematical precedence. Let us prove it.

Ensure `snek.py` is unchanged from the end of Chapter 3, where it calls `scanner.scan_tokens()`, passes them to `parser.parse()`, and prints the result using `AstPrinter`.

**Test it out:**
Run your REPL: `python snek.py`
Type the following expression:
`-123 * (45.67 + 8) == 10;`

Press Enter. The `AstPrinter` should output the exact hierarchical structure of the AST:
`(== (* (- 123.0) (group (+ 45.67 8.0))) 10.0)`

If your output matches, congratulations! You have successfully implemented a recursive descent parser. Your interpreter now possesses a rigorous understanding of mathematics and logic. In the next chapter, we will bring these trees to life by writing the actual evaluation logic.

---

## 7. Challenges

### 1. The Exponentiation Operator (`**`)
Add an exponentiation operator (`**`) to Snek. 

**Requirements:**
*   It should have higher precedence than multiplication and division (`factor`), but lower precedence than unary operators like `-` (`unary`).
*   Unlike addition and multiplication, exponentiation is **right-associative**. Mathematical rules state that `2 ** 3 ** 2` must be evaluated as `2 ** (3 ** 2)` (which is `2 ** 9 = 512`), NOT `(2 ** 3) ** 2` (which is `8 ** 2 = 64`).
*   Your updated grammar rules for this section of the precedence ladder should look like this (notice the `?` in the `power` rule, which means the operator and right-hand side are optional - can appear zero or one time before recursing):
    ```text
    factor → power ( ( "/" | "*" ) power )* ;
    power  → unary ( "**" power )? ;
    unary  → ( "!" | "-" ) unary | primary ;
    ```

<details>
<summary>Implementation Hints</summary>

To implement this successfully, you will need to touch a few different parts of the pipeline:

1.  **The Scanner:** 
    *   Add a new `STAR_STAR` enum value to `TokenType`.
    *   In your scanner, modify the logic that handles `*`. Use `self.match('*')` to check if a second asterisk follows the first. If it does, emit a `STAR_STAR` token; otherwise, emit a standard `STAR`.
2.  **The AST:** 
    *   You do not need a new AST node. Exponentiation is just another `Binary` expression. Your `AstPrinter` will automatically handle it using the operator's lexeme.
3.  **The Parser (Precedence):** 
    *   Create a new method named `power()`. 
    *   To slot it into the correct precedence level, update your `factor()` method to call `self.power()` instead of `self.unary()`. 
    *   Your new `power()` method will then be the one to call `self.unary()`.
4.  **The Parser (Associativity):** 
    *   Because exponentiation evaluates right-to-left, you cannot parse it using a `while` loop like the other binary operators. 
    *   Instead, inside `power()`, first call `self.unary()` to get the left operand. 
    *   Then, use an `if self.match(TokenType.STAR_STAR):` block. If you find the operator, grab the previous token, and **recursively call `self.power()`** to get the right operand. Finally, wrap them in an `expr.Binary` node and return it.
</details>

### 2. The Ternary Operator (`? :`)
Many languages feature a C-style conditional operator, also known as the ternary operator: `condition ? true_expr : false_expr`. 

Add this to your AST and parser.

**Requirements:**
*   It should have the lowest precedence, right below `equality`.
*   Ternary operators are right-associative. The expression `a ? b : c ? d : e` evaluates as `a ? b : (c ? d : e)`. 
*   Your updated grammar rules for this section of the precedence ladder should look like this:
    ```text
    expression → ternary ;
    ternary    → equality ( "?" expression ":" ternary )? ;
    equality   → comparison ( ( "!=" | "==" ) comparison )* ;
    ```

<details>
<summary>Implementation Hints</summary>

1.  **The Scanner:**
    *   Add `QUESTION` and `COLON` to `TokenType`.
    *   Update `scanner.py` to recognize `?` and `:` as single-character tokens.
2.  **The AST Node:** 
    *   You will need a new node in `expr.py`:
        ```python
        @dataclass
        class Ternary(Expr):
            condition: Expr
            then_branch: Expr
            else_branch: Expr
        ```
    *   Update `ast_printer.py` with a new `case` to format this node (e.g., returning something like `(? condition then_branch else_branch)`).
3.  **Precedence:** 
    *   The ternary operator should have the lowest precedence, sitting right below `equality`. 
    *   Update your `expression()` entry point to call a new `ternary()` method instead of `equality()`.
4.  **Associativity and Parsing Logic:** 
    *   Ternary operators are right-associative. The expression `a ? b : c ? d : e` evaluates as `a ? b : (c ? d : e)`. 
    *   In your new `ternary()` method, start by parsing the condition using `self.equality()`. 
    *   Then, use `if self.match(TokenType.QUESTION):` to check for the operator. 
    *   If it matches, parse the `then_branch`. You can use `self.expression()` here to allow any valid expression.
    *   Next, use `self.consume(TokenType.COLON, "...")` to ensure the colon is present.
    *   Finally, for the `else_branch`, **recursively call `self.ternary()`** to ensure right-associativity, and return your new `expr.Ternary` node.
5.  **Verification:**
    *   If you run the REPL and type `1 == 2 ? 3 : 4 == 4 ? 5 : 6;`, your `AstPrinter` should output exactly:
        `(? (== 1.0 2.0) 3.0 (? (== 4.0 4.0) 5.0 6.0))`
</details>