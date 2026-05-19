---
layout: default
title: "10. Classes"
nav_order: 11
---

# 10. Classes, Methods, & Initializers

We have variables, control flow, and functions. Our interpreter can run complex algorithms, but as programs grow, organizing them becomes difficult. Object-Oriented Programming (OOP) provides a paradigm for bundling data (state) with the functions that operate on that data (behavior). 

In this chapter, we will add classes to Snek. We will build the ability to declare classes, instantiate them into objects, store data in properties, and define methods that interact with that data using the `this` keyword.

## 1. Object-Oriented Snek

There are several approaches to object-oriented programming. Some languages, like JavaScript and Lua, use *prototypes*, where objects inherit directly from other objects. Languages like Java and C++ use *classes*, acting as rigid blueprints that define exactly what an instance contains.

Snek takes a hybrid approach similar to Python. It is class-based, meaning behaviors (methods) are defined in a class. However, instances are dynamic. You do not need to declare fields in the class definition. You can attach new data to an instance at runtime simply by assigning to it.

Let us start by defining the syntax for a class declaration.

```text
declaration    → classDecl
               | funDecl
               | varDecl
               | statement ;

classDecl      → "class" IDENTIFIER "{" function* "}" ;
```

A class declaration is the `class` keyword, a name, and a curly-braced block containing zero or more method declarations. Notice that methods do not use the `fun` keyword. 

First, we add the new Abstract Syntax Tree (AST) node to `stmt.py`.

```python
@dataclass
class Class(Stmt):
    name: Token
    methods: list['Function']
```

## 2. Class Declarations

To parse this new syntax, open `parser.py`. We update our `declaration()` entry point to look for the new keyword.

```python
    def declaration(self) -> stmt.Stmt | None:
        try:
            if self.match(TokenType.CLASS):
                return self.class_declaration()
            if self.match(TokenType.FUN):
                return self.function("function")
            # ... existing code ...
```

Next, we write the parsing method. It looks for the class name, the opening brace, parses methods until it hits the closing brace, and returns the AST node.

```python
    def class_declaration(self) -> stmt.Stmt:
        name = self.consume(TokenType.IDENTIFIER, "Expect class name.")
        self.consume(TokenType.LEFT_BRACE, "Expect '{' before class body.")

        methods = []
        while not self.check(TokenType.RIGHT_BRACE) and not self.is_at_end():
            methods.append(self.function("method"))

        self.consume(TokenType.RIGHT_BRACE, "Expect '}' after class body.")
        return stmt.Class(name, methods)
```

Notice that we reuse the existing `function()` parser method, passing in `"method"` so that any syntax errors report "Expect method name" instead of "Expect function name".

### 2.1 Resolving and Interpreting Classes

Before we execute a class, it must pass through semantic analysis. Open `resolver.py` and add the `match/case` logic to `resolve()`:

```python
            case stmt.Class(name, methods):
                self.declare(name)
                self.define(name)
                # We will resolve the methods later in this chapter.
```

At runtime, a class declaration creates a SnekClass object and binds it to a variable. Create a new file named `snek_class.py`. This is the runtime representation of a class.

```python
class SnekClass:
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name
```

Now, open `interpreter.py`. Make sure to import `SnekClass`, then add the execution logic to `execute()`.

```python
            case stmt.Class(name, methods):
                self.environment.define(name.lexeme, None)
                klass = SnekClass(name.lexeme)
                self.environment.assign(name, klass)
```

We declare the class's name in the environment with `None` before actually creating the `SnekClass` object, and then use `assign` to store the object afterward. This two-stage process is important for closures. It ensures that if a method inside the class refers to the class itself (for example, to instantiate a new instance of its own class), it captures an environment where the class name is already registered. If we didn't declare it first, the methods would capture an environment that didn't know the class existed yet.

## 3. Creating Instances

A class is useless if we cannot create instances of it. In Snek, we do not use a `new` keyword. Instead, classes are callable. Calling a class acts as a factory that generates instances.

Open `snek_class.py`. Make `SnekClass` inherit from our existing `SnekCallable` interface.

