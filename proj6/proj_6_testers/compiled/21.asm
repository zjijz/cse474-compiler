.data
a:	.asciiz	"True"	
b:	.asciiz	"False"	
.text
li $v0, 4
la $t2, a
move $a0, $t2
syscall
la $s3, b
move $a0, $s3
syscall
move $a0, $t2
syscall
move $a0, $s3
syscall
