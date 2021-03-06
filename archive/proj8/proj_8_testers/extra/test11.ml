# Pass-by-reference in a recursion call

begin
    fib(int x, int ref y) begin
        if x <= 1 then begin
            y := x;
        end else begin
            int a := 0, b := 0;
            fib(x - 1, a)
            fib(x - 2, b)
            y := a + b;
        end
    end

    int f := 8;
    int x := 0;
    fib(f, x)
    write(x, "\n");
end
