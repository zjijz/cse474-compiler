import re
import sys

class LexerError(Exception):
    """
    Exception to be thrown when the lexer encounters a bad token.
    """
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return str(self.msg)

class Token:
    """
    A class for storing token information.
    The variable instances for a token object are:
    * t_class: The token class.
    * name: The name of the token.
    * pattern: The specific pattern of the token
    * line: The line containing the token
    * line_num: The line number (numbered from 1)
    * col: The column number (numbered from 0)
    """

    def __init__(self, t_class, name, pattern, line, line_num, col):
        """
        Constructor
        """
        self.t_class = t_class
        self.name = name
        self.pattern = pattern
        self.line = line
        self.line_num = int(line_num)
        self.col = int(col)

    def __str__(self):
        """
        Defines behavior of the str function on the Token class.
        Prints as a tupple all information except self.line.
        """
        return str((self.t_class, self.name, self.pattern, self.line_num, self.col))

    def __repr__(self):
        """
        Defines the behaviour of the repr() function
        on the Token class.
        """
        return "Token: " + str(self)

    def __eq__(self, other):
        """
        Defines behaviour of the == operator on the Token class
        """
        return self.t_class == other.t_class and self.name == other.name and \
               self.pattern == other.pattern and self.line == other.line and \
               self.line_num == other.line_num and self.col == other.col

def printAll(source_file, token_file):
    for t in lexer(source_file, token_file):
        print(t)

def lexer(source_file, token_file):

    re_list = []
    token_hash = {}

    with open(token_file) as tokenFp:
        for line in tokenFp:
            A = re.split("\s+", line.rstrip())
            re_list.append(A[2])
            token_hash[A[2]] = (A[0], A[1])

    lineNum = 0
    with open(source_file) as sourceFp:
        for line in sourceFp:
            lineNum += 1
            line = re.sub("#(.|\s)*$", "", line.rstrip())
            col = len(line) - len(line.lstrip())

            """
            while(col < len(line)):
                match = None
                for ptn in re_list:
                    match = re.match(ptn, line[col:])
                    if match:
                        yield Token(token_hash[ptn][0], token_hash[ptn][1], match.group(1), line, lineNum, col)
                        col += match.end(1) + re.match("\s*", line[col + match.end(1):]).end(0)
                        break
                if not match:
                    raise LexerError("Bad token (line %d, column %d): %s" %(lineNum, col, line[col:]))
            """

            while col < len(line):
                match = next(m for m in [re.match(ptn, line[col:]) for ptn in re_list] if m)

                if match:
                    yield Token(token_hash[match.re.pattern][0], token_hash[match.re.pattern][1],
                            match.group(1), line, lineNum, col)
                    col += match.end(1) + re.match("\s*", line[col + match.end(1):]).end(0)
                if not match:
                    raise LexerError("Bad token (line %d, column %d): %s" %(lineNum, col, line[col:]))

    yield Token("$", "$", "$", "$", -1, -1)