```python
from snek_callable import SnekCallable
from snek_instance import SnekInstance

class SnekClass(SnekCallable):
    def __init__(self, name: str):
        self.name = name

    def arity(self) -> int:
        return 0

    def call(self, interpreter, arguments: list[object]) -> object:
        instance = SnekInstance(self)
        return instance

    def __str__(self):
        return self.name
```

To support this, we need the runtime representation of an instance. Create `snek_instance.py`.

```python
class SnekInstance:
    def __init__(self, klass: 'SnekClass'):
        self.klass = klass

    def __str__(self):
        return f"{self.klass.name} instance"
```

### Test it out
Run the REPL and type the following:
```c
class Bagel {}
var bagel = Bagel();
print bagel;
```
If your interpreter prints `Bagel instance`, you have successfully implemented object instantiation.

## 4. Properties (State)

Instances need to store data. We access and modify data using "get" and "set" expressions via the dot (`.`) operator.

```text
call           → primary ( "(" arguments? ")" | "." IDENTIFIER )* ;
assignment     → ( call "." )? IDENTIFIER "=" assignment
               | logic_or ;
```

Add the two new AST nodes to `expr.py`.

```python
@dataclass
class Get(Expr):
    object: Expr
    name: Token

@dataclass
class Set(Expr):
    object: Expr
    name: Token
    value: Expr
```

### 4.1 Parsing Properties

In `parser.py`, update `call()` to recognize property access.

```python
    def call(self) -> expr.Expr:
        expr_node = self.primary()

        while True:
            if self.match(TokenType.LEFT_PAREN):
                expr_node = self.finish_call(expr_node)
            elif self.match(TokenType.DOT):
                name = self.consume(TokenType.IDENTIFIER, "Expect property name after '.'.")
                expr_node = expr.Get(expr_node, name)
            else:
                break

        return expr_node
```

Parsing assignment is trickier. A property assignment (`cake.flavor = "chocolate";`) looks exactly like a property access (`cake.flavor`) until the parser hits the `=` sign. 

> **Technical Note: L-Values and R-Values**
> 
> The left side of an assignment is called an *l-value*, because it specifies a storage location rather than evaluating to a concrete value. 
> To parse it, we parse the left side normally. If we subsequently hit an `=`, we take the expression we just parsed and transform it into an assignment node.

Update `assignment()` in `parser.py`:

```python
    def assignment(self) -> expr.Expr:
        expr_node = self.ternary() # Or logic_or(), if you did not implement ternary

        if self.match(TokenType.EQUAL):
            equals = self.previous()
            value = self.assignment()

            if isinstance(expr_node, expr.Variable):
                name = expr_node.name
                return expr.Assign(name, value)
            elif isinstance(expr_node, expr.Get):
                return expr.Set(expr_node.object, expr_node.name, value)

            self.error(equals, "Invalid assignment target.")

        return expr_node
```

### 4.2 Resolving and Interpreting Properties

In `resolver.py`, add the two new cases to `resolve()`. We do not resolve the property name itself because properties are strictly looked up dynamically at runtime.

```python
            case expr.Get(object_expr, name):
                self.resolve(object_expr)
                
            case expr.Set(object_expr, name, value_expr):
                self.resolve(value_expr)
                self.resolve(object_expr)
```

Now for the interpreter. First, open `snek_instance.py` and give it a dictionary to hold state, along with getters and setters.

```python
from token_class import Token
import error

class SnekInstance:
    def __init__(self, klass: 'SnekClass'):
        self.klass = klass
        self.fields: dict[str, object] = {}

    def get(self, name: Token) -> object:
        if name.lexeme in self.fields:
            return self.fields[name.lexeme]
            
        raise error.SnekRuntimeError(name, f"Undefined property '{name.lexeme}'.")

    def set(self, name: Token, value: object):
        self.fields[name.lexeme] = value

    def __str__(self):
        return f"{self.klass.name} instance"
```

In `interpreter.py`, first add the necessary import for `SnekInstance` at the top of the file: `from snek_instance import SnekInstance`. Then, add two new cases to the `evaluate` method's `match` block.

```python
            case expr.Get(object_expr, name):
                obj = self.evaluate(object_expr)
                if not isinstance(obj, SnekInstance):
                    raise error.SnekRuntimeError(name, "Only instances have properties.")
                return obj.get(name)
                
            case expr.Set(object_expr, name, value_expr):
                obj = self.evaluate(object_expr)
                if not isinstance(obj, SnekInstance):
                    raise error.SnekRuntimeError(name, "Only instances have properties.")
                    
                value = self.evaluate(value_expr)
                obj.set(name, value)
                return value
```

### Test it out
You can now attach data to objects.
```c
class Bagel {}
var cake = Bagel();
cake.flavor = "Everything";
print cake.flavor;
```

## 5. Methods and `this`

State is working, now we need behavior. Methods are defined on the class but are accessed through the instance. 

First, update `SnekClass` in `snek_class.py` to hold its methods.

```python
class SnekClass(SnekCallable):
    def __init__(self, name: str, methods: dict[str, 'SnekFunction']):
        self.name = name
        self.methods = methods
        
    def find_method(self, name: str) -> 'SnekFunction | None':
        return self.methods.get(name)
        
    # ... existing code ...
```

In `interpreter.py`, update the stmt.Class case to populate this dictionary.

```python
            case stmt.Class(name, methods):
                self.environment.define(name.lexeme, None)
                
                class_methods = {}
                for method in methods:
                    function = SnekFunction(method, self.environment)
                    class_methods[method.name.lexeme] = function
                
                klass = SnekClass(name.lexeme, class_methods)
                self.environment.assign(name, klass)
```

Now, update `SnekInstance.get()` in `snek_instance.py` to look for a method if a field is not found.

```python
    def get(self, name: Token) -> object:
        if name.lexeme in self.fields:
            return self.fields[name.lexeme]
            
        method = self.klass.find_method(name.lexeme)
        if method is not None:
            return method
            
        raise error.SnekRuntimeError(name, f"Undefined property '{name.lexeme}'.")
```

### 5.1 Binding `this`

If you call a method, how does it access the instance's fields? It needs the `this` keyword. 

`this` acts like a hidden parameter. When a method is accessed, we must create a special environment that binds the instance to the name `"this"`. 

First, add the AST node to `expr.py`:

```python
@dataclass
class This(Expr):
    keyword: Token
```

In `parser.py`, add the rule to `primary()`:

```python
        if self.match(TokenType.THIS):
            return expr.This(self.previous())
```

Now, open `snek_function.py`. We add a `bind()` method to `SnekFunction`.

```python
    def bind(self, instance: 'SnekInstance') -> 'SnekFunction':
        environment = Environment(self.closure)
        environment.define("this", instance)
        return SnekFunction(self.declaration, environment)
```

We wrap the original closure in a new environment containing `"this"`, and return a new function object. We use this back in `SnekInstance.get()`.

```python
        method = self.klass.find_method(name.lexeme)
        if method is not None:
            return method.bind(self)
```

> **Python Toolbox: Bound Methods**
> 
> Snek's implementation mirrors how Python itself handles methods. In Python, a method is just a function attached to a class. When you access `obj.method_name`, Python intercepts the access and wraps the function in a "bound method" object that remembers `obj`. Snek's `bind()` method creates our equivalent of a bound method.

### 5.2 Statically Checking `this`

The user should not be allowed to use `this` outside of a method body. We catch this during Semantic Analysis.

In `resolver.py`, add a `ClassType` enum alongside `FunctionType`.

```python
class ClassType(Enum):
    NONE = auto()
    CLASS = auto()
```

Initialize `self.current_class = ClassType.NONE` in `__init__`. Then update `stmt.Class` to set it, and properly resolve the methods:

```python
            case stmt.Class(name, methods):
                enclosing_class = self.current_class
                self.current_class = ClassType.CLASS
                
                self.declare(name)
                self.define(name)
                
                self.begin_scope()
                self.scopes[-1]["this"] = {"defined": True, "used": True, "line": name.line}
                
                for method in methods:
                    self.resolve_function(method.params, method.body)
                    
                self.end_scope()
                self.current_class = enclosing_class
```

Finally, resolve the `This` expression:

```python
            case expr.This(keyword):
                if self.current_class == ClassType.NONE:
                    error.error(keyword.line, "Can't use 'this' outside of a class.")
                    return
                self.resolve_local(node, keyword)
```

And in `interpreter.py`, evaluate it just like a variable:

