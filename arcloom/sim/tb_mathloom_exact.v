`timescale 1ns/1ps
// Actual RTL component falsifier; not a silicon or organism witness.
module tb_mathloom_exact;
  reg clk=0, rst_n=0, start=0;
  always #5 clk=~clk;
  reg [23:0] a=0, b=0;
  wire [23:0] sum, quotient, remainder, absolute;
  wire [47:0] product;
  wire [1:0] carry;
  wire eq, gt, lt, done, dbz, negative;
  wire [18:0] cycles;
  integer failures=0, checks=0, i, j;
  arcloom_mathloom_alu alu(a,b,sum,carry,product,eq,gt,lt);
  arcloom_bt_abs #(.N(12)) abs_dut(a,absolute,negative);
  arcloom_mathloom_div div_dut(.clk(clk),.rst_n(rst_n),.start(start),
    .a_in(a),.b_in(b),.quotient(quotient),.remainder(remainder),
    .done(done),.div_by_zero(dbz),.cycle_count(cycles));

  function [23:0] encode;
    input integer value;
    integer n, digit, k;
    begin
      n=value; encode=0;
      for(k=0;k<12;k=k+1) begin
        digit=n%3; n=n/3;
        if(digit==2) begin digit=-1; n=n+1; end
        if(digit==-2) begin digit=1; n=n-1; end
        case(digit)
          1: encode[k*2 +: 2]=2'b01;
         -1: encode[k*2 +: 2]=2'b10;
          0: encode[k*2 +: 2]=2'b00;
        endcase
      end
      if(n!=0) $fatal(1,"test operand out of range");
    end
  endfunction
  function signed [63:0] decode;
    input [47:0] value;
    reg signed [63:0] power;
    integer k;
    begin
      decode=0; power=1;
      for(k=0;k<24;k=k+1) begin
        case(value[k*2 +: 2])
          2'b01: decode=decode+power;
          2'b10: decode=decode-power;
          2'b00: ;
          default: $fatal(1,"noncanonical/unknown result trit");
        endcase
        power=power*3;
      end
    end
  endfunction
  task require;
    input condition;
    input [511:0] label;
    begin
      checks=checks+1;
      if(condition!==1'b1) begin
        failures=failures+1;
        if(failures<=12) $display("FAIL %0s",label);
      end
    end
  endtask
  task check_alu;
    input integer x,y;
    reg signed [63:0] expected_product;
    begin
      a=encode(x); b=encode(y); #1;
      expected_product=x; expected_product=expected_product*y;
      require(decode({22'b0,carry,sum})==x+y,"sum with carry");
      require(decode(product)==expected_product,"full 24-trit product");
      require(eq==(x==y) && gt==(x>y) && lt==(x<y),"comparison");
      require(decode({24'b0,absolute})==(x<0 ? -x : x),"absolute/sign of leading nonzero trit");
    end
  endtask
  task check_div;
    input integer x,y;
    integer q,r,budget,ticks;
    begin
      @(negedge clk); a=encode(x); b=encode(y); start=1;
      @(posedge clk); #1;
      if(y==0) begin
        require(done && dbz,"divide-by-zero completion");
        require(cycles==0,"divide-by-zero clears stale cycle count");
        require(decode({24'b0,remainder})==x,"divide-by-zero preserves numerator");
        @(negedge clk); start=0;
      end else begin
        q=x/y; r=x-q*y; budget=(q<0 ? -q : q)+1;
        @(negedge clk); start=0; ticks=0;
        while(!done && ticks<budget+2) begin
          @(posedge clk); #1; ticks=ticks+1;
        end
        if(!done) begin
          require(0,"signed division exceeded mathematical operation bound");
          @(negedge clk); rst_n=0;
          @(negedge clk); rst_n=1;
        end else begin
          require(!dbz,"nonzero divisor status");
          require(decode({24'b0,quotient})==q,"signed quotient truncates toward zero");
          require(decode({24'b0,remainder})==r,"signed remainder preserves A=B*q+r");
          require(cycles==budget,"full cycle count equals folds plus final check");
        end
      end
    end
  endtask
  initial begin
    #1; rst_n=0; #10; rst_n=1;
    for(i=-40;i<=40;i=i+1)
      for(j=-40;j<=40;j=j+1) check_alu(i,j);
    check_alu(265720,265720); check_alu(-265720,-265720);
    check_alu(265720,-265720); check_alu(-1,265720);
    check_div(100,5); check_div(100,7); check_div(500,25);
    check_div(-100,7); check_div(100,-7); check_div(-100,-7);
    check_div(-1,7); check_div(1,-7); check_div(0,7);
    check_div(500,1); check_div(50,0); check_div(-50,0);
    check_div(265720,1); check_div(-265720,1);
    check_div(265720,-265720); check_div(-265720,-265720);
    if(failures) $fatal(1,"MathLoom RTL failures=%0d checks=%0d",failures,checks);
    $display("PASS MathLoom actual RTL checks=%0d",checks); $finish;
  end
endmodule
