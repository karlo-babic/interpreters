from token_type import TokenType
from token_class import Token
import expr
import error
import stmt

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

    # --- Grammar Rules ---

    def declaration(self) -> stmt.Stmt | None:
        try:
            if self.match(TokenType.CLASS):
                return self.class_declaration()
            if self.match(TokenType.FUN):
                return self.function("function")
            if self.match(TokenType.VAR):
                return self.var_declaration()
            return self.statement()
        except ParseError:
            self.synchronize()
            return None

    def class_declaration(self) -> stmt.Stmt:
        name = self.consume(TokenType.IDENTIFIER, "Expect class name.")
        self.consume(TokenType.LEFT_BRACE, "Expect '{' before class body.")

        methods = []
        while not self.check(TokenType.RIGHT_BRACE) and not self.is_at_end():
            is_static = self.match(TokenType.CLASS)
            method = self.function("method")
            method.is_static = is_static
            methods.append(method)

        self.consume(TokenType.RIGHT_BRACE, "Expect '}' after class body.")
        return stmt.Class(name, methods)

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
        self.consume(TokenType.LEFT_BRACE, "Expect '{' before " + kind + " body.")
        
        body = self.block()
        return stmt.Function(name, parameters, body)

    def var_declaration(self) -> stmt.Stmt:
        name = self.consume(TokenType.IDENTIFIER, "Expect variable name.")

        initializer = None
        if self.match(TokenType.EQUAL):
            initializer = self.expression()

        self.consume(TokenType.SEMICOLON, "Expect ';' after variable declaration.")
        return stmt.Var(name, initializer)

    def statement(self) -> stmt.Stmt:
        if self.match(TokenType.PRINT):
            return self.print_statement()
        if self.match(TokenType.LEFT_BRACE):
            return stmt.Block(self.block())
        if self.match(TokenType.IF):
            return self.if_statement()
        if self.match(TokenType.WHILE):
            return self.while_statement()
        if self.match(TokenType.FOR):
            return self.for_statement()
        if self.match(TokenType.RETURN):
            return self.return_statement()

        return self.expression_statement()

    def print_statement(self) -> stmt.Stmt:
        value = self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after value.")
        return stmt.Print(value)

    def block(self) -> list[stmt.Stmt]:
        statements = []

        while not self.check(TokenType.RIGHT_BRACE) and not self.is_at_end():
            decl = self.declaration()
            if decl is not None:
                statements.append(decl)

        self.consume(TokenType.RIGHT_BRACE, "Expect '}' after block.")
        return statements

    def if_statement(self) -> stmt.Stmt:
        self.consume(TokenType.LEFT_PAREN, "Expect '(' after 'if'.")
        condition = self.expression()
        self.consume(TokenType.RIGHT_PAREN, "Expect ')' after if condition.")

        then_branch = self.statement()
        else_branch = None
        if self.match(TokenType.ELSE):
            else_branch = self.statement()

        return stmt.If(condition, then_branch, else_branch)

    def while_statement(self) -> stmt.Stmt:
        self.consume(TokenType.LEFT_PAREN, "Expect '(' after 'while'.")
        condition = self.expression()
        self.consume(TokenType.RIGHT_PAREN, "Expect ')' after condition.")
        body = self.statement()

        return stmt.While(condition, body)

    def for_statement(self) -> stmt.Stmt:
        self.consume(TokenType.LEFT_PAREN, "Expect '(' after 'for'.")

        # Parse Initializer
        if self.match(TokenType.SEMICOLON):
            initializer = None
        elif self.match(TokenType.VAR):
            initializer = self.var_declaration()
        else:
            initializer = self.expression_statement()

        # Parse Condition
        condition = None
        if not self.check(TokenType.SEMICOLON):
            condition = self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after loop condition.")

        # Parse Increment
        increment = None
        if not self.check(TokenType.RIGHT_PAREN):
            increment = self.expression()
        self.consume(TokenType.RIGHT_PAREN, "Expect ')' after for clauses.")

        # Parse Body
        body = self.statement()

        # Desugar into a While loop
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

    def return_statement(self) -> stmt.Stmt:
        keyword = self.previous()
        value = None
        if not self.check(TokenType.SEMICOLON):
            value = self.expression()

        self.consume(TokenType.SEMICOLON, "Expect ';' after return value.")
        return stmt.Return(keyword, value)

    def expression_statement(self) -> stmt.Stmt:
        expr_node = self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after expression.")
        return stmt.Expression(expr_node)

    def expression(self) -> expr.Expr:
        return self.assignment()

    def assignment(self) -> expr.Expr:
        expr_node = self.ternary()

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

    def ternary(self) -> expr.Expr:
        e = self.logic_or() 

        if self.match(TokenType.QUESTION):
            then_branch = self.expression()
            self.consume(TokenType.COLON, "Expect ':' after then branch of ternary operator.")
            # Recursively call ternary() for right-associativity
            else_branch = self.ternary() 
            e = expr.Ternary(e, then_branch, else_branch)

        return e

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

    def equality(self) -> expr.Expr:
        e = self.comparison()

        while self.match(TokenType.BANG_EQUAL, TokenType.EQUAL_EQUAL):
            operator = self.previous()
            right = self.comparison()
            e = expr.Binary(e, operator, right)

        return e
    
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
        e = self.power()

        while self.match(TokenType.SLASH, TokenType.STAR):
            operator = self.previous()
            right = self.power()
            e = expr.Binary(e, operator, right)

        return e

    def power(self) -> expr.Expr:
        e = self.unary()

        if self.match(TokenType.STAR_STAR):
            operator = self.previous()
            # Recursively call power() to build a right-leaning tree
            right = self.power() 
            e = expr.Binary(e, operator, right)

        return e

    def unary(self) -> expr.Expr:
        if self.match(TokenType.BANG, TokenType.MINUS):
            operator = self.previous()
            right = self.unary()
            return expr.Unary(operator, right)

        return self.call()

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

    def primary(self) -> expr.Expr:
        if self.match(TokenType.FALSE): return expr.Literal(False)
        if self.match(TokenType.TRUE): return expr.Literal(True)
        if self.match(TokenType.NIL): return expr.Literal(None)

        if self.match(TokenType.NUMBER, TokenType.STRING):
            return expr.Literal(self.previous().literal)

        if self.match(TokenType.IDENTIFIER):
            return expr.Variable(self.previous())

        if self.match(TokenType.FUN):
            return self.anonymous_function()

        if self.match(TokenType.THIS):
            return expr.This(self.previous())

        if self.match(TokenType.LEFT_PAREN):
            e = self.expression()
            self.consume(TokenType.RIGHT_PAREN, "Expect ')' after expression.")
            return expr.Grouping(e)

        raise self.error(self.peek(), "Expect expression.")

    def anonymous_function(self) -> expr.AnonymousFunction:
        keyword = self.previous() # The 'fun' token
        self.consume(TokenType.LEFT_PAREN, "Expect '(' after 'fun'.")
        
        parameters = []
        if not self.check(TokenType.RIGHT_PAREN):
            while True:
                if len(parameters) >= 255:
                    self.error(self.peek(), "Can't have more than 255 parameters.")
                
                parameters.append(self.consume(TokenType.IDENTIFIER, "Expect parameter name."))
                
                if not self.match(TokenType.COMMA):
                    break
                    
        self.consume(TokenType.RIGHT_PAREN, "Expect ')' after parameters.")
        self.consume(TokenType.LEFT_BRACE, "Expect '{' before anonymous function body.")
        
        body = self.block()
        return expr.AnonymousFunction(keyword, parameters, body)

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

    # --- Parser Entry Point ---

    def parse(self) -> list[stmt.Stmt]:
        statements = []
        while not self.is_at_end():
            decl = self.declaration()
            if decl is not None:
                statements.append(decl)
        return statements