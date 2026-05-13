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

We will implement a custom dynamic language called **Snek** (Snek is Not Exactly Komplicated). This language is modeled after the **Lox** language described in the Crafting Interpreters textbook. While we follow the core design of Lox, our implementation utilizes modern Python idioms (specifically Python 3.10+ `match`/`case` structural pattern matching) to elegantly traverse tree structures. 

The project covers the entire language pipeline:
1.  **Scanning:** Converting raw source code into semantic tokens.
2.  **Parsing:** Constructing Abstract Syntax Trees (ASTs) using Recursive Descent.
3.  **Static Analysis:** Lexical variable resolution and early error detection.
4.  **Interpretation:** Executing the AST to run the program.

---

### Try it Live: The Snek Web REPL
We have compiled the Python interpreter to run directly in the browser. You can write and execute Snek code immediately without installing anything locally.

<div align="center" style="margin: 1rem 0;">
  <a href="repl/" class="btn btn-primary fs-5">Launch the Snek Web REPL</a>
</div>

<details>
<summary>How Snek Runs on the Web (The Execution Stack):<br><strong>Snek ➔ Python ➔ C ➔ WebAssembly ➔ Machine Code ➔ Silicon</strong><br>(Click to expand details)</summary>

<br>

Running a custom interpreter in the browser via PyScript creates a deep execution pipeline.
When you type `print 1 + 2;` into the Web REPL, the computation traverses six layers of abstraction.

1. **Snek (The Guest Language):** Your Python code scans, parses, and evaluates the Snek AST. Snek requests that Python add two numbers.
2. **Python Bytecode (The Host Language):** The Snek interpreter is compiled into Python Bytecode (`.pyc`), an internal instruction set meant for the CPython Virtual Machine.
3. **WebAssembly (The Target):** The CPython Virtual Machine (written in C) has been compiled ahead-of-time by Emscripten into **WebAssembly (Wasm)**. Wasm is a low-level binary format that the browser understands.
4. **The Browser Engine (JIT):** The browser's engine (e.g., V8 in Chrome) uses a Just-In-Time (JIT) compiler to translate the WebAssembly bytecode into optimized **Native Machine Code** for your specific operating system and architecture.
5. **The Operating System:** The OS schedules and hands the native binary instructions (ones and zeroes) over to your physical CPU.
6. **The Silicon:** The CPU routes electrical voltages through logic gates (transistors) in the Arithmetic Logic Unit (ALU) to physically calculate the number `3` and return the result all the way back up the stack to your screen.

As the creator of Snek, you only ever have to worry about Layer 1. The rest of the stack handles the execution.

</details>

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