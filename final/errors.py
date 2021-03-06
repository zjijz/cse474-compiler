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

    @staticmethod
    def raise_declaration_error(variable, line, col):
        raise SemanticError('Semantic error: Declaration Error: Line num: {:d}, column num: {:d}\n\t{:s} not '
                            'declared before use.'.format(line, col, variable))

    @staticmethod
    def raise_already_declared_error(variable, line, col):
        raise SemanticError('Semantic error: Declaration Error: Line num: {:d}, column num: {:d}\n\t'
                            '{:s} is already declared.'.format(line, col, variable))

    @staticmethod
    def raise_initialization_error(variable, line, col):
        raise SemanticError('Semantic error: Initiatilization Error: Line num: {:d}, column num: {:d}\n\t{:s} not '
                            'initialized before use.'.format(line, col, variable))

    @staticmethod
    def raise_type_mismatch_error(var_1, var_2, type_1, type_2, line, col):
        raise SemanticError('Semantic error: Type Mismatch Error: Line num {:d}, column num: {:d}\n\t{:s} is of '
                            'type {:s}, but {:s} is of type {:s}.'.format(line, col, var_1, type_1, var_2, type_2))

    @staticmethod
    def raise_incompatible_type(var_name, type_name, func_name, line, col):
        raise SemanticError('Semantic error: Incompatible Type for Function: Line num {:d}, column num: {:d}\n\t{:s} is'
                            ' of incompatible type {:s} for {:s}.'.format(line, col, var_name, type_name, func_name))

    @staticmethod
    def raise_parameter_type_mismatch(param_name, type_name, func_name, line, col):
        raise SemanticError('Semantic error: Parameter Type Mismatch: Line num {:d}, column num: {:d}\n\t{:s} is'
                            ' of incompatible type {:s} in function {:s}.'.format(line, col, param_name, type_name, func_name))

    @staticmethod
    def raise_parameter_number_mismatch(num_params_expected, func_name, line, col):
        raise SemanticError('Semantic error: Parameter Number Mismatch: Line num {:d}, column num: {:d}\n\t{:s} should have'
                            ' {:d} parameters.'.format(line, col, func_name, num_params_expected))

    @staticmethod
    def raise_expression_pass_by_ref(expression, func_name, line, col):
        raise SemanticError('Semantic error: Illegal Pass By Reference: Line num {:d}, column num: {:d}\n\tIn {:s},'
                            ' {:s} cannot be passed by reference.'.format(line, col, func_name, expression))

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg
