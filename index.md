---
layout: home
title: Home
nav_order: 1
---

# Implementing Interpreters

>"Fairy tales are more than true: not because they tell us that dragons exist, but because they tell us that dragons can be beaten."
>\- G.K. Chesterton

This course covers the design and implementation of programming languages. While compilers and interpreters are often viewed as complex systems, they are built upon standard data structures and algorithms. By building one from scratch, we will examine the engineering principles required to process and execute code.

### The Project: Snek

We will implement a custom dynamic language called **Snek**. The project covers the entire language pipeline:

1.  **Scanning:** Converting raw source code into tokens.
2.  **Parsing:** Constructing Abstract Syntax Trees (ASTs) from tokens.
3.  **Static Analysis:** Variable resolution and error checking.
4.  **Interpretation:** Executing the AST to run the program.

We will use **Python (version 3.10 or newer)** as the implementation language.

---

You can begin with **[1. Introduction](1-Introduction.md)**.

## Literature

The course structure follows the first half of Robert Nystrom's book.

-   [**Crafting Interpreters**](https://craftinginterpreters.com/contents.html) by Robert Nystrom.

### Supplementary Resources
-   [**Compilers: Principles, Techniques, and Tools**](https://en.wikipedia.org/wiki/Compilers:_Principles,_Techniques,_and_Tools) (The "Dragon Book").
    *   The classic text on compiler theory. Useful if you want to dig deeper into the math behind parsers.
-   [**Python 3.10+ Documentation**](https://docs.python.org/3/)

<img src="https://craftinginterpreters.com/image/header.png" alt="Crafting Interpreters Illustration">