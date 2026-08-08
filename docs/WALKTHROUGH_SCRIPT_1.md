[← Back to README](../README.md)

# 🎙️ Video Walkthrough Script (5-Minute Submission)

**Project Title**: ESN-Based Battery SOC/SOH Estimation with Embedded Hardware Validation  
**PDF Presentation Reference**: [`Review_1_PPT.pdf`](Presentations/Review_1_PPT.pdf)  
**Total Spoken Duration**: **300.00 seconds (5 minutes 0.00 seconds)**  
**Word Count**: **620 words**  
**Speech Rate**: **124 wpm** (Natural Academic Pace)  

---

## 📜 Segment-by-Segment Word-for-Word Script

### Segment 1: Title & Capstone Overview
- **Timestamp**: `0:00 - 0:30` (Duration: **30.00s**)
- **Visual Screen**: Slide 1 of [`Review_1_PPT.pdf`](Presentations/Review_1_PPT.pdf)
- **Narration**:
  > *"Good morning evaluators. Our project is titled ESN-Based Battery SOC/SOH Estimation with Embedded Hardware Validation, presented by Sanjna Patankar, Akshay Nambiar, Satvik Verma, and Tanish Sanghvi, guided by Dr. Kadambari Sharma in the Department of Automation and Robotics at VESIT, Mumbai. We combine a standalone software state estimator with embedded C99 and FPGA hardware verification."*

---

### Segment 2: Problem & Proposed Solution
- **Timestamp**: `0:30 - 1:15` (Duration: **45.00s**)
- **Visual Screen**: Slide 2 of [`Review_1_PPT.pdf`](Presentations/Review_1_PPT.pdf)
- **Narration**:
  > *"Existing observers face fundamental trade-offs: Coulomb Counting accumulates open-loop integration drift over time, while Extended Kalman Filters are model-dependent and computationally heavy for embedded microcontrollers. We propose a data-driven Echo State Network as a lightweight alternative. The software algorithm serves as our final estimator product, while C99 microcontrollers and ARTIX A7100T FPGA hardware form our verification platform."*

---

### Segment 3: Phase 1 — Completed Work & Hardware RTL Verification
- **Timestamp**: `1:15 - 2:15` (Duration: **60.00s**)
- **Visual Screen**: Slide 3 of [`Review_1_PPT.pdf`](Presentations/Review_1_PPT.pdf)
- **Narration**:
  > *"In Phase 1, we completed both software and hardware milestones. Our software pipeline includes a physics-based 2-RC battery simulator, EKF and Coulomb Counting baselines, ESN training workflows, a deployed Flask visualizer dashboard, and C99 firmware optimized with Compressed Sparse Row matrix compression for a six point seven times speedup. On hardware, we designed a Q6.10 fixed-point Verilog ESN RTL with a 100-neuron reservoir, hardware tanh LUT, and double-buffered state memory. In Vivado XSim simulations targeting the ARTIX A7100T FPGA, 200 out of 200 neuron updates matched our Python golden model bit-exactly."*

---

### Segment 4: Live Software Simulator & Dashboard Demonstration
- **Timestamp**: `2:15 - 3:15` (Duration: **60.00s**)
- **Visual Screen**: Browser split-screen at `http://localhost:8000` (Physics Engine) and `http://localhost:5000` (Visualiser Dashboard)
- **Narration**:
  > *"Demonstrating our live software system: at port eight thousand, our physics engine generates dynamic voltage, current, and temperature telemetry under simulated EV drive cycles. At port five thousand, our Visualiser Dashboard plots real-time State of Charge estimation. Notice how the Echo State Network tracks true SOC smoothly alongside Coulomb Counting and EKF baselines without integration drift or lag. When thermal faults are injected, diagnostic monitors instantly capture the anomaly."*

---

### Segment 5: Phase 2 — In Progress Work & FPGA Roadmap
- **Timestamp**: `3:15 - 4:15` (Duration: **60.00s**)
- **Visual Screen**: Slide 4 of [`Review_1_PPT.pdf`](Presentations/Review_1_PPT.pdf)
- **Narration**:
  > *"Phase 2 is currently in progress. On the software side, we are integrating online Recursive Least Squares readout adaptation to handle capacity fade, benchmarking against deep learning LSTM and GRU models, and evaluating dynamic EV drive cycles. On the hardware side, we are extending our verified single-step FPGA design to multi-timestep sequence inputs u(0) to u(T), conducting FPGA sequence verification on the ARTIX A7100T board, and building a UART Hardware-in-the-Loop interface."*

---

### Segment 6: Phase 3 — Final Goal, IEEE Target & Timeline
- **Timestamp**: `4:15 - 5:00` (Duration: **45.00s**)
- **Visual Screen**: Slide 5 of [`Review_1_PPT.pdf`](Presentations/Review_1_PPT.pdf)
- **Narration**:
  > *"Our final goal in Phase 3 is to deploy and validate our lightweight ESN estimator on embedded ARTIX A7100T hardware using real drive-cycle data. Our academic literature review paper is targeted for IEEE submission by August thirty-first. We will finalize ESN software by October fifteenth, complete hardware HIL validation by October twenty-fifth, and submit our capstone thesis by November twentieth, twenty twenty-six. Thank you."*