```python
            case expr.This(keyword):
                return self.look_up_variable(keyword, expression)
```

### Test it out
You can now execute methods that alter instance state.

```c
class Egotist {
  speak() {
    print "My name is " + this.name;
  }
}

var ego = Egotist();
ego.name = "Snek";
ego.speak();
```

## 6. Initializers

To ensure an object starts in a valid state, we need initialization logic. In Snek, if a class declares a method named `init()`, it will be executed automatically when the class is instantiated.

Open `snek_class.py`. Update `call()` to look for the initializer and run it.

```python
    def call(self, interpreter, arguments: list[object]) -> object:
        instance = SnekInstance(self)
        
        initializer = self.find_method("init")
        if initializer is not None:
            initializer.bind(instance).call(interpreter, arguments)
            
        return instance
```

We must also update the class's `arity()` to match the `init()` method so parameter validation works.

```python
    def arity(self) -> int:
        initializer = self.find_method("init")
        if initializer is not None:
            return initializer.arity()
        return 0
```

### 6.1 Edge Cases and Safeguards

What happens if a user calls `init()` directly (e.g., `obj.init()`)? What if they try to return a value from it? We must strictly enforce that an initializer *always* returns `this` and never an arbitrary value.

First, update `SnekFunction` in `snek_function.py` to track if it is an initializer.

```python
    def __init__(self, declaration: stmt.Function | expr.AnonymousFunction, closure: Environment, is_initializer: bool = False):
        self.declaration = declaration
        self.closure = closure
        self.is_initializer = is_initializer
        
    def bind(self, instance: 'SnekInstance') -> 'SnekFunction':
        environment = Environment(self.closure)
        environment.define("this", instance)
        return SnekFunction(self.declaration, environment, self.is_initializer)
```

Next, in `interpreter.py`'s `stmt.Class` block, detect the `"init"` method when populating the dictionary:

```python
                for method in methods:
                    is_init = method.name.lexeme == "init"
                    function = SnekFunction(method, self.environment, is_init)
                    class_methods[method.name.lexeme] = function
```

Finally, in `snek_function.py` update `SnekFunction.call()` to explicitly return `this` if it is an initializer.

```python
        try:
            interpreter.execute_block(self.declaration.body, environment)
        except ReturnException as return_value:
            if self.is_initializer:
                return self.closure.get_at(0, "this")
            return return_value.value
            
        if self.is_initializer:
            return self.closure.get_at(0, "this")
        return None
```

To prevent a user from returning a value inside an `init()` method, we can detect this statically during the resolution phase. 

First, open `resolver.py` and expand the `FunctionType` enum to include methods and initializers:

```python
class FunctionType(Enum):
    NONE = auto()
    FUNCTION = auto()
    INITIALIZER = auto()
    METHOD = auto()
```

Next, update your `resolve_function` helper method to accept a new `function_type` parameter. Instead of hardcoding `FunctionType.FUNCTION`, it will use this parameter to track our current state.

```python
    def resolve_function(self, params: list['Token'], body: list[stmt.Stmt], function_type: FunctionType):
        enclosing_function = self.current_function
        self.current_function = function_type
        
        self.begin_scope()
        for param in params:
            self.declare(param)
            self.define(param)
        
        self.resolve_statements(body)
        self.end_scope()
        
        self.current_function = enclosing_function
```

Because we changed the signature of `resolve_function`, you will need to update your existing `stmt.Function` and `expr.AnonymousFunction` cases to pass `FunctionType.FUNCTION` as the third argument.

Now we can properly pass the context from the `stmt.Class` loop. If the method is named `"init"`, we pass `INITIALIZER`; otherwise, we pass `METHOD`. Update your `stmt.Class` case:

```python
                for method in methods:
                    declaration = FunctionType.METHOD
                    if method.name.lexeme == "init":
                        declaration = FunctionType.INITIALIZER
                    
                    self.resolve_function(method.params, method.body, declaration)
```

Finally, add the validation to the `stmt.Return` case. We throw an error if the user tries to return a value while the resolver's state is set to `INITIALIZER`.

