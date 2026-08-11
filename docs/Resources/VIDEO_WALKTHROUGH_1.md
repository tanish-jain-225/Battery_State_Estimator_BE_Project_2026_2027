[← Back to README](../README.md)

# Video Walkthrough Plan: 5-Minute Project Submission

**Project Title**: ESN-Based Battery SOC/SOH Estimation with Embedded Hardware Validation  
**Full Synchronized Script**: [`WALKTHROUGH_SCRIPT_1.md`](WALKTHROUGH_SCRIPT_1.md)  
**Total Target Duration**: 5 Minutes (300 Seconds)  

---

## ⏱️ Video Timeline & Screen Script

The script below aligns what is shown on screen with the synthesized narration audio and project slides:

| Time | Segment | Visual Action / Setup | Narration Script Focus |
| :---: | :--- | :--- | :--- |
| **0:00 - 0:30**<br>(30s) | **1. Title & Team** | Slide 1 featuring team: Sanjna Patankar, Akshay Nambiar, Satvik Verma, Tanish Sanghvi; Guide: Dr. Kadambari Sharma | Title, team members, VESIT Automation & Robotics department, and project scope. |
| **0:30 - 1:15**<br>(45s) | **2. Problem & Solution** | Slide 2 highlighting CC drift, EKF model complexity vs lightweight ESN reservoir computing | Why existing observers fall short, ESN proposed solution, software = final product, hardware = verification platform. |
| **1:15 - 2:15**<br>(60s) | **3. Phase 1 Completed** | Slide 3 showing completed software (2-RC, EKF, ESN, Flask, C99 CSR 6.7x speedup) & Verilog HDL (Q6.10, 100-neuron, Vivado/XSim 200/200 bit-exact match) | Completed software estimator + hardware RTL verification on ARTIX A7100T target. |
| **2:15 - 3:15**<br>(60s) | **4. Live Demos** | Browser split screen at `http://localhost:8000` (Physics Simulator) and `http://localhost:5000` (Visualiser Dashboard) | Dynamic telemetry generation, 3-line SOC tracking comparison (CC, EKF, ESN), thermal fault injection. |
| **3:15 - 4:15**<br>(60s) | **5. Phase 2 In Progress** | Slide 4 detailing online RLS adaptation, LSTM/GRU benchmark, EV drive cycles, and 5-stage FPGA sequence roadmap | Active software adaptation and FPGA sequence verification $u(0)\dots u(T)$ on ARTIX A7100T. |
| **4:15 - 5:00**<br>(45s) | **6. Phase 3 & Timeline** | Slide 5 showcasing final goal statement and milestone axis | Final goal, UART HIL testing, IEEE literature review paper (Aug 31), and thesis deadline (Nov 20). |

---

## 🎬 Tips for a High-Quality Video Recording

1. **Prerequisites Checklist**:
   * Make sure your physics engine database or local buffer is active.
   * Run `python software/visualiser/training/train_rc.py` and `python hardware/STM_Verifier/train_classifier.py` beforehand so all model files (`model_rc.pkl`, `esn_classifier_weights.h`) are up to date.
   * Execute `python hardware/FPGA_Verifier/compare_results.py` to confirm the 200/200 bit-exact Vivado/XSim verifier report is clean.
   * Open the dashboard browser (`http://localhost:5000`) and simulator (`http://localhost:8000`) in side-by-side windows.
2. **Narration Pacing**:
   * The total script is approximately **610 words**. Speaking at a moderate rate of 130 words per minute will leave around 45 seconds of buffer time for screen transitions and clicks.
3. **Screen Resolution**:
   * Set your screen resolution to `1920x1080` (1080p) and use comfortable font scaling so evaluation metrics, C99 code, and Verilog wave logs are clear.
