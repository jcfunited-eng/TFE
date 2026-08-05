// ============================================================
// ArcLoom MathLoom Array Processor
// ============================================================
//
// First balanced ternary array processor.
//
// Takes an array of BT-encoded values in BRAM, runs aggregate
// operations across the array using the existing MathLoom ALU,
// and produces scalar results.
//
// Operations:
//   0: NOP
//   1: SUM        — accumulate all elements
//   2: MIN        — find minimum element
//   3: MAX        — find maximum element
//   4: SUB_SCALAR — subtract a constant from every element (in-place)
//   5: SUM_SQ     — sum of squares (for variance)
//   6: MEAN       — sum / count (uses divider)
//   7: COUNT_NZ   — count non-zero elements
//
// Interface:
//   - Python writes BT values into array BRAM via AXI
//   - Python writes op code, array length, scalar operand, and triggers
//   - State machine iterates through BRAM using MathLoom ALU
//   - Results readable via AXI when done
//
// Uses existing arcloom_mathloom_alu for add/multiply/compare.
// Uses existing arcloom_mathloom_div for division.
//
// Array BRAM: 64 entries × 24 bits (12-trit BT values)
//
// NO heuristics. NO floating point. Pure balanced ternary.
//
// Target: PYNQ-Z2 (XC7Z020-1CLG400C)
// ============================================================

