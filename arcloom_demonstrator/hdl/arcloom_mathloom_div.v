// ArcLoom exact signed 12-trit division. Canonical digits: 00, 01, 10.
// q truncates toward zero; A = B*q + r; |r| < |B| for B != 0.
// This is a CLOCKED repeated-subtraction divider, not a clockless operator.
// For nonzero B the counter measures |q| subtractions + one terminal check:
// maximum 265721, requiring 19 bits. Start/setup is NOT included.
// Division by zero completes immediately with q=0, r=A, cycles=0, dbz=1.
// A start while running is ignored. Operands and signs are captured at start.
module arcloom_mathloom_div (
    input wire clk, rst_n, start,
    input wire [23:0] a_in, b_in,
    output reg [23:0] quotient, remainder,
    output reg done, div_by_zero,
    output reg [18:0] cycle_count
);
    reg [23:0] accum, denom, count;
    reg running, quotient_negative, remainder_negative;
    wire [23:0] magnitude_a, magnitude_b;
    wire negative_a, negative_b;
    arcloom_bt_abs #(.N(12)) abs_a(a_in, magnitude_a, negative_a);
    arcloom_bt_abs #(.N(12)) abs_b(b_in, magnitude_b, negative_b);

    wire cmp_eq, cmp_gt, cmp_lt;
    arcloom_bt_compare #(.N(12)) cmp_inst(
        .a(accum), .b(denom), .eq(cmp_eq), .gt(cmp_gt), .lt(cmp_lt));
    wire [23:0] sub_result, count_plus_one;
    wire [1:0] sub_carry, inc_carry;
    arcloom_bt_sub #(.N(12)) sub_inst(
        .a(accum), .b(denom), .diff_out(sub_result), .c_final(sub_carry));
    arcloom_bt_adder #(.N(12)) inc_inst(
        .a(count), .b(24'd1), .sum_out(count_plus_one), .c_final(inc_carry));

    wire [23:0] negative_count, negative_accum;
    genvar i;
    generate for (i=0; i<12; i=i+1) begin : sign_restore
        arcloom_trit_neg neg_q(count[2*i +: 2], negative_count[2*i +: 2]);
        arcloom_trit_neg neg_r(accum[2*i +: 2], negative_accum[2*i +: 2]);
    end endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            quotient <= 0; remainder <= 0; done <= 0; div_by_zero <= 0;
            cycle_count <= 0; accum <= 0; denom <= 0; count <= 0;
            running <= 0; quotient_negative <= 0; remainder_negative <= 0;
        end else begin
            done <= 0;
            if (start && !running) begin
                cycle_count <= 0;
                div_by_zero <= (b_in == 0);
                if (b_in == 0) begin
                    quotient <= 0; remainder <= a_in; done <= 1;
                end else begin
                    accum <= magnitude_a; denom <= magnitude_b; count <= 0;
                    quotient_negative <= negative_a ^ negative_b;
                    remainder_negative <= negative_a;
                    running <= 1;
                end
            end
            if (running) begin
                cycle_count <= cycle_count + 19'd1;
                if (cmp_gt || cmp_eq) begin
                    accum <= sub_result;
                    count <= count_plus_one;
                end else begin
                    quotient <= quotient_negative ? negative_count : count;
                    remainder <= remainder_negative ? negative_accum : accum;
                    done <= 1;
                    running <= 0;
                end
            end
        end
    end
endmodule
