from tree import *
from MLparser import *
from assembly_helper import *
from errors import *
from copy import *

# Symbol Table (Keys are ID pattern, Values are Dicts themselves)
#  'type': Data type (functions have [(params), ret_type])
#  'mem_name": variable name for .data
#  'init_val': initial value ('DYNAMIC' if set with READ)('TEMP' if TEMP variable)
#  'curr_val': current value (None if used in an operation with a variable from READ)
#  'addr_reg': temporary register with memory address
#  'val_reg': temporary register with value
#  'used': True | False

# Array Sym Table
# Keeps track of arrays/strings
# - Keys are the array or string
# - 'mem_name': MIPs variable name
# - 'type': output type (.ascii, .asciiz, or array type (=.word))
# - 'addr_reg': register that holds address to oth index
# - 'used: True | False

# Register Table (Keys are register names, Values are Dicts themselves)
#  'id': ID pattern
#  'mem_type': Variable type (ADDRESS, VALUE, or TYPE[type of varible])

# Auxiliary Reg Table (Keeps track registers not used for variables)
# Keeps track of $v0, $v1, $a0, $a1, $s0
# Each value has:
# - 'id': ID pattern
# - 'val': current integer value in register or a Register
# - 'mem_type': Variable type

# Float Reg Table
# Keeps track of the float registers
#   'id': ID pattern
#   'mem_type': Variable type (ADDRESS, VALUE, or TYPE[type of variable])

# Var Queue
#  Holds a {'reg': "...", 'id': "...", 'mem_type': "VALUE"|"ADDRESS"|"ARRAY_ADDRESS"|"TYPE.type"} dict
#  Push to back, pop from front

# Float Var Queue:
#  Holds a {'reg': "...", 'id': "...", 'mem_type': "VALUE"|"ADDRESS"|"TYPE.float"} dict
#  Push to back, pop from front

# Block Variable Edits Hash Table
# This will keep track of when conditional blocks edit variables
#  Keys are 'mem_name' (unique variable identifiers)
#
#  Values are a list of properties from Symbol Table that have been edited

# Activation Record
# Old Frame Pointer (4 bytes)
# Return address (4 bytes)
# Parameters (variable length)
# Return value (variable space - to head of $sp)(always 4 bytes for this project)


# Courtesy of Dr. Karro
def next_variable_name(curr_name):
   curr_name_len = len(curr_name)
   for i in range(curr_name_len - 1, -1, -1):
       if curr_name[i] != 'z':
           return curr_name[:i] + chr(ord(curr_name[i]) + 1) + curr_name[i + 1:]
       else:
           curr_name = curr_name[:i] + 'a' + curr_name[i + 1:]
   return 'a' + curr_name


def variable_name_generator():
    s = ""
    while True:
        s = next_variable_name(s)
        yield s


def temp_var_id_generator():
    s = ""
    while True:
        s = next_variable_name(s)
        yield str('temp_' + s)


# A glorified string wrapper class
class Register:
    def __init__(self, name):
        self.name = name

    # Allows for use of :s in str.format(...)
    def __format__(self, format):
        if format == 's':
            return str(self)

    # Allows for Register objects to be used as dictionary keys
    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        if type(other) is Register:
            return self.name == other.name
        else:
            return False

    def __ne__(self, other):
        if type(other) is Register:
            return self.name != other.name
        else:
            return True


class SymbolTable:
    @staticmethod
    def _empty_sym_table_dict():
        return {'type': None, 'scope': None, 'mem_name': None, 'init_val': None,
                'curr_val': None, 'addr_reg': None, 'val_reg': None, 'used': False}

    @staticmethod
    def _empty_array_sym_table_dict():
        return {'type': None, 'mem_name': None, 'addr_reg': None, 'used': False}

    def _find_table(self, ident):
        curr_scope = self.scope
        while curr_scope >= 0:
            try:
                self.symbol_tables[curr_scope][ident]
                break
            except KeyError:
                pass

            curr_scope -= 1
        return curr_scope

    def _create_array_sym_table(self):
        array_sym_table = {}

        # 'True' for bool
        true_dict = self._empty_array_sym_table_dict()
        true_dict['type'] = '.asciiz'
        true_dict['mem_name'] = next(self.var_name_generator)
        array_sym_table['"True"'] = true_dict

        # 'False' for bool
        false_dict = self._empty_array_sym_table_dict()
        false_dict['type'] = '.asciiz'
        false_dict['mem_name'] = next(self.var_name_generator)
        array_sym_table['"False"'] = false_dict

        return array_sym_table

    def __init__(self):
        # Scope stuff
        self.scope = -1

        # Name generators
        self.var_name_generator = variable_name_generator()

        # Symbol tables
        self.symbol_tables = [{}]
        self.array_symbol_table = self._create_array_sym_table()
        self.closed_table_entries = []

    def create_entry(self, ident, token, mem_type, init_val, curr_val, addr_reg, val_reg, used):
        if self.check_entered(ident):
            SemanticError.raise_already_declared_error(ident, token.line_num, token.col)

        self.symbol_tables[self.scope][ident] = {'type': mem_type, 'mem_name': next(self.var_name_generator),
                                                 'init_val': init_val, 'curr_val': curr_val, 'addr_reg': addr_reg,
                                                 'val_reg': val_reg, 'used': used}

    def create_array_entry(self, string, mem_type, addr_reg, used):
        self.array_symbol_table[string] = {'type': mem_type, 'mem_name': next(self.var_name_generator),
                                           'addr_reg': addr_reg, 'used': used}

    def get_entry(self, ident, token):
        table_num = self._find_table(ident)

        if table_num == -1:
            SemanticError.raise_declaration_error(ident, token.line_num, token.col)

        ret_dict = self.symbol_tables[table_num][ident]
        return ret_dict['type'], ret_dict['mem_name'], ret_dict['init_val'], ret_dict['curr_val'], \
               ret_dict['addr_reg'], ret_dict['val_reg'], ret_dict['used']

    def get_array_entry(self, string, token):
        ret_dict = self.array_symbol_table[string]
        return ret_dict['type'], ret_dict['mem_name'], ret_dict['addr_reg'], ret_dict['used']

    def get_entry_suppress(self, ident):
        table_num = self._find_table(ident)

        if table_num == -1:
            return None, None, None, None, None, None, None

        ret_dict = self.symbol_tables[table_num][ident]
        return ret_dict['type'], ret_dict['mem_name'], ret_dict['init_val'], ret_dict['curr_val'], \
               ret_dict['addr_reg'], ret_dict['val_reg'], ret_dict['used']

    def get_array_entry_suppress(self, string):
        try:
            ret_dict = self.array_symbol_table[string]
            return ret_dict['type'], ret_dict['mem_name'], ret_dict['addr_reg'], ret_dict['used']
        except KeyError:
            return None, None, None, None

    def check_entered(self, ident):
        try:
            self.symbol_tables[self.scope][ident]
            return True
        except KeyError:
            return False

    def set_entry(self, ident, mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used):
        table_num = self._find_table(ident)
        # Might have an error here if ident isn't found
        self.symbol_tables[table_num][ident] = {'type': mem_type, 'mem_name': mem_name, 'init_val': init_val,
                                                'curr_val': curr_val, 'addr_reg': addr_reg,
                                                'val_reg': val_reg, 'used': used}

    def set_array_entry(self, string, mem_type, mem_name, addr_reg, used):
        self.array_symbol_table[string] = {'mem_name': mem_name, 'type': mem_type, 'addr_reg': addr_reg,
                                           'used': used}

    def open_scope(self):
        self.scope += 1
        self.symbol_tables.append({})

    def close_scope(self):
        # Save off all table entries to a list to then process for printing at the end
        for mem_id, dict in self.symbol_tables[self.scope].items():
            dict['mem_id'] = mem_id
            dict['scope'] = self.scope
            self.closed_table_entries.append(dict)

        self.symbol_tables = self.symbol_tables[:self.scope]
        self.scope -= 1

    def remove_all_reg(self):
        for table in self.symbol_tables:
            for k, v in table.items():
                v['addr_reg'] = None
                v['val_reg'] = None


