// ============================================================
// ArcLoom MathLoom — Balanced Ternary Arithmetic
// ============================================================
//
// MathLoom Addendum v1.4 d0.1: Ternary arithmetic primitives.
// ALL COMBINATIONAL. No clock.
//
// Balanced ternary digit set T = {-1, 0, +1}
// Encoding: 00=0, 01=+1, 10=-1, 11=invalid (treated as 0)
//
// Core local digit constraint (addition):
//   a_i + b_i + c_i = s_i + 3 * c_{i+1}
//
// Deterministic tie-break (normative):
//   1. Minimize |s_i|   (prefer 0 over +/-1)
//   2. Minimize |c_{i+1}|
//   3. Else neutral
//
// Truth table (all 7 possible totals):
//   total  sum  carry
//    -3     0    -1
//    -2    +1    -1
//    -1    -1     0
//     0     0     0
//    +1    +1     0
//    +2    -1    +1
//    +3     0    +1
//
// Verify: sum + 3*carry = total for all rows. ✓
// ============================================================


// ============================================================
// Trit Negation — swap +1 <-> -1, 0 stays
// ============================================================
module arcloom_trit_neg (
    input  wire [1:0] trit_in,
    output wire [1:0] trit_out
);
    // 00 -> 00 (0 stays)
    // 01 -> 10 (+1 becomes -1)
    // 10 -> 01 (-1 becomes +1)
    // 11 -> 11 (invalid stays invalid)
    assign trit_out = {trit_in[0], trit_in[1]};
endmodule


