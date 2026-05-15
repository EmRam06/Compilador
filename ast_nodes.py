# AST Node definitions

class Program:
    def __init__(self, name, var_decls, body):
        self.name = name
        self.var_decls = var_decls  # list of VarDecl
        self.body = body            # list of statements

class VarDecl:
    def __init__(self, names, vtype):
        self.names = names  # list of str
        self.vtype = vtype  # 'int'

class Assign:
    def __init__(self, name, expr, line):
        self.name = name
        self.expr = expr
        self.line = line

class Increment:
    """name++ or name--"""
    def __init__(self, name, op, line):
        self.name = name
        self.op = op   # '++' or '--'
        self.line = line

class Write:
    def __init__(self, expr, line):
        self.expr = expr
        self.line = line

class If:
    def __init__(self, condition, then_body, else_body, line):
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body  # may be None
        self.line = line

class While:
    def __init__(self, condition, body, line):
        self.condition = condition
        self.body = body
        self.line = line

class For:
    def __init__(self, init, condition, update, body, line):
        self.init = init          # Assign
        self.condition = condition
        self.update = update      # Increment or Assign
        self.body = body
        self.line = line

# Expressions
class BinOp:
    def __init__(self, left, op, right, line):
        self.left = left
        self.op = op
        self.right = right
        self.line = line

class UnaryOp:
    def __init__(self, op, operand, line):
        self.op = op
        self.operand = operand
        self.line = line

class IntLiteral:
    def __init__(self, value, line):
        self.value = value
        self.line = line

class StringLiteral:
    def __init__(self, value, line):
        self.value = value
        self.line = line

class Var:
    def __init__(self, name, line):
        self.name = name
        self.line = line
