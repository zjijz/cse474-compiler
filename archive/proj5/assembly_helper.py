# _______________________Assembly________________________


# Allocates space to the stack
def asm_allocate_stack_space(space = 4):
    return asm_add('$sp', '$sp', -space)


# Pass in type information to indicate which syscall to use:
# 5 - read int
# 6 - read float
# 7 - read double
# 8 - read string
def asm_read(var_type):
    ret_asm = ''
    if var_type == 'int':
        ret_asm += asm_reg_set('$v0', 5)
    elif var_type == 'float':
        ret_asm += asm_reg_set('$v0', 6)
    elif var_type == 'double':
        ret_asm += asm_reg_set('$v0', 7)
    else:
        ret_asm += asm_reg_set('$v0', 8)
    return ret_asm + 'syscall\n'


# Check current syscode if it's correct for the var_type passed
def asm_check_syscode_write(var_type, val):
    return (var_type == 'int' and val != 1) or (var_type == 'float' and val != 2) \
           or (var_type == 'double' and val != 3) or (var_type == 'string' and val != 4)


# Pass it a var_type
# Return the necessary syscode to print
def asm_get_syscode_write(var_type):
    if var_type == 'int':
        return 1
    elif var_type == 'float':
        return 2
    elif var_type == 'double':
        return 3
    else:
        return 4


# Broke this off from write to optimize writes a little faster
# var_type: The type of variable to write
# 1 - print int, arg in $a0
# 2 - print float, arg in $f12
# 3 - print double, arg in $f12
# 4 - print string, arg in $a0
def asm_set_syscode_write(var_type):
    return asm_reg_set('$v0', asm_get_syscode_write(var_type))


# var_type is the type of the variable to print
# reg is the register where the variable is stored
# 1 - print int, arg in $a0
# 2 - print float, arg in $f12
# 3 - print double, arg in $f12
# 4 - print string, arg in $a0
def asm_write(var_reg, var_type):
    ret_asm = ''
    if var_type == 'int':
        ret_asm += asm_reg_set('$a0', var_reg)
    elif var_type == 'float':
        ret_asm += asm_reg_set('$f12', var_reg)
    elif var_type == 'double':
        ret_asm += asm_reg_set('$f12', var_reg)
    else:
        ret_asm += asm_reg_set('$a0', var_reg)

    return ret_asm + 'syscall\n'


# Used to add two values
# Includes override for immediates
def asm_add(r_reg, f_reg, s_reg):
    if type(s_reg) is int:
        return 'addi {:s}, {:s}, {:d}\n'.format(r_reg, f_reg, s_reg)
    else:
        return 'add {:s}, {:s}, {:s}\n'.format(r_reg, f_reg, s_reg)


# Used to subtract two values
# Includes override for immediates
def asm_sub(r_reg, f_reg, s_reg):
    if type(s_reg) is int:
        return 'subi {:s}, {:s}, {:d}\n'.format(r_reg, f_reg, s_reg)
    else:
        return 'sub {:s}, {:s}, {:s}\n'.format(r_reg, f_reg, s_reg)


# Result stored in hi and lo
# First 32 bits in lo
# Second 32 bits (overflow) are in hi
def asm_multiply(f_reg, s_reg):
    if type(s_reg) is int:
        return 'multi {:s}, {:d}\n'.format(f_reg, s_reg)
    else:
        return 'mult {:s}, {:s}\n'.format(f_reg, s_reg)


# Stores result in lo register
def asm_multiply_int(r_reg, f_reg, s_reg):
    return 'mul {:s}, {:s}, {:s}'.format(r_reg, f_reg, s_reg)


# Load a value from one register to another
def asm_reg_set(f_reg, s_reg):
    # This branches if s_reg is a register (i.e. string) or an immediate (i.e. int)
    if type(s_reg) is int:
        return 'li {:s}, {:d}\n'.format(f_reg, s_reg)
    else:
        return 'move {:s}, {:s}\n'.format(f_reg, s_reg) # move is a pseudo-instruction


# Loads a variable's memory address into a register
def asm_load_mem_addr(mem_name, temp_reg):
    return 'la {:s}, {:s}\n'.format(temp_reg, mem_name)


# Assumes mem_name address isn't in memory already
def asm_load_mem_var(mem_name, addr_reg, dest_reg, offset = 0):
    return 'la {:s}, {:s}\nlw {:s}, {:d}({:s})\n'.format(addr_reg, mem_name, dest_reg, offset, addr_reg)


# Assumes mem_addr_reg holds RAM location of desired variable
def asm_load_mem_var_from_addr(mem_addr_reg, dest_reg, offset = 0):
    return 'lw {:s}, {:d}({:s})\n'.format(dest_reg, offset, mem_addr_reg)


# Assumes mem_name address isn't in memory already
def asm_save_mem_var(mem_name, addr_reg, var_reg, offset = 0):
    return 'la {:s}, {:s}\nsw {:s}, {:d}({:s})\n'.format(addr_reg, mem_name, var_reg, offset, addr_reg)


# Assumes mem_addr_reg holds RAM location of desired variable
def asm_save_mem_var_from_addr(mem_addr_reg, var_reg, offset = 0):
    return 'sw {:s}, {:d}({:s})\n'.format(var_reg, offset, mem_addr_reg)


# Load variable from stack
def asm_load_reg_from_stack(reg, offset = 0):
    return asm_read_mem_addr('$sp', reg, offset)


# Save variable to stack
def asm_save_reg_to_stack(reg, offset = 0):
    return asm_write_mem_addr('$sp', reg, offset)

# _______________________Helpers________________________


# Helper function to make swapping variables easier
# Writes the old variable from $var_reg to RAM, and then loads the new one to the same reg
# At the end: $addre_reg = address of s_mem_name and $var_reg = value of s_mem_name
def asm_swap_variables(f_mem_name, s_mem_name, addr_reg, var_reg, f_offset = 0, s_offset = 0):
    return 'la {:s}, {:s}\nsw {:s}, {:d}({:s})\nla {:s}, {:s}\nlw {:s}, {:d}({:s})\n'\
        .format(addr_reg, f_mem_name, var_reg, f_offset, addr_reg, addr_reg, s_mem_name, var_reg, s_offset, addr_reg)


# Helper to make repeated addition easier
def asm_add_rep(r_reg, *regs):
    ret_asm = ''
    ret_asm += asm_add(r_reg, regs[0], regs[1]) # initial add of two variables
    for i in [2..len(regs)]:
        ret_asm += asm_add(r_reg, r_reg, regs[i])
    return ret_asm


# Helper to make repeated subtraction easier
def asm_sub_rep(r_reg, *regs):
    ret_asm = ''
    ret_asm += asm_sub(r_reg, regs[0], regs[1]) # initial add of two variables
    for i in [2..len(regs)]:
        ret_asm += asm_sub(r_reg, r_reg, regs[i])
    return ret_asm

