// ============================================================
// ArcLoom MathLoom ALU — Add, Multiply, Compare
// ============================================================
//
// Standalone combinational module wrapping all three
// MathLoom operations. No generate blocks in the wrapper.
//
// Inputs: two 4-digit balanced ternary operands (8 bits each)
// Outputs: sum, product, comparison flags
// All combinational. No clock.
// ============================================================

module arcloom_mathloom_alu (
    input  wire [7:0]  a,          // operand A: 4-digit BT
    input  wire [7:0]  b,          // operand B: 4-digit BT

    // Addition result
    output wire [7:0]  sum_out,    // 4-digit sum
    output wire [1:0]  carry_out,  // carry trit

    // Multiplication result
    output wire [15:0] product_out, // 8-digit product

    // Comparison result
    output wire        cmp_eq,
    output wire        cmp_gt,
    output wire        cmp_lt
);

    // ---- Addition ----
    arcloom_bt_adder #(.N(4)) adder (
        .a(a), .b(b), .sum_out(sum_out), .c_final(carry_out)
    );

    // ---- Comparison ----
    arcloom_bt_compare #(.N(4)) comparator (
        .a(a), .b(b), .eq(cmp_eq), .gt(cmp_gt), .lt(cmp_lt)
    );

    // ---- Multiplication: shift-and-add ----
    // For each digit of B: if +1, add A<<i; if -1, subtract A<<i

    // Negate A (for -1 digits)
    wire [7:0] neg_a;
    arcloom_trit_neg n0 (.trit_in(a[1:0]), .trit_out(neg_a[1:0]));
    arcloom_trit_neg n1 (.trit_in(a[3:2]), .trit_out(neg_a[3:2]));
    arcloom_trit_neg n2 (.trit_in(a[5:4]), .trit_out(neg_a[5:4]));
    arcloom_trit_neg n3 (.trit_in(a[7:6]), .trit_out(neg_a[7:6]));

    // Partial products: select A, -A, or 0 based on B digit, then shift
    wire [15:0] sel0 = (b[1:0] == 2'b01) ? {8'b0, a} :
                       (b[1:0] == 2'b10) ? {8'b0, neg_a} : 16'b0;

    wire [15:0] sel1 = (b[3:2] == 2'b01) ? {6'b0, a, 2'b0} :
                       (b[3:2] == 2'b10) ? {6'b0, neg_a, 2'b0} : 16'b0;

    wire [15:0] sel2 = (b[5:4] == 2'b01) ? {4'b0, a, 4'b0} :
                       (b[5:4] == 2'b10) ? {4'b0, neg_a, 4'b0} : 16'b0;

    wire [15:0] sel3 = (b[7:6] == 2'b01) ? {2'b0, a, 6'b0} :
                       (b[7:6] == 2'b10) ? {2'b0, neg_a, 6'b0} : 16'b0;

    // Sum partial products using 8-digit adders
    wire [15:0] sum01, sum23;
    wire [1:0]  c01, c23, cfinal;

    arcloom_bt_adder #(.N(8)) add01 (
        .a(sel0), .b(sel1), .sum_out(sum01), .c_final(c01)
    );
    arcloom_bt_adder #(.N(8)) add23 (
        .a(sel2), .b(sel3), .sum_out(sum23), .c_final(c23)
    );
    arcloom_bt_adder #(.N(8)) add_final (
        .a(sum01), .b(sum23), .sum_out(product_out), .c_final(cfinal)
    );

endmodule
