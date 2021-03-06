class LexerError(Exception):
    """
    Exception to be thrown when the lexer encounters a bad token.
    """
    def __init__(self, msg):
        self.msg = "Lexical error: " + msg

    def __str__(self):
        return str(self.msg)


class ParserError(Exception):
    """
    Exception to be thrown when MLparser encounters an incorrect string
    """

    @staticmethod
    def raise_redundant_tokens_error(curToken):
        raise ParserError('There are redundant tokens at the end of the program, '
                          'starting with: %s\nLine num: %d, column num: %d'
                          %(curToken.line, curToken.line_num, curToken.col))

    @staticmethod
    def raise_parse_error(symbolName, expectedTokenStr, actualToken):
        raise ParserError('Syntax error in <%s>, expected "%s", actually is "%s" \nLine num: %d, column num: %d'
                      %(symbolName, expectedTokenStr, actualToken.pattern, actualToken.line_num, actualToken.col))

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class SemanticError(Exception):
    """
    Exception to be raised for various semantic errors
    """

    # Used for when variables are used before initialization
    @staticmethod
    def raise_initialization_error(variable, line, col):
        raise SemanticError('Semantic error: Initiatilization Error: Line num: {:d}, column num: {:d}\n\t{:s} not '
                            'initialized before use.'.format(line, col, variable))

    # Raised when two variables of different types are equated and implicit type conversion
    @staticmethod
    def raise_type_mismatch_error(var_1, var_2, type_1, type_2, line, col):
        raise SemanticError('Semantic error: Type Mismatch Error: Line num {:d}, column num: {:d}\n\t{:s} is of '
                            'type {:s}, but {:s} is of type {:s}.').format(line, col, var_1, type_1, var_2, type_2)

    # Raised for incorrect variable type used in a function
    @staticmethod
    def raise_incompatible_type(var_name, type_name, line, col):
        raise SemanticError('Semantic error: Incopmatible type error: Line num {:d}, column num: {:d}\n\t{:s} is'
                            'of incompatible type {:s}.').format(line, col, var_name, type_name)

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg
