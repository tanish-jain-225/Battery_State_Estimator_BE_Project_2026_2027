"""
PDF Generator for Project Deliverables:
1. docs/Poster/Project_Poster.pdf
2. docs/Publications/Review_Paper.pdf
3. docs/Publications/Research_Paper.pdf
"""

import os
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

def add_header_footer(canvas_obj, doc, title_text, doc_type="MANUSCRIPT PREPRINT"):
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica-Bold", 8)
    canvas_obj.setFillColor(colors.HexColor("#4B5563"))
    canvas_obj.drawString(54, doc.pagesize[1] - 36, f"VESIT AUTOMATION & ROBOTICS / INSTRUMENTATION | {doc_type}")
    canvas_obj.drawRightString(doc.pagesize[0] - 54, doc.pagesize[1] - 36, "BE CAPSTONE 2026-2027")
    
    canvas_obj.setStrokeColor(colors.HexColor("#D1D5DB"))
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(54, doc.pagesize[1] - 42, doc.pagesize[0] - 54, doc.pagesize[1] - 42)
    canvas_obj.line(54, 45, doc.pagesize[0] - 54, 45)
    
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.drawString(54, 32, f"Target: IEEE / Scopus-Indexed Journal - {title_text[:60]}...")
    canvas_obj.drawRightString(doc.pagesize[0] - 54, 32, f"Page {canvas_obj._pageNumber}")
    canvas_obj.restoreState()