class CodeGenerator:
    """
    Object that takes a parse tree, symbol table, and output file,
    and has methods to compile the parse tree to asm
    """

    @staticmethod
    def _empty_reg_dict():
        return {'id': None, 'mem_type': None}

    @staticmethod
    def _empty_aux_reg_dict():
        return {'id': None, 'val': None, 'mem_type': None}

    @staticmethod
    def _empty_tail_call(accum_id, val_reg, val_type, val_token, immediate_val):
        return val_reg, immediate_val, val_type

    def __init__(self, parse_tree, output_filename, is_debug, is_safe):
        # Name / ID generators
        self.temp_id_generator = temp_var_id_generator()
        self.conditional_name_generator = variable_name_generator()

        # Compiler Flags
        self.debug_mode = is_debug
        self.safe_mode = is_safe

        # Function dictionary
        self.func_factory = {"READ": self._read, "WRITE": self._write, "ID_STATEMENT": self._id_statement,
                             "DECLARATION": self._declare, "IF_STATEMENT": self._process_if,
                             "WHILE_STATEMENT": self._process_while, 'RETURN': self._process_return}

        # Stuff from Parser
        self.tree = parse_tree

        # Symbol Tables
        self.sym_table = SymbolTable()

        # Registers
        # self.reg_pool = all normal registers
        # self.aux_reg_pool = all auxiliary registers
        # self.float_reg_pool = all floating point registers
        self.reg_table = self._init_reg_table()
        self.aux_reg_table = self._init_reg_table('aux')
        self.float_reg_table = self._init_reg_table('float')
        # Also has these attributes set in _create_register_pool:
        #   self.val_0 - Read-in ints are stored here
        #   self.val_1 - We use it as a temp register for our psuedoinstructions (instead of $at) - DO NOT USE THIS
        #   self.arg_0 - Integer / String printing
        #   self.arg_1 -
        #   self.arg_2 -
        #   self.arg_3 -
        #   self.save_0 - Where addresses are temporarily loaded
        #   self.float_0 - Where read-in floats are stored
        #   self.float_12 - Used for printing floats
        #   float_13 ($f13) is reserved for float immediates in asm_helper and has no guaranteed value

        # Variable Queues
        self.var_queue = []
        self.float_var_queue = []

        # Used to keep track of things a block changes to reconcile them when it closes
        self.forced_dynamic = False

        # Output options
        self.output_name = output_filename
        self.output_string = ''
        self.func_string = ''

    def compile(self):
        self._start()
        self._process_block(self.tree)
        self._finish()

    def _create_register_pool(self, type_s = 'normal'):
        pool = []

        if type_s == 'aux':
            # v regs
            for i in range(2):
                reg = Register('$v' + str(i))
                pool.append(reg)
                setattr(self, 'val_' + str(i), reg)

            # a regs
            for i in range(2):
                reg = Register('$a' + str(i))
                pool.append(reg)
                setattr(self, 'arg_' + str(i), reg)

            # $s0 register (used for loading addresses in variable swaps)
            reg = Register('$s0')
            pool.append(reg)
            setattr(self, 'save_0', reg)

            # $f0
            reg = Register('$f0')
            pool.append(reg)
            setattr(self, 'float_0', reg)

            # $f12
            reg = Register('$f12')
            pool.append(reg)
            setattr(self, 'float_12', reg)

            setattr(self, 'aux_reg_pool', pool)

        elif type_s == 'float':
            # Generates first set of temporary float registers
            for i in range(4,11):
                pool.append(Register('$f' + str(i)))

            # Generates second set of temporary float registers
            for i in range(16,19):
                pool.append(Register('$f' + str(i)))

            # Generates 'preserved' float registers
            if not self.safe_mode:
                for i in range(20,32):
                    pool.append(Register('$f' + str(i)))

            setattr(self, 'float_reg_pool', pool)

        else:
            # Generate $t_ registers
            for i in range(10):
                pool.append(Register('$t' + str(i)))

            # Generate $s_ registers
            if not self.safe_mode:
                for i in range(1,7):
                    pool.append(Register('$s' + str(i)))

            setattr(self, 'reg_pool', pool)

        return pool

    def _init_reg_table(self, type_s = 'normal'):
        reg_pool = self._create_register_pool(type_s)
        empty_dict = self._empty_aux_reg_dict() if type_s == 'aux' else self._empty_reg_dict()

        ret_dict = {}
        for reg in reg_pool:
            ret_dict[reg] = deepcopy(empty_dict)

        return ret_dict

    def _find_free_register(self, var_type='normal'):
        ### Sub-function ###
        def save_using_s0(name, var_reg):
            # If we are in safe mode, we need to save off the old value
            if self.safe_mode:
                # Save $s0 value to stack
                # Allocate stack space
                self.output_string += asm_allocate_stack_space()

                # We don't have to increment stack_offset since it would just be decremented at the end of this block
                self.output_string += asm_save_reg_to_stack(self.save_0, 0)

            save_reg = '$s0'

            # Load address to $s0
            self.output_string += asm_load_mem_addr(name, save_reg)

            # Write value from val_reg to RAM
            self.output_string += asm_save_mem_var_from_addr(save_reg, var_reg)

            # If we are in safe_mode, we need to restore the old value
            if self.safe_mode:
                # Reset $s0 to what it was before
                self.output_string += asm_load_reg_from_stack(self.save_0, 0)
        #################

        # Get what registers/var_queue to look at (float or normal)
        reg_table = self.float_reg_table if var_type == 'float' else self.reg_table
        var_queue = self.float_var_queue if var_type == 'float' else self.var_queue

        # Look for open register
        for reg in reg_table:
            if not reg_table[reg]['id']:
                return reg

        # If none are open, free up a register
        reg_pop = var_queue.pop(0)

        mem_id = reg_pop['id']
        mem_type = reg_pop['mem_type']
        reg = reg_pop['reg']

        if mem_type == 'ARRAY_ADDRESS': # Update array_sym_table and return reg
            mem_type, mem_name, addr_reg, used = self.sym_table.get_array_entry(mem_id, None)
            self.sym_table.set_array_entry(mem_id, mem_type, mem_name, None, used)
        elif mem_type == 'ADDRESS': # If the register stores an address, just update tables
            mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used = self.sym_table.get_entry(mem_id, None)
            self.sym_table.set_entry(mem_id, mem_type, mem_name, init_val, curr_val, None, val_reg, used)
        elif mem_type == 'VALUE':
            mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used = self.sym_table.get_entry(mem_id, None)

            # Try to find addr_reg, else free up a register
            if not addr_reg:
                save_using_s0(mem_name, reg)
            else:
                # Write value from reg to RAM
                self.output_string += asm_save_mem_var_from_addr(addr_reg, reg)

            # Remove old references in symbol and register tables
            self.sym_table.set_entry(mem_id, mem_type, mem_name, init_val, curr_val, addr_reg, None, used)
        else: # mem_type = TYPE.*
            mem_type = mem_type[mem_type.find('.') + 1:]

            mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used = self.sym_table.get_entry_suppress(mem_id)
            if mem_name is None:
                # Create sym_table entry
                self.sym_table.create_entry(ident=mem_id, token=None, mem_type=mem_type, init_val='TEMP', curr_val=None,
                                            addr_reg=None, val_reg=None, used=True)
                _, mem_name, _, _, _, _, _ = self.sym_table.get_entry(mem_id, None)

            # Save variable to memory
            save_using_s0(mem_name, reg)

        # Clear register in reg_table
        reg_table[reg] = CodeGenerator._empty_reg_dict()
        return reg

    # Used mostly or expr to reserve registers for temporary variables
    def _update_reg_table(self, table_type, mem_id, reg, reg_type):
        reg_table = self.float_reg_table if table_type == 'float' else self.reg_table

        reg_dict = reg_table[reg]
        reg_dict['id'] = mem_id
        reg_dict['mem_type'] = reg_type

    # Will update tables to reflect the changes made to val_reg and addr_reg
    # Even though this may call more updates than necessary, just use it to ensure everything is updated
    # This WILL NOT update if passed registers are None. Instead, manually remove them yourself (might make a separate
    #  method for this later)
    # DOES NOT update var_queue, that is up to you
    def _update_tables(self, table_type, ident, new_addr_reg, new_val_reg, addr_reg_dict = None, val_reg_dict = None):
        val_reg_table = self.float_reg_table if table_type == 'float' else self.reg_table

        mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used = self.sym_table.get_entry(ident, None)

        if not addr_reg_dict and new_addr_reg:
            addr_reg_dict = self.reg_table[new_addr_reg]
        if not val_reg_dict and new_val_reg:
            val_reg_dict = val_reg_table[new_val_reg]

        # Edit addr_reg dict
        if new_addr_reg:
            addr_reg_dict['id'] = ident
            addr_reg_dict['mem_type'] = 'ADDRESS'
            addr_reg = new_addr_reg

        # Edit val_reg dict
        if new_val_reg:
            val_reg_dict['id'] = ident
            val_reg_dict['mem_type'] = 'VALUE'
            val_reg = new_val_reg

        self.sym_table.set_entry(ident, mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used)

    def _start(self):
        # Append .text' section
        self.output_string = '.text\n' + asm_init_frame_pointer()

    def _finish(self):
        data_section = ''

        for dict in self.sym_table.closed_table_entries:
            if dict['used'] and dict['type'] is not list:
                mem_id = dict['mem_id']
                val_type = dict['type']
                name = dict['mem_name']
                init_val = dict['init_val']
                scope = dict['scope']

                # Variables can be:
                # - ints, floats -> .word
                # - booleans -> .word (change to .word later)
                # - strings -> different sym table
                o_type = '.word'

                if val_type == 'float':
                    o_type = '.float'

                # If init_val is not a string (i.e. 'DYNAMIC' or 'TEMP'), change o_val to the value
                o_val = 0
                if init_val is not None and type(init_val) is bool:
                    o_val = 1 if init_val else 0
                elif init_val is not None and type(init_val) is not str:
                    o_val = init_val

                data_section += '{:s}:\t{:s}\t{:s}\t# {:s} [{:d}] in original\n'\
                                .format(name, o_type, str(o_val), mem_id, scope)

        for string, id_dict in self.sym_table.array_symbol_table.items():
            if id_dict['used']:
                name = id_dict['mem_name']
                o_type = id_dict['type']

                # string might have to be sanitized when using arrays
                data_section += '{:s}:\t{:s}\t{:s}\n'.format(name, o_type, string)

        # Prepend .data section instead of adding at beginning
        if data_section != '':
            data_section = '.data\n' + data_section

        self.output_string = data_section + self.output_string

        # Add exit on main function
        self.output_string += asm_call_exit()

        # Append other functions
        self.output_string += self.func_string

        # Write file
        fp = open(self.output_name, 'w')
        fp.write(self.output_string)
        fp.close()

        # Debug printing
        if self.debug_mode:
            print('\n',
                  'Symbol Table: ', self.sym_table.closed_table_entries, '\n\n',
                  'Array Symbol Table: ', self.sym_table.array_symbol_table, '\n\n',
                  'Register Table: ', self.reg_table, '\n\n',
                  'Float Register Table', self.float_reg_table, '\n\n',
                  'Auxiliary Register Table', self.aux_reg_table, '\n\n',
                  'Variable Queue: ', self.var_queue, '\n\n',
                  'Float Variable Queue: ', self.float_var_queue, '\n')

    def _save_off_registers(self):
        while len(self.var_queue) > 0:
            entry = self.var_queue.pop(0)
            reg = entry['reg']
            mem_id = entry['id']
            mem_type = entry['mem_type']
            if mem_type == 'VALUE':
                mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used = self.sym_table.get_entry(mem_id, None)
                if type(mem_type) is not list:
                    self.sym_table.set_entry(ident=mem_id, mem_type=mem_type, mem_name=mem_name, init_val=init_val,
                                             curr_val=curr_val, addr_reg=addr_reg, val_reg=None, used=True)
                    self.output_string += asm_save_mem_var_from_addr(mem_name, reg)
            elif mem_type == 'ADDRESS':
                mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used = self.sym_table.get_entry(mem_id, None)
                if val_reg != 'REF':
                    self.sym_table.set_entry(ident=mem_id, mem_type=mem_type, mem_name=mem_name, init_val=init_val,
                                             curr_val=curr_val, addr_reg=None, val_reg=val_reg, used=used)
                else:
                    self.sym_table.set_entry(ident=mem_id, mem_type=mem_type, mem_name=mem_name, init_val=init_val,
                                             curr_val=curr_val, addr_reg=reg, val_reg=val_reg, used=used)
            elif mem_type == 'ARRAY_ADDRESS':
                mem_type, mem_name, addr_reg, used = self.sym_table.get_array_entry(mem_id, None)
                self.sym_table.set_array_entry(mem_id, mem_type, mem_name, None, True)

        while len(self.float_var_queue) > 0:
            entry = self.float_var_queue.pop(0)
            reg = entry['reg']
            mem_id = entry['id']
            mem_type = entry['mem_type']
            if mem_type == 'VALUE':
                mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used = self.sym_table.get_entry(mem_id, None)
                if type(mem_type) is not list:
                    self.sym_table.set_entry(ident=mem_id, mem_type=mem_type, mem_name=mem_name, init_val=init_val,
                                             curr_val=curr_val, addr_reg=addr_reg, val_reg=None, used=True)
                    self.output_string += asm_save_mem_var_from_addr(mem_name, reg)
            elif mem_type == 'ADDRESS':
                mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used = self.sym_table.get_entry(mem_id, None)
                self.sym_table.set_entry(ident=mem_id, mem_type=mem_type, mem_name=mem_name, init_val=init_val,
                                         curr_val=curr_val, addr_reg=None, val_reg=val_reg, used=used)

        self.reg_table = self._init_reg_table('normal')
        self.float_reg_table = self._init_reg_table('float')
        self.aux_reg_table = self._init_reg_table('aux')
        self.sym_table.remove_all_reg()

    def _process_block(self, tree_nodes):
        self._save_off_registers()
        self.sym_table.open_scope()
        self._traverse(tree_nodes)
        self._save_off_registers()
        self.sym_table.close_scope()

    # Processing a block has ZERO side effects on the state of the compiler
    def _process_func_block(self, ident, func_name, parameters, tree_nodes):
        # Save off current state
        saved_output_string = self.output_string
        saved_forced_dynamic = self.forced_dynamic
        saved_reg_table = self.reg_table
        saved_float_reg_table = self.float_reg_table
        saved_aux_reg_table = self.aux_reg_table
        saved_var_queue = self.var_queue
        saved_float_var_queue = self.float_var_queue

        # Reset all tables
        self.reg_table = self._init_reg_table('normal')
        self.float_reg_table = self._init_reg_table('float')
        self.aux_reg_table = self._init_reg_table('aux')
        self.var_queue = []
        self.float_var_queue = []

        # Start function work
        self.output_string = ''
        self.forced_dynamic = True
        self.sym_table.open_scope()

        # Update sym_table for parameters
        mem_type, mem_name, _, _, _, _, _ = self.sym_table.get_entry(ident, None)
        param_types = mem_type[0]
        fp_offset = -8
        for i in range(0, len(parameters)):
            # Load parameters
            param = parameters[i]
            var_id = param[2] if len(param) > 2 else param[1]
            mem_type = param[0]
            cleaned_type = 'float' if mem_type == 'float' else 'normal'
            val_var_queue = self.float_var_queue if mem_type == 'float' else self.var_queue

            # Reserve a register
            if param[1] == 'ref':
                addr_reg = self._find_free_register()

                self.sym_table.create_entry(var_id, None, mem_type + ' ref', 'PARAM', None, None, addr_reg, False)
                _, var_mem_name, _, _, _, _, _ = self.sym_table.get_entry(var_id, None)
                self._update_tables(cleaned_type, var_id, None, addr_reg)
                #val_var_queue.append({'reg': addr_reg, 'id': var_id, 'mem_type': 'ADDRESS'})

                self.output_string += asm_load_mem_var_from_addr('$fp', addr_reg, fp_offset)
                self.output_string += asm_save_mem_var_from_addr(var_mem_name, addr_reg)
            else:
                val_reg = self._find_free_register()

                self.output_string += asm_load_mem_var_from_addr('$fp', val_reg, fp_offset)
                self.sym_table.create_entry(var_id, None, mem_type, 'PARAM', None, None, val_reg, False)
                self._update_tables(cleaned_type, var_id, None, val_reg)
                val_var_queue.append({'reg': val_reg, 'id': var_id, 'mem_type': 'VALUE'})

            fp_offset -= 4

        self._traverse(tree_nodes.children[1])

        # Remove old references (save anyhting changed)
        self._save_off_registers()

        saved_table = [v for k, v in self.sym_table.symbol_tables[self.sym_table.scope].items()]
        pre_string = asm_save_variables_to_stack(saved_table)
        post_string = asm_load_variables_from_stack(saved_table)

        # Hack to reoffset the return stack address (this is bad)
        split = self.output_string.split('\n')
        process_split = []
        found = False
        for i in range(0, len(split)):
            s = split[i]
            if 'return' in s:
                s = s.replace('0($sp)', str(4 * len(saved_table)) + '($sp)')
                split[i] = s
                process_split.append(s)
                process_split.append(post_string)
                found = True
            else:
                process_split.append(s)

        if found == True:
            self.output_string = pre_string + '\n'.join(process_split)
        else:
            self.output_string = pre_string + '\n'.join(process_split) + post_string

        # Remove loaded addresses and such
        for entry in self.var_queue + self.float_var_queue:
            if entry['mem_type'] == 'ARRAY_ADDRESS':
                mem_type, mem_name, addr_reg, used = self.sym_table.get_array_entry(entry['id'], None)
                self.sym_table.set_array_entry(entry['id'],  mem_type, mem_name, None, used)
            else:
                mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used \
                    = self.sym_table.get_entry_suppress(entry['id'])
                if mem_type is not None:
                    self.sym_table.set_entry(entry['id'], mem_type, mem_name, 'DYNAMIC', None, None, None, used)

        self.func_string += func_name + ':\n' + self.output_string + 'jr $ra\n'

        # Restore old stuff
        self.output_string = saved_output_string
        self.forced_dynamic = saved_forced_dynamic
        self.sym_table.close_scope()

        # Reset tables and var_queues
        self.reg_table = saved_reg_table
        self.float_reg_table = saved_float_reg_table
        self.aux_reg_table = saved_aux_reg_table
        self.var_queue = saved_var_queue
        self.float_var_queue = saved_float_var_queue

    def _id_statement(self, tree_nodes):
        self._process_id_state_body(tree_nodes[0].children[0], tree_nodes[0].children[1])

    def _process_id_state_body(self, ident_node, id_state_body_node):
        if id_state_body_node.children[0].label == "ASSIGN":
            self._assign(ident_node, id_state_body_node.children[0])
        else:
            self._process_func(ident_node, id_state_body_node.children[0])

    def _process_func(self, ident_node, tree_nodes):
        tail_nodes = None
        if len(tree_nodes.children) > 1:
            tail_nodes = tree_nodes.children[1].children
        self._process_func_gen(ident_node, tree_nodes.children[0], tail_nodes)

    def _process_func_gen(self, ident_node, tree_nodes, tail_nodes):
        if tree_nodes.label == "FUNC_DEC" or tail_nodes is not None:
            self._process_func_dec(ident_node, tree_nodes.children, tail_nodes)
        elif tree_nodes.label == "FUNC_CALL" or tail_nodes is None:
            self._process_func_call(ident_node, tree_nodes.children)

    def _process_func_dec_params(self, parameter_nodes):
        params = []
        i = 0
        while i < len(parameter_nodes):
            type = parameter_nodes[i].token.pattern
            if parameter_nodes[i+1].label == 'REF':
                ref = 'ref'
                ident = parameter_nodes[i+2].token.pattern
                params.append((type, ref, ident))
                i += 1
            else:
                ident = parameter_nodes[i+1].token.pattern
                params.append((type, ident))
            i += 2
        return tuple(params)

    def _process_func_dec(self, ident_node, parameter_nodes, tail_nodes):
        ret_value = None
        block_node = None
        if len(tail_nodes) > 1:
            ret_value = tail_nodes[0].token.pattern
            block_node = tail_nodes[1]
        else:
            block_node = tail_nodes[0]

        # Get parameters
        parameters = ()
        if len(parameter_nodes) > 0:
            parameters = self._process_func_dec_params(parameter_nodes[0].children)

        # Create function table entry for function
        token = ident_node.token
        ident = token.pattern
        self.sym_table.create_entry(ident, token, [parameters, ret_value], None, None, None, None, None)

        # Append function block to func_string
        _, mem_name, _, _, _, _, _ = self.sym_table.get_entry(ident, token)
        self._process_func_block(ident, mem_name, parameters, block_node)

    def _create_activation_record(self, parameters):
        # Old frame pointer
        self.output_string += asm_allocate_stack_space(4)
        self.output_string += asm_save_mem_var_from_addr('$sp', '$fp')

        # Set new frame pointer
        self.output_string += asm_reg_set('$fp', '$sp')

        # Store old Return address
        self.output_string += asm_allocate_stack_space(4)
        self.output_string += asm_save_mem_var_from_addr('$sp', '$ra')

        # Parameters
        for p in parameters:
            pass_type = p[2]

            self.output_string += asm_allocate_stack_space(4)

            val_reg, val_type, val_token = self._process_expr_bool(p[0].children)

            # Type check
            if val_type != p[1]:
                SemanticError.raise_parameter_type_mismatch("I'm too lazy to get the param name...", val_type,
                                                            "Also too lazy to get func name...", val_token.line_num,
                                                            val_token.col)

            if pass_type == 'ref':
                mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used \
                    = self.sym_table.get_entry(val_token.pattern, val_token)

                if curr_val is not None:
                    self.output_string += asm_save_mem_var_from_addr(mem_name, curr_val)
                    curr_val = None
                    used = True

                if addr_reg is None:
                    addr_reg = self._find_free_register()
                    self.output_string += asm_load_mem_addr(mem_name, addr_reg)

                # Assume function will edit this
                self.sym_table.set_entry(val_token.pattern, mem_type, mem_name, init_val, None, None, None, used)
                if 'ref' not in mem_type:
                    val_reg = addr_reg

            if type(val_reg) is str:
                string = val_reg
                _, mem_name, _, _ = self.sym_table.get_array_entry(string, None)
                val_reg = self._find_free_register()

                self._update_reg_table('normal', string, val_reg, 'ARRAY_ADDRESS')
                self.var_queue.append({'reg': val_reg, 'id': string, 'mem_type': 'ARRAY_ADDRESS'})
                self.output_string += asm_load_mem_addr(mem_name, val_reg)

            self.output_string += asm_save_mem_var_from_addr('$sp', val_reg)
            #if pass_type == 'ref':
            #    self.output_string +=  asm_save_mem_var_from_addr(mem_name, val_reg)

        # Return value
        self.output_string += asm_allocate_stack_space(4)

    def _destroy_activation_record(self):
        # Restore old return address
        self.output_string += asm_load_mem_var_from_addr('$fp', '$ra', -4)

        # Restore old stack pointer
        self.output_string += asm_reg_set('$sp', '$fp')
        #self.output_string += asm_sub('$sp', '$sp', -4)

        # Restore old frame pointer
        self.output_string += asm_load_mem_var_from_addr('$fp', '$v1')
        self.output_string += asm_reg_set('$fp', '$v1')

    def _process_func_call(self, ident_node, parameter_nodes):
        token = ident_node.token
        ident = token.pattern

        mem_type, mem_name, _, _, _, _, _ = self.sym_table.get_entry(ident, token)

        # Extract parameter_nodes
        func_params = mem_type[0]
        if len(parameter_nodes) > 0:
            parameter_nodes = parameter_nodes[0].children[0].children
        if len(parameter_nodes) != len(func_params):
            SemanticError.raise_parameter_number_mismatch(len(func_params), ident, token.line_num, token.col)
        parameters = []
        for i in range(0, len(func_params)):
            param = func_params[i]
            parameters.append((parameter_nodes[i], param[0], param[1]))

        return self._run_func(ident, mem_type, mem_name, parameters)

    def _run_func(self, ident, mem_type, mem_name, parameters):
        self._save_off_registers()

        #saved_reg_pool = self.reg_pool + self.float_reg_pool + self.aux_reg_pool
        self._create_activation_record(parameters)
        #self.output_string += asm_save_off_reg_pool(saved_reg_pool)
        self.output_string += 'jal ' + mem_name + '\n'

        #self.output_string += asm_load_reg_pool_from_stack(saved_reg_pool)
        # Get return value (if necessary)
        ret_reg = None
        ret_type = mem_type[1]
        if ret_type is not None:
            cleaned_type = 'float' if ret_type == 'float' else 'normal'
            val_var_queue = self.float_var_queue if mem_type == 'float' else self.var_queue

            ret_reg = self._find_free_register(cleaned_type)
            self._update_reg_table('normal', ident, ret_reg, 'FUNC')
            val_var_queue.append({'reg': ret_reg, 'id': ident, 'mem_type': 'FUNC'})
            self.output_string += asm_load_mem_var_from_addr('$sp', ret_reg)
        self._destroy_activation_record()

        return ret_reg, ret_type, None

    def _process_return(self, tree_nodes):
        val_reg, val_type, val_token = self._process_expr_bool(tree_nodes[0].children[0].children)
        self.output_string += asm_save_mem_var_from_addr('$sp', val_reg, ret_stat=True) + 'jr $ra\n'

    # Searches tree until it finds something to process
    def _traverse(self, tree):
        if self.tree.children:
            for child in tree.children:
                if child.label in self.func_factory:
                    self.func_factory[child.label](tree.children)
                    break
                else:
                    self._traverse(child)

    # Takes a list of id's and writes required code to read input into each
    def _read(self, tree_nodes):
        id_list = tree_nodes[1].children
        for ident in id_list:
            token = ident.token
            var_id = token.pattern
            mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used = self.sym_table.get_entry(var_id, token)

            if mem_type in {'string', 'bool'}:
                SemanticError.raise_incompatible_type(var_id, mem_type, 'Read Function', token.line_num, token.col)

            # Reset $v0
            self.aux_reg_table[self.val_0] = self._empty_aux_reg_dict()

            if init_val is None:
                init_val = 'DYNAMIC'

            # Used = True might be unneccasry (THIS MIGHT BE UNNECESSARY - TEST REMOVING IT)
            self.sym_table.set_entry(var_id, mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, True)

            input_reg = self.float_0 if mem_type == 'float' else self.val_0

            self.output_string += asm_read(mem_type) # places input into $v0
            self._assign_id(var_id, input_reg)

    # Takes a list of expressions and correctly prints them
    def _write(self, tree_nodes):
        expr_lst = tree_nodes[1].children
        for expr in expr_lst:
            var_reg, var_type, var_token = self._process_expr_bool(expr.children)

            # Construct expr_type, which will control what's written out
            expr_reg = var_reg
            expr_type = 'string' if var_type in {'bool', 'string'} else var_type

            curr_v0 = self.aux_reg_table[self.val_0]['val']
            # If check_syscode is true, then edits need to be made
            if asm_check_syscode_write(expr_type, curr_v0):
                self.output_string += asm_set_syscode_write(expr_type)
                self.aux_reg_table[self.val_0]['id'] = None
                self.aux_reg_table[self.val_0]['val'] = asm_get_syscode_write(expr_type)
                self.aux_reg_table[self.val_0]['mem_name'] = None
                self.aux_reg_table[self.val_0]['mem_type'] = None

            # Tracking $a0
            is_a0_set = False

            # Convert bool to string for printing
            if var_type == 'bool':
                if type(expr_reg) is bool: # literal
                    # set expr_reg to the string and let the string conditional print it
                    expr_reg = '"True"' if var_reg else '"False"'
                else: # dynamically set
                    true_mem_type, true_mem_name, true_addr_reg, true_used = self.sym_table.get_array_entry('"True"', None)
                    fal_mem_type, fal_mem_name, fal_addr_reg, fal_used = self.sym_table.get_array_entry('"False"', None)

                    true_used = True
                    fal_used = True

                    # Ensure addresses are loaded
                    if true_addr_reg is None:
                        true_addr_reg = self._find_free_register()
                        self._update_reg_table('normal', '"True"', true_addr_reg, 'ARRAY_ADDRESS')
                        self.var_queue.append({'reg': true_addr_reg, 'id': '"True"',
                                               'mem_type': 'ARRAY_ADDRESS'})
                        self.output_string += asm_load_mem_addr(true_mem_name, true_addr_reg)

                    if fal_addr_reg is None:
                        fal_addr_reg = self._find_free_register()
                        self._update_reg_table('normal', '"FALSE"', fal_addr_reg, 'ARRAY_ADDRESS')
                        self.var_queue.append({'reg': fal_addr_reg, 'id': '"False"',
                                               'mem_type': 'ARRAY_ADDRESS'})
                        self.output_string += asm_load_mem_addr(fal_mem_name, fal_addr_reg)

                    self.sym_table.set_array_entry('"True"', true_mem_type, true_mem_name, true_addr_reg, true_used)
                    self.sym_table.set_array_entry('"False"', fal_mem_type, fal_mem_name, fal_addr_reg, fal_used)

                    # Since this register will only be used in this function, with no other calls to _find_free_reg(),
                    # it does not have to be reserved, just cleared and made accessible
                    r_reg = self._find_free_register()
                    self.output_string += asm_dynamic_bool_print(r_reg, expr_reg, true_addr_reg, fal_addr_reg)
                    expr_reg = r_reg

                    # Reset $a0
                    self.aux_reg_table[self.arg_0] = self._empty_aux_reg_dict()

            # If expr_reg is a string, we look it up and print using it's address
            if type(expr_reg) is str:
                # Get string
                mem_type, mem_name, addr_reg, used = self.sym_table.get_array_entry(expr_reg, var_token)

                # Set string.'used' = True
                used = True

                # Ensure addr_reg is not None
                if addr_reg is None:
                    addr_reg = self._find_free_register()
                    self.var_queue.append({'reg': addr_reg, 'id': expr_reg, 'mem_type': 'ARRAY_ADDRESS'})
                    self._update_reg_table('normal', expr_reg, addr_reg, 'ADDRESS_ARRAY')
                    self.output_string += asm_load_mem_addr(mem_name, addr_reg)

                self.sym_table.set_array_entry(expr_reg, mem_type, mem_name, addr_reg, used)

                # Check if address is already in $a0
                a0_dict = self.aux_reg_table[self.arg_0]
                if a0_dict['val'] == expr_reg:
                    is_a0_set = True
                else:
                    a0_dict['val'] = expr_reg
                    a0_dict['mem_type'] = 'ADDRESS'
                    a0_dict['id'] = None
                    expr_reg = addr_reg
            elif var_type != 'string': # then expr_reg is int or float
                a0_dict = self.aux_reg_table[self.arg_0]
                f12_dict = self.aux_reg_table[self.float_12]
                if type(expr_reg) is int or expr_type == 'int':
                    #if a0_dict['val'] != expr_reg:
                    #    a0_dict['val'] = expr_reg
                    #    a0_dict['id'] = None
                    #    a0_dict['mem_type'] = 'int'
                    #else:
                    #    is_a0_set = True
                    a0_dict['val'] = expr_reg
                    a0_dict['id'] = None
                    a0_dict['mem_type'] = 'int'
                elif type(expr_reg) is float or expr_type == 'float':
                    #if f12_dict['val'] != expr_reg:
                    #    f12_dict['val'] = expr_reg
                    #    f12_dict['id'] = None
                    #    f12_dict['mem_type'] = 'float'
                    #else:
                    #    is_a0_set = True
                    f12_dict['val'] = expr_reg
                    f12_dict['id'] = None
                    f12_dict['mem_type'] = 'float'
            self.output_string += asm_write(expr_reg, expr_type, is_a0_set)

    # Takes assign tree_nodes: with an ID on the left and some expression on the right
    # Initializes variable on the left, and evalutes RHS using '_expr_funct'
    def _assign(self, ident_node, tree_nodes):
        # Get RHS result
        expr_id = None
        expr_reg, expr_type, expr_token = self._process_expr_bool(tree_nodes.children[0].children)

        # Get LHS variable
        token = ident_node.token
        ident = token.pattern
        mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used = self.sym_table.get_entry(ident, token)

        ref_type = mem_type.split(' ')[0]

        # Set init_val if first time calling
        if init_val is None:
            if type(expr_reg) is Register:
                init_val = 'DYNAMIC'
            else:
                init_val = expr_reg

        # Throw type error
        if ref_type != expr_type:
            # Coerce int into float (but not the other way around?)
            if ref_type == 'float' and expr_type == 'int':
                if type(expr_reg) is not int:
                    # Reserve this just in case _assign_id removes it
                    expr_float_reg = self._find_free_register('float')
                    expr_temp_id = next(self.temp_id_generator)
                    self.float_var_queue.append({'reg': expr_float_reg, 'id': expr_temp_id, 'mem_type': 'TYPE.float'})
                    # Coerce next_type up
                    self.output_string += asm_cast_int_to_float(expr_float_reg, expr_reg)
                    # set expr_reg to be the new float_reg
                    expr_reg = expr_float_reg
                else:
                    expr_reg = float(expr_reg)
            else:
                SemanticError.raise_type_mismatch_error(ident, expr_token.pattern, mem_type, expr_type,
                                                        expr_token.line_num, expr_token.col)
        # Save changes
        self.sym_table.set_entry(ident, mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used)

        #if 'ref' in mem_type:
        #    actual_val_reg = self._find_free_register()
        #    self.output_string += asm_load_mem_var_from_addr(val_reg, actual_val_reg)
        #    self._update_reg_table('normal', ident, actual_val_reg, 'VALUE')
        #    expr_reg = actual_val_reg

        # Run _assign_id
        self._assign_id(ident, expr_reg, expr_id)

    # Takes an id
    # Ensures that the id addr and val are initialized into registers
    # Returns nothing, since it should correctly equate values
    # (Either changing curr_val if RHS is an immediate, or
    def _assign_id(self, var_id, assn_reg, expr_id = None):
        mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used = self.sym_table.get_entry(var_id, None)
        ref_flag = True if 'ref' in mem_type else False

        python_assn_type = type(assn_reg)
        if not self.forced_dynamic:
            if python_assn_type is Register:
                curr_val = None
            elif python_assn_type is int and mem_type == 'int':
                curr_val = assn_reg
            elif python_assn_type is float and mem_type == 'float':
                curr_val = assn_reg
            elif python_assn_type is bool and mem_type == 'bool':
                curr_val = assn_reg
            elif python_assn_type is str and mem_type == 'string':
                curr_val = assn_reg

        # Only load variable into memory if there is no curr_val (i.e. the compiler can't do static analysis)
        if curr_val is None or self.forced_dynamic:
            # Set id to be printed out to MIPS
            used = True

            curr_val = None

            # Load variable addr and val into registers
            if not val_reg:
                type_str = 'float' if mem_type == 'float' else 'normal'
                val_var_queue = self.float_var_queue if mem_type == 'float' else self.var_queue

                val_reg = self._find_free_register(type_str)
                self._update_tables(type_str, var_id, addr_reg, val_reg)

                if not addr_reg:
                    addr_reg = self._find_free_register()
                    self._update_tables(type_str, var_id, addr_reg, val_reg)
                    self.var_queue.append({'reg': addr_reg, 'id': var_id, 'mem_type': 'ADDRESS'})
                    self.output_string += asm_load_mem_addr(mem_name, addr_reg)

                # Since it is less work to pop an addr register from the queue, I would rather push that first
                # (if necessary), and then push the value register
                if not ref_flag:
                    val_var_queue.append({'reg': val_reg, 'id': var_id, 'mem_type': 'VALUE'})

                self.output_string += asm_load_mem_var_from_addr(addr_reg, val_reg)

            # Ensure expr_id is loaded (if not None)
            if expr_id:
                assn_reg = self._ensure_id_loaded(expr_id, assn_reg)

            act_reg = val_reg
            if ref_flag:
                new_reg = self._find_free_register()
                self.output_string += asm_load_mem_var_from_addr(val_reg, new_reg)
                act_reg = new_reg

            # Equate registers (move assn_reg value into val_reg)
            self.output_string += asm_reg_set(act_reg, assn_reg)

            if ref_flag:
                # save to memory
                self.output_string += asm_save_mem_var_from_addr(val_reg, act_reg)

        self.sym_table.set_entry(var_id, mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used)

    # Needs to initialize an identifier's symbol table
    # Update: type, mem_name, init_val, curr_val, addr_reg, var_reg (unless value can be statically analyzed)
    # Returns nothing
    # Code for handling variable declarations
    # Needs to create the symbol table
    # All calls to the symbol table need to be in try/catch statements
    # if an error is thrown, redirect to throw semantic error?
    # Load into memory
    # Grab empty symbol table and edit types
    # sym_table[id] = empty table?
    def _declare(self, tree_nodes):
        # The type is the first child of declare and the
        # declaration list is the second
        var_type = tree_nodes[0].children[0].token.name.lower()
        decl_list = tree_nodes[0].children[1].children

        # Need to go through the list of ids being declared
        for term in decl_list:
            self._process_declare_term(term.children, var_type)

    # Used to run individual declare statements
    def _process_declare_term(self, children, mem_type):
        # Get var_id and reserve MIPS name
        token = children[0].token
        var_id = token.pattern

        # Clean up the type and get correct var_queue for variable type
        clean_type = 'float' if mem_type == 'float' else 'normal'
        var_queue = self.float_var_queue if clean_type == 'float' else self.var_queue

        # Default to None
        curr_val = None
        init_val = None
        val_reg = None
        addr_reg = None

        # If declaration includes an assignment (to expr_bool)
        if len(children) > 1:
            expr_reg, expr_type, expr_token = self._process_expr_bool(children[1].children)

            # Raise SemanticError on type mismatch
            if expr_type != mem_type:
                # Coerce int into float (but not the other way around?)
                if mem_type == 'float' and expr_type == 'int':
                    if type(expr_reg) is not int:
                        # Reserve this just in case _assign_id removes it
                        expr_float_reg = self._find_free_register('float')
                        expr_temp_id = next(self.temp_id_generator)
                        self.float_var_queue.append({'reg': expr_float_reg, 'id': expr_temp_id, 'mem_type': 'TYPE.float'})
                        # Coerce next_type up
                        self.output_string += asm_cast_int_to_float(expr_float_reg, expr_reg)
                        # set expr_reg to be the new float_reg
                        expr_reg = expr_float_reg
                    else:
                        expr_reg = float(expr_reg)
                else:
                    SemanticError.raise_type_mismatch_error(var_id, expr_token.pattern, mem_type, expr_type,
                                                            expr_token.line_num, expr_token.col)

            # Check for immediates
            if type(expr_reg) is not Register:
                curr_val = init_val = expr_reg
                val_reg = None
            elif expr_reg is not None: # If not, load address and variable registers and equate
                init_val = 'DYNAMIC'

                # Load addr_reg
                addr_reg = self._find_free_register(clean_type)
                var_queue.append({'reg': addr_reg, 'id': var_id, 'mem_type': 'ADDRESS'})
                self._update_reg_table(clean_type, var_id, addr_reg, 'ADDRESS')

                # Load var_reg
                val_reg = self._find_free_register(clean_type)
                var_queue.append({'reg': val_reg, 'id': var_id, 'mem_type': 'VALUE'})
                self._update_reg_table(clean_type, var_id, val_reg, 'VALUE')

                self.output_string += asm_reg_set(val_reg, expr_reg)

        # Throws error if already declared
        # Maybe move this up so it throws error earlier instead of running through all processes?
        self.sym_table.create_entry(var_id, token, mem_type, init_val, curr_val, addr_reg, val_reg, False)

    def _process_if(self, tree_nodes):
        saved_forced_dynamic = True if self.forced_dynamic else False

        if_children = tree_nodes[0]

        # Grab conditional, if block, and else block
        conditional_expr = if_children.children[1]
        if_block = if_children.children[3]
        else_block = if_children.children[5] if len(if_children.children) > 4 else None

        # Generate labels
        block_label = next(self.conditional_name_generator)
        if_label = block_label + '_if'
        else_label = block_label + '_else'
        end_label = block_label + '_end'

        # Process conditional and if block
        self._save_off_registers()
        cond_reg, cond_type, cond_token = self._process_expr_bool(conditional_expr.children)
        if cond_type != 'bool':
            SemanticError.raise_incompatible_type(cond_token.pattern, cond_type, 'conditional blocks',
                                                  cond_token.line_num, cond_token.col)

        self.output_string += asm_conditional_check(cond_reg, end_label if else_block is None else else_label)
        self.output_string += if_label + ':\n'
        self.forced_dynamic = True
        self._process_block(if_block)
        self.output_string += asm_branch_to_label(end_label)

        # Process else block
        if else_block:
            self.output_string += else_label + ':\n'
            self._process_block(else_block)

        self.output_string += end_label + ':\n'

        self.forced_dynamic = saved_forced_dynamic

    def _process_while(self, tree_nodes):
        saved_forced_dynamic = True if self.forced_dynamic else False

        while_children = tree_nodes[0]

        # Grab conditional, if block, and else block
        conditional_expr = while_children.children[1]
        while_block = while_children.children[2]

        # Generate labels
        block_label = next(self.conditional_name_generator)
        while_label = block_label + '_while'
        end_label = block_label + '_end'

        # Create while
        self._save_off_registers()
        self.forced_dynamic = True
        self.output_string += while_label + ':\n'
        cond_reg, cond_type, cond_token = self._process_expr_bool(conditional_expr.children)
        if cond_type != 'bool':
            SemanticError.raise_incompatible_type(cond_token.pattern, cond_type, 'conditional blocks',
                                                  cond_token.line_num, cond_token.col)

        self.output_string += asm_conditional_check(cond_reg, end_label)
        self._process_block(while_block)
        self.output_string += asm_branch_to_label(while_label)

        # Create end label
        self.output_string += end_label + ':\n'

        self.forced_dynamic = saved_forced_dynamic

    # Used for expressions
    # Returns the register that has the value of accum_id loaded
    def _ensure_id_loaded(self, curr_id, curr_reg):
        # Assume curr_reg is correct
        id_reg = curr_reg

        # Get register type
        clean_type = 'float' if 'f' in str(curr_reg) else 'normal'
        val_var_queue = self.float_var_queue if clean_type == 'float' else self.var_queue

        # Check if value in register
        mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used \
            = self.sym_table.get_entry_suppress(curr_id)

        # If id_dict is not found, then curr_reg is correct
        if mem_name and type(mem_type) is not list:
            # If id_reg is None, load it into memory
            if not val_reg:
                # Ensure 'used' is checked
                # If it was removed from a register, and we had to load it again, it means we need it written down
                used = True

                val_reg = self._find_free_register(clean_type)
                val_var_queue.append({'reg': val_reg, 'id': curr_id, 'mem_type': 'VALUE'})
                self._update_tables(clean_type, curr_id, None, val_reg)

                # If addr_reg is None
                if not addr_reg:
                    addr_reg = self._find_free_register()
                    self.var_queue.append({'reg': addr_reg, 'id': curr_id, 'mem_type': 'ADDRESS'})
                    self._update_tables(clean_type, curr_id, addr_reg, val_reg)

                    # Load address into addr_reg
                    self.output_string += asm_load_mem_addr(mem_name, addr_reg)

                # Load id_reg from addr_reg
                self.output_string += asm_load_mem_var_from_addr(addr_reg, val_reg)

            self.sym_table.set_entry(curr_id, mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used)

            id_reg = val_reg

        return id_reg

    # Used for expressions
    # Returns the newly reserved accum_register
    def _init_val_reg(self, mem_id, curr_reg, curr_type):
        cleaned_type = 'float' if curr_type == 'float' else 'normal'
        var_queue = self.float_var_queue if cleaned_type == 'float' else self.var_queue

        # Initialize val_reg
        accum_reg = self._find_free_register(cleaned_type)

        # Add to var_queue
        var_queue.append({'reg': accum_reg, 'id': mem_id, 'mem_type': 'TYPE.' + str(curr_type)})

        # Reserve accum_reg
        self._update_reg_table(cleaned_type, mem_id, accum_reg, 'VALUE')

        # Equate val_reg and curr_reg
        self.output_string += asm_reg_set(accum_reg, curr_reg)

        return accum_reg

    # Abstraction of <expr> functions
    # children = tree_nodes
    # children_function == function to process children
    # body_function == function that runs logic (must return val_reg, immediate_val)
    # - must ensure that both val_reg and next_reg are loaded at proper times
    # - must take (tree_nodes, accum_id, val_reg, val_type, val_token, immediate_val, next_reg, next_type, next_token)
    #   as parameters
    # tail function:
    # - accum_id, val_reg, val_type, val_token, immediate_val as children
    def _process_expr_skeleton(self, children, children_function, body_function, tail_function):
        # If len(children) == 1 on any expression function, it means the expression just drops through to a lower one
        # Thus, we can just return exactly whatever returned from the one below
        if len(children) == 1:
            return children_function(children[0].children)
        else:
            # Reserve accum_id
            accum_id = next(self.temp_id_generator)
            immediate_val = None
            val_reg = None

            temp_reg, val_type, val_token = children_function(children[0].children)
            if type(temp_reg) in {int, float, bool, str} and not self.forced_dynamic:
                immediate_val = temp_reg
            else: # Register
                val_reg = self._init_val_reg(accum_id, temp_reg, val_type)

            # Run the body function of the expression
            for i in range(1, len(children), 2):
                # Get RHS
                next_reg, next_type, next_token = children_function(children[i+1].children)

                # Save off next_id
                next_id = None
                if type(next_reg) is Register:
                    reg_table = self.float_reg_table if 'f' in str(next_reg) else self.reg_table
                    next_id = reg_table[next_reg]['id']

                # Ensure val_reg is loaded
                val_reg = self._ensure_id_loaded(accum_id, val_reg)

                # Ensure next_reg is loaded
                if next_id:
                    next_reg = self._ensure_id_loaded(next_id, next_reg)

                val_reg, immediate_val, val_type = \
                    body_function(accum_id, val_reg, val_type, val_token, immediate_val, children[i], next_reg,
                                  next_type, next_token)

            # Run a tail call if necessary
            val_reg, immediate_val, val_type = tail_function(accum_id, val_reg, val_type, val_token, immediate_val)

            if not val_reg:
                return immediate_val, val_type, val_token
            else:
                return val_reg, val_type, val_token

    # <expr_bool>     ->  <term_bool> { <log_or> <term_bool> }
    def _process_expr_bool(self, tree_nodes):
        def expr_bool_body(accum_id, val_reg, val_type, val_token, immediate_val,
                           oper, next_reg, next_type, next_token):
            # Check if val_reg is a bool
            if val_type != 'bool':
                SemanticError.raise_incompatible_type(val_token.pattern, val_type, 'Boolean OR',
                                                      val_token.line_num, val_token.col)

            # Check if next_reg is also a bool
            if next_type != 'bool':
                SemanticError.raise_type_mismatch_error(val_token.pattern, next_token.pattern, val_type, next_type,
                                                        val_token.line_num, val_token.col)

            # Add them up
            if type(next_reg) is bool: # static analysis
                if immediate_val is None:
                    immediate_val = next_reg
                else:
                    immediate_val = immediate_val or next_reg
            else: # MIPS
                self.output_string += asm_log_or(val_reg, val_reg, next_reg)

            return val_reg, immediate_val, val_type

        def expr_bool_tail(accum_id, val_reg, val_type, val_token, immediate_val):
             # OR immediates and non-immediates together
            if immediate_val is not None and val_reg is not None:
                self.output_string += asm_log_or(val_reg, val_reg, immediate_val)

            return val_reg, immediate_val, val_type

        return self._process_expr_skeleton(tree_nodes, getattr(self, '_process_term_bool'), expr_bool_body,
                                           expr_bool_tail)

    # <term_bool>     ->  <expr_eq> { <log_and> <expr_eq> }
    # Returns value register (or immediate), value type, and token
    def _process_term_bool(self, tree_nodes):
        def term_bool_body(accum_id, val_reg, val_type, val_token, immediate_val, oper, next_reg, next_type,
                           next_token):
            # Check if val_reg is a bool
            if val_type != 'bool':
                SemanticError.raise_incompatible_type(val_token.pattern, val_type, 'Boolean AND',
                                                      val_token.line_num, val_token.col)

            # Check if next_reg is also a bool
            if next_type != 'bool':
                SemanticError.raise_type_mismatch_error(val_token.pattern, next_token.pattern, val_type, next_type,
                                                        val_token.line_num, val_token.col)

            # Add them up
            if type(next_reg) is bool: # static analysis
                if immediate_val is None:
                    immediate_val = next_reg
                else:
                    immediate_val = immediate_val and next_reg
            else: # Code evaluation
                if val_reg is None:
                    val_reg = self._init_val_reg(accum_id, next_reg, val_type)
                else:
                    self.output_string += asm_log_and(val_reg, val_reg, next_reg)

            return val_reg, immediate_val, val_type

        def term_bool_tail(accum_id, val_reg, val_type, val_token, immediate_val):
            # AND immediates and non-immediates together
            if immediate_val is not None and val_reg is not None:
                self.output_string += asm_log_and(val_reg, val_reg, immediate_val)

            return val_reg, immediate_val, val_type

        return self._process_expr_skeleton(tree_nodes, getattr(self, '_process_expr_eq'), term_bool_body,
                                           term_bool_tail)

    # <expr_eq>       ->  <expr_relation> [ <equal_op> <expr_relation> ]
    # Returns value register (or immediate), value type, and token
    def _process_expr_eq(self, tree_nodes):
        def expr_eq_body(accum_id, val_reg, val_type, val_token, immediate_val, oper, next_reg, next_type, next_token):
            # Save off operator
            equal_op = oper.token.name

            # We set '==' and '!=' to be hard type checkers, so we don't need to worry about type coercion
            # I want to eventually add '=', and '!=' for soft equality checking and '==' and '!==' for hard checking
            if val_type != next_type:
                immediate_val = False if equal_op == 'EQUAL' else True
                val_reg = None
            else:
                # Check if val_reg or immediate_val has value
                # Run immediate comparison or MIPS if val_reg
                if val_reg is None:
                    if type(next_reg) in {str, bool, int, float}: # Both are immediates
                        immediate_val = immediate_val == next_reg \
                            if equal_op == 'EQUAL' else immediate_val != next_reg
                    else:
                        val_reg = self._init_val_reg(accum_id, immediate_val, val_type)
                        self.output_string += asm_rel_eq(val_reg, val_reg, next_reg) \
                            if equal_op == 'EQUAL' else asm_rel_neq(val_reg, val_reg, next_reg)
                else: # val_reg and a register or immediate (overloads in assembly_helper for this)
                    self.output_string += asm_rel_eq(val_reg, val_reg, next_reg) \
                        if equal_op == 'EQUAL' else asm_rel_neq(val_reg, val_reg, next_reg)

            # Ensure val_reg is a normal register
            if val_reg in self.float_reg_pool:
                new_val_reg = self._find_free_register('normal')
                self.output_string += asm_reg_set(new_val_reg, val_reg)

                mem_id = next(self.temp_id_generator)
                self.reg_table[new_val_reg]['id'] = mem_id
                self.reg_table[new_val_reg]['mem_type'] = 'VALUE'
                self.var_queue.append({'reg': new_val_reg, 'id': mem_id, 'mem_type': 'TYPE.bool'})

                self.float_var_queue = [x for x in self.float_var_queue if x['reg'] != val_reg]
                self.float_reg_table[val_reg] = self._empty_reg_dict()

                val_reg = new_val_reg

            return val_reg, immediate_val, 'bool'

        return self._process_expr_skeleton(tree_nodes, getattr(self, '_process_expr_rel'), expr_eq_body,
                                           self._empty_tail_call)

    # <expr_relation> ->  <expr_arith> [ <rel_op> <expr_arith> ]
    # Returns value register (or immediate), value type, and token
    def _process_expr_rel(self, tree_nodes):
        def expr_rel_body(accum_id, val_reg, val_type, val_token, immediate_val, oper, next_reg, next_type, next_token):
            # Save off op
            rel_op = oper.label

            # If type is string or bool, throw incompatible type error
            if val_type not in {'int', 'float'}:
                SemanticError.raise_incompatible_type(val_token.pattern, val_type, 'Number Relationships',
                                                      val_token.line_num, val_token.col)

            if next_type not in {'int', 'float'}:
                SemanticError.raise_incompatible_type(next_token.pattern, next_type, 'Number Relationships',
                                                      next_token.line_num, next_token.col)

            # Check for static analysis
            if immediate_val is not None and type(next_reg) in {int, float}:
                if rel_op == 'GREATER':
                    return None, immediate_val > next_reg, 'bool'
                elif rel_op == 'LESS':
                    return None, immediate_val < next_reg, 'bool'
                elif rel_op == 'GREATER_EQUAL':
                    return None, immediate_val >= next_reg, 'bool'
                elif rel_op == 'LESS_EQUAL':
                    return None, immediate_val <= next_reg, 'bool'

            # first_reg defaults to val_reg or immediate_val depending on which one was set
            first_reg = immediate_val if not val_reg else val_reg

            # second_reg defaults to next_reg
            second_reg = next_reg

            # Ensure val_reg is loaded for return
            if not val_reg:
                cleaned_type = 'float' if val_type == 'float' else 'normal'
                var_queue = self.float_var_queue if cleaned_type == 'float' else self.var_queue

                val_reg = self._find_free_register(cleaned_type)
                var_queue.append({'reg': val_reg, 'id': accum_id, 'mem_type': 'TYPE.' + str(val_type)})
                self._update_reg_table(cleaned_type, accum_id, val_reg, 'VALUE')

            if val_type == 'int' and next_type == 'float':
                # We don't have to worry about reserving this register since normal val_reg will still hold the
                # return bool
                val_float_reg = self._find_free_register('float')

                # Coerce val_type up
                self.output_string += asm_cast_int_to_float(val_float_reg, val_reg)

                # set first_reg to be val_float_reg
                first_reg = val_float_reg
            elif val_type == 'float' and next_type == 'int':
                next_float_reg = self._find_free_register('float')

                # Coerce next_type up
                self.output_string += asm_cast_int_to_float(next_float_reg, next_reg)

                # set second_reg to be next_float_reg
                second_reg = next_float_reg

            if rel_op == 'GREATER':
                self.output_string += asm_rel_gt(val_reg, first_reg, second_reg)
            elif rel_op == 'LESS':
                self.output_string += asm_rel_lt(val_reg, first_reg, second_reg)
            elif rel_op == 'GREATER_EQUAL':
                self.output_string += asm_rel_ge(val_reg, first_reg, second_reg)
            elif rel_op == 'LESS_EQUAL':
                self.output_string += asm_rel_le(val_reg, first_reg, second_reg)

            # Ensure val_reg is a normal register
            if val_reg in self.float_reg_pool:
                new_val_reg = self._find_free_register('normal')
                self.output_string += asm_reg_set(new_val_reg, val_reg)

                mem_id = next(self.temp_id_generator)
                self.reg_table[new_val_reg]['id'] = mem_id
                self.reg_table[new_val_reg]['mem_type'] = 'VALUE'
                self.var_queue.append({'reg': new_val_reg, 'id': mem_id, 'mem_type': 'TYPE.bool'})

                self.float_var_queue = [x for x in self.float_var_queue if x['reg'] != val_reg]
                self.float_reg_table[val_reg] = self._empty_reg_dict()

                val_reg = new_val_reg

            return val_reg, immediate_val, 'bool'

        return self._process_expr_skeleton(tree_nodes, getattr(self, '_process_expr_arith'), expr_rel_body,
                                           self._empty_tail_call)

    # <expr_arith>    ->  <term_arith> { <unary_add_op> <term_arith> }
    # Returns value register (or immediate), value type, and token
    def _process_expr_arith(self, tree_nodes):
        def expr_arith_body(accum_id, val_reg, val_type, val_token, immediate_val, oper, next_reg, next_type,
                            next_token):
            # Load the operation
            oper = oper.label

            # Type check
            if val_type not in {'int', 'float'}:
                SemanticError.raise_incompatible_type(val_token.pattern, val_type, 'Arithmetic',
                                                      val_token.line_num, val_token.col)

            if next_type not in {'int', 'float'}:
                SemanticError.raise_incompatible_type(next_token.pattern, next_type, 'Arithmetic',
                                                      next_token.line_num, next_token.col)

            if type(next_reg) in {int, float}: # next_reg is an immediate
                # initialize immediate
                immediate_val = 0 if immediate_val is None else immediate_val

                if oper == 'PLUS':
                    immediate_val += next_reg
                elif oper == 'MINUS':
                    immediate_val -= next_reg
            elif not val_reg: # Initialize val_reg since not immediate
                # If next is a 'float', ensure we will initialize val_reg as one too
                if next_type == 'float':
                    val_type = 'float'

                if oper == 'PLUS':
                    val_reg = self._init_val_reg(accum_id, next_reg, val_type)
                elif oper == 'MINUS':
                    val_reg = self._init_val_reg(accum_id, next_reg, val_type)
                    # Multiply val_reg by -1
                    self.output_string += asm_multiply(val_reg, val_reg, -1)
            else: # add/sub (coerce types if necessary)
                # Coerce int to float
                if val_type == 'int' and next_type == 'float':
                    # We care if val_reg is changed to a float, since we're going to keep track of it
                    val_float_reg = self._find_free_register('float')

                    # Update sym_table (if available)
                    try:
                        mem_type, mem_name, init_val, curr_val, addr_reg, next_val_reg, used \
                            = self.sym_table.get_entry_suppress(accum_id)
                        mem_type = 'float'
                        next_val_reg = val_float_reg
                        self.sym_table.set_entry(accum_id, mem_type, mem_name, init_val, curr_val, addr_reg,
                                                 next_val_reg, used)
                    except KeyError:
                        pass

                    # Remove from normal var_queue
                    self.var_queue = [i for i in self.var_queue if i['id'] != accum_id]

                    # Add to float var_queue
                    self.float_var_queue.append({'reg': val_float_reg, 'id': accum_id, 'mem_type': 'TYPE.float'})

                    # Coerce val_type up
                    self.output_string += asm_cast_int_to_float(val_float_reg, val_reg)

                    # set first_reg to be val_float_reg
                    val_reg = val_float_reg
                    val_type = 'float'
                elif val_type == 'float' and next_type == 'int':
                    # We don't care to save this, so we'll just let it die once we're done with it
                    next_float_reg = self._find_free_register('float')
                    # Coerce next_type up
                    self.output_string += asm_cast_int_to_float(next_float_reg, next_reg)
                    # set second_reg to be next_float_reg
                    next_reg = next_float_reg

                if oper == 'PLUS':
                    self.output_string += asm_add(val_reg, val_reg, next_reg)
                elif oper == 'MINUS':
                    self.output_string += asm_sub(val_reg, val_reg, next_reg)

            return val_reg, immediate_val, val_type

        def expr_arith_tail(accum_id, val_reg, val_type, val_token, immediate_val):
            # Add up the immediate and val_reg if necessary
            if immediate_val is not None and immediate_val != 0 and val_reg is not None:
                self.output_string += asm_add(val_reg, val_reg, immediate_val)

            return val_reg, immediate_val, val_type

        return self._process_expr_skeleton(tree_nodes, getattr(self, '_process_term_arith'), expr_arith_body,
                                           expr_arith_tail)

    # <term_arith>    ->  <fact_arith> { <mul_op> <fact_arith> }
    # Returns value register (or immediate), value type, and token
    def _process_term_arith(self, tree_nodes):
        def term_arith_body(accum_id, val_reg, val_type, val_token, immediate_val, oper, next_reg, next_type,
                            next_token):
            # Initialize val_reg to immediate_val if necessary
            if val_reg is None: # else, val_reg is already good to go
                val_reg = self._init_val_reg(accum_id, immediate_val, val_type)

            # Load the operation
            oper = oper.label

            # Type checks
            if (val_type not in {'int', 'float'}) or (oper == 'MODULO' and val_type != 'int'):
                SemanticError.raise_incompatible_type(val_token.pattern, val_type, 'Arithmetic',
                                                      val_token.line_num, val_token.col)

            if (next_type not in {'int', 'float'}) or (oper == 'MODULO' and next_type != 'int'):
                SemanticError.raise_incompatible_type(next_token.pattern, next_type, 'Arithmetic',
                                                      next_token.line_num, next_token.col)

            # Coerce int to float
            if val_type == 'int' and next_type == 'float':
                # We care if val_reg is changed to a float, since we're going to keep track of it
                val_float_reg = self._find_free_register('float')

                # Update sym_table (if available)
                try:
                    mem_type, mem_name, init_val, curr_val, addr_reg, next_val_reg, used \
                        = self.sym_table.get_entry_suppress(accum_id)
                    mem_type = 'float'
                    next_val_reg = val_float_reg
                    self.sym_table.set_entry(accum_id, mem_type, mem_name, init_val, curr_val, addr_reg,
                                             next_val_reg, used)
                except KeyError:
                    pass

                # Remove from normal var_queue
                self.var_queue = [i for i in self.var_queue if i['id'] != accum_id]

                # Add to float var_queue
                self.float_var_queue.append({'reg': val_float_reg, 'id': accum_id, 'mem_type': 'TYPE.float'})

                # Coerce val_type up
                self.output_string += asm_cast_int_to_float(val_float_reg, val_reg)

                # set first_reg to be val_float_reg
                val_reg = val_float_reg
                val_type = 'float'
            elif val_type == 'float' and next_type == 'int':
                # We don't care to save this, so we'll just let it die once we're done with it
                next_float_reg = self._find_free_register('float')
                # Coerce next_type up
                self.output_string += asm_cast_int_to_float(next_float_reg, next_reg)
                # set second_reg to be next_float_reg
                next_reg = next_float_reg

            # Just move all operations into accumulator (optimize later)
            # Immediates and register values are handled in asm methods
            if oper == 'MULTIPLY':
                self.output_string += asm_multiply(val_reg, val_reg, next_reg)
            elif oper == 'DIVIDE':
                self.output_string += asm_divide(val_reg, val_reg, next_reg)
            elif oper == 'MODULO':
                self.output_string += asm_modulo(val_reg, val_reg, next_reg)

            return val_reg, immediate_val, val_type

        return self._process_expr_skeleton(tree_nodes, getattr(self, '_process_fact_arith'), term_arith_body,
                                           self._empty_tail_call)

    # <fact_arith>    ->  <unary_op> <term_unary> | <unary_add_op> <term_unary> | <term_unary>
    # Returns value register (or immediate), value type, and token
    def _process_fact_arith(self, fact_children):
        # len(fact_node.children) = 1 or 2
        if len(fact_children) == 2:
            unary_op = fact_children[0].label

            accum_id = next(self.temp_id_generator)
            immediate_val = None
            val_reg = None

            temp_reg, val_type, val_token = self._process_term_unary(fact_children[1])
            if type(temp_reg) in {int, float, bool, str} and not self.forced_dynamic:
                immediate_val = temp_reg
            else: # Register
                val_reg = self._init_val_reg(accum_id, temp_reg, val_type)

            if unary_op == 'PLUS':
                # Throw error if not numeric type; do nothing otherwise
                if val_type not in {'int', 'float'}:
                    SemanticError.raise_incompatible_type(val_token.pattern, val_type, 'Unary Numberical Operations',
                                                          val_token.line_num, val_token.col)
            elif unary_op == 'MINUS':
                # Throw type error
                if val_type not in {'int', 'float'}:
                    SemanticError.raise_incompatible_type(val_token.pattern, val_type, 'Unary Numerical Operations',
                                                          val_token.line_num, val_token.col)

                if not val_reg: # immediate_val holds value
                    immediate_val *= -1
                else: # could not be statically analyzed
                    self.output_string += asm_multiply(val_reg, val_reg, -1)
            elif unary_op == 'LOG_NEGATION':
                # Throw type error
                if val_type != 'bool':
                    SemanticError.raise_incompatible_type(val_token.pattern, val_type, 'Unary Boolean Opertions',
                                                          val_token.line_num, val_token.col)

                if not val_reg:
                    immediate_val = not immediate_val
                else:
                    self.output_string += asm_log_negate(val_reg, val_reg)

            if not val_reg:
                return immediate_val, val_type, val_token
            else:
                return val_reg, val_type, val_token
        else: # len(cildren) = 1
            return self._process_term_unary(fact_children[0])

    # <term_unary>    ->  <literals> | <ident> | (expr_bool)
    # Returns value register (or immediate), value type, and token
    def _process_term_unary(self, term_unary):
        child = term_unary.children[0]
        token = child.token
        if token:
            if token.t_class == 'LITERAL': # If token is a literal
                literal = token.pattern
                # Check int, float, bool, string literals
                if token.name == 'STRINGLIT':
                    # See if literal already in array_sym_table
                    str_mem_type, str_mem_name, str_addr_reg, str_used = self.sym_table.get_array_entry_suppress(literal)
                    if str_mem_name is None:
                        # Create new global entry for string
                        str_mem_type = '.asciiz'
                        self.sym_table.create_array_entry(literal, str_mem_type, None, False)

                    # Create a temp pointer to the string
                    if self.forced_dynamic:
                        str_mem_type, str_mem_name, str_addr_reg, str_used \
                            = self.sym_table.get_array_entry(literal, token)
                        str_used = True

                        var_id = next(self.temp_id_generator)
                        self.sym_table.create_entry(var_id, token, 'string', 'DYNAMIC', None, None,
                                                    None, True)

                        mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used \
                            = self.sym_table.get_entry(var_id, token)

                        # Load address
                        addr_reg = self._find_free_register()
                        self._update_tables('normal', var_id, addr_reg, None)
                        self.var_queue.append({'reg': addr_reg, 'id': var_id, 'mem_type': 'ADDRESS'})
                        self.output_string += asm_load_mem_addr(mem_name, addr_reg)

                        # Load Value
                        val_reg = self._find_free_register()
                        self._update_tables('normal', var_id, addr_reg, val_reg, None)
                        self.var_queue.append({'reg': val_reg, 'id': var_id, 'mem_type': 'VALUE'})
                        self.output_string += asm_load_mem_addr(str_mem_name, val_reg)

                        self.sym_table.set_entry(var_id, mem_type, mem_name, init_val, curr_val, addr_reg, val_reg,
                                                 used)
                        self.sym_table.set_array_entry(literal, str_mem_type, str_mem_name, str_addr_reg, str_used)

                        return val_reg, 'string', token

                    return literal, 'string', token
                elif token.name == 'BOOLLIT':
                    return literal == 'True', 'bool', token
                elif token.name == 'INTLIT':
                    return int(literal), 'int', token
                elif token.name == 'FLOATLIT':
                    return float(literal), 'float', token
        elif child.label == 'VAR_IDENT': # If child is <ident><var_or_func>
            children = child.children
            if len(children[1].children) == 0:
                return self._process_id(children[0].token)
            else:
                ident_node = children[0]
                parameter_nodes = children[1].children[0].children[0].children
                return self._process_func_call(ident_node, parameter_nodes)
        else: # if token is <expr_bool>
            return self._process_expr_bool(child.children)

    # Takes a full ID token
    # Handles loading a variable's address and value into registers
    # Returns value register (or immediate), value type, and token
    # (This is mainly for expressions)
    # (Note: This will NOT force a variable to loaded into memory if the compiler can statically evaluate the value)
    def _process_id(self, token):
        ident = token.pattern

        mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used = self.sym_table.get_entry(ident, token)

        cleaned_type = 'float' if mem_type == 'float' else 'normal'
        val_var_queue = self.float_var_queue if cleaned_type == 'float' else self.var_queue
        ref_flag = True if 'ref' in mem_type else False
        real_type = mem_type
        if ref_flag:
            real_type = mem_type.split(' ')[0]

        # If not initialized, throw an error
        if init_val is None:
            SemanticError.raise_initialization_error(ident, token.line_num, token.col)

        # Check if curr_val is not None (thus, if we can just return it)
        if curr_val is not None and not self.forced_dynamic:
            return curr_val, mem_type, token
        # If the value of the variable is not in register, load it
        elif not val_reg:
            # If not, load the value into a register if the addr is already loaded
            if addr_reg:
                val_reg = self._find_free_register(cleaned_type)

                self._update_tables(cleaned_type, ident, addr_reg, val_reg)
                val_var_queue.append({'reg': val_reg, 'id': ident, 'mem_type': 'VALUE'})

                self.output_string += asm_load_mem_var_from_addr(addr_reg, val_reg)
            # Worst case, you have to load both the addr and the value into registers
            else:
                addr_reg = self._find_free_register()
                self._update_tables(cleaned_type, ident, addr_reg, val_reg)
                self.var_queue.append({'reg': addr_reg, 'id': ident, 'mem_type': 'ADDRESS'})

                val_reg = self._find_free_register(cleaned_type)
                self._update_tables(cleaned_type, ident, addr_reg, val_reg)
                val_var_queue.append({'reg': val_reg, 'id': ident, 'mem_type': 'VALUE'})

                self.output_string += asm_load_mem_var(mem_name, addr_reg, val_reg)
        # else: If val_reg was good to go, just return it

        # Set id to be printed out in MIPS if it couldn't be statically analyzed
        used = True

        self.sym_table.set_entry(ident, mem_type, mem_name, init_val, curr_val, addr_reg, val_reg, used)

        if ref_flag:
            actual_val_reg = self._find_free_register()

            while actual_val_reg == val_reg:
                actual_val_reg = self._find_free_register()
                self._update_reg_table('normal', ident, actual_val_reg, 'FUNC')

            self.output_string += asm_load_mem_var_from_addr(val_reg, actual_val_reg)
            val_reg = actual_val_reg

        return val_reg, real_type, token
