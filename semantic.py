from ast_nodes import *


class SemanticError(Exception):
    pass


class SemanticAnalyzer:
    """
    Checks:
      1. Variables declared before use.
      2. Type consistency: arithmetic ops require int operands;
         boolean/logical operators require bool (relational) operands.
      3. Assignment type match.
    
    Returns a type for each expression node:
      'int'  – integer value
      'bool' – boolean / relational result
      'str'  – string literal
    """

    def __init__(self):
        self.symbol_table = {}  # name → 'int'
        self.errors = []

    def error(self, msg):
        self.errors.append(msg)

    def analyze(self, program: Program):
        # Register all variables
        for decl in program.var_decls:
            for name in decl.names:
                if name in self.symbol_table:
                    self.error(f"Variable '{name}' declared more than once.")
                self.symbol_table[name] = decl.vtype

        for stmt in program.body:
            self.check_stmt(stmt)

        if self.errors:
            raise SemanticError("Semantic errors found:\n" +
                                "\n".join(f"  - {e}" for e in self.errors))

    # ------------------------------------------------------------------ #
    #  Statements
    # ------------------------------------------------------------------ #
    def check_stmt(self, stmt):
        if isinstance(stmt, Assign):
            self.check_assign(stmt)
        elif isinstance(stmt, Increment):
            self.check_increment(stmt)
        elif isinstance(stmt, Write):
            self.check_expr(stmt.expr)  # any type OK for write
        elif isinstance(stmt, If):
            self.check_if(stmt)
        elif isinstance(stmt, While):
            self.check_while(stmt)
        elif isinstance(stmt, For):
            self.check_for(stmt)
        else:
            self.error(f"Unknown statement type: {type(stmt)}")

    def check_assign(self, stmt: Assign):
        if stmt.name not in self.symbol_table:
            self.error(f"Line {stmt.line}: variable '{stmt.name}' used before declaration.")
            return
        rhs_type = self.check_expr(stmt.expr)
        var_type = self.symbol_table[stmt.name]
        if rhs_type == 'str':
            self.error(
                f"Line {stmt.line}: cannot assign string to variable '{stmt.name}' of type {var_type}."
            )

    def check_increment(self, stmt: Increment):
        if stmt.name not in self.symbol_table:
            self.error(f"Line {stmt.line}: variable '{stmt.name}' used before declaration.")

    def check_if(self, stmt: If):
        cond_type = self.check_expr(stmt.condition)
        if cond_type not in ('bool', 'int'):
            self.error(
                f"Line {stmt.line}: if condition must be boolean or relational, got '{cond_type}'."
            )
        # Warn: using an int expression (not a comparison) as condition is a semantic error
        if cond_type == 'int':
            self.error(
                f"Line {stmt.line}: condition is a plain integer expression, not a boolean. "
                f"Use a comparison operator (e.g. a > 0)."
            )
        for s in stmt.then_body:
            self.check_stmt(s)
        if stmt.else_body:
            for s in stmt.else_body:
                self.check_stmt(s)

    def check_while(self, stmt: While):
        cond_type = self.check_expr(stmt.condition)
        if cond_type not in ('bool', 'int'):
            self.error(f"Line {stmt.line}: while condition must be boolean.")
        for s in stmt.body:
            self.check_stmt(s)

    def check_for(self, stmt: For):
        self.check_assign(stmt.init)
        cond_type = self.check_expr(stmt.condition)
        if cond_type not in ('bool', 'int'):
            self.error(f"Line {stmt.line}: for condition must be boolean.")
        if isinstance(stmt.update, Increment):
            self.check_increment(stmt.update)
        else:
            self.check_assign(stmt.update)
        for s in stmt.body:
            self.check_stmt(s)

    # ------------------------------------------------------------------ #
    #  Expressions – returns type string
    # ------------------------------------------------------------------ #
    def check_expr(self, expr):
        if isinstance(expr, IntLiteral):
            return 'int'

        if isinstance(expr, StringLiteral):
            return 'str'

        if isinstance(expr, Var):
            if expr.name not in self.symbol_table:
                self.error(f"Line {expr.line}: variable '{expr.name}' used before declaration.")
                return 'int'  # recover
            return self.symbol_table[expr.name]

        if isinstance(expr, UnaryOp):
            t = self.check_expr(expr.operand)
            if t != 'int':
                self.error(f"Line {expr.line}: unary '-' requires int operand, got '{t}'.")
            return 'int'

        if isinstance(expr, BinOp):
            return self.check_binop(expr)

        self.error(f"Unknown expression type: {type(expr)}")
        return 'int'

    RELATIONAL_OPS = {'<', '>', '<=', '>=', '==', '!='}
    LOGICAL_OPS    = {'and', 'or'}
    ARITH_OPS      = {'+', '-', '*', '/'}

    def check_binop(self, expr: BinOp):
        lt = self.check_expr(expr.left)
        rt = self.check_expr(expr.right)
        op = expr.op

        if op in self.ARITH_OPS:
            if lt != 'int':
                self.error(
                    f"Line {expr.line}: operator '{op}' requires int operands, "
                    f"left operand is '{lt}'."
                )
            if rt != 'int':
                self.error(
                    f"Line {expr.line}: operator '{op}' requires int operands, "
                    f"right operand is '{rt}'."
                )
            return 'int'

        if op in self.RELATIONAL_OPS:
            if lt == 'str' or rt == 'str':
                self.error(
                    f"Line {expr.line}: cannot compare strings with '{op}'."
                )
            return 'bool'

        if op in self.LOGICAL_OPS:
            if lt not in ('bool', 'int'):
                self.error(
                    f"Line {expr.line}: '{op}' requires boolean operands, left is '{lt}'."
                )
            if rt not in ('bool', 'int'):
                self.error(
                    f"Line {expr.line}: '{op}' requires boolean operands, right is '{rt}'."
                )
            # Extra check: if either operand is a plain int (not from a comparison), flag it
            if lt == 'int' and not self._is_relational(expr.left):
                self.error(
                    f"Line {expr.line}: left operand of '{op}' is a plain integer expression, "
                    f"not a boolean comparison."
                )
            if rt == 'int' and not self._is_relational(expr.right):
                self.error(
                    f"Line {expr.line}: right operand of '{op}' is a plain integer expression, "
                    f"not a boolean comparison."
                )
            return 'bool'

        self.error(f"Line {expr.line}: unknown operator '{op}'.")
        return 'int'

    def _is_relational(self, expr):
        """True if the expression is a relational/logical BinOp (produces bool)."""
        if isinstance(expr, BinOp):
            return expr.op in self.RELATIONAL_OPS or expr.op in self.LOGICAL_OPS
        return False
