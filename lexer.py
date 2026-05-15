import re
from enum import Enum, auto

class TokenType(Enum):
    # Literals
    INT_LITERAL = auto()
    STRING_LITERAL = auto()
    ID = auto()

    # Keywords
    PROGRAM = auto()
    VAR = auto()
    INT = auto()
    BEGIN = auto()
    END = auto()
    WRITE = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    WHILE = auto()
    DO = auto()
    FOR = auto()
    AND = auto()
    OR = auto()

    # Operators
    ASSIGN = auto()       # :=
    PLUS = auto()         # +
    MINUS = auto()        # -
    TIMES = auto()        # *
    DIV = auto()          # /
    GT = auto()           # >
    LT = auto()           # <
    GTE = auto()          # >=
    LTE = auto()          # <=
    EQ = auto()           # ==
    NEQ = auto()          # !=
    INC = auto()          # ++
    DEC = auto()          # --

    # Delimiters
    LPAREN = auto()       # (
    RPAREN = auto()       # )
    LBRACE = auto()       # {
    RBRACE = auto()       # }
    SEMICOLON = auto()    # ;
    COMMA = auto()        # ,
    COLON = auto()        # :

    EOF = auto()


KEYWORDS = {
    'program': TokenType.PROGRAM,
    'var': TokenType.VAR,
    'int': TokenType.INT,
    'begin': TokenType.BEGIN,
    'end': TokenType.END,
    'write': TokenType.WRITE,
    'if': TokenType.IF,
    'then': TokenType.THEN,
    'else': TokenType.ELSE,
    'while': TokenType.WHILE,
    'do': TokenType.DO,
    'for': TokenType.FOR,
    'and': TokenType.AND,
    'or': TokenType.OR,
}


class Token:
    def __init__(self, type_, value, line):
        self.type = type_
        self.value = value
        self.line = line

    def __repr__(self):
        return f'Token({self.type}, {self.value!r}, line={self.line})'


class LexerError(Exception):
    pass


class Lexer:
    def __init__(self, source):
        self.source = source
        self.pos = 0
        self.line = 1
        self.tokens = []

    def error(self, char):
        raise LexerError(f"Unexpected character '{char}' at line {self.line}")

    def peek(self, offset=1):
        p = self.pos + offset
        if p < len(self.source):
            return self.source[p]
        return None

    def advance(self):
        ch = self.source[self.pos]
        if ch == '\n':
            self.line += 1
        self.pos += 1
        return ch

    def skip_whitespace_and_comments(self):
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch in ' \t\r\n':
                self.advance()
            elif ch == '/' and self.peek() == '/':
                while self.pos < len(self.source) and self.source[self.pos] != '\n':
                    self.pos += 1
            else:
                break

    def read_string(self):
        line = self.line
        self.advance()  # consume opening "
        s = ''
        while self.pos < len(self.source) and self.source[self.pos] != '"':
            s += self.advance()
        if self.pos >= len(self.source):
            raise LexerError(f"Unterminated string at line {line}")
        self.advance()  # consume closing "
        return Token(TokenType.STRING_LITERAL, s, line)

    def read_number(self):
        line = self.line
        num = ''
        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            num += self.advance()
        return Token(TokenType.INT_LITERAL, int(num), line)

    def read_id_or_keyword(self):
        line = self.line
        word = ''
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
            word += self.advance()
        ttype = KEYWORDS.get(word, TokenType.ID)
        return Token(ttype, word, line)

    def tokenize(self):
        while self.pos < len(self.source):
            self.skip_whitespace_and_comments()
            if self.pos >= len(self.source):
                break

            ch = self.source[self.pos]
            line = self.line

            if ch == '"':
                self.tokens.append(self.read_string())
            elif ch.isdigit():
                self.tokens.append(self.read_number())
            elif ch.isalpha() or ch == '_':
                self.tokens.append(self.read_id_or_keyword())
            elif ch == ':':
                if self.peek() == '=':
                    self.advance(); self.advance()
                    self.tokens.append(Token(TokenType.ASSIGN, ':=', line))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.COLON, ':', line))
            elif ch == '>':
                if self.peek() == '=':
                    self.advance(); self.advance()
                    self.tokens.append(Token(TokenType.GTE, '>=', line))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.GT, '>', line))
            elif ch == '<':
                if self.peek() == '=':
                    self.advance(); self.advance()
                    self.tokens.append(Token(TokenType.LTE, '<=', line))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.LT, '<', line))
            elif ch == '=':
                if self.peek() == '=':
                    self.advance(); self.advance()
                    self.tokens.append(Token(TokenType.EQ, '==', line))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.EQ, '=', line))
            elif ch == '!':
                if self.peek() == '=':
                    self.advance(); self.advance()
                    self.tokens.append(Token(TokenType.NEQ, '!=', line))
                else:
                    self.error(ch)
            elif ch == '+':
                if self.peek() == '+':
                    self.advance(); self.advance()
                    self.tokens.append(Token(TokenType.INC, '++', line))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.PLUS, '+', line))
            elif ch == '-':
                if self.peek() == '-':
                    self.advance(); self.advance()
                    self.tokens.append(Token(TokenType.DEC, '--', line))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.MINUS, '-', line))
            elif ch == '*':
                self.advance()
                self.tokens.append(Token(TokenType.TIMES, '*', line))
            elif ch == '/':
                self.advance()
                self.tokens.append(Token(TokenType.DIV, '/', line))
            elif ch == '(':
                self.advance()
                self.tokens.append(Token(TokenType.LPAREN, '(', line))
            elif ch == ')':
                self.advance()
                self.tokens.append(Token(TokenType.RPAREN, ')', line))
            elif ch == '{':
                self.advance()
                self.tokens.append(Token(TokenType.LBRACE, '{', line))
            elif ch == '}':
                self.advance()
                self.tokens.append(Token(TokenType.RBRACE, '}', line))
            elif ch == ';':
                self.advance()
                self.tokens.append(Token(TokenType.SEMICOLON, ';', line))
            elif ch == ',':
                self.advance()
                self.tokens.append(Token(TokenType.COMMA, ',', line))
            else:
                self.error(ch)

        self.tokens.append(Token(TokenType.EOF, None, self.line))
        return self.tokens