module arcloom_mathloom_array (
    input  wire        clk,
    input  wire        rst_n,

    // Control (from AXI)
    input  wire [2:0]  op_code,       // operation to perform
    input  wire [5:0]  array_len,     // number of elements (1-64)
    input  wire [23:0] scalar_in,     // scalar operand (for SUB_SCALAR)
    input  wire        start,         // pulse to begin operation

    // Array BRAM write port (from AXI — Python loads data)
    input  wire [5:0]  wr_addr,
    input  wire [23:0] wr_data,
    input  wire        wr_en,

    // Results (to AXI)
    output reg  [23:0] result_sum,    // accumulated sum (BT)
    output reg  [23:0] result_min,    // minimum element (BT)
    output reg  [23:0] result_max,    // maximum element (BT)
    output reg  [23:0] result_mean,   // sum / count (BT)
    output reg  [5:0]  result_count,  // count of non-zero elements
    output reg         result_valid,  // pulse when operation complete
    output reg         busy           // high while processing
);

    // ---- Operation codes ----
    localparam OP_NOP       = 3'd0;
    localparam OP_SUM       = 3'd1;
    localparam OP_MIN       = 3'd2;
    localparam OP_MAX       = 3'd3;
    localparam OP_SUB_SCALAR = 3'd4;
    localparam OP_SUM_SQ    = 3'd5;
    localparam OP_MEAN      = 3'd6;
    localparam OP_COUNT_NZ  = 3'd7;

    // ---- Array BRAM (64 × 24-bit) ----
    reg [23:0] array_mem [0:63];
    reg [23:0] rd_data;

    // BRAM write (from AXI)
    always @(posedge clk) begin
        if (wr_en)
            array_mem[wr_addr] <= wr_data;
    end

    // BRAM read (from state machine)
    reg [5:0] rd_addr;
    always @(posedge clk) begin
        rd_data <= array_mem[rd_addr];
    end

    // ---- MathLoom ALU instance (combinational) ----
    // ALU inputs are combinational muxes — NOT registered.
    // This ensures alu_sum/alu_product/alu_cmp reflect current-cycle values.
    reg  [23:0] alu_a_r, alu_b_r;  // mux outputs, driven combinationally
    wire [23:0] alu_sum;
    wire [1:0]  alu_carry;
    wire [47:0] alu_product;
    wire        alu_eq, alu_gt, alu_lt;

    arcloom_mathloom_alu alu_inst (
        .a(alu_a_r), .b(alu_b_r),
        .sum_out(alu_sum), .carry_out(alu_carry),
        .product_out(alu_product),
        .cmp_eq(alu_eq), .cmp_gt(alu_gt), .cmp_lt(alu_lt)
    );

    // ---- MathLoom Divider instance (clocked) ----
    reg         div_start;
    reg  [23:0] div_a, div_b;
    wire [23:0] div_quotient, div_remainder;
    wire        div_done, div_by_zero;
    wire [17:0] div_cycles;

    arcloom_mathloom_div div_inst (
        .clk(clk), .rst_n(rst_n),
        .start(div_start),
        .a_in(div_a), .b_in(div_b),
        .quotient(div_quotient), .remainder(div_remainder),
        .done(div_done), .div_by_zero(div_by_zero),
        .cycle_count(div_cycles)
    );

    // ---- State machine ----
    reg [3:0]  state;
    reg [2:0]  cur_op;
    reg [5:0]  idx;
    reg [5:0]  len;
    reg [23:0] accum;
    reg [23:0] scalar_reg;
    reg [5:0]  nz_count;
    reg [23:0] latched_sq;  // latched square result for SUM_SQ two-stage

    localparam S_IDLE      = 4'd0;
    localparam S_FETCH     = 4'd1;  // issue BRAM read
    localparam S_WAIT_RD   = 4'd2;  // wait one cycle for BRAM data
    localparam S_EXECUTE   = 4'd3;  // run ALU operation
    localparam S_WRITEBACK = 4'd4;  // write back to BRAM (for SUB_SCALAR)
    localparam S_NEXT      = 4'd5;  // advance to next element
    localparam S_DIV_START = 4'd6;  // start division (for MEAN)
    localparam S_DIV_WAIT  = 4'd7;  // wait for division to complete
    localparam S_DONE      = 4'd8;

    // Running BT-encoded element count — incremented each iteration
    // by a dedicated adder so MEAN can divide sum/count in BT.
    reg [23:0] bt_counter;

    localparam [23:0] BT_ONE = 24'h000001;     // BT encoding of 1
    localparam [23:0] BT_MAX_POS = 24'h555555; // BT(+3280) all +1 trits
    localparam [23:0] BT_MAX_NEG = 24'hAAAAAA; // BT(-3280) all -1 trits

    // ---- Dedicated BT counter adder ----
    // Separate from main ALU so counter can increment same cycle as operation.
    // Just adds BT_ONE to bt_counter each iteration.
    wire [23:0] bt_counter_next;
    wire [1:0]  bt_counter_carry;  // unused
    wire [47:0] bt_counter_prod;   // unused
    wire        bt_cnt_eq, bt_cnt_gt, bt_cnt_lt; // unused

    arcloom_mathloom_alu counter_alu (
        .a(bt_counter), .b(BT_ONE),
        .sum_out(bt_counter_next), .carry_out(bt_counter_carry),
        .product_out(bt_counter_prod),
        .cmp_eq(bt_cnt_eq), .cmp_gt(bt_cnt_gt), .cmp_lt(bt_cnt_lt)
    );

    // ---- Combinational ALU input mux ----
    // Drives ALU inputs based on current state so results are
    // available in the same cycle for the clocked state machine.
    always @(*) begin
        alu_a_r = 24'd0;
        alu_b_r = 24'd0;
        case (state)
            S_EXECUTE: begin
                case (cur_op)
                    OP_SUM, OP_MEAN: begin
                        alu_a_r = accum;
                        alu_b_r = rd_data;
                    end
                    OP_MIN, OP_MAX: begin
                        alu_a_r = rd_data;
                        alu_b_r = accum;
                    end
                    OP_SUB_SCALAR: begin
                        alu_a_r = rd_data;
                        alu_b_r = bt_negate(scalar_reg);
                    end
                    OP_SUM_SQ: begin
                        alu_a_r = rd_data;
                        alu_b_r = rd_data;
                    end
                    default: ;
                endcase
            end
            S_WRITEBACK: begin
                if (cur_op == OP_SUM_SQ) begin
                    alu_a_r = accum;
                    alu_b_r = latched_sq;
                end
            end
            default: ;
        endcase
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state        <= S_IDLE;
            busy         <= 1'b0;
            result_valid <= 1'b0;
            result_sum   <= 24'd0;
            result_min   <= 24'd0;
            result_max   <= 24'd0;
            result_mean  <= 24'd0;
            result_count <= 6'd0;
            idx          <= 6'd0;
            len          <= 6'd0;
            accum        <= 24'd0;
            nz_count     <= 6'd0;
            bt_counter   <= 24'd0;
            latched_sq   <= 24'd0;
            div_start    <= 1'b0;
            rd_addr      <= 6'd0;
            cur_op       <= 3'd0;
            scalar_reg   <= 24'd0;
            div_a        <= 24'd0;
            div_b        <= 24'd0;
        end else begin
            result_valid <= 1'b0;
            div_start    <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (start) begin
                        cur_op     <= op_code;
                        len        <= array_len;
                        scalar_reg <= scalar_in;
                        idx        <= 6'd0;
                        busy       <= 1'b1;
                        bt_counter <= 24'd0;
                        nz_count   <= 6'd0;

                        case (op_code)
                            OP_SUM, OP_SUM_SQ, OP_MEAN, OP_COUNT_NZ:
                                accum <= 24'd0;
                            OP_MIN:
                                accum <= BT_MAX_POS;
                            OP_MAX:
                                accum <= BT_MAX_NEG;
                            default:
                                accum <= 24'd0;
                        endcase

                        rd_addr <= 6'd0;
                        state   <= S_FETCH;
                    end
                end

                S_FETCH: begin
                    state <= S_WAIT_RD;
                end

                S_WAIT_RD: begin
                    // rd_data valid next cycle. Set up ALU inputs now
                    // so combinational results are ready in S_EXECUTE.
                    state <= S_EXECUTE;
                end

                S_EXECUTE: begin
                    // BT counter increments every element (for MEAN division)
                    bt_counter <= bt_counter_next;

                    // ALU inputs set by combinational mux above.
                    // ALU outputs (alu_sum, alu_product, alu_lt, alu_gt)
                    // are valid this cycle.

                    case (cur_op)
                        OP_SUM, OP_MEAN: begin
                            accum <= alu_sum;  // accum + rd_data
                            if (rd_data != 24'd0)
                                nz_count <= nz_count + 6'd1;
                            state <= S_NEXT;
                        end

                        OP_MIN: begin
                            if (alu_lt)        // rd_data < accum
                                accum <= rd_data;
                            state <= S_NEXT;
                        end

                        OP_MAX: begin
                            if (alu_gt)        // rd_data > accum
                                accum <= rd_data;
                            state <= S_NEXT;
                        end

                        OP_SUB_SCALAR: begin
                            // alu_sum = rd_data + (-scalar), write back next cycle
                            state <= S_WRITEBACK;
                        end

                        OP_SUM_SQ: begin
                            // alu_product = rd_data * rd_data, latch lower 24 bits
                            latched_sq <= alu_product[23:0];
                            state <= S_WRITEBACK;
                        end

                        OP_COUNT_NZ: begin
                            if (rd_data != 24'd0)
                                nz_count <= nz_count + 6'd1;
                            state <= S_NEXT;
                        end

                        default: state <= S_NEXT;
                    endcase
                end

                S_WRITEBACK: begin
                    // ALU inputs set by combinational mux for this state.
                    if (cur_op == OP_SUB_SCALAR) begin
                        array_mem[idx] <= alu_sum;  // rd_data - scalar
                        state <= S_NEXT;
                    end else if (cur_op == OP_SUM_SQ) begin
                        accum <= alu_sum;  // accum + latched_sq
                        state <= S_NEXT;
                    end else begin
                        state <= S_NEXT;
                    end
                end

                S_NEXT: begin
                    if (idx + 6'd1 >= len) begin
                        // Done iterating — produce results
                        case (cur_op)
                            OP_SUM: begin
                                result_sum   <= accum;
                                result_count <= nz_count;
                                state <= S_DONE;
                            end
                            OP_MIN: begin
                                result_min <= accum;
                                state <= S_DONE;
                            end
                            OP_MAX: begin
                                result_max <= accum;
                                state <= S_DONE;
                            end
                            OP_SUB_SCALAR: begin
                                state <= S_DONE;
                            end
                            OP_SUM_SQ: begin
                                result_sum <= accum;
                                state <= S_DONE;
                            end
                            OP_MEAN: begin
                                result_sum   <= accum;
                                result_count <= len;
                                div_a <= accum;
                                div_b <= bt_counter_next;  // count includes last element
                                state <= S_DIV_START;
                            end
                            OP_COUNT_NZ: begin
                                result_count <= nz_count;
                                state <= S_DONE;
                            end
                            default: state <= S_DONE;
                        endcase
                    end else begin
                        idx     <= idx + 6'd1;
                        rd_addr <= idx + 6'd1;
                        state   <= S_FETCH;
                    end
                end

                S_DIV_START: begin
                    div_start <= 1'b1;
                    state <= S_DIV_WAIT;
                end

                S_DIV_WAIT: begin
                    if (div_done) begin
                        result_mean <= div_quotient;
                        state <= S_DONE;
                    end
                end

                S_DONE: begin
                    result_valid <= 1'b1;
                    busy <= 1'b0;
                    state <= S_IDLE;
                end
            endcase
        end
    end

    // ---- BT negate: swap +1 (01) and -1 (10) trits ----
    function [23:0] bt_negate;
        input [23:0] val;
        integer j;
        reg [1:0] t;
        begin
            bt_negate = 24'd0;
            for (j = 0; j < 12; j = j + 1) begin
                t = val[2*j +: 2];
                case (t)
                    2'b01: bt_negate[2*j +: 2] = 2'b10;  // +1 → -1
                    2'b10: bt_negate[2*j +: 2] = 2'b01;  // -1 → +1
                    default: bt_negate[2*j +: 2] = t;     // 0 → 0
                endcase
            end
        end
    endfunction

endmodule
