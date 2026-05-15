#!/usr/bin/env python3
"""
Compiler entry point.

Usage:
    python compiler.py <source_file> [--quads] [--ast]

Options:
    --quads   Print the generated quadruples before execution.
    --ast     Print a brief AST summary.
"""

import sys
import os

# Make sure our modules are importable
sys.path.insert(0, os.path.dirname(__file__))

from lexer import Lexer, LexerError
from parser import Parser, ParseError
from semantic import SemanticAnalyzer, SemanticError
from codegen import CodeGenerator, VirtualMachine, VMError


def compile_and_run(source: str, show_quads: bool = False, show_ast: bool = False):
    # ── 1. Lexical Analysis ──────────────────────────────────────────────
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
    except LexerError as e:
        print(f"[LEXER ERROR] {e}")
        return False

    # ── 2. Syntactic Analysis ────────────────────────────────────────────
    try:
        parser = Parser(tokens)
        ast = parser.parse()
    except ParseError as e:
        print(f"[PARSER ERROR] {e}")
        return False

    if show_ast:
        print("── AST Summary ──────────────────────────────────────────────────")
        print(f"Program: {ast.name}")
        for d in ast.var_decls:
            print(f"  VarDecl {d.names} : {d.vtype}")
        print(f"  {len(ast.body)} top-level statement(s)")
        print()

    # ── 3. Semantic Analysis ─────────────────────────────────────────────
    analyzer = SemanticAnalyzer()
    try:
        analyzer.analyze(ast)
    except SemanticError as e:
        print(f"[SEMANTIC ERROR]\n{e}")
        return False

    # ── 4. Code Generation ───────────────────────────────────────────────
    codegen = CodeGenerator()
    quads = codegen.generate(ast)

    if show_quads:
        print("── Quadruples ───────────────────────────────────────────────────")
        for i, q in enumerate(quads):
            print(f"  {i:3d}  {q}")
        print()

    # ── 5. Execute (Virtual Machine) ─────────────────────────────────────
    vm = VirtualMachine(quads, analyzer.symbol_table)
    try:
        print("── Output ───────────────────────────────────────────────────────")
        vm.run()
        print("─────────────────────────────────────────────────────────────────")
    except VMError as e:
        print(f"[RUNTIME ERROR] {e}")
        return False

    return True


def main():
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        sys.exit(1)

    show_quads = '--quads' in args
    show_ast   = '--ast'   in args
    files = [a for a in args if not a.startswith('--')]

    if not files:
        print("No source file specified.")
        sys.exit(1)

    for filepath in files:
        print(f"\n{'='*65}")
        print(f"  Compiling: {filepath}")
        print(f"{'='*65}")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
        except FileNotFoundError:
            print(f"File not found: {filepath}")
            continue

        ok = compile_and_run(source, show_quads=show_quads, show_ast=show_ast)
        if not ok:
            print(f"  *** Compilation/execution failed for {filepath}")


if __name__ == '__main__':
    main()
