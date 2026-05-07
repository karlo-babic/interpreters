from token_type import TokenType
from token_class import Token
import error

class Scanner:
    keywords = {
        "and": TokenType.AND,
        "class": TokenType.CLASS,
        "else": TokenType.ELSE,
        "false": TokenType.FALSE,
        "for": TokenType.FOR,
        "fun": TokenType.FUN,
        "if": TokenType.IF,
        "nil": TokenType.NIL,
        "or": TokenType.OR,
        "print": TokenType.PRINT,
        "return": TokenType.RETURN,
        "super": TokenType.SUPER,
        "this": TokenType.THIS,
        "true": TokenType.TRUE,
        "var": TokenType.VAR,
        "while": TokenType.WHILE,
    }

    def __init__(self, source):
        self.source = source
        self.tokens = []
        
        self.start = 0   # First character in the lexeme being scanned
        self.current = 0 # Character currently being considered
        self.line = 1    # What source line `current` is on

    def scan_tokens(self) -> list[Token]:
        while not self.is_at_end():
            # We are at the beginning of the next lexeme.
            self.start = self.current
            self.scan_token()

        self.tokens.append(Token(TokenType.EOF, "", None, self.line))
        return self.tokens

    def is_at_end(self) -> bool:
        return self.current >= len(self.source)

    def scan_token(self):
        c = self.advance()
        
        if c == '(': self.add_token(TokenType.LEFT_PAREN)
        elif c == ')': self.add_token(TokenType.RIGHT_PAREN)
        elif c == '{': self.add_token(TokenType.LEFT_BRACE)
        elif c == '}': self.add_token(TokenType.RIGHT_BRACE)
        elif c == ',': self.add_token(TokenType.COMMA)
        elif c == '.': self.add_token(TokenType.DOT)
        elif c == '-': self.add_token(TokenType.MINUS)
        elif c == '+': self.add_token(TokenType.PLUS)
        elif c == ';': self.add_token(TokenType.SEMICOLON)
        elif c == '?': self.add_token(TokenType.QUESTION)
        elif c == ':': self.add_token(TokenType.COLON)

        elif c == '!':
            self.add_token(TokenType.BANG_EQUAL if self.match('=') else TokenType.BANG)
        elif c == '=':
            self.add_token(TokenType.EQUAL_EQUAL if self.match('=') else TokenType.EQUAL)
        elif c == '<':
            self.add_token(TokenType.LESS_EQUAL if self.match('=') else TokenType.LESS)
        elif c == '>':
            self.add_token(TokenType.GREATER_EQUAL if self.match('=') else TokenType.GREATER)
        elif c == '*':
            self.add_token(TokenType.STAR_STAR if self.match('*') else TokenType.STAR)

        elif c == '/':
            if self.match('/'):
                # A comment goes until the end of the line.
                while self.peek() != '\n' and not self.is_at_end():
                    self.advance()
            elif self.match('*'):
                # Block comment
                self.block_comment()
            else:
                self.add_token(TokenType.SLASH)

        elif c == '"':
            self.string()

        elif c.isdigit():
            self.number()

        elif c.isalpha() or c == '_':
            self.identifier()

        # Ignore whitespace
        elif c in [' ', '\r', '\t']:
            pass 
        elif c == '\n':
            self.line += 1
            
        else:
            error.error(self.line, "Unexpected character.")

    def advance(self) -> str:
        """Consumes the next character and returns it."""
        c = self.source[self.current]
        self.current += 1
        return c

    def add_token(self, type: TokenType, literal=None):
        """Grabs the text of the current lexeme and creates a token."""
        text = self.source[self.start : self.current]
        self.tokens.append(Token(type, text, literal, self.line))

    def match(self, expected: str) -> bool:
        if self.is_at_end(): return False
        if self.source[self.current] != expected: return False

        self.current += 1
        return True
    
    def peek(self) -> str:
        if self.is_at_end(): return '\0'
        return self.source[self.current]
    
    def string(self):
        while self.peek() != '"' and not self.is_at_end():
            if self.peek() == '\n':
                self.line += 1
            self.advance()

        if self.is_at_end():
            error.error(self.line, "Unterminated string.")
            return

        # The closing ".
        self.advance()

        # Trim the surrounding quotes and save the literal value.
        value = self.source[self.start + 1 : self.current - 1]
        self.add_token(TokenType.STRING, value)

    def number(self):
        while self.peek().isdigit():
            self.advance()

        # Look for a fractional part.
        if self.peek() == '.' and self.peek_next().isdigit():
            # Consume the "."
            self.advance()

            while self.peek().isdigit():
                self.advance()

        # Parse the string into a Python float for the literal value
        self.add_token(TokenType.NUMBER, float(self.source[self.start : self.current]))

    def peek_next(self) -> str:
        if self.current + 1 >= len(self.source): return '\0'
        return self.source[self.current + 1]

    def identifier(self):
        while self.peek().isalnum() or self.peek() == '_':
            self.advance()

        text = self.source[self.start : self.current]
        type = self.keywords.get(text, TokenType.IDENTIFIER)
        self.add_token(type)

    def block_comment(self):
        # Continue until we find '*/'
        while not (self.peek() == '*' and self.peek_next() == '/') and not self.is_at_end():
            if self.peek() == '\n':
                self.line += 1
            self.advance()

        if self.is_at_end():
            error.error(self.line, "Unterminated block comment.")
            return

        # Consume the closing '*/'
        self.advance() # Consumes '*'
        self.advance() # Consumes '/'