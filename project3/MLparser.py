"""
Parser for the Micro-language.
Grammar:
   <program> -> begin <statement_list> end
   <statement_list> -> <statement>; { <statement>; }
   <statement> -> <assign> | read( <id_list> ) | write( <expr_list> )
   <assign> -> <ident> := <expression>
   <id_list> -> <ident> {, <ident>}
   <expr_list> -> <expression> {, <expression>}
   <expression> -> <primary> {<arith_op> <primary>}
   <primary> -> (<expression>) | <ident> | INTLITERAL
   <ident> -> ID
   <arith_op> -> + | -
"""

from lexer import *
import re

#######################
# For debugging
debug = False
recursion_level = 0

def add_debug(fn):
    def debugged_fn(current, G):
        global recursion_level
        print(" "*recursion_level + "Entering: %s (%s)" % (fn.__name__, current))
        recursion_level += 3
        R = fn(current, G)
        recursion_level -= 3
        print(" "*recursion_level + "Leaving: %s" % (fn.__name__))
        return R

    return debugged_fn if debug else fn
#######################

class ParserError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


#######################################
# Parsing code
def parser(source_file, token_file):
    """
    source_file: A program written in the ML langauge.
    returns True if the code is syntactically correct.
    Throws a ParserError otherwise.
    """
    G = lexer(source_file, token_file)
    return program(next(G), G).line == "$"

def raiseParserError(symbol, expectedTokenStr, actualToken):
    raise ParserError('Error in <%s>, expect "%s", actually is "%s" \nLine num: %d, column num: %d'
                      %(symbol, expectedTokenStr, actualToken.pattern, actualToken.line_num, actualToken.col))

@add_debug
#<program> -> begin <statement_list> end
def program(curToken, G):
    if curToken.pattern != "begin":
        raise raiseParserError("program", "begin", curToken)
    curToken = statement_list(next(G), G)
    if curToken.pattern != "end":
        raiseParserError("program", "end", curToken)
    return next(G)

@add_debug
#<statement_list> -> <statement>; { <statement>; }
def statement_list(curToken, G):
    curToken = statement(curToken, G)
    if curToken.pattern != ";":
        raiseParserError("statement_list", ";", curToken)
    while True: # re.match("write|read|[a-zA-Z]\w*", next(G)):
        curToken = next(G)
        ###########################################################################
        if curToken.pattern == "end":
            return curToken
        ###########################################################################
        if not re.match("write|read|[a-zA-Z]\w*", curToken.pattern):
            break
        curToken = statement(curToken, G)
        if curToken.pattern != ";":
            raiseParserError("statement_list", ";", curToken)

    return curToken

@add_debug
#<statement> -> <assign> | read( <id_list> ) | write( <expr_list> )
def statement(curToken, G):
    if curToken.pattern == "read":
        curToken = next(G)
        if curToken.pattern != '(':
            raiseParserError("statement", '(', curToken)
        curToken = id_list(next(G), G)
        if curToken.pattern != ')':
            raiseParserError("statement", ')', curToken)
        return next(G)
    if curToken.pattern == "write":
        curToken = next(G)
        if curToken.pattern != '(':
            raiseParserError("statement", '(', curToken)
        curToken = expr_list(next(G), G)
        if curToken.pattern != ')':
            raiseParserError("statement", ')', curToken)
        return next(G)
    return assign(curToken, G)

@add_debug
#<assign> -> <ident> := <expression>
def assign(curToken, G):
    curToken = ident(curToken, G)
    if curToken.pattern != ":=":
        raiseParserError("assign", ":=", curToken)
    return expression(next(G), G)

@add_debug
#<id_list> -> <ident> {, <ident>}
def id_list(curToken, G):
    curToken = ident(curToken, G)
    while curToken.pattern == ",":
        curToken = ident(next(G), G)
    return curToken

@add_debug
#<expr_list> -> <expression> {, <expression>}
def expr_list(curToken, G):
    curToken = expression(curToken, G)
    while curToken.pattern == ",":
        curToken = expression(next(G), G)
    return curToken

@add_debug
#<expression> -> <primary> {<arith_op> <primary>}
def expression(curToken, G):
    curToken = primary(curToken, G)
    while curToken.pattern in ("+", "-"):
        curToken = primary(arith_op(curToken, G), G)
    return curToken

@add_debug
#<primary> -> (<expression>) | <ident> | INTLITERAL
def primary(curToken, G):
    if curToken.pattern == "(":
        curToken = expression(next(G), G)
        if curToken.pattern != ")":
            raiseParserError("primary", ")", curToken)
        return next(G)
    if re.match("[a-zA-Z]\w*", curToken.pattern):
        return ident(curToken, G)
    if not re.match("\d+", curToken.pattern):
        raiseParserError('INTLITERAL', "\d+", curToken)
    return next(G)

@add_debug
#<ident> -> ID
def ident(curToken, G):
    # if re.match("end|read|write", curToken.pattern) or not re.match("[a-zA-Z]\w*", curToken.pattern):
    # line above would match all the test cases but it's still wrong
    # because it didn't exclude the reserved word begin for ID
    if re.match("begin|end|read|write", curToken.pattern) or not re.match("[a-zA-Z]\w*", curToken.pattern):
        raiseParserError("ID", "[a-zA-Z]\w* and not RESERVED tokens", curToken)
    return next(G)

@add_debug
#<arith_op> -> + | -
def arith_op(curToken, G):
    if curToken.pattern not in ("+", "-"):
        raiseParserError("arith_op", "+|-", curToken)
    return next(G)










