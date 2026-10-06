`timescale 1ns/1ps
// Real wrapper + real controller and arithmetic RTL. No replacement DUT models.
module tb_mathloom_axi;
  reg clk=0, reset=0;
  always #5 clk=~clk;
  reg [7:0] awaddr=0, araddr=0;
  reg [31:0] wdata=0;
  reg [3:0] wstrb=15;
  reg awvalid=0,wvalid=0,bready=0,arvalid=0,rready=0;
  wire awready,wready,bvalid,arready,rvalid;
  wire [31:0] rdata;
  wire [1:0] bresp,rresp;
  wire m1,m2,m3,m4;
  integer checks=0, ticks;
  reg [1:0] expected_bresp=0;
  reg [31:0] value;
  arcloom_axi_wrapper dut(
    .S_AXI_ACLK(clk),.S_AXI_ARESETN(reset),
    .S_AXI_AWADDR(awaddr),.S_AXI_AWPROT(3'b0),.S_AXI_AWVALID(awvalid),.S_AXI_AWREADY(awready),
    .S_AXI_WDATA(wdata),.S_AXI_WSTRB(wstrb),.S_AXI_WVALID(wvalid),.S_AXI_WREADY(wready),
    .S_AXI_BRESP(bresp),.S_AXI_BVALID(bvalid),.S_AXI_BREADY(bready),
    .S_AXI_ARADDR(araddr),.S_AXI_ARPROT(3'b0),.S_AXI_ARVALID(arvalid),.S_AXI_ARREADY(arready),
    .S_AXI_RDATA(rdata),.S_AXI_RRESP(rresp),.S_AXI_RVALID(rvalid),.S_AXI_RREADY(rready),
    .hw_sensor_data(16'b0),.hw_sensor_valid(1'b0),
    .hw_sensor_data_left(16'b0),.hw_sensor_valid_left(1'b0),
    .hw_sensor_data_right(16'b0),.hw_sensor_valid_right(1'b0),
    .motor_ain1(m1),.motor_ain2(m2),.motor_bin1(m3),.motor_bin2(m4));

  function [23:0] encode;
    input integer x;
    integer n,d,k;
    begin
      n=x; encode=0;
      for(k=0;k<12;k=k+1) begin
        d=n%3; n=n/3;
        if(d==2) begin d=-1; n=n+1; end
        if(d==-2) begin d=1; n=n-1; end
        encode[2*k +: 2]=(d<0 ? 2 : d);
      end
    end
  endfunction
  task check;
    input ok; input [511:0] label;
    begin checks=checks+1; if(ok!==1'b1) $fatal(1,"FAIL %0s",label); end
  endtask
  task write_word;
    input [7:0] address; input [31:0] data; input [3:0] strobes;
    input integer address_delay,data_delay;
    begin
      fork
        begin
          repeat(address_delay+1) @(negedge clk);
          awaddr=address; awvalid=1;
          @(posedge clk); while(!awready) @(posedge clk);
          @(negedge clk); awvalid=0;
        end
        begin
          repeat(data_delay+1) @(negedge clk);
          wdata=data; wstrb=strobes; wvalid=1;
          @(posedge clk); while(!wready) @(posedge clk);
          @(negedge clk); wvalid=0;
        end
      join
      wait(bvalid); #1;
      check(bresp==expected_bresp,"write response/refusal");
      repeat(3) begin @(posedge clk); #1; check(bvalid,"BVALID held under backpressure"); end
      @(negedge clk); bready=1;
      @(negedge clk); bready=0;
    end
  endtask
  task read_word;
    input [7:0] address; output [31:0] result;
    begin
      @(negedge clk); araddr=address; arvalid=1;
      @(posedge clk); while(!arready) @(posedge clk);
      @(negedge clk); arvalid=0;
      wait(rvalid); #1; result=rdata;
      repeat(3) begin
        @(posedge clk); #1;
        check(rvalid && rdata===result && !arready,"read stable under backpressure");
      end
      @(negedge clk); rready=1;
      @(negedge clk); rready=0;
    end
  endtask
  task division;
    input integer x,y,q,r,cycles;
    begin
      write_word(8'h04,encode(x),15,0,3);
      write_word(8'h08,encode(y),15,3,0);
      write_word(8'h0c,32'h10000,15,0,0);
      read_word(8'h7c,value); ticks=0;
      while(!value[0] && ticks<600) begin read_word(8'h7c,value); ticks=ticks+1; end
      check(value[0] && !value[2] && value[1]==(y==0),"dedicated division completion/status");
      read_word(8'h0c,value); check(value[23:0]==encode(q),"AXI signed quotient");
      read_word(8'h10,value); check(value[23:0]==encode(r),"AXI signed remainder");
      read_word(8'h74,value); check(value==cycles,"untruncated AXI cycle count");
    end
  endtask
  initial begin
    repeat(3) @(negedge clk); reset=1;
    read_word(8'h78,value); check(value==32'h4d4c0001,"ABI identity");
    check({m1,m2,m3,m4}===4'b0,"motor gate off after reset");
    expected_bresp=2;
    write_word(8'h10,4,1,0,2);
    expected_bresp=0;
    read_word(8'h28,value); check(value[12]==0,"partial write cannot enable motors");
    write_word(8'h10,4,15,2,0);
    read_word(8'h28,value); check(value[12]==1,"full write enables gate");
    write_word(8'h10,0,15,0,2);
    check({m1,m2,m3,m4}===4'b0,"disabled gate forces four logic zeros");
    write_word(8'h04,encode(265720),15,0,3);
    write_word(8'h08,encode(265720),15,3,0);
    read_word(8'h08,value);
    check(value[25:24]==1 && value[31:29]==1,"carry and equal flag register positions");
    division(100,7,14,2,15);
    division(-100,7,-14,-2,15);
    division(500,1,500,0,501);
    // Re-trigger identical operands: old READY must not remain asserted.
    write_word(8'h0c,32'h10000,15,0,0);
    read_word(8'h7c,value); check(value[2] && !value[0],"restart clears stale READY");
    expected_bresp=2;
    write_word(8'h04,encode(123),15,0,0);
    write_word(8'h0c,32'h10000,15,0,0);
    expected_bresp=0;
    read_word(8'h7c,value); check(value[2] && !value[0],"busy writes refuse without losing custody");
    // Reset aborts pending operation and clears all completion custody.
    @(negedge clk); reset=0;
    repeat(2) @(negedge clk); reset=1;
    read_word(8'h7c,value); check(value==0,"reset cancels pending arithmetic");
    division(-50,0,0,-50,0);
    check({m1,m2,m3,m4}===4'b0,"arithmetic never enables motors");
    $display("PASS actual AXI/controller/MathLoom checks=%0d",checks); $finish;
  end
  initial begin #1000000; $fatal(1,"bounded AXI witness timed out"); end
endmodule
