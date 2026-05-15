from ast_nodes import *


# ─────────────────────────────────────────────
#  Quadruple  (op, arg1, arg2, result)
# ─────────────────────────────────────────────
class Quad:
    def __init__(self, op, arg1=None, arg2=None, result=None):
        self.op = op
        self.arg1 = arg1
        self.arg2 = arg2
        self.result = result

    def __repr__(self):
        return f"({self.op!s:<12} {str(self.arg1):<12} {str(self.arg2):<12} {str(self.result)})"


class CodeGenerator:
    """Generates a flat list of Quad objects from the AST."""

    def __init__(self):
        self.quads = []
        self._temp_count = 0

    def new_temp(self):
        self._temp_count += 1
        return f"t{self._temp_count}"

    def emit(self, op, arg1=None, arg2=None, result=None):
        q = Quad(op, arg1, arg2, result)
        self.quads.append(q)
        return q

    def current_index(self):
        return len(self.quads)

    # patch the jump address of a quad at index idx
    def patch(self, idx, target):
        self.quads[idx].result = target

    # ------------------------------------------------------------------ #
    def generate(self, program: Program):
        for stmt in program.body:
            self.gen_stmt(stmt)
        self.emit('HALT')
        return self.quads

    # ------------------------------------------------------------------ #
    #  Statements
    # ------------------------------------------------------------------ #
    def gen_stmt(self, stmt):
        if isinstance(stmt, Assign):
            val = self.gen_expr(stmt.expr)
            self.emit('=', val, None, stmt.name)

        elif isinstance(stmt, Increment):
            if stmt.op == '++':
                self.emit('+', stmt.name, 1, stmt.name)
            else:
                self.emit('-', stmt.name, 1, stmt.name)

        elif isinstance(stmt, Write):
            val = self.gen_expr(stmt.expr)
            self.emit('WRITE', val)

        elif isinstance(stmt, If):
            self.gen_if(stmt)

        elif isinstance(stmt, While):
            self.gen_while(stmt)

        elif isinstance(stmt, For):
            self.gen_for(stmt)

    def gen_if(self, stmt: If):
        cond = self.gen_expr(stmt.condition)

        # JMPF cond _ <else/end>
        jmpf_idx = self.current_index()
        self.emit('JMPF', cond, None, None)   # patch later

        for s in stmt.then_body:
            self.gen_stmt(s)

        if stmt.else_body:
            # JMP to skip else
            jmp_idx = self.current_index()
            self.emit('JMP', None, None, None)

            else_start = self.current_index()
            self.patch(jmpf_idx, else_start)

            for s in stmt.else_body:
                self.gen_stmt(s)

            end = self.current_index()
            self.patch(jmp_idx, end)
        else:
            end = self.current_index()
            self.patch(jmpf_idx, end)

    def gen_while(self, stmt: While):
        loop_start = self.current_index()
        cond = self.gen_expr(stmt.condition)

        jmpf_idx = self.current_index()
        self.emit('JMPF', cond, None, None)

        for s in stmt.body:
            self.gen_stmt(s)

        self.emit('JMP', None, None, loop_start)
        end = self.current_index()
        self.patch(jmpf_idx, end)

    def gen_for(self, stmt: For):
        # init
        init_val = self.gen_expr(stmt.init.expr)
        self.emit('=', init_val, None, stmt.init.name)

        loop_start = self.current_index()
        cond = self.gen_expr(stmt.condition)

        jmpf_idx = self.current_index()
        self.emit('JMPF', cond, None, None)

        for s in stmt.body:
            self.gen_stmt(s)

        # update
        upd = stmt.update
        if isinstance(upd, Increment):
            if upd.op == '++':
                self.emit('+', upd.name, 1, upd.name)
            else:
                self.emit('-', upd.name, 1, upd.name)
        else:
            v = self.gen_expr(upd.expr)
            self.emit('=', v, None, upd.name)

        self.emit('JMP', None, None, loop_start)
        end = self.current_index()
        self.patch(jmpf_idx, end)

    # ------------------------------------------------------------------ #
    #  Expressions – return the name/temp that holds the result
    # ------------------------------------------------------------------ #
    def gen_expr(self, expr):
        if isinstance(expr, IntLiteral):
            return expr.value     # use constant directly

        if isinstance(expr, StringLiteral):
            return ('str', expr.value)   # tagged tuple

        if isinstance(expr, Var):
            return expr.name

        if isinstance(expr, UnaryOp):
            operand = self.gen_expr(expr.operand)
            t = self.new_temp()
            self.emit('NEG', operand, None, t)
            return t

        if isinstance(expr, BinOp):
            l = self.gen_expr(expr.left)
            r = self.gen_expr(expr.right)
            t = self.new_temp()
            self.emit(expr.op, l, r, t)
            return t

        raise ValueError(f"Unknown expr node: {type(expr)}")


# ─────────────────────────────────────────────
#  Virtual Machine
# ─────────────────────────────────────────────
class VMError(Exception):
    pass


class VirtualMachine:
    """Executes the quadruple list produced by CodeGenerator."""

    ARITH = {'+', '-', '*', '/'}
    RELATIONAL = {'<', '>', '<=', '>=', '==', '!='}
    LOGICAL = {'and', 'or'}

    def __init__(self, quads, symbol_table):
        self.quads = quads
        # Initialize all declared variables to 0
        self.memory = {name: 0 for name in symbol_table}
        self.pc = 0   # program counter

    def load(self, name_or_val):
        """Resolve an argument to a concrete Python value."""
        if isinstance(name_or_val, tuple) and name_or_val[0] == 'str':
            return name_or_val[1]
        if isinstance(name_or_val, int):
            return name_or_val
        if isinstance(name_or_val, str):
            if name_or_val not in self.memory:
                raise VMError(f"Undefined variable or temp: '{name_or_val}'")
            return self.memory[name_or_val]
        return name_or_val

    def store(self, name, value):
        self.memory[name] = value

    def run(self):
        while self.pc < len(self.quads):
            q = self.quads[self.pc]
            self.pc += 1

            op = q.op

            if op == 'HALT':
                break

            elif op == '=':
                val = self.load(q.arg1)
                self.store(q.result, val)

            elif op == 'NEG':
                val = self.load(q.arg1)
                self.store(q.result, -val)

            elif op in self.ARITH:
                a = self.load(q.arg1)
                b = self.load(q.arg2)
                if op == '+':  result = a + b
                elif op == '-': result = a - b
                elif op == '*': result = a * b
                elif op == '/':
                    if b == 0:
                        raise VMError("Division by zero")
                    result = a // b
                self.store(q.result, result)

            elif op in self.RELATIONAL:
                a = self.load(q.arg1)
                b = self.load(q.arg2)
                if op == '<':  result = 1 if a < b  else 0
                elif op == '>': result = 1 if a > b  else 0
                elif op == '<=': result = 1 if a <= b else 0
                elif op == '>=': result = 1 if a >= b else 0
                elif op == '==': result = 1 if a == b else 0
                elif op == '!=': result = 1 if a != b else 0
                self.store(q.result, result)

            elif op in self.LOGICAL:
                a = self.load(q.arg1)
                b = self.load(q.arg2)
                if op == 'and': result = 1 if (a and b) else 0
                elif op == 'or': result = 1 if (a or b) else 0
                self.store(q.result, result)

            elif op == 'WRITE':
                val = self.load(q.arg1)
                print(val)

            elif op == 'JMPF':
                cond = self.load(q.arg1)
                if not cond:
                    self.pc = q.result

            elif op == 'JMP':
                self.pc = q.result

            else:
                raise VMError(f"Unknown opcode: '{op}'")
