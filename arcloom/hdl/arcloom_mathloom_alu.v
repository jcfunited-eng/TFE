// ============================================================
// ArcLoom MathLoom ALU — Add, Multiply, Compare
// ============================================================
//
// 12-trit balanced ternary arithmetic.
// Inputs: two 12-digit BT operands (24 bits each)
// Range: ±265,720
// Outputs: 24-trit sum, 24-trit product, comparison flags
// All combinational. No clock.
//
// Fractional support: 6 integer trits + 6 fractional trits
// gives ~3.8 decimal digits of precision.
// The radix point is managed by software — hardware just
// computes on raw trits.
// ============================================================

module arcloom_mathloom_alu (
    input  wire [23:0] a,          // operand A: 12-digit BT
    input  wire [23:0] b,          // operand B: 12-digit BT

    // Addition result
    output wire [23:0] sum_out,    // 12-digit sum
    output wire [1:0]  carry_out,  // carry trit

    // Multiplication result
    output wire [47:0] product_out, // 24-digit product

    // Comparison result
    output wire        cmp_eq,
    output wire        cmp_gt,
    output wire        cmp_lt
);

    // ---- Addition: 12-trit adder ----
    arcloom_bt_adder #(.N(12)) adder (
        .a(a), .b(b), .sum_out(sum_out), .c_final(carry_out)
    );

    // ---- Comparison: 12-trit ----
    arcloom_bt_compare #(.N(12)) comparator (
        .a(a), .b(b), .eq(cmp_eq), .gt(cmp_gt), .lt(cmp_lt)
    );

    // ---- Multiplication: shift-and-add ----
    // For each digit of B: if +1, add A<<i; if -1, subtract A<<i
    // 12 partial products, summed in a tree

    // Negate A
    wire [23:0] neg_a;
    genvar ni;
    generate
        for (ni = 0; ni < 12; ni = ni + 1) begin : neg_gen
            arcloom_trit_neg neg_inst (
                .trit_in(a[2*ni+1:2*ni]),
                .trit_out(neg_a[2*ni+1:2*ni])
            );
        end
    endgenerate

    // Partial products: select A, -A, or 0 for each B digit, shifted
    wire [47:0] pp0, pp1, pp2, pp3, pp4, pp5;
    wire [47:0] pp6, pp7, pp8, pp9, pp10, pp11;

    wire [23:0] s0  = (b[1:0]   == 2'b01) ? a : (b[1:0]   == 2'b10) ? neg_a : 24'b0;
    wire [23:0] s1  = (b[3:2]   == 2'b01) ? a : (b[3:2]   == 2'b10) ? neg_a : 24'b0;
    wire [23:0] s2  = (b[5:4]   == 2'b01) ? a : (b[5:4]   == 2'b10) ? neg_a : 24'b0;
    wire [23:0] s3  = (b[7:6]   == 2'b01) ? a : (b[7:6]   == 2'b10) ? neg_a : 24'b0;
    wire [23:0] s4  = (b[9:8]   == 2'b01) ? a : (b[9:8]   == 2'b10) ? neg_a : 24'b0;
    wire [23:0] s5  = (b[11:10] == 2'b01) ? a : (b[11:10] == 2'b10) ? neg_a : 24'b0;
    wire [23:0] s6  = (b[13:12] == 2'b01) ? a : (b[13:12] == 2'b10) ? neg_a : 24'b0;
    wire [23:0] s7  = (b[15:14] == 2'b01) ? a : (b[15:14] == 2'b10) ? neg_a : 24'b0;
    wire [23:0] s8  = (b[17:16] == 2'b01) ? a : (b[17:16] == 2'b10) ? neg_a : 24'b0;
    wire [23:0] s9  = (b[19:18] == 2'b01) ? a : (b[19:18] == 2'b10) ? neg_a : 24'b0;
    wire [23:0] s10 = (b[21:20] == 2'b01) ? a : (b[21:20] == 2'b10) ? neg_a : 24'b0;
    wire [23:0] s11 = (b[23:22] == 2'b01) ? a : (b[23:22] == 2'b10) ? neg_a : 24'b0;

    assign pp0  = {24'b0, s0};
    assign pp1  = {22'b0, s1, 2'b0};
    assign pp2  = {20'b0, s2, 4'b0};
    assign pp3  = {18'b0, s3, 6'b0};
    assign pp4  = {16'b0, s4, 8'b0};
    assign pp5  = {14'b0, s5, 10'b0};
    assign pp6  = {12'b0, s6, 12'b0};
    assign pp7  = {10'b0, s7, 14'b0};
    assign pp8  = {8'b0,  s8, 16'b0};
    assign pp9  = {6'b0,  s9, 18'b0};
    assign pp10 = {4'b0,  s10, 20'b0};
    assign pp11 = {2'b0,  s11, 22'b0};

    // Sum tree: 12 partial products → 6 → 3 → 2 → 1
    // Layer 1: pairs
    wire [47:0] l1_0, l1_1, l1_2, l1_3, l1_4, l1_5;
    wire [1:0]  c1_0, c1_1, c1_2, c1_3, c1_4, c1_5;

    arcloom_bt_adder #(.N(24)) l1a0 (.a(pp0),  .b(pp1),  .sum_out(l1_0), .c_final(c1_0));
    arcloom_bt_adder #(.N(24)) l1a1 (.a(pp2),  .b(pp3),  .sum_out(l1_1), .c_final(c1_1));
    arcloom_bt_adder #(.N(24)) l1a2 (.a(pp4),  .b(pp5),  .sum_out(l1_2), .c_final(c1_2));
    arcloom_bt_adder #(.N(24)) l1a3 (.a(pp6),  .b(pp7),  .sum_out(l1_3), .c_final(c1_3));
    arcloom_bt_adder #(.N(24)) l1a4 (.a(pp8),  .b(pp9),  .sum_out(l1_4), .c_final(c1_4));
    arcloom_bt_adder #(.N(24)) l1a5 (.a(pp10), .b(pp11), .sum_out(l1_5), .c_final(c1_5));

    // Layer 2: triplets → pairs
    wire [47:0] l2_0, l2_1, l2_2;
    wire [1:0]  c2_0, c2_1, c2_2;

    arcloom_bt_adder #(.N(24)) l2a0 (.a(l1_0), .b(l1_1), .sum_out(l2_0), .c_final(c2_0));
    arcloom_bt_adder #(.N(24)) l2a1 (.a(l1_2), .b(l1_3), .sum_out(l2_1), .c_final(c2_1));
    arcloom_bt_adder #(.N(24)) l2a2 (.a(l1_4), .b(l1_5), .sum_out(l2_2), .c_final(c2_2));

    // Layer 3
    wire [47:0] l3_0, l3_1;
    wire [1:0]  c3_0, c3_1;

    arcloom_bt_adder #(.N(24)) l3a0 (.a(l2_0), .b(l2_1), .sum_out(l3_0), .c_final(c3_0));
    assign l3_1 = l2_2;

    // Layer 4: final
    wire [1:0] cfinal;
    arcloom_bt_adder #(.N(24)) l4a0 (.a(l3_0), .b(l3_1), .sum_out(product_out), .c_final(cfinal));

endmodule