// ============================================================
// Balanced Ternary Full Adder — ONE digit position
// ============================================================
// Inputs: a, b, c_in (each a trit)
// Outputs: sum, c_out (each a trit)
// Constraint: a + b + c_in = sum + 3 * c_out
// Purely combinational.
// ============================================================
module arcloom_bt_fulladder (
    input  wire [1:0] a,        // trit: 00=0, 01=+1, 10=-1
    input  wire [1:0] b,        // trit
    input  wire [1:0] c_in,     // carry trit
    output reg  [1:0] sum_out,  // result trit
    output reg  [1:0] c_out     // carry trit
);
    // Convert trit encoding to signed integer
    wire signed [2:0] a_s = (a == 2'b01) ?  3'sd1 :
                            (a == 2'b10) ? -3'sd1 : 3'sd0;
    wire signed [2:0] b_s = (b == 2'b01) ?  3'sd1 :
                            (b == 2'b10) ? -3'sd1 : 3'sd0;
    wire signed [2:0] c_s = (c_in == 2'b01) ?  3'sd1 :
                            (c_in == 2'b10) ? -3'sd1 : 3'sd0;

    wire signed [2:0] total = a_s + b_s + c_s;  // range: -3 to +3

    // Decompose total into (sum, carry) per truth table
    always @(*) begin
        case (total)
            -3'sd3: begin sum_out = 2'b00; c_out = 2'b10; end  // ( 0, -1)
            -3'sd2: begin sum_out = 2'b01; c_out = 2'b10; end  // (+1, -1)
            -3'sd1: begin sum_out = 2'b10; c_out = 2'b00; end  // (-1,  0)
             3'sd0: begin sum_out = 2'b00; c_out = 2'b00; end  // ( 0,  0)
             3'sd1: begin sum_out = 2'b01; c_out = 2'b00; end  // (+1,  0)
             3'sd2: begin sum_out = 2'b10; c_out = 2'b01; end  // (-1, +1)
             3'sd3: begin sum_out = 2'b00; c_out = 2'b01; end  // ( 0, +1)
            default: begin sum_out = 2'b00; c_out = 2'b00; end // unreachable
        endcase
    end
endmodule


// ============================================================
// Balanced Ternary Ripple-Carry Adder — N digits
// ============================================================
// Carry ripple from LSB to MSB. All combinational.
// Propagation delay = N * (one full adder delay).
// For N=9 trits on Zynq-7020: ~10-15 ns.
// ============================================================
module arcloom_bt_adder #(
    parameter N = 9   // number of balanced ternary digits
)(
    input  wire [2*N-1:0] a,        // operand A: N trits packed
    input  wire [2*N-1:0] b,        // operand B: N trits packed
    output wire [2*N-1:0] sum_out,  // result: N trits packed
    output wire [1:0]     c_final   // carry out of MSB
);
    wire [1:0] carry [0:N];   // carry chain

    assign carry[0] = 2'b00;  // initial carry = 0

    genvar i;
    generate
        for (i = 0; i < N; i = i + 1) begin : digit
            arcloom_bt_fulladder fa (
                .a(a[2*i+1:2*i]),
                .b(b[2*i+1:2*i]),
                .c_in(carry[i]),
                .sum_out(sum_out[2*i+1:2*i]),
                .c_out(carry[i+1])
            );
        end
    endgenerate

    assign c_final = carry[N];
endmodule


// ============================================================
// Balanced Ternary Subtractor — N digits
// ============================================================
// SUB(A, B) = ADD(A, NEG(B))
// Combinational.
// ============================================================
module arcloom_bt_sub #(
    parameter N = 9
)(
    input  wire [2*N-1:0] a,
    input  wire [2*N-1:0] b,
    output wire [2*N-1:0] diff_out,
    output wire [1:0]     c_final
);
    // Negate B: swap bit pairs
    wire [2*N-1:0] neg_b;

    genvar i;
    generate
        for (i = 0; i < N; i = i + 1) begin : neg
            arcloom_trit_neg negate (
                .trit_in(b[2*i+1:2*i]),
                .trit_out(neg_b[2*i+1:2*i])
            );
        end
    endgenerate

    // ADD(A, -B)
    arcloom_bt_adder #(.N(N)) add_inst (
        .a(a),
        .b(neg_b),
        .sum_out(diff_out),
        .c_final(c_final)
    );
endmodule


// ============================================================
// Balanced Ternary Absolute Value — N digits
// ============================================================
// If MSB trit is -1, negate the whole number. Else pass through.
// Combinational.
// ============================================================
module arcloom_bt_abs #(
    parameter N = 9
)(
    input  wire [2*N-1:0] a,
    output wire [2*N-1:0] abs_out,
    output wire            was_negative
);
    wire [1:0] msb_trit = a[2*N-1:2*N-2];
    assign was_negative = (msb_trit == 2'b10);  // -1

    // Negate all digits
    wire [2*N-1:0] neg_a;
    genvar i;
    generate
        for (i = 0; i < N; i = i + 1) begin : neg
            arcloom_trit_neg negate (
                .trit_in(a[2*i+1:2*i]),
                .trit_out(neg_a[2*i+1:2*i])
            );
        end
    endgenerate

    assign abs_out = was_negative ? neg_a : a;
endmodule


// ============================================================
// Balanced Ternary Comparator — N digits
// ============================================================
// Computes A - B and checks sign of result.
// Outputs: eq (A=B), gt (A>B), lt (A<B)
// Combinational.
// ============================================================
module arcloom_bt_compare #(
    parameter N = 9
)(
    input  wire [2*N-1:0] a,
    input  wire [2*N-1:0] b,
    output wire            eq,
    output wire            gt,
    output wire            lt
);
    wire [2*N-1:0] diff;
    wire [1:0]     c_final;

    arcloom_bt_sub #(.N(N)) sub_inst (
        .a(a), .b(b),
        .diff_out(diff), .c_final(c_final)
    );

    // Check if diff is all zeros (A = B)
    wire all_zero = (diff == {2*N{1'b0}}) && (c_final == 2'b00);

    // Determine sign: carry first, then scan from MSB for first non-null trit
    reg sign_pos, sign_neg;
    integer k;
    always @(diff or c_final) begin
        sign_pos = 1'b0;
        sign_neg = 1'b0;
        if (c_final == 2'b01)
            sign_pos = 1'b1;
        else if (c_final == 2'b10)
            sign_neg = 1'b1;
        else begin
            // Scan from MSB down to find first non-null trit
            sign_pos = 1'b0;
            sign_neg = 1'b0;
            for (k = N-1; k >= 0; k = k - 1) begin
                if (!sign_pos && !sign_neg) begin
                    if (diff[2*k +: 2] == 2'b01)
                        sign_pos = 1'b1;
                    else if (diff[2*k +: 2] == 2'b10)
                        sign_neg = 1'b1;
                end
            end
        end
    end

    assign eq = all_zero;
    assign gt = ~all_zero & sign_pos;
    assign lt = ~all_zero & sign_neg;
endmodule


// ============================================================
// Balanced Ternary Digit Multiply — single trit × single trit
// ============================================================
// -1 × -1 = +1,  -1 × 0 = 0,  -1 × +1 = -1
//  0 × -1 = 0,   0 × 0 = 0,   0 × +1 = 0
// +1 × -1 = -1,  +1 × 0 = 0,  +1 × +1 = +1
// Combinational.
// ============================================================
module arcloom_trit_mul (
    input  wire [1:0] a,
    input  wire [1:0] b,
    output wire [1:0] product
);
    // If either is 0 (00), product is 0
    // If both same sign, product is +1
    // If different signs, product is -1
    wire a_nonzero = (a == 2'b01) | (a == 2'b10);
    wire b_nonzero = (b == 2'b01) | (b == 2'b10);
    wire same_sign = (a == b);

    assign product = (~a_nonzero | ~b_nonzero) ? 2'b00 :  // either zero
                     same_sign                  ? 2'b01 :  // same sign → +1
                     2'b10;                                 // diff sign → -1
endmodule
