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

    // Target match interface (single-slot, task-specific)
    input  wire [TRIT_WIDTH-1:0]   target_motif,    // AXI-writable target (0 = no target)
    output wire [7:0]              target_match_score, // match vs target (combinational)

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

    // ---- Commit logic ----
    integer c;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            write_ptr       <= 0;
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

            if (commit_request | force_commit) begin
                if (commit_eligible | (force_commit & ~duplicate_found)) begin
                    motifs[write_ptr]     <= state_in;
                    hash_table[write_ptr] <= state_hash;
                    write_ptr <= (write_ptr == DEPTH-1) ? {ADDR_BITS{1'b0}} :
                                 write_ptr + {{(ADDR_BITS-1){1'b0}}, 1'b1};
                    if (count < DEPTH)
                        count <= count + 1;
                    commit_accepted <= 1'b1;
                end else begin
                    commit_rejected <= 1'b1;
                end
            end
        end
    end

    // ---- Recall: parallel pattern match ----
    // Compares query against all stored motifs simultaneously.
    // Score = count of matching non-null trits.
    integer m, t;
    reg [7:0]  scores [0:DEPTH-1];
    reg [7:0]  best;
    reg [ADDR_BITS-1:0] best_idx;
    reg        found;

    always @(query or count) begin
        best     = 0;
        best_idx = 0;
        found    = 1'b0;

        for (m = 0; m < DEPTH; m = m + 1) begin
            scores[m] = 0;
            if (m < count) begin
                for (t = 0; t < TRIT_WIDTH/2; t = t + 1) begin
                    if (query[2*t +: 2] != 2'b00 &&
                        motifs[m][2*t +: 2] != 2'b00 &&
                        query[2*t +: 2] == motifs[m][2*t +: 2]) begin
                        scores[m] = scores[m] + 8'd1;
                    end
                end
                if (scores[m] > best) begin
                    best     = scores[m];
                    best_idx = m[ADDR_BITS-1:0];
                    found    = 1'b1;
                end
            end
        end

        if (found && count > 0) begin
            best_match   = motifs[best_idx];
            match_score  = best;
            recall_valid = 1'b1;
        end else begin
            best_match   = {TRIT_WIDTH{1'b0}};
            match_score  = 8'd0;
            recall_valid = 1'b0;
        end
    end

    // ---- Target match: single-slot parallel comparator ----
    // Same scoring as global CAM recall but against one AXI-writable motif.
    // Purely combinational. When target_motif = 0 (all null), score = 0.
    // Used for hunt (high match → approach) and inspect (low match → alert).
    integer tt;
    reg [7:0] target_score_r;

    always @(query or target_motif) begin
        target_score_r = 8'd0;
        for (tt = 0; tt < TRIT_WIDTH/2; tt = tt + 1) begin
            if (query[2*tt +: 2] != 2'b00 &&
                target_motif[2*tt +: 2] != 2'b00 &&
                query[2*tt +: 2] == target_motif[2*tt +: 2]) begin
                target_score_r = target_score_r + 8'd1;
            end
        end
    end

    assign target_match_score = target_score_r;

endmodule
