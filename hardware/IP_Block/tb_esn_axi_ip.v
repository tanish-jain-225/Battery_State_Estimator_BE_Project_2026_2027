`timescale 1ns / 1ps
// AXI4-Lite + AXI4-Stream test of esn_axi_ip on NASA B0018 cycle 115.
//  1) register-mode: load all memories through MEM_SEL/MEM_ADDR/MEM_DATA, CLEAR, 64 x (START, poll, read SOC), SOH
//  2) stream-mode:   input memory zeroed, STREAM_EN=1, 64 beats in, 64 result beats out (random back-pressure)
// Outputs: rtl_axil.csv, rtl_axis.csv  (compare with golden_readout.csv)
module tb_esn_axi_ip;
reg aclk = 0; always #5 aclk = ~aclk;
reg aresetn = 0;
reg [7:0] awaddr = 0; reg awvalid = 0; wire awready; reg [31:0] wdata = 0; reg wvalid = 0; wire wready;
wire [1:0] bresp; wire bvalid; reg bready = 1;
reg [7:0] araddr = 0; reg arvalid = 0; wire arready; wire [31:0] rdata; wire [1:0] rresp; wire rvalid; reg rready = 1;
reg [63:0] s_tdata = 0; reg s_tvalid = 0; wire s_tready;
wire [63:0] m_tdata; wire m_tvalid; reg m_tready = 0; wire m_tlast; wire irq;

esn_axi_ip #(.N_IN(4), .N_RES(100), .T_MAX(64)) dut (
    .aclk(aclk), .aresetn(aresetn),
    .s_axi_awaddr(awaddr), .s_axi_awvalid(awvalid), .s_axi_awready(awready),
    .s_axi_wdata(wdata), .s_axi_wstrb(4'hF), .s_axi_wvalid(wvalid), .s_axi_wready(wready),
    .s_axi_bresp(bresp), .s_axi_bvalid(bvalid), .s_axi_bready(bready),
    .s_axi_araddr(araddr), .s_axi_arvalid(arvalid), .s_axi_arready(arready),
    .s_axi_rdata(rdata), .s_axi_rresp(rresp), .s_axi_rvalid(rvalid), .s_axi_rready(rready),
    .s_axis_tdata(s_tdata), .s_axis_tvalid(s_tvalid), .s_axis_tready(s_tready),
    .m_axis_tdata(m_tdata), .m_axis_tvalid(m_tvalid), .m_axis_tready(m_tready), .m_axis_tlast(m_tlast),
    .irq(irq));

task axi_w(input [7:0] a, input [31:0] d);
begin
    @(negedge aclk); awaddr = a; wdata = d; awvalid = 1; wvalid = 1;
    @(posedge aclk); while (!(awready && wready)) @(posedge aclk);
    @(negedge aclk); awvalid = 0; wvalid = 0;
    @(posedge aclk); while (!bvalid) @(posedge aclk);
end
endtask
reg [31:0] rd;
task axi_r(input [7:0] a);
begin
    @(negedge aclk); araddr = a; arvalid = 1;
    @(posedge aclk); while (!arready) @(posedge aclk);
    @(negedge aclk); arvalid = 0;
    @(posedge aclk); while (!rvalid) @(posedge aclk);
    rd = rdata;
end
endtask

reg [15:0] m_win [0:399]; reg [15:0] m_w [0:9999]; reg [15:0] m_b [0:99]; reg [15:0] m_in [0:255];
reg [17:0] m_rs [0:100]; reg [17:0] m_rh [0:100];
integer fd, fs, i, t, errors, nb;
reg [15:0] soc_t, soh_t; reg [5:0] st_t;

// stream result collector with random back-pressure
integer seed = 7;
always @(negedge aclk) m_tready <= ($random(seed) & 3) != 0;
always @(posedge aclk) if (m_tvalid && m_tready) begin
    $fwrite(fs, "%0d,%04h\n", m_tdata[21:16], m_tdata[15:0]);
    if (m_tlast) $fwrite(fs, "SOH,%04h\n", m_tdata[47:32]);
    nb = nb + 1;
end

initial begin
    nb = 0; errors = 0;
    $readmemh("win_bram.mem", m_win); $readmemh("w_bram.mem", m_w); $readmemh("bias_bram.mem", m_b);
    $readmemh("input_c115.mem", m_in); $readmemh("readout_soc.mem", m_rs); $readmemh("readout_soh.mem", m_rh);
    fd = $fopen("rtl_axil.csv", "w"); $fwrite(fd, "step,soc_hex\n");
    fs = $fopen("rtl_axis.csv", "w"); $fwrite(fs, "step,soc_hex\n");
    repeat (10) @(negedge aclk); aresetn = 1; repeat (5) @(negedge aclk);

    axi_r(8'h00); if (rd !== 32'h45534E31) begin errors = errors + 1; $display("ID mismatch %h", rd); end
    axi_r(8'h04); $display("CAPS = %h (expect 04006404)", rd); if (rd !== 32'h04006404) begin errors = errors + 1; end

    // ---- load memories (auto-increment) ----
    axi_w(8'h28, 0); axi_w(8'h2C, 32'h8000_0000); for (i = 0; i < 400;   i = i + 1) axi_w(8'h30, m_win[i]);
    axi_w(8'h28, 1); axi_w(8'h2C, 32'h8000_0000); for (i = 0; i < 10000; i = i + 1) axi_w(8'h30, m_w[i]);
    axi_w(8'h28, 2); axi_w(8'h2C, 32'h8000_0000); for (i = 0; i < 256;   i = i + 1) axi_w(8'h30, m_in[i]);
    axi_w(8'h28, 3); axi_w(8'h2C, 32'h8000_0000); for (i = 0; i < 100;   i = i + 1) axi_w(8'h30, m_b[i]);
    axi_w(8'h28, 4); axi_w(8'h2C, 32'h8000_0000); for (i = 0; i <= 100;  i = i + 1) axi_w(8'h30, m_rs[i]);
    axi_w(8'h28, 5); axi_w(8'h2C, 32'h8000_0000); for (i = 0; i <= 100;  i = i + 1) axi_w(8'h30, m_rh[i]);

    // ---- 1) register mode ----
    axi_w(8'h14, 32'h7);                       // enable all irq
    axi_w(8'h08, 32'h2);                       // CLEAR
    axi_r(8'h0C); while (rd[0]) axi_r(8'h0C);
    for (t = 0; t < 64; t = t + 1) begin
        axi_w(8'h08, 32'h1);                   // START
        axi_r(8'h10); while (!rd[0]) axi_r(8'h10);
        axi_w(8'h10, 32'h1);                   // clear STEP_DONE
        axi_r(8'h20); soc_t = rd[15:0]; st_t = rd[21:16];
        if (st_t !== t[5:0]) begin errors = errors + 1; $display("step tag %0d != %0d", st_t, t); end
        $fwrite(fd, "%0d,%04h\n", st_t, soc_t);
        // wait until core idle
        axi_r(8'h0C); while (rd[0]) axi_r(8'h0C);
    end
    axi_r(8'h24); $fwrite(fd, "SOH,%04h\n", rd[15:0]);
    axi_r(8'h1C); $display("CYCLES (last step) = %0d", rd);
    axi_r(8'h10); $display("IRQ_STAT = %h, irq pin = %b", rd, irq);
    $fclose(fd);

    // ---- 2) stream mode (input memory zeroed first, so the stream must provide the data) ----
    axi_w(8'h28, 2); axi_w(8'h2C, 32'h8000_0000); for (i = 0; i < 256; i = i + 1) axi_w(8'h30, 0);
    axi_w(8'h08, 32'h2);                       // CLEAR
    axi_r(8'h0C); while (rd[0]) axi_r(8'h0C);
    axi_w(8'h08, 32'h4);                       // STREAM_EN
    for (t = 0; t < 64; t = t + 1) begin
        @(negedge aclk); s_tdata = {m_in[t*4+3], m_in[t*4+2], m_in[t*4+1], m_in[t*4+0]}; s_tvalid = 1;
        @(posedge aclk); while (!s_tready) @(posedge aclk);
        @(negedge aclk); s_tvalid = 0;
        // random gap between beats
        repeat ($random(seed) & 7) @(negedge aclk);
    end
    // wait for the last result beat
    while (nb < 64) @(negedge aclk);
    repeat (10) @(negedge aclk);
    $fclose(fs);
    $display("tb_esn_axi_ip done, errors = %0d, stream beats = %0d", errors, nb);
    $finish;
end
initial begin #400000000; $display("TIMEOUT"); $finish; end
endmodule