```python
            case stmt.Return(keyword, value):
                if self.current_function == FunctionType.NONE:
                    error.error(keyword.line, "Can't return from top-level code.")
                elif self.current_function == FunctionType.INITIALIZER and value is not None:
                    error.error(keyword.line, "Can't return a value from an initializer.")
                    
                if value is not None:
                    self.resolve(value)
```

Our classes are fully operational. They have state, behavior, and initialization logic.

### Test it out
Let's put everything together to prove that our classes can enforce arity, initialize state, and execute methods.

```c
class Coffee {
  init(roast) {
    this.roast = roast;
  }

  brew() {
    print "Brewing " + this.roast + " coffee";
  }
}

var maker = Coffee("dark");
maker.brew();
```
If it prints `Brewing dark coffee`, your interpreter now fully supports Object-Oriented Programming. If you try to call `Coffee()` without passing exactly one argument, your newly added arity checking should safely catch the error.

---

## 7. Challenges

### 1. Dynamic vs. Static Fields
In Snek, as in Python and JavaScript, fields are created dynamically when you assign to them (`obj.field = 1`). In Java, C#, and C++, fields must be explicitly declared inside the class block before runtime.

What are the performance and memory trade-offs of Snek's dynamic approach? How does it affect the interpreter's ability to catch typos? 

### 2. Feature Addition: Static Methods
We have methods on instances, but no way to define "static" methods that are called directly on the class itself (e.g., `Math.square(3)`). 

Extend Snek to support static methods. Use the `class` keyword preceding a method declaration to indicate it belongs to the class, not its instances.

```c
class Math {
  class square(n) {
    return n * n;
  }
}

print Math.square(3); // Prints 9
```

<details>
<summary>Implementation Hints</summary>

1. **The AST (`stmt.py`)**: Add a boolean flag `is_static: bool = False` to the `stmt.Function` node so the interpreter knows what kind of method it's dealing with.
2. **The Parser (`parser.py`)**: Inside `class_declaration()`, check `if self.match(TokenType.CLASS):` right before parsing a method. If it matches, set your new `is_static` flag on the parsed method to `True`.
3. **The Runtime (`snek_class.py`)**: `SnekClass` is the object that represents the class at runtime. Update its `__init__` method to accept a second dictionary: `static_methods`. Add a helper method `find_static_method(name)` to look them up.
4. **The Interpreter (`interpreter.py`)**: 
   * When executing `stmt.Class`, iterate through the methods and partition them into two separate dictionaries (`class_methods` and `static_methods`) based on the flag. Pass both to the `SnekClass` constructor.
   * When evaluating `expr.Get`, add an `elif isinstance(obj, SnekClass):` block. If the object being accessed is a class, try to look up the name in its static methods instead of failing.
5. **Semantic Analysis (`resolver.py`)**: Because static methods are called on the class itself, there is no instance! Therefore, using the `this` keyword inside a static method should be a static error. 
   * Add a new `STATIC_METHOD` value to your `FunctionType` enum. 
   * When iterating over the class methods in the `stmt.Class` case, if the method is static, pass `FunctionType.STATIC_METHOD` to `self.resolve_function`.
   * Finally, in the `expr.This` case, add an `elif` block that checks if `self.current_function == FunctionType.STATIC_METHOD`. If so, report a precise error: `"Can't use 'this' inside a static method."`
</details>

### 3. Trace-it: Method Resolution
Given the following Snek code, trace the chain of events that occurs on the final line when `callback()` is invoked. 

```c
class Person {
  init(name) {
    this.name = name;
  }

  sayName() {
    print this.name;
  }
}

var jane = Person("Jane");
var callback = jane.sayName;

callback();
```

<details>
<summary>Answer</summary>

1. Evaluating `jane.sayName` evaluates to an `expr.Get`.
2. The interpreter calls `jane.get()`. It fails to find a field named `sayName`.
3. It calls `jane.klass.find_method("sayName")`, retrieving the `SnekFunction`.
4. It calls `bind(jane)`, returning a *new* `SnekFunction` wrapped in an environment where `"this"` maps to `jane`.
5. The `callback` variable stores this newly bound function.
6. When `callback()` is evaluated, the `SnekFunction.call()` method runs. It looks up `this.name` inside its captured environment, successfully resolving to `jane`'s fields, printing `"Jane"`.
</details>