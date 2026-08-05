// ============================================================
// ArcLoom MathLoom Folding Division — 12-Trit Balanced Ternary
// ============================================================
//
// Division by iterative field reduction (folding):
//   quotient = number of times B can be subtracted from A
//   remainder = what's left after folding
//
// 12-trit operands: range ±265,720
// 12-trit quotient and remainder
//
// CLOCKED — iterative, not combinational.
// Worst case: 265,720 cycles at 100MHz = 2.66ms
// Typical: much faster (real quotients are small)
//
// Interface: write A and B, assert start, wait for done, read result.
// ============================================================

module arcloom_mathloom_div (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         start,
    input  wire [23:0]  a_in,        // numerator (12-digit BT)
    input  wire [23:0]  b_in,        // denominator (12-digit BT)

    output reg  [23:0]  quotient,
    output reg  [23:0]  remainder,
    output reg          done,
    output reg          div_by_zero,
    output reg  [17:0]  cycle_count  // up to 265,720
);

    reg [23:0] accum;
    reg [23:0] denom;
    reg [23:0] count;
    reg        running;

    // Comparator: accum vs denom
    wire cmp_eq, cmp_gt, cmp_lt;
    arcloom_bt_compare #(.N(12)) cmp_inst (
        .a(accum), .b(denom),
        .eq(cmp_eq), .gt(cmp_gt), .lt(cmp_lt)
    );

    // Subtraction: accum - denom = accum + (-denom)
    wire [23:0] neg_denom;
    genvar i;
    generate
        for (i = 0; i < 12; i = i + 1) begin : neg_gen
            arcloom_trit_neg neg_inst (
                .trit_in(denom[2*i+1:2*i]),
                .trit_out(neg_denom[2*i+1:2*i])
            );
        end
    endgenerate

    wire [23:0] sub_result;
    wire [1:0]  sub_carry;
    arcloom_bt_adder #(.N(12)) sub_inst (
        .a(accum), .b(neg_denom),
        .sum_out(sub_result), .c_final(sub_carry)
    );

    // Increment count: count + 1
    wire [23:0] count_plus_one;
    wire [1:0]  inc_carry;
    arcloom_bt_adder #(.N(12)) inc_inst (
        .a(count), .b(24'b000000000000000000000001),
        .sum_out(count_plus_one), .c_final(inc_carry)
    );

    wire accum_eq_zero = (accum == 24'b0);
    wire accum_ge_denom = cmp_gt || cmp_eq;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            quotient    <= 24'd0;
            remainder   <= 24'd0;
            done        <= 1'b0;
            div_by_zero <= 1'b0;
            running     <= 1'b0;
            accum       <= 24'd0;
            denom       <= 24'd0;
            count       <= 24'd0;
            cycle_count <= 18'd0;
        end else begin
            done <= 1'b0;

            if (start && !running) begin
                if (b_in == 24'b0) begin
                    div_by_zero <= 1'b1;
                    quotient    <= 24'b0;
                    remainder   <= a_in;
                    done        <= 1'b1;
                end else begin
                    div_by_zero <= 1'b0;
                    accum       <= a_in;
                    denom       <= b_in;
                    count       <= 24'b0;
                    cycle_count <= 18'd0;
                    running     <= 1'b1;
                end
            end

            if (running) begin
                cycle_count <= cycle_count + 18'd1;

                if (accum_ge_denom && !accum_eq_zero) begin
                    accum <= sub_result;
                    count <= count_plus_one;
                end else begin
                    quotient  <= count;
                    remainder <= accum;
                    done      <= 1'b1;
                    running   <= 1'b0;
                end
            end
        end
    end

endmodule
