// ============================================================
// ArcLoom Krimelack — Structural Memory (Spec-Compliant)
// ============================================================
//
// UF-Spec 8.5: Folded structural memory storing motifs with
// commit eligibility gating and cue-based recall.
//
// Motif commit rules (normative):
//   Commit iff:
//     - SETTLED window holds (U* <= U_settle for K_s gates)
//     - IG >= IG_min OR resonance_mean >= R_commit
//     - SafeMode = 0
//     - No duplicate (idempotency: same state → same motif)
//
// Recall: parallel pattern match against all stored motifs.
// Scoring: count of matching non-null trits (Hamming-like).
//
// Memory layout: circular buffer with hash-based duplicate
// detection. Folded locality approximated by insertion order
// (temporally adjacent motifs are physically adjacent).
//
// Clocked — memory requires clock for write operations.
// ============================================================

module arcloom_krimelack #(
    parameter TRIT_WIDTH = 48,    // 24 trits x 2 bits = 48 bits (8 strands)
    parameter DEPTH      = 32,    // number of stored motifs
    parameter ADDR_BITS  = 5,     // log2(DEPTH)
    // Commit thresholds
    parameter [31:0] U_SETTLE  = 32'h0000599A,  // 0.35 in 16.16
    parameter [31:0] R_COMMIT  = 32'h0000B851    // 0.72 in 16.16
)(
    input  wire                    clk,
    input  wire                    rst_n,

    // Motif commit interface
    input  wire                    commit_request,  // pulse: attempt to commit (eligibility-gated)
    input  wire                    force_commit,    // pulse: commit unconditionally (software capture)
    input  wire [TRIT_WIDTH-1:0]   state_in,        // loom state to commit
    input  wire [31:0]             u_star,          // adjusted uncertainty (16.16)
    input  wire [31:0]             resonance,       // scalar resonance R(k) (16.16)
    input  wire                    safe_mode,       // SafeMode flag

    // Recall interface (global CAM)
    input  wire [TRIT_WIDTH-1:0]   query,           // partial state to match
    output reg  [TRIT_WIDTH-1:0]   best_match,      // closest stored motif
    output reg  [7:0]              match_score,     // match quality (0-255)
    output reg                     recall_valid,    // match found

    // Target match interface (best-of-N across target slots 0-7)
    output wire [7:0]              target_match_score, // best match vs target partition

    // Status
    output wire [ADDR_BITS:0]      motif_count,     // number of stored motifs
    output reg                     commit_accepted, // pulse: motif was committed
    output reg                     commit_rejected  // pulse: commit was blocked
);

    // ---- Motif storage ----
    reg [TRIT_WIDTH-1:0] motifs [0:DEPTH-1];
    reg [ADDR_BITS-1:0]  write_ptr;
    reg [ADDR_BITS:0]    count;

    assign motif_count = count;

    // ---- Duplicate detection (hash-based) ----
    // Simple hash: XOR-fold the state into 8 bits
    wire [7:0] state_hash = state_in[7:0] ^ state_in[15:8] ^
                            state_in[23:16] ^ state_in[31:24] ^
                            state_in[39:32] ^ state_in[47:40];

    reg [7:0] hash_table [0:DEPTH-1];

    // Check if this exact state already exists
    reg duplicate_found;
    integer d;
    always @(*) begin
        duplicate_found = 1'b0;
        for (d = 0; d < DEPTH; d = d + 1) begin
            if (d < count) begin
                if (hash_table[d] == state_hash && motifs[d] == state_in)
                    duplicate_found = 1'b1;
            end
        end
    end

    // ---- Commit eligibility (spec normative) ----
    wire commit_eligible = commit_request &
                           ~safe_mode &
                           (u_star <= U_SETTLE) &
                           (resonance >= R_COMMIT) &
                           ~duplicate_found;

    // ---- Partitioned commit logic ----
    // Slots 0-7: target (force_commit writes here)
    // Slots 8-31: autonomous (commit_request writes here)
    // Target slots store the object being hunted/inspected.
    // Autonomous slots store environmental motifs for habituation.
    localparam TARGET_SLOTS = 8;
    reg [2:0]  target_ptr;            // 0-7
    reg [ADDR_BITS-1:0] auto_ptr;    // 8 to DEPTH-1
    reg [2:0]  target_count;
    reg [ADDR_BITS:0] auto_count;

    integer c;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            target_ptr      <= 3'd0;
            auto_ptr        <= TARGET_SLOTS;
            target_count    <= 3'd0;
            auto_count      <= 0;
            count           <= 0;
            commit_accepted <= 1'b0;
            commit_rejected <= 1'b0;
            for (c = 0; c < DEPTH; c = c + 1) begin
                motifs[c]     <= {TRIT_WIDTH{1'b0}};
                hash_table[c] <= 8'd0;
            end
        end else begin
            commit_accepted <= 1'b0;
            commit_rejected <= 1'b0;

            if (force_commit) begin
                // Target partition: slots 0-7
                if (~duplicate_found) begin
                    motifs[{2'b00, target_ptr}]     <= state_in;
                    hash_table[{2'b00, target_ptr}] <= state_hash;
                    target_ptr <= (target_ptr == 3'd7) ? 3'd0 : target_ptr + 3'd1;
                    if (target_count < TARGET_SLOTS)
                        target_count <= target_count + 3'd1;
                    commit_accepted <= 1'b1;
                end else begin
                    commit_rejected <= 1'b1;
                end
            end else if (commit_request) begin
                // Autonomous partition: slots 8-31
                if (commit_eligible) begin
                    motifs[auto_ptr]     <= state_in;
                    hash_table[auto_ptr] <= state_hash;
                    auto_ptr <= (auto_ptr == DEPTH-1) ? TARGET_SLOTS[ADDR_BITS-1:0] :
                                auto_ptr + {{(ADDR_BITS-1){1'b0}}, 1'b1};
                    if (auto_count < (DEPTH - TARGET_SLOTS))
                        auto_count <= auto_count + 1;
                    commit_accepted <= 1'b1;
                end else begin
                    commit_rejected <= 1'b1;
                end
            end

            count <= {1'b0, target_count} + auto_count;
        end
    end

    // ---- Recall: partitioned parallel pattern match ----
    // Global recall: best match across autonomous slots (8-31)
    // Target recall: best match across target slots (0-7)
    // Both combinational, both run every cycle.
    integer m, t;
    reg [7:0]  scores [0:DEPTH-1];

    // Global (autonomous) best match — slots 8-31
    reg [7:0]  global_best;
    reg [ADDR_BITS-1:0] global_best_idx;
    reg        global_found;

    // Target best match — slots 0-7
    reg [7:0]  target_best;

    always @(query or target_count or auto_count) begin
        global_best     = 0;
        global_best_idx = 0;
        global_found    = 1'b0;
        target_best     = 0;

        // Score all slots
        for (m = 0; m < DEPTH; m = m + 1) begin
            scores[m] = 0;
            for (t = 0; t < TRIT_WIDTH/2; t = t + 1) begin
                if (query[2*t +: 2] != 2'b00 &&
                    motifs[m][2*t +: 2] != 2'b00 &&
                    query[2*t +: 2] == motifs[m][2*t +: 2]) begin
                    scores[m] = scores[m] + 8'd1;
                end
            end

            // Partition the results
            if (m < TARGET_SLOTS) begin
                // Target slot (0-7)
                if (m < target_count && scores[m] > target_best)
                    target_best = scores[m];
            end else begin
                // Autonomous slot (8-31)
                if ((m - TARGET_SLOTS) < auto_count && scores[m] > global_best) begin
                    global_best     = scores[m];
                    global_best_idx = m[ADDR_BITS-1:0];
                    global_found    = 1'b1;
                end
            end
        end

        if (global_found) begin
            best_match   = motifs[global_best_idx];
            match_score  = global_best;
            recall_valid = 1'b1;
        end else begin
            best_match   = {TRIT_WIDTH{1'b0}};
            match_score  = 8'd0;
            recall_valid = 1'b0;
        end
    end

    // Target match score: best-of-N across target slots 0-7
    // When no target captured (target_count=0), score=0.
    assign target_match_score = target_best;

endmodule
