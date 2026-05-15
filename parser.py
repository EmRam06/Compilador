from lexer import TokenType, Token
from ast_nodes import *


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos]

    def peek(self, offset=1):
        p = self.pos + offset
        if p < len(self.tokens):
            return self.tokens[p]
        return self.tokens[-1]  # EOF

    def advance(self):
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def expect(self, ttype):
        tok = self.current()
        if tok.type != ttype:
            raise ParseError(
                f"Line {tok.line}: expected {ttype}, got {tok.type} ({tok.value!r})"
            )
        return self.advance()

    def match(self, *ttypes):
        if self.current().type in ttypes:
            return self.advance()
        return None

    # ------------------------------------------------------------------ #
    #  Top level
    # ------------------------------------------------------------------ #
    def parse(self):
        return self.parse_program()

    def parse_program(self):
        self.expect(TokenType.PROGRAM)
        name_tok = self.expect(TokenType.ID)
        self.expect(TokenType.LBRACE)

        var_decls = []
        while self.current().type == TokenType.VAR:
            var_decls.extend(self.parse_var_decl())

        self.expect(TokenType.BEGIN)
        self.expect(TokenType.SEMICOLON)

        body = self.parse_statement_list()

        self.expect(TokenType.END)
        self.expect(TokenType.SEMICOLON)
        self.expect(TokenType.RBRACE)
        self.expect(TokenType.EOF)

        return Program(name_tok.value, var_decls, body)

    def parse_var_decl(self):
        """var a, b, c : int;  → list of VarDecl"""
        self.expect(TokenType.VAR)
        names = [self.expect(TokenType.ID).value]
        while self.match(TokenType.COMMA):
            names.append(self.expect(TokenType.ID).value)
        self.expect(TokenType.COLON)
        vtype_tok = self.expect(TokenType.INT)
        self.expect(TokenType.SEMICOLON)
        return [VarDecl(names, 'int')]

    # ------------------------------------------------------------------ #
    #  Statements
    # ------------------------------------------------------------------ #
    def parse_statement_list(self):
        stmts = []
        while self.current().type not in (TokenType.END, TokenType.RBRACE, TokenType.EOF, TokenType.ELSE):
            stmts.append(self.parse_statement())
        return stmts

    def parse_statement(self):
        tok = self.current()

        if tok.type == TokenType.ID:
            return self.parse_assign_or_inc()

        if tok.type == TokenType.WRITE:
            return self.parse_write()

        if tok.type == TokenType.IF:
            return self.parse_if()

        if tok.type == TokenType.WHILE:
            return self.parse_while()

        if tok.type == TokenType.FOR:
            return self.parse_for()

        raise ParseError(f"Line {tok.line}: unexpected token {tok.type} ({tok.value!r})")

    def parse_assign_or_inc(self):
        """ID := expr ;   or   ID++ ;   or   ID-- ;"""
        id_tok = self.expect(TokenType.ID)

        if self.current().type == TokenType.ASSIGN:
            self.advance()
            expr = self.parse_expr()
            self.expect(TokenType.SEMICOLON)
            return Assign(id_tok.value, expr, id_tok.line)

        if self.current().type in (TokenType.INC, TokenType.DEC):
            op_tok = self.advance()
            self.expect(TokenType.SEMICOLON)
            return Increment(id_tok.value, op_tok.value, id_tok.line)

        raise ParseError(
            f"Line {id_tok.line}: expected ':=' or '++' or '--' after identifier"
        )

    def parse_write(self):
        tok = self.expect(TokenType.WRITE)
        self.expect(TokenType.LPAREN)
        expr = self.parse_expr()
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.SEMICOLON)
        return Write(expr, tok.line)

    def parse_if(self):
        tok = self.expect(TokenType.IF)
        self.expect(TokenType.LPAREN)
        cond = self.parse_expr()
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.THEN)
        self.expect(TokenType.LBRACE)
        then_body = self.parse_statement_list()
        self.expect(TokenType.RBRACE)

        else_body = None
        if self.match(TokenType.ELSE):
            self.expect(TokenType.LBRACE)
            else_body = self.parse_statement_list()
            self.expect(TokenType.RBRACE)

        return If(cond, then_body, else_body, tok.line)

    def parse_while(self):
        tok = self.expect(TokenType.WHILE)
        self.expect(TokenType.LPAREN)
        cond = self.parse_expr()
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.DO)
        self.expect(TokenType.LBRACE)
        body = self.parse_statement_list()
        self.expect(TokenType.RBRACE)
        return While(cond, body, tok.line)

    def parse_for(self):
        """for (id := expr ; cond ; id++ ) { body }"""
        tok = self.expect(TokenType.FOR)
        self.expect(TokenType.LPAREN)

        # init: id := expr
        id_tok = self.expect(TokenType.ID)
        self.expect(TokenType.ASSIGN)
        init_expr = self.parse_expr()
        init = Assign(id_tok.value, init_expr, id_tok.line)
        self.expect(TokenType.SEMICOLON)

        # condition
        cond = self.parse_expr()
        self.expect(TokenType.SEMICOLON)

        # update: id++ or id-- or id := expr
        upd_id = self.expect(TokenType.ID)
        if self.current().type in (TokenType.INC, TokenType.DEC):
            op_tok = self.advance()
            update = Increment(upd_id.value, op_tok.value, upd_id.line)
        elif self.current().type == TokenType.ASSIGN:
            self.advance()
            update = Assign(upd_id.value, self.parse_expr(), upd_id.line)
        else:
            raise ParseError(f"Line {upd_id.line}: expected update expression in for")

        self.expect(TokenType.RPAREN)
        self.expect(TokenType.LBRACE)
        body = self.parse_statement_list()
        self.expect(TokenType.RBRACE)

        return For(init, cond, update, body, tok.line)

    # ------------------------------------------------------------------ #
    #  Expressions  (recursive descent with precedence)
    # ------------------------------------------------------------------ #
    # Precedence (lowest → highest):
    #   or
    #   and
    #   == !=
    #   < > <= >=
    #   + -
    #   * /
    #   unary -
    #   primary

    def parse_expr(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.current().type == TokenType.OR:
            op = self.advance()
            right = self.parse_and()
            left = BinOp(left, 'or', right, op.line)
        return left

    def parse_and(self):
        left = self.parse_equality()
        while self.current().type == TokenType.AND:
            op = self.advance()
            right = self.parse_equality()
            left = BinOp(left, 'and', right, op.line)
        return left

    def parse_equality(self):
        left = self.parse_relational()
        while self.current().type in (TokenType.EQ, TokenType.NEQ):
            op = self.advance()
            right = self.parse_relational()
            left = BinOp(left, op.value, right, op.line)
        return left

    def parse_relational(self):
        left = self.parse_additive()
        while self.current().type in (TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op = self.advance()
            right = self.parse_additive()
            left = BinOp(left, op.value, right, op.line)
        return left

    def parse_additive(self):
        left = self.parse_multiplicative()
        while self.current().type in (TokenType.PLUS, TokenType.MINUS):
            op = self.advance()
            right = self.parse_multiplicative()
            left = BinOp(left, op.value, right, op.line)
        return left

    def parse_multiplicative(self):
        left = self.parse_unary()
        while self.current().type in (TokenType.TIMES, TokenType.DIV):
            op = self.advance()
            right = self.parse_unary()
            left = BinOp(left, op.value, right, op.line)
        return left

    def parse_unary(self):
        if self.current().type == TokenType.MINUS:
            op = self.advance()
            operand = self.parse_unary()
            return UnaryOp('-', operand, op.line)
        return self.parse_primary()

    def parse_primary(self):
        tok = self.current()

        if tok.type == TokenType.INT_LITERAL:
            self.advance()
            return IntLiteral(tok.value, tok.line)

        if tok.type == TokenType.STRING_LITERAL:
            self.advance()
            return StringLiteral(tok.value, tok.line)

        if tok.type == TokenType.ID:
            self.advance()
            return Var(tok.value, tok.line)

        if tok.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expr()
            self.expect(TokenType.RPAREN)
            return expr

        raise ParseError(
            f"Line {tok.line}: unexpected token in expression: {tok.type} ({tok.value!r})"
        )