def build_poster_pdf(output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pagesize = landscape(A4)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=pagesize,
        leftMargin=28,
        rightMargin=28,
        topMargin=25,
        bottomMargin=25
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'PosterTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1E3A8A"),
        alignment=1
    )
    
    sub_title_style = ParagraphStyle(
        'PosterSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0D9488"),
        alignment=1
    )

    authors_style = ParagraphStyle(
        'PosterAuthors',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1F2937"),
        alignment=1
    )

    box_title_style = ParagraphStyle(
        'BoxTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#1E3A8A")
    )

    box_body_style = ParagraphStyle(
        'BoxBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.5,
        textColor=colors.HexColor("#1F2937")
    )
    
    story = []

    # Title Banner Block
    story.append(Paragraph("VIVEKANAND EDUCATION SOCIETY'S INSTITUTE OF TECHNOLOGY (VESIT)", sub_title_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph("Battery State Estimator: An ESN-Based Alternative to EKF and Coulomb Counting", title_style))
    story.append(Spacer(1, 3))
    authors_text = (
        "<b>Students:</b> Sanjna Patankar &bull; Akshay Nambiar &bull; Satvik Verma &bull; Tanish Sanghvi &nbsp;|&nbsp; "
        "<b>Guide:</b> Dr. Kadambari Sharma &nbsp;|&nbsp; <b>Coordinator:</b> Prof. Gopalakrishnan Narayanan<br/>"
        "<i>Department of Automation and Robotics / Instrumentation, Chembur, Mumbai - 400074</i>"
    )
    story.append(Paragraph(authors_text, authors_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceBefore=1, spaceAfter=8))

    # 4 Columns of Poster content
    col1_content = [
        Paragraph("<b>1. Problem & Motivation</b>", box_title_style),
        Spacer(1, 3),
        Paragraph(
            "&bull; <b>Coulomb Counting:</b> Drifts rapidly over time due to current integration errors, sensor bias, and zero-point offset.<br/>"
            "&bull; <b>Extended Kalman Filter:</b> High accuracy but relies on exact physics and suffers parameter drift under thermal variation.<br/>"
            "&bull; <b>Deep RNNs/LSTMs:</b> Require excessive compute, high SRAM, and floating-point power beyond low-cost edge automotive MCUs.<br/>"
            "&bull; <b>Target:</b> Develop an edge-capable Leaky-Integrator ESN combined with EKF state observers and Verilog RTL for real-time BMS.",
            box_body_style
        ),
        Spacer(1, 6),
        Paragraph("<b>2. 2-RC Electro-Thermal Physics</b>", box_title_style),
        Spacer(1, 3),
        Paragraph(
            "&bull; Models polarization voltages (V<sub>1</sub>, V<sub>2</sub>), ohmic resistance (R<sub>0</sub>), and dynamic capacity fade.<br/>"
            "&bull; <b>Arrhenius Law:</b> Parameters dynamically scale with cell temperature:<br/>"
            "&nbsp;&nbsp;<i>&theta;(T) = &theta;(T<sub>ref</sub>) &middot; exp[(E<sub>a</sub> / R<sub>gas</sub>)(1/T - 1/T<sub>ref</sub>)]</i><br/>"
            "&bull; Dual-timescale decoupled SOC/SOH observer design.",
            box_body_style
        )
    ]

    col2_content = [
        Paragraph("<b>3. Cyber-Physical Architecture</b>", box_title_style),
        Spacer(1, 3),
        Paragraph(
            "&bull; <b>Physics Simulator Service:</b> Microservice simulating 2-RC cell dynamics, Arrhenius thermal variation, and fault modes.<br/>"
            "&bull; <b>Observer Pipeline:</b> Joint EKF, Unscented Kalman Filter (UKF), and Leaky-Integrator Echo State Network (ESN).<br/>"
            "&bull; <b>Leaky Reservoir Dynamics:</b><br/>"
            "&nbsp;&nbsp;<i>x~<sub>t</sub> = tanh(W<sub>in</sub>[1; u<sub>t</sub>] + W<sub>res</sub>x<sub>t-1</sub>)</i><br/>"
            "&nbsp;&nbsp;<i>x<sub>t</sub> = (1 - &alpha;)x<sub>t-1</sub> + &alpha; x~<sub>t</sub></i><br/>"
            "&bull; Output trained via Ridge Regression (&lambda; regularization).",
            box_body_style
        ),
        Spacer(1, 6),
        Paragraph("<b>4. Edge Embedded C99 Optimization</b>", box_title_style),
        Spacer(1, 3),
        Paragraph(
            "&bull; <b>Compressed Sparse Row (CSR):</b> Stores only non-zero reservoir weights in row_ptr, col_idx, and val arrays.<br/>"
            "&bull; <b>Q15 Fixed-Point Math:</b> Replaces expensive float32 multiply-accumulate with 16-bit integer operations.<br/>"
            "&bull; <b>256-Entry LUT Tanh:</b> Piecewise linear interpolation eliminates floating-point transcendental functions.",
            box_body_style
        )
    ]

    col3_content = [
        Paragraph("<b>5. Xilinx Artix-7 FPGA RTL</b>", box_title_style),
        Spacer(1, 3),
        Paragraph(
            "&bull; <b>5-Stage Pipelined Architecture:</b> MAC &rarr; BIAS &rarr; SUM &rarr; TANH_IN &rarr; TANH_OUT.<br/>"
            "&bull; <b>Q6.10 Quantization:</b> 16-bit word length with 10 fractional bits for exact hardware-software parity.<br/>"
            "&bull; <b>BRAM Dual-Port Storage:</b> Input vector and state vector buffered in block RAM.<br/>"
            "&bull; <b>Bit-Exact Match:</b> 200/200 reservoir states match Python golden reference bit-for-bit (0 error).<br/>"
            "&bull; Target Device: Xilinx Artix-7 (xc7a100tcsg324-1) with 64-step NASA B0005 validation.",
            box_body_style
        ),
        Spacer(1, 6),
        Paragraph("<b>6. Comprehensive Test Suite</b>", box_title_style),
        Spacer(1, 3),
        Paragraph(
            "&bull; <b>62 Pytest Tests:</b> 100% pass across simulator, chemistry, ESN model, estimator pipeline, and Verilog RTL.<br/>"
            "&bull; <b>Regression Runner:</b> Automated 8-step verification on Windows (`.bat`) and Linux/macOS (`.sh`).",
            box_body_style
        )
    ]

    col4_content = [
        Paragraph("<b>7. Quantitative Results</b>", box_title_style),
        Spacer(1, 3),
        Paragraph(
            "<b>Key Hardware & Software Metrics:</b><br/>"
            "&bull; <b>Execution Speedup:</b> <b>6.7&times; faster</b> on ARM Cortex-M.<br/>"
            "&bull; <b>Flash Memory Savings:</b> <b>~10 KB saved</b> via CSR SpMV.<br/>"
            "&bull; <b>Thermal Safety Accuracy:</b> <b>98.40%</b> (Q15 fixed-point).<br/>"
            "&bull; <b>SOC Estimation RMSE:</b> <b>&lt; 0.80%</b> (0.00803).<br/>"
            "&bull; <b>SOH Estimation RMSE:</b> <b>5.73%</b> under aging cycles.",
            box_body_style
        ),
        Spacer(1, 6),
        Paragraph("<b>8. Live Demonstrations</b>", box_title_style),
        Spacer(1, 3),
        Paragraph(
            "&bull; <b>Visualiser Dashboard:</b><br/>"
            "&nbsp;&nbsp;<u>battery-visualizer.onrender.com</u><br/>"
            "&bull; <b>Physics Simulator:</b><br/>"
            "&nbsp;&nbsp;<u>battery-physics-simulator.onrender.com</u><br/>"
            "&bull; <b>GitHub Release v2.0.0:</b><br/>"
            "&nbsp;&nbsp;<u>github.com/tanish-jain-225/Battery_State_Estimator</u>",
            box_body_style
        )
    ]

    col_w = (doc.pagesize[0] - 56 - 24) / 4.0

    table_data = [[col1_content, col2_content, col3_content, col4_content]]
    
    col_table = Table(table_data, colWidths=[col_w, col_w, col_w, col_w])
    col_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F9FAFB")),
        ('BOX', (0,0), (0,0), 0.75, colors.HexColor("#CBD5E1")),
        ('BOX', (1,0), (1,0), 0.75, colors.HexColor("#CBD5E1")),
        ('BOX', (2,0), (2,0), 0.75, colors.HexColor("#CBD5E1")),
        ('BOX', (3,0), (3,0), 0.75, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(col_table)
    story.append(Spacer(1, 8))
    
    # Bottom Summary Notice
    banner_text = (
        "<b>VESIT Department of Automation & Robotics / Instrumentation &bull; Capstone Project 2026-2027 &bull; "
        "Evaluated for IEEE / Q3 Scopus-Indexed Publications (20 Marks Criterion)</b>"
    )
    banner_p = Paragraph(banner_text, ParagraphStyle(
        'Banner',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        textColor=colors.HexColor("#FFFFFF"),
        alignment=1
    ))
    banner_table = Table([[banner_p]], colWidths=[doc.pagesize[0] - 56])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#1E3A8A")),
        ('PADDING', (0,0), (-1,-1), 4),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(banner_table)

    doc.build(story)
    print(f"[SUCCESS] Built Project Poster PDF: {output_path}")

def build_review_paper_pdf(output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'PaperTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#111827"),
        alignment=1
    )

    authors_style = ParagraphStyle(
        'PaperAuthors',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#374151"),
        alignment=1
    )

    affil_style = ParagraphStyle(
        'PaperAffil',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#4B5563"),
        alignment=1
    )

    abstract_style = ParagraphStyle(
        'PaperAbstract',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1F2937")
    )

    h1_style = ParagraphStyle(
        'PaperH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'PaperBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#374151")
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("Neuromorphic Computing for Intelligent Battery Management Systems: A Comprehensive Review of Spiking Neural Networks, Reservoir Computing and Edge AI", title_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Sanjna Patankar, Akshay Nambiar, Satvik Verma, Tanish Sanghvi, and Kadambari Sharma</b>", authors_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph("Department of Automation and Robotics / Instrumentation, Vivekanand Education Society's Institute of Technology (VESIT), Mumbai, India<br/>Email: {2023.sanjna.patankar, 2023.akshay.nambiar, 2023.satvik.verma, 2023.tanish.sanghvi}@ves.ac.in", affil_style))
    story.append(Spacer(1, 6))

    # Target Venue Callout Box
    venue_text = (
        "<b>Target Publication:</b> IEEE Transactions / Q3 Scopus-Indexed Review Journal &nbsp;|&nbsp; "
        "<b>Status:</b> Camera-Ready / Publication Draft Placeholder &nbsp;|&nbsp; "
        "<b>Full Manuscript:</b> reference/review_paper.md (29 pages, 11 sections, 90+ citations)"
    )
    venue_p = Paragraph(venue_text, ParagraphStyle('VBox', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=colors.HexColor("#1E3A8A"), alignment=1))
    venue_table = Table([[venue_p]], colWidths=[doc.pagesize[0] - 108])
    venue_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#3B82F6")),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(venue_table)
    story.append(Spacer(1, 10))

    # Abstract Box
    abs_text = (
        "<b><i>Abstract</i></b>—Lithium-ion battery packs sit at the centre of electric vehicles and grid-scale energy storage. "
        "Every safety, control and prognostic function of a Battery Management System (BMS) depends on accurate, real-time estimates of "
        "State of Charge (SOC), State of Health (SOH), State of Power (SOP) and Remaining Useful Life (RUL), none of which can be measured directly. "
        "This review traces the field from classical model-based estimators (Coulomb counting, OCV mapping, ECMs, Kalman-filter variants) through "
        "conventional deep learning (RNNs, LSTMs, Transformers) to neuromorphic computing, Spiking Neural Networks (SNNs), reservoir computing, "
        "and Liquid State Machines (LSMs), together with the hardware (Intel Loihi 2, SpiNNaker2, BrainChip Akida, IBM TrueNorth, and FPGA platforms) "
        "and event-driven sensing schemes required to deploy them at the edge. A multi-dimensional benchmarking framework demonstrates that while neuromorphic "
        "paradigms achieve order-of-magnitude energy efficiency on sparse battery signals, standardized hardware benchmarking is the next critical milestone."
    )
    story.append(Paragraph(abs_text, abstract_style))
    story.append(Spacer(1, 4))
    kw_text = "<b><i>Keywords</i></b>—Battery Management System; State of Charge; State of Health; Spiking Neural Networks; Reservoir Computing; Liquid State Machine; Neuromorphic Hardware; Edge AI."
    story.append(Paragraph(kw_text, abstract_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#9CA3AF"), spaceBefore=1, spaceAfter=8))

    # Sections Overview
    story.append(Paragraph("I. EXECUTIVE SUMMARY & BENCHMARKING TAXONOMY", h1_style))
    story.append(Paragraph(
        "Modern BMS hardware is bounded by strict thermal envelopes, microampere quiescent currents, and low-cost microcontrollers. "
        "Traditional deep neural networks provide high predictive accuracy but their dense matrix-multiplication demands outstrip automotive MCU budgets. "
        "Neuromorphic computing offers event-driven, temporally native computation well suited for quasi-static battery sensor telemetry.",
        body_style
    ))
    story.append(Spacer(1, 6))

    # Benchmark Table
    bench_data = [
        ["Estimator Paradigm", "Typical Model", "Inference Energy", "MCU SRAM Footprint", "Dynamic Adaptability", "Edge Feasibility"],
        ["Classical Observer", "2-RC EKF / UKF", "~50 uJ", "< 4 KB", "Moderate (needs RLS)", "High (Production standard)"],
        ["Deep Learning", "LSTM / GRU / Transformer", "~5 mJ", "> 128 KB", "Low (needs retrain)", "Low (requires NPU/DSP)"],
        ["Spiking Neural Net", "LIF / Spike-Reservoir", "~5 uJ", "~16 KB", "Moderate (STDP)", "High on Neuromorphic ASIC"],
        ["Reservoir Computing", "Leaky-Integrator ESN", "~12 uJ", "< 12 KB (with CSR)", "High (Online Ridge/RLS)", "High on ARM Cortex-M/FPGA"]
    ]
    t = Table(bench_data, colWidths=[100, 110, 75, 80, 85, 85])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E3A8A")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 7),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 6.8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F8FAFC"), colors.white]),
        ('PADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    story.append(Paragraph("II. STRUCTURE OF THE COMPLETE REVIEW MANUSCRIPT", h1_style))
    sections_text = (
        "<b>Section 1:</b> Introduction & Academic Landscape &nbsp;|&nbsp; "
        "<b>Section 2:</b> BMS Estimation Tasks (SOC, SOH, SOP, RUL)<br/>"
        "<b>Section 3:</b> Classical Model-Based Estimators & Multi-Timescale Decoupling &nbsp;|&nbsp; "
        "<b>Section 4:</b> Conventional Deep Learning Architectures<br/>"
        "<b>Section 5:</b> Spiking Neural Networks for Battery Telemetry &nbsp;|&nbsp; "
        "<b>Section 6:</b> Reservoir Computing, Echo State Networks & LSMs<br/>"
        "<b>Section 7:</b> Neuromorphic Silicon Benchmarking (Loihi 2, SpiNNaker2, Akida, Artix-7) &nbsp;|&nbsp; "
        "<b>Section 8:</b> Event-Driven Asynchronous Sensing Schemes<br/>"
        "<b>Section 9:</b> Multi-Dimensional Benchmark & Radar Analysis &nbsp;|&nbsp; "
        "<b>Section 10:</b> Open Challenges & 5-Year Horizon &nbsp;|&nbsp; "
        "<b>Section 11:</b> Conclusion & Synthesis"
    )
    story.append(Paragraph(sections_text, body_style))
    story.append(Spacer(1, 8))

    # Verification Note
    note_text = (
        "<i>Note: The authoritative manuscript containing all mathematical formulations, 11 detailed sections, and complete reference bibliography "
        "is maintained in markdown format at <b>reference/review_paper.md</b>. This document serves as the formal IEEE preprint deliverable.</i>"
    )
    story.append(Paragraph(note_text, ParagraphStyle('Note', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=7.5, textColor=colors.HexColor("#6B7280"))))

    doc.build(story, onFirstPage=lambda c, d: add_header_footer(c, d, "Neuromorphic BMS Review Paper", "REVIEW ARTICLE PREPRINT"),
                    onLaterPages=lambda c, d: add_header_footer(c, d, "Neuromorphic BMS Review Paper", "REVIEW ARTICLE PREPRINT"))
    print(f"[SUCCESS] Built Review Paper PDF: {output_path}")

def build_research_paper_pdf(output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'PaperTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#111827"),
        alignment=1
    )

    authors_style = ParagraphStyle(
        'PaperAuthors',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#374151"),
        alignment=1
    )

    affil_style = ParagraphStyle(
        'PaperAffil',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#4B5563"),
        alignment=1
    )

    abstract_style = ParagraphStyle(
        'PaperAbstract',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1F2937")
    )

    h1_style = ParagraphStyle(
        'PaperH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#0D9488"),
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'PaperBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#374151")
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("Edge-Based Sparse Reservoir Computing and State Observers for Real-Time Battery Diagnostics in Cyber-Physical Systems", title_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Sanjna Patankar, Akshay Nambiar, Satvik Verma, Tanish Sanghvi, and Kadambari Sharma</b>", authors_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph("Department of Automation and Robotics / Instrumentation, VESIT, Chembur, Mumbai, India<br/>Email: {2023.sanjna.patankar, 2023.akshay.nambiar, 2023.satvik.verma, 2023.tanish.sanghvi}@ves.ac.in", affil_style))
    story.append(Spacer(1, 6))

    # Target Venue Callout Box
    venue_text = (
        "<b>Target Publication:</b> IEEE / Q3 Scopus-Indexed Journal on Industrial Electronics / Cyber-Physical Systems<br/>"
        "<b>Status:</b> Camera-Ready / Publication Draft Placeholder &nbsp;|&nbsp; "
        "<b>Full Manuscript:</b> reference/paper.md (Hardware/Software Co-Design & Experimental Benchmarks)"
    )
    venue_p = Paragraph(venue_text, ParagraphStyle('VBox', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=colors.HexColor("#0D9488"), alignment=1))
    venue_table = Table([[venue_p]], colWidths=[doc.pagesize[0] - 108])
    venue_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0FDFA")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#14B8A6")),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(venue_table)
    story.append(Spacer(1, 10))

    # Abstract Box
    abs_text = (
        "<b><i>Abstract</i></b>—Reliable estimation of State of Charge (SOC) and State of Health (SOH) in Lithium-Ion batteries is critical "
        "for electric vehicles (EVs) and smart grids. Traditional estimators, such as the Extended Kalman Filter (EKF), rely on high-fidelity physical models "
        "but degrade under unmodeled dynamics and cell aging. Conversely, deep recurrent neural networks present high computational costs that prevent edge deployment. "
        "This paper presents a co-designed cyber-physical system combining a 2-RC Equivalent Circuit Model (ECM) simulator, EKF state observers and Echo State Networks (ESNs) "
        "for state tracking. Additionally, we implement an optimized, edge-capable ESN classifier on an ARM Cortex-M microcontroller for thermal safety diagnostics. "
        "By introducing Compressed Sparse Row (CSR) sparse matrix-vector multiplication (SpMV) and fixed-point Q12/Q15 integer arithmetic with lookup table (LUT) "
        "linear interpolation, we achieve a <b>6.7&times; execution speedup</b> and save <b>~10 KB of Flash memory</b>, while maintaining classification accuracy at <b>98.40%</b> "
        "under dynamic drive cycles. An Artix-7 FPGA Verilog RTL pipeline achieves <b>200/200 bit-exact golden parity</b> with zero numerical deviation."
    )
    story.append(Paragraph(abs_text, abstract_style))
    story.append(Spacer(1, 4))
    kw_text = "<b><i>Keywords</i></b>—Battery state estimation; Extended Kalman Filter; Echo State Network; Reservoir Computing; Compressed Sparse Row; Fixed-Point Arithmetic; FPGA RTL; Cyber-Physical Systems."
    story.append(Paragraph(kw_text, abstract_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#9CA3AF"), spaceBefore=1, spaceAfter=8))

    # Quantitative Experimental Outcomes Table
    story.append(Paragraph("I. EXPERIMENTAL RESULTS & HARDWARE BENCHMARKS", h1_style))
    story.append(Paragraph(
        "The proposed cyber-physical framework was evaluated across synthetic 2-RC thermal stress cycles, real NASA B0005 aging datasets, and target edge microcontrollers.",
        body_style
    ))
    story.append(Spacer(1, 6))

    exp_data = [
        ["Benchmark Metric", "Baseline / Float32", "Optimized / Hardware Target", "Performance Improvement / Verification"],
        ["C99 ARM Cortex-M Speedup", "Dense Float32 (1.00x)", "CSR SpMV Q15 Fixed-Point", "6.7x Execution Acceleration"],
        ["Firmware Flash Memory Footprint", "13.4 KB (Dense Weights)", "3.2 KB (CSR Encoded)", "10.2 KB Flash Saved (~76% reduction)"],
        ["Thermal Safety Diagnostic Accuracy", "99.80% (Float32)", "98.40% (Q15 Fixed-Point)", "1.4% drop with 0 FPU dependency"],
        ["SOC Observer RMSE (Drive Cycles)", "EKF Baseline: 1.42%", "Decoupled ESN Observer: 0.80%", "43% Error Reduction"],
        ["Xilinx Artix-7 FPGA RTL Verification", "Python Golden Model", "5-Stage Pipelined Verilog RTL", "200/200 Bit-Exact States (0 Deviation)"],
        ["Automated Pytest Regression Suite", "N/A", "62 End-to-End Tests", "100% Pass Rate across all modules"]
    ]
    t = Table(exp_data, colWidths=[140, 125, 125, 145])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0D9488")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 7),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 6.8),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F0FDFA"), colors.white]),
        ('PADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    story.append(Paragraph("II. SYSTEM METHODOLOGY & PIPELINE OVERVIEW", h1_style))
    method_text = (
        "<b>1. Physics Simulation:</b> 2-RC ECM with dynamic Arrhenius thermal coupling and temperature-dependent internal impedance.<br/>"
        "<b>2. Multi-Timescale Observer:</b> Fast SOC state estimation via EKF decoupled from slow capacity fade tracking via RLS.<br/>"
        "<b>3. Sparse Leaky ESN:</b> Continuous-time leaky integrator reservoir with spectral radius tuning (&rho;=0.95, &alpha;=0.3).<br/>"
        "<b>4. Microcontroller Deployment:</b> Compressed Sparse Row (CSR) storage format with Q15 integer arithmetic and 256-word tanh LUT.<br/>"
        "<b>5. FPGA Accelerator:</b> Fully pipelined RTL on Xilinx Artix-7 processing sequential time-series inputs at zero float overhead."
    )
    story.append(Paragraph(method_text, body_style))
    story.append(Spacer(1, 8))

    # Verification Note
    note_text = (
        "<i>Note: The authoritative manuscript containing all mathematical proofs, ECM schematics, circuit figures, and code listings "
        "is maintained in markdown format at <b>reference/paper.md</b>. This document serves as the formal IEEE publication deliverable.</i>"
    )
    story.append(Paragraph(note_text, ParagraphStyle('Note', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=7.5, textColor=colors.HexColor("#6B7280"))))

    doc.build(story, onFirstPage=lambda c, d: add_header_footer(c, d, "Edge ESN Battery State Diagnostics Research Paper", "ORIGINAL RESEARCH PREPRINT"),
                    onLaterPages=lambda c, d: add_header_footer(c, d, "Edge ESN Battery State Diagnostics Research Paper", "ORIGINAL RESEARCH PREPRINT"))
    print(f"[SUCCESS] Built Research Paper PDF: {output_path}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    poster_pdf = os.path.join(base_dir, "docs", "Poster", "Project_Poster.pdf")
    review_pdf = os.path.join(base_dir, "docs", "Publications", "Review_Paper.pdf")
    research_pdf = os.path.join(base_dir, "docs", "Publications", "Research_Paper.pdf")
    
    # Also place copies in reference/ so navigation from either directory works seamlessly
    ref_review_pdf = os.path.join(base_dir, "reference", "Review_Paper.pdf")
    ref_research_pdf = os.path.join(base_dir, "reference", "Research_Paper.pdf")

    print("Building Project Poster PDF...")
    build_poster_pdf(poster_pdf)
    
    print("Building Review Paper PDF...")
    build_review_paper_pdf(review_pdf)
    build_review_paper_pdf(ref_review_pdf)
    
    print("Building Research Paper PDF...")
    build_research_paper_pdf(research_pdf)
    build_research_paper_pdf(ref_research_pdf)
    
    print("All 3 project PDF deliverables generated successfully!")

