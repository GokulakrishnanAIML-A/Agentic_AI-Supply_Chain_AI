import os
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    LOGO_PATH = "Screenshot 2026-09-28 234056.png"

    # Color Palette Definitions
    COLOR_PRIMARY = RGBColor(15, 23, 42)      # Deep Navy / Slate 900
    COLOR_SECONDARY = RGBColor(30, 58, 138)   # Blue 900
    COLOR_ACCENT = RGBColor(2, 132, 199)      # Sky 600
    COLOR_GOLD = RGBColor(217, 119, 6)        # Amber 600 / REC Gold
    COLOR_PURPLE = RGBColor(109, 40, 217)     # REC Purple
    COLOR_BG_LIGHT = RGBColor(248, 250, 252)  # Slate 50
    COLOR_CARD_BG = RGBColor(255, 255, 255)   # Pure White
    COLOR_CARD_BORDER = RGBColor(226, 232, 240)# Slate 200
    COLOR_TEXT_MAIN = RGBColor(15, 23, 42)    # Slate 900
    COLOR_TEXT_MUTED = RGBColor(71, 85, 105)  # Slate 600
    COLOR_TEXT_LIGHT = RGBColor(148, 163, 184)# Slate 400
    COLOR_SUCCESS = RGBColor(16, 185, 129)    # Emerald 500
    COLOR_TAG_BG = RGBColor(238, 242, 255)    # Indigo 50
    COLOR_TAG_TEXT = RGBColor(67, 56, 202)    # Indigo 700

    def add_blank_slide(bg_color=COLOR_BG_LIGHT):
        slide = prs.slides.add_slide(blank_layout)
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = bg_color
        bg.line.fill.background()
        return slide

    def add_header(slide, title, category="RAJALAKSHMI ENGINEERING COLLEGE", slide_num=1):
        # Top banner / tag
        tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(9.0), Inches(0.35))
        tf_tag = tag_box.text_frame
        tf_tag.word_wrap = True
        tf_tag.margin_left = tf_tag.margin_top = tf_tag.margin_right = tf_tag.margin_bottom = 0
        p_tag = tf_tag.paragraphs[0]
        p_tag.text = f"RAJALAKSHMI ENGINEERING COLLEGE  |  {category.upper()}"
        p_tag.font.size = Pt(10)
        p_tag.font.bold = True
        p_tag.font.color.rgb = COLOR_PURPLE

        # Slide Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(10.2), Inches(0.6))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_PRIMARY

        # Logo on top right
        if os.path.exists(LOGO_PATH):
            slide.shapes.add_picture(LOGO_PATH, Inches(11.8), Inches(0.35), height=Inches(0.95))

        # Thin divider line
        divider = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.4), Inches(11.733), Inches(0.02))
        divider.fill.solid()
        divider.fill.fore_color.rgb = COLOR_CARD_BORDER
        divider.line.fill.background()

        # Footer
        footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.733), Inches(0.3))
        tf_foot = footer_box.text_frame
        tf_foot.word_wrap = True
        tf_foot.margin_left = tf_foot.margin_top = tf_foot.margin_right = tf_foot.margin_bottom = 0
        p_foot = tf_foot.paragraphs[0]
        p_foot.text = f"SupplyChainAI: Autonomous Multi-Agent Supply Chain Optimization  |  Dept. of AIML, REC  |  Slide {slide_num}"
        p_foot.font.size = Pt(9)
        p_foot.font.color.rgb = COLOR_TEXT_LIGHT

    def add_card(slide, left, top, width, height, bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.2)
        return card

    def add_metric_badge(slide, left, top, width, height, value_text, label_text, subtext=None, border_color=COLOR_ACCENT):
        card = add_card(slide, left, top, width, height, bg_color=COLOR_CARD_BG, border_color=border_color)
        tb = slide.shapes.add_textbox(left + Inches(0.15), top + Inches(0.12), width - Inches(0.3), height - Inches(0.24))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        
        pv = tf.paragraphs[0]
        pv.text = value_text
        pv.font.size = Pt(22)
        pv.font.bold = True
        pv.font.color.rgb = border_color
        
        pl = tf.add_paragraph()
        pl.text = label_text
        pl.font.size = Pt(10)
        pl.font.bold = True
        pl.font.color.rgb = COLOR_TEXT_MAIN
        
        if subtext:
            ps = tf.add_paragraph()
            ps.text = subtext
            ps.font.size = Pt(8.5)
            ps.font.color.rgb = COLOR_TEXT_MUTED

    def add_table(slide, left, top, width, height, headers, rows, col_widths=None):
        table_shape = slide.shapes.add_table(len(rows) + 1, len(headers), left, top, width, height)
        table = table_shape.table
        
        if col_widths:
            for i, w in enumerate(col_widths):
                table.columns[i].width = w

        # Format Headers
        for i, header in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = header
            cell.fill.solid()
            cell.fill.fore_color.rgb = COLOR_PRIMARY
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(10.5)
                p.font.bold = True
                p.font.color.rgb = RGBColor(255, 255, 255)
                p.alignment = PP_ALIGN.CENTER
        
        # Format Data Rows
        for r_idx, row in enumerate(rows):
            fill_color = COLOR_CARD_BG if r_idx % 2 == 0 else RGBColor(241, 245, 249)
            for c_idx, val in enumerate(row):
                cell = table.cell(r_idx + 1, c_idx)
                cell.text = str(val)
                cell.fill.solid()
                cell.fill.fore_color.rgb = fill_color
                for p in cell.text_frame.paragraphs:
                    p.font.size = Pt(9.5)
                    p.font.color.rgb = COLOR_TEXT_MAIN
                    if c_idx == 0:
                        p.font.bold = True
                    if c_idx >= 2:
                        p.alignment = PP_ALIGN.CENTER

    # =========================================================================
    # SLIDE 1 — TITLE SLIDE
    # =========================================================================
    slide1 = add_blank_slide(bg_color=RGBColor(15, 23, 42)) # Deep Navy
    
    # Place College Logo Centered / Prominent
    if os.path.exists(LOGO_PATH):
        slide1.shapes.add_picture(LOGO_PATH, Inches(5.95), Inches(0.65), height=Inches(1.4))

    # College Name
    tb = slide1.shapes.add_textbox(Inches(1.0), Inches(2.15), Inches(11.333), Inches(0.7))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "RAJALAKSHMI ENGINEERING COLLEGE"
    p.alignment = PP_ALIGN.CENTER
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)

    p2 = tf.add_paragraph()
    p2.text = "An Autonomous Institution | Affiliated to Anna University, Chennai"
    p2.alignment = PP_ALIGN.CENTER
    p2.font.size = Pt(11)
    p2.font.color.rgb = COLOR_GOLD

    # Project Title
    tb_title = slide1.shapes.add_textbox(Inches(1.2), Inches(3.0), Inches(10.933), Inches(1.3))
    tf_title = tb_title.text_frame
    tf_title.word_wrap = True
    p_t = tf_title.paragraphs[0]
    p_t.text = "SUPPLYCHAINAI: AN AUTONOMOUS MULTI-AGENT SYSTEM FOR RESILIENT SUPPLY CHAIN RE-PLANNING AND PROCUREMENT OPTIMIZATION"
    p_t.alignment = PP_ALIGN.CENTER
    p_t.font.size = Pt(21)
    p_t.font.bold = True
    p_t.font.color.rgb = RGBColor(56, 189, 248) # Cyan

    p_sub = tf_title.add_paragraph()
    p_sub.text = "Final Year Project Presentation  •  Academic Year: 2025–2026"
    p_sub.alignment = PP_ALIGN.CENTER
    p_sub.font.size = Pt(13)
    p_sub.font.color.rgb = RGBColor(226, 232, 240)

    # 2 Bottom Cards: Presented By & Guided By
    # Left Card: Presented By
    c1 = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.5), Inches(4.5), Inches(4.9), Inches(2.2))
    c1.fill.solid()
    c1.fill.fore_color.rgb = RGBColor(30, 41, 59)
    c1.line.color.rgb = RGBColor(51, 65, 85)
    tb_c1 = slide1.shapes.add_textbox(Inches(1.7), Inches(4.65), Inches(4.5), Inches(1.9))
    tf_c1 = tb_c1.text_frame
    tf_c1.word_wrap = True
    p = tf_c1.paragraphs[0]
    p.text = "PRESENTED BY"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_GOLD

    items_c1 = [
        "• Student Name: [Student Name 1]   (Reg. No: [Register Number 1])",
        "• Student Name: [Student Name 2]   (Reg. No: [Register Number 2])",
        "• Student Name: [Student Name 3]   (Reg. No: [Register Number 3])",
        "Department of Artificial Intelligence and Machine Learning"
    ]
    for it in items_c1:
        pi = tf_c1.add_paragraph()
        pi.text = it
        pi.font.size = Pt(10)
        pi.font.color.rgb = RGBColor(241, 245, 249)

    # Right Card: Guided By
    c2 = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.933), Inches(4.5), Inches(4.9), Inches(2.2))
    c2.fill.solid()
    c2.fill.fore_color.rgb = RGBColor(30, 41, 59)
    c2.line.color.rgb = RGBColor(51, 65, 85)
    tb_c2 = slide1.shapes.add_textbox(Inches(7.133), Inches(4.65), Inches(4.5), Inches(1.9))
    tf_c2 = tb_c2.text_frame
    tf_c2.word_wrap = True
    p = tf_c2.paragraphs[0]
    p.text = "GUIDED BY"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_GOLD

    items_c2 = [
        "• [Guide Name]",
        "• [Designation / Assistant Professor]",
        "• Department of Artificial Intelligence and Machine Learning",
        "Rajalakshmi Engineering College, Thandalam, Chennai - 602 105"
    ]
    for it in items_c2:
        pi = tf_c2.add_paragraph()
        pi.text = it
        pi.font.size = Pt(10)
        pi.font.color.rgb = RGBColor(241, 245, 249)

    # =========================================================================
    # SLIDE 2 — PROJECT OVERVIEW
    # =========================================================================
    slide2 = add_blank_slide()
    add_header(slide2, "Project Overview", category="Executive Summary", slide_num=2)

    # 4 Structured Overview Cards (2x2 Grid)
    w_card = Inches(5.65)
    h_card = Inches(2.55)
    
    # Card 1: Domain & Problem
    add_card(slide2, Inches(0.8), Inches(1.6), w_card, h_card)
    tb = slide2.shapes.add_textbox(Inches(1.0), Inches(1.75), w_card - Inches(0.4), h_card - Inches(0.3))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "DOMAIN & CHALLENGE ADDRESSED"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY
    
    bullets = [
        "• Domain: Supply Chain Management, Operations Research & Agentic AI.",
        "• Core Challenge: Vulnerability of multi-echelon supply networks to sudden disruptions (supplier factory outages, port delays, demand spikes).",
        "• Critical Bottleneck: Legacy ERP systems rely on static safety buffers and batch logic; manual recovery takes 4 to 24 hours."
    ]
    for b in bullets:
        p_b = tf.add_paragraph()
        p_b.text = b
        p_b.font.size = Pt(10)
        p_b.font.color.rgb = COLOR_TEXT_MAIN

    # Card 2: Proposed Technology
    add_card(slide2, Inches(6.85), Inches(1.6), w_card, h_card)
    tb = slide2.shapes.add_textbox(Inches(7.05), Inches(1.75), w_card - Inches(0.4), h_card - Inches(0.3))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "PROPOSED AGENTIC AI ARCHITECTURE"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY
    
    bullets = [
        "• StateGraph Multi-Agent Orchestration: LangGraph state machine coordinating 5 specialized autonomous agents with cyclic replanning.",
        "• Deterministic Optimization: Google OR-Tools Mixed-Integer Linear Programming (MILP) guaranteeing mathematical cost optimality.",
        "• Hybrid Agentic RAG: Dense vector search (pgvector) + BM25 keyword matching fused via Reciprocal Rank Fusion (RRF) over contracts."
    ]
    for b in bullets:
        p_b = tf.add_paragraph()
        p_b.text = b
        p_b.font.size = Pt(10)
        p_b.font.color.rgb = COLOR_TEXT_MAIN

    # Card 3: Main Objective
    add_card(slide2, Inches(0.8), Inches(4.35), w_card, h_card)
    tb = slide2.shapes.add_textbox(Inches(1.0), Inches(4.5), w_card - Inches(0.4), h_card - Inches(0.3))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "PRIMARY PROJECT OBJECTIVE"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY
    
    bullets = [
        "• Autonomous Closed-Loop Re-Planning: Detect supply chain anomalies, evaluate impacts, retrieve legal SLA constraints, and optimize procurement orders without human latency.",
        "• Elimination of AI Hallucinations: Completely decouple qualitative reasoning from numerical budgeting to guarantee 100% constraint adherence."
    ]
    for b in bullets:
        p_b = tf.add_paragraph()
        p_b.text = b
        p_b.font.size = Pt(10)
        p_b.font.color.rgb = COLOR_TEXT_MAIN

    # Card 4: Key Validated Outcomes
    add_card(slide2, Inches(6.85), Inches(4.35), w_card, h_card)
    tb = slide2.shapes.add_textbox(Inches(7.05), Inches(4.5), w_card - Inches(0.4), h_card - Inches(0.3))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "KEY VALIDATED OUTCOMES"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY
    
    bullets = [
        "• Sub-Second Latency: 125 ms re-planning time for 10,000 units across 7 global suppliers; emergency rerouting executed in 71 ms.",
        "• 100% Constraint Compliance: Zero capacity violations or minimum order quantity (MOQ) breaches across all benchmark scenarios.",
        "• Comprehensive Verification: 19/19 passing automated Pytest tests validating multi-agent state transitions, solver, and RAG grounding."
    ]
    for b in bullets:
        p_b = tf.add_paragraph()
        p_b.text = b
        p_b.font.size = Pt(10)
        p_b.font.color.rgb = COLOR_TEXT_MAIN

    # =========================================================================
    # SLIDE 3 — 1. INTRODUCTION
    # =========================================================================
    slide3 = add_blank_slide()
    add_header(slide3, "1. Introduction: Background & Technological Motivation", category="Introduction", slide_num=3)

    # Left Column: Motivation and Context
    add_card(slide3, Inches(0.8), Inches(1.6), Inches(5.65), Inches(5.2))
    tb = slide3.shapes.add_textbox(Inches(1.0), Inches(1.75), Inches(5.25), Inches(4.9))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "GLOBAL SUPPLY CHAIN VULNERABILITIES"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY
    
    bullets = [
        "• Scale & Criticality: Modern manufacturing and distribution networks manage trillions in global trade across interdependent multi-tier supply networks.",
        "• Fragility Under Shocks: Geopolitical friction, maritime chokepoints (Red Sea, Panama Canal), and extreme weather trigger severe lead-time inflation and factory stockouts.",
        "• The High Cost of Latency: Unplanned industrial downtime costs large manufacturers up to $22,000 per minute; stockouts permanently degrade enterprise customer loyalty.",
        "• Siloed Data Infrastructure: Enterprise data is fractured across isolated WMS, ERP, and TMS systems, preventing holistic end-to-end visibility.",
        "• Failure of Static Rules: Fixed buffer inventory and heuristic safety thresholds are incapable of dynamically reallocating volume during compounding disruptions."
    ]
    for b in bullets:
        p_b = tf.add_paragraph()
        p_b.text = b
        p_b.font.size = Pt(9.5)
        p_b.font.color.rgb = COLOR_TEXT_MAIN

    # Right Column: Visual Paradigm Shift
    add_card(slide3, Inches(6.85), Inches(1.6), Inches(5.65), Inches(5.2))
    tb_r = slide3.shapes.add_textbox(Inches(7.05), Inches(1.75), Inches(5.25), Inches(4.9))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True
    p = tf_r.paragraphs[0]
    p.text = "TECHNOLOGICAL PARADIGM TRANSITION"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_PURPLE

    stages = [
        ("STAGE 1: TRADITIONAL ERP & HEURISTICS", "Batch nightly runs, static reorder points, hardcoded threshold alerts. Zero predictive reasoning or external market adaptability."),
        ("STAGE 2: GENERATIVE AI & CHATBOTS", "Natural language query synthesis and report summaries. However, prone to hallucinated arithmetic, contract inaccuracies, and zero execution control."),
        ("STAGE 3: DISCONNECTED AI AGENTS", "Isolated single-prompt agents with tool calling. Lack stateful memory, cyclic self-correction, or multi-echelon coordination."),
        ("STAGE 4: AGENTIC AI (SUPPLYCHAINAI)", "StateGraph multi-agent orchestration combining LLM semantic reasoning with deterministic MILP solvers, hybrid RAG, and Human-in-the-Loop governance.")
    ]
    for title_s, desc_s in stages:
        p_st = tf_r.add_paragraph()
        p_st.text = title_s
        p_st.font.size = Pt(10)
        p_st.font.bold = True
        p_st.font.color.rgb = COLOR_PRIMARY
        p_sd = tf_r.add_paragraph()
        p_sd.text = desc_s
        p_sd.font.size = Pt(8.5)
        p_sd.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 4 — NEED FOR AGENTIC AI
    # =========================================================================
    slide4 = add_blank_slide()
    add_header(slide4, "Need for Agentic AI in Enterprise Supply Networks", category="System Rationale", slide_num=4)

    # Evolution Diagram along top (4 chevron/card steps)
    steps = [
        ("Traditional AI", "Static Heuristics\nBatch ERP\nFixed Buffers", COLOR_TEXT_MUTED),
        ("Generative AI", "Text Completion\nSummary Chatbots\nProne to Hallucination", COLOR_SECONDARY),
        ("AI Agents", "Prompted Tool Calling\nIsolated Execution\nNo Reflexive Loop", COLOR_PURPLE),
        ("Agentic AI", "Stateful Orchestration\nMILP Exact Solvers\nClosed-Loop Self-Repair", COLOR_ACCENT)
    ]
    card_w = Inches(2.7)
    for i, (st, desc, col) in enumerate(steps):
        left_pos = Inches(0.8 + i * 2.95)
        add_card(slide4, left_pos, Inches(1.6), card_w, Inches(1.4), border_color=col)
        tb = slide4.shapes.add_textbox(left_pos + Inches(0.1), Inches(1.7), card_w - Inches(0.2), Inches(1.2))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"Step {i+1}: {st}"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = col
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(8.5)
        p2.font.color.rgb = COLOR_TEXT_MAIN

    # Bottom Area: 3 Core Pillars of Agentic Value
    pillars = [
        ("AUTONOMOUS DECOMPOSITION", [
            "• Complex Problem Formulation: Translates ambiguous real-world alerts ('Red Sea route closed') into structured operational sub-tasks.",
            "• Dynamic Specialist Dispatch: Dispatches inventory, supplier risk, and logistics sub-problems concurrently.",
            "• Context Preservation: StateGraph retains intermediate hypotheses across execution turns."
        ]),
        ("DETERMINISTIC TOOL SYNERGY", [
            "• Neuro-Symbolic Decoupling: Offloads mathematical calculations entirely to Google OR-Tools CBC/SCIP solvers.",
            "• Zero Hallucination: Quantities, unit costs, and delivery dates are mathematically guaranteed.",
            "• Real-Time Enterprise DB Access: Interrogates live inventory levels and supplier quotas on demand."
        ]),
        ("REFLECTIVE SELF-CORRECTION", [
            "• Constraint Validation: Evaluator agent audits proposed plans against business SLAs before approval.",
            "• Automated Cyclic Recovery: If capacity is exceeded, state loops back to re-plan with updated bounds.",
            "• Human-in-the-Loop Gate: Presents auditable, explainable mitigation proposals for one-click human sign-off."
        ])
    ]
    w_p = Inches(3.7)
    for i, (title_p, items_p) in enumerate(pillars):
        left_pos = Inches(0.8 + i * 3.95)
        add_card(slide4, left_pos, Inches(3.25), w_p, Inches(3.6))
        tb = slide4.shapes.add_textbox(left_pos + Inches(0.15), Inches(3.4), w_p - Inches(0.3), Inches(3.3))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_p
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = COLOR_SECONDARY
        for it in items_p:
            pi = tf.add_paragraph()
            pi.text = it
            pi.font.size = Pt(9)
            pi.font.color.rgb = COLOR_TEXT_MAIN

    # =========================================================================
    # SLIDE 5 — PROJECT OBJECTIVES
    # =========================================================================
    slide5 = add_blank_slide()
    add_header(slide5, "Project Objectives: Engineering an Autonomous Framework", category="Objectives", slide_num=5)

    objectives = [
        ("1. Multi-Agent Orchestration Engine",
         "Design and implement a coordinated multi-agent architecture using LangGraph StateGraph, featuring dedicated specialist agents for Inventory Analysis, Supplier Risk Assessment, Logistics Routing, and Procurement Re-Planning.",
         COLOR_PURPLE),
        ("2. Mathematical Optimization Integration",
         "Decouple qualitative natural language reasoning from numerical allocation by embedding Google OR-Tools Mixed-Integer Linear Programming (MILP) to guarantee mathematically optimal, least-cost procurement under capacity constraints.",
         COLOR_SECONDARY),
        ("3. Hybrid Agentic RAG Knowledge Pipeline",
         "Construct a dual-stream retrieval-augmented generation pipeline combining 768-dimensional dense vector embeddings (pgvector) and sparse BM25 lexical search fused via Reciprocal Rank Fusion (RRF) over supplier contracts and SOPs.",
         COLOR_ACCENT),
        ("4. Interactive Disruption Sandbox (What-If)",
         "Build an interactive simulation engine allowing supply chain managers to inject synthetic disruptions (supplier plant shutdowns, maritime route blocks, tariff spikes) and evaluate sub-second mitigation re-plans.",
         COLOR_GOLD),
        ("5. Enterprise Governance & Auditability",
         "Enforce a Human-in-the-Loop (HITL) approval gate and immutable JSON decision logging to ensure all automated actions maintain zero-hallucination compliance, full transparency, and audit readiness.",
         COLOR_SUCCESS)
    ]

    for i, (title_o, desc_o, col_o) in enumerate(objectives):
        top_pos = Inches(1.6 + i * 1.05)
        add_card(slide5, Inches(0.8), top_pos, Inches(11.733), Inches(0.95), border_color=col_o)
        
        # Number badge on left
        badge = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.95), top_pos + Inches(0.15), Inches(0.65), Inches(0.65))
        badge.fill.solid()
        badge.fill.fore_color.rgb = col_o
        badge.line.fill.background()
        tf_b = badge.text_frame
        p_b = tf_b.paragraphs[0]
        p_b.text = f"0{i+1}"
        p_b.font.size = Pt(13)
        p_b.font.bold = True
        p_b.font.color.rgb = RGBColor(255, 255, 255)
        p_b.alignment = PP_ALIGN.CENTER

        # Text box
        tb = slide5.shapes.add_textbox(Inches(1.75), top_pos + Inches(0.08), Inches(10.6), Inches(0.8))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_o
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = COLOR_PRIMARY
        p2 = tf.add_paragraph()
        p2.text = desc_o
        p2.font.size = Pt(9)
        p2.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 6 — 2. PROBLEM STATEMENT & BUSINESS CASE
    # =========================================================================
    slide6 = add_blank_slide()
    add_header(slide6, "2. Problem Statement & Business Case", category="Problem & Business Case", slide_num=6)

    # 3-Stage Visual Flow across middle: Problem -> Impact -> Proposed Direction
    w_flow = Inches(3.7)
    h_flow = Inches(4.8)
    
    # Box 1: Core Problem
    add_card(slide6, Inches(0.8), Inches(1.6), w_flow, h_flow, border_color=RGBColor(239, 68, 68))
    tb1 = slide6.shapes.add_textbox(Inches(0.95), Inches(1.75), w_flow - Inches(0.3), h_flow - Inches(0.3))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "CORE PROBLEM"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = RGBColor(239, 68, 68)
    
    pts1 = [
        "• Extreme Fragility: Multi-tier supply chains lack real-time visibility into tier-1 and tier-2 vendor dependencies.",
        "• Static Buffer Failure: Conventional safety stock rules assume normal distributions, failing catastrophically under 'black swan' disruptions.",
        "• Data Fragmentation: Inventory counts, vendor risk, and transit updates reside in disconnected enterprise silos.",
        "• Hallucination Risk: Generative AI cannot be used raw due to arithmetic errors and unverified contract interpretations."
    ]
    for pt in pts1:
        p_pt = tf1.add_paragraph()
        p_pt.text = pt
        p_pt.font.size = Pt(9.5)
        p_pt.font.color.rgb = COLOR_TEXT_MAIN

    # Box 2: Enterprise Impact
    add_card(slide6, Inches(4.8), Inches(1.6), w_flow, h_flow, border_color=COLOR_GOLD)
    tb2 = slide6.shapes.add_textbox(Inches(4.95), Inches(1.75), w_flow - Inches(0.3), h_flow - Inches(0.3))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    p = tf2.paragraphs[0]
    p.text = "ENTERPRISE & BUSINESS IMPACT"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_GOLD
    
    pts2 = [
        "• Severe Financial Losses: Unplanned plant downtime costs automotive and tech firms $22,000+ per minute ($1.3M/hr).",
        "• Manual Triage Latency: Planners spend 4 to 24 hours manually consolidating spreadsheets, causing stockouts.",
        "• Premium Freight Penalties: Reactive expediting via air freight inflates logistics costs by up to 300%.",
        "• Contractual Breach: Unnoticed SLA terms and missed force majeure clauses lead to unrecovered vendor penalties."
    ]
    for pt in pts2:
        p_pt = tf2.add_paragraph()
        p_pt.text = pt
        p_pt.font.size = Pt(9.5)
        p_pt.font.color.rgb = COLOR_TEXT_MAIN

    # Box 3: Proposed Direction
    add_card(slide6, Inches(8.8), Inches(1.6), w_flow, h_flow, border_color=COLOR_SUCCESS)
    tb3 = slide6.shapes.add_textbox(Inches(8.95), Inches(1.75), w_flow - Inches(0.3), h_flow - Inches(0.3))
    tf3 = tb3.text_frame
    tf3.word_wrap = True
    p = tf3.paragraphs[0]
    p.text = "PROPOSED AGENTIC DIRECTION"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_SUCCESS
    
    pts3 = [
        "• Autonomous Multi-Agent Triaging: Continuous background anomaly monitoring and automatic goal decomposition.",
        "• Neuro-Symbolic Optimization: Coupling LLM semantic reasoning with Google OR-Tools MILP for exact cost-optimal allocation.",
        "• Grounded Legal RAG: Hybrid pgvector + BM25 search directly quoting verified contractual clauses and lead times.",
        "• Human-Governed Execution: Sub-second re-planning with human-in-the-loop oversight and audit logs."
    ]
    for pt in pts3:
        p_pt = tf3.add_paragraph()
        p_pt.text = pt
        p_pt.font.size = Pt(9.5)
        p_pt.font.color.rgb = COLOR_TEXT_MAIN

    # Bottom summary pill
    add_card(slide6, Inches(0.8), Inches(6.55), Inches(11.733), Inches(0.4), bg_color=COLOR_PRIMARY)
    tb_b = slide6.shapes.add_textbox(Inches(1.0), Inches(6.58), Inches(11.333), Inches(0.3))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.text = "Key Value: SupplyChainAI converts hours of stressful manual spreadsheet firefighting into sub-second, mathematically verified decisions."
    p_b.font.size = Pt(9.5)
    p_b.font.bold = True
    p_b.font.color.rgb = RGBColor(255, 255, 255)
    p_b.alignment = PP_ALIGN.CENTER

    # =========================================================================
    # SLIDE 7 — 3. USER & STAKEHOLDER ANALYSIS
    # =========================================================================
    slide7 = add_blank_slide()
    add_header(slide7, "3. User and Stakeholder Analysis", category="Stakeholders", slide_num=7)

    # Top: Target Users (3 cards)
    users = [
        ("Supply Chain Planners", "Require instantaneous disruption triage, inventory health monitoring, and interactive 'What-If' scenario simulation without manual spreadsheet crunching."),
        ("Procurement Officers", "Require automated multi-supplier cost optimization, contract SLA verification, minimum order quantity compliance, and dynamic order generation."),
        ("Logistics Coordinators", "Need real-time transit delay monitoring, alternative carrier/route discovery, and multi-modal freight cost evaluation during chokepoint failures.")
    ]
    w_u = Inches(3.7)
    for i, (u_title, u_desc) in enumerate(users):
        left_pos = Inches(0.8 + i * 3.95)
        add_card(slide7, left_pos, Inches(1.6), w_u, Inches(1.5), border_color=COLOR_SECONDARY)
        tb = slide7.shapes.add_textbox(left_pos + Inches(0.15), Inches(1.7), w_u - Inches(0.3), Inches(1.3))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = u_title
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = COLOR_SECONDARY
        p2 = tf.add_paragraph()
        p2.text = u_desc
        p2.font.size = Pt(8.5)
        p2.font.color.rgb = COLOR_TEXT_MAIN

    # Bottom: Stakeholder Analysis Table
    headers = ["Stakeholder Group", "Organizational Role", "Core Responsibility & Impact", "System Value Delivered"]
    rows = [
        ["VP of Supply Chain", "Executive Sponsor", "Global supply chain resilience, risk governance, and working capital optimization.", "Real-time enterprise visibility and guaranteed minimal landed cost during crises."],
        ["Procurement Director", "Core Operational User", "Vendor relationship management, supplier quota allocation, contract negotiations.", "Automated optimal order splits complying 100% with vendor capacity & SLAs."],
        ["Logistics Manager", "Operational User", "Freight carrier assignment, port transit monitoring, warehouse stock reception.", "Rapid alternative routing mitigating maritime and road transportation delays."],
        ["Enterprise IT / SecOps", "System Gatekeeper", "Data governance, API security, ERP system integration, compliance auditability.", "Air-gapped on-premise container deployment with immutable cryptographic JSON logs."]
    ]
    col_widths = [Inches(2.2), Inches(2.0), Inches(4.3), Inches(3.233)]
    add_table(slide7, Inches(0.8), Inches(3.35), Inches(11.733), Inches(3.4), headers, rows, col_widths)

    # =========================================================================
    # SLIDE 8 — USER REQUIREMENTS
    # =========================================================================
    slide8 = add_blank_slide()
    add_header(slide8, "System Requirements: Functional & Non-Functional Specifications", category="Requirements", slide_num=8)

    w_col = Inches(5.65)
    h_col = Inches(5.2)

    # Left Card: Functional Requirements
    add_card(slide8, Inches(0.8), Inches(1.6), w_col, h_col, border_color=COLOR_SECONDARY)
    tb_fr = slide8.shapes.add_textbox(Inches(1.0), Inches(1.75), w_col - Inches(0.4), h_col - Inches(0.3))
    tf_fr = tb_fr.text_frame
    tf_fr.word_wrap = True
    p = tf_fr.paragraphs[0]
    p.text = "FUNCTIONAL REQUIREMENTS (FR)"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY

    fr_items = [
        ("FR-1: Multi-Echelon Data Ingestion", "Ingest real-time stock levels, supplier capacity bounds, lead times, and transit status across 10 SKUs, 7 suppliers, and 4 hubs."),
        ("FR-2: Disruption Detection & Classification", "Perceive anomalies (supplier shutdowns, lead time spikes) and categorize risk severity within 500 ms."),
        ("FR-3: Deterministic MILP Procurement", "Execute Mixed-Integer Linear Programming to compute cost-optimal order quantities strictly respecting capacity limits and MOQs."),
        ("FR-4: Hybrid RAG Contract Extraction", "Retrieve relevant legal clauses, lead time penalties, and SLAs using pgvector dense search + BM25 keyword matching with verifiable citations."),
        ("FR-5: What-If Simulation Sandbox", "Enable dynamic parameter overriding (supplier offline, lead time multiplier) to stress-test resilience in real time."),
        ("FR-6: Human-in-the-Loop Approval Gate", "Enforce manager approval workflows and log all decisions into tamper-evident JSON audit trails.")
    ]
    for title_f, desc_f in fr_items:
        pf = tf_fr.add_paragraph()
        pf.text = f"• {title_f}: {desc_f}"
        pf.font.size = Pt(8.5)
        pf.font.color.rgb = COLOR_TEXT_MAIN

    # Right Card: Non-Functional Requirements
    add_card(slide8, Inches(6.85), Inches(1.6), w_col, h_col, border_color=COLOR_PURPLE)
    tb_nfr = slide8.shapes.add_textbox(Inches(7.05), Inches(1.75), w_col - Inches(0.4), h_col - Inches(0.3))
    tf_nfr = tb_nfr.text_frame
    tf_nfr.word_wrap = True
    p = tf_nfr.paragraphs[0]
    p.text = "NON-FUNCTIONAL REQUIREMENTS (NFR)"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_PURPLE

    nfr_items = [
        ("NFR-1: Real-Time Performance & Latency", "End-to-end multi-agent re-planning must complete in under 2.0 seconds (empirically achieved: 125 ms baseline, 71 ms emergency replan)."),
        ("NFR-2: Zero Hallucination & Determinism", "100% mathematical constraint satisfaction; numerical allocations must be computed by external solvers, completely eliminating LLM arithmetic errors."),
        ("NFR-3: Enterprise Scalability", "Horizontally scalable stateless microservices using Docker containers and PostgreSQL pgvector with HNSW index for sub-10ms vector querying."),
        ("NFR-4: Security & Compliance", "Role-Based Access Control (RBAC), TLS 1.3 encrypted data transmission, and on-premise air-gapped deployment capability."),
        ("NFR-5: Usability & Interpretability", "Modern, responsive React 18 dashboard featuring interactive risk heatmaps, thought stream visualization, and natural language copilot interaction.")
    ]
    for title_n, desc_n in nfr_items:
        pn = tf_nfr.add_paragraph()
        pn.text = f"• {title_n}: {desc_n}"
        pn.font.size = Pt(8.5)
        pn.font.color.rgb = COLOR_TEXT_MAIN

    # =========================================================================
    # SLIDE 9 — 4. PROPOSED AGENTIC AI SOLUTION
    # =========================================================================
    slide9 = add_blank_slide()
    add_header(slide9, "4. Proposed Agentic AI Solution: High-Level Architecture", category="Solution Architecture", slide_num=9)

    # High-level architecture flow across the slide
    flow_steps = [
        ("1. Input & Sensing", "Disruption Webhook\nManual User Query\nLive Telemetry Stream", COLOR_PRIMARY),
        ("2. Supervisor Agent", "LangGraph Planner\nIntent Classification\nTask Decomposition", COLOR_PURPLE),
        ("3. Specialist Agents", "Inventory Analyst\nSupplier Risk Agent\nLogistics Route Agent", COLOR_SECONDARY),
        ("4. Hybrid Engine", "OR-Tools MILP Solver\nDense + BM25 RAG\nContract Citations", COLOR_ACCENT),
        ("5. Evaluator & HITL", "Reflective Plan Audit\nManager Review Gate\nDecision Dispatch", COLOR_SUCCESS)
    ]
    w_step = Inches(2.1)
    for i, (st, desc, col) in enumerate(flow_steps):
        left_pos = Inches(0.8 + i * 2.4)
        add_card(slide9, left_pos, Inches(1.6), w_step, Inches(1.8), border_color=col)
        tb = slide9.shapes.add_textbox(left_pos + Inches(0.1), Inches(1.7), w_step - Inches(0.2), Inches(1.6))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = st
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = col
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(8.5)
        p2.font.color.rgb = COLOR_TEXT_MAIN

    # Bottom Area: 3 Core Solution Pillars
    add_card(slide9, Inches(0.8), Inches(3.6), Inches(11.733), Inches(3.2))
    tb_sol = slide9.shapes.add_textbox(Inches(1.0), Inches(3.75), Inches(11.333), Inches(2.9))
    tf_sol = tb_sol.text_frame
    tf_sol.word_wrap = True
    p = tf_sol.paragraphs[0]
    p.text = "CORE ARCHITECTURAL PILLARS OF SUPPLYCHAINAI"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY

    sol_pillars = [
        ("• Decoupled Neuro-Symbolic Computation", "LLMs excel at natural language comprehension, unstructured contract parsing, and strategy formulation, but fail at mathematical calculation. SupplyChainAI completely decouples qualitative reasoning from numerical budgeting by delegating resource allocation to Google OR-Tools."),
        ("• LangGraph StateGraph Resilience", "Unlike linear chain-of-thought pipelines, our stateful execution graph supports cyclical transitions. If the Evaluator Agent detects an SLA breach, the state seamlessly loops back to the Re-Planner with corrective boundary constraints."),
        ("• Explainable Contract Grounding via Hybrid RAG", "Recommendations do not rely on implicit model memory. Every re-allocation decision is explicitly grounded in indexed supplier contracts and SOPs, retrieving penalty terms, delivery guarantees, and minimum order quantities.")
    ]
    for title_sp, desc_sp in sol_pillars:
        psp = tf_sol.add_paragraph()
        psp.text = f"{title_sp}: {desc_sp}"
        psp.font.size = Pt(9.5)
        psp.font.color.rgb = COLOR_TEXT_MAIN

    # =========================================================================
    # SLIDE 10 — KEY FEATURES
    # =========================================================================
    slide10 = add_blank_slide()
    add_header(slide10, "Key Features of SupplyChainAI Framework", category="Core Capabilities", slide_num=10)

    # 6 Visual Feature Cards (3x2 Grid)
    features = [
        ("LangGraph Multi-Agent Engine", "Stateful orchestration coordinating 5 specialized agents with cyclical replanning, dynamic routing, and persistent execution state.", COLOR_PURPLE),
        ("Deterministic MILP Optimization", "Mixed-Integer Linear Programming using Google OR-Tools CBC/SCIP solvers, guaranteeing 100% mathematical constraint compliance.", COLOR_SECONDARY),
        ("Hybrid Agentic RAG Pipeline", "Dual-stream dense (pgvector HNSW) and sparse (BM25) retrieval fused via Reciprocal Rank Fusion for zero-hallucination contract analysis.", COLOR_ACCENT),
        ("Interactive What-If Sandbox", "Real-time simulation environment enabling managers to inject plant outages, shipping delays, and tariff spikes to evaluate mitigation.", COLOR_GOLD),
        ("Reflective Self-Correction", "Dedicated Evaluator Agent auditing proposed procurement plans against business constraints before presenting them for human sign-off.", COLOR_SUCCESS),
        ("Human-in-the-Loop (HITL) Gate", "Configurable autonomy levels featuring one-click approval, interactive manual overrides, and tamper-evident JSON audit logging.", COLOR_PRIMARY)
    ]

    w_feat = Inches(3.7)
    h_feat = Inches(2.4)
    for i, (title_feat, desc_feat, col_feat) in enumerate(features):
        r = i // 3
        c = i % 3
        left_pos = Inches(0.8 + c * 3.95)
        top_pos = Inches(1.6 + r * 2.65)
        add_card(slide10, left_pos, top_pos, w_feat, h_feat, border_color=col_feat)
        
        tb = slide10.shapes.add_textbox(left_pos + Inches(0.15), top_pos + Inches(0.15), w_feat - Inches(0.3), h_feat - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"FEATURE {i+1}"
        p.font.size = Pt(9)
        p.font.bold = True
        p.font.color.rgb = col_feat
        
        p2 = tf.add_paragraph()
        p2.text = title_feat
        p2.font.size = Pt(11)
        p2.font.bold = True
        p2.font.color.rgb = COLOR_TEXT_MAIN
        
        p3 = tf.add_paragraph()
        p3.text = desc_feat
        p3.font.size = Pt(8.5)
        p3.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 11 — 5. DATASET / KNOWLEDGE SOURCES
    # =========================================================================
    slide11 = add_blank_slide()
    add_header(slide11, "5. Dataset & Knowledge Sources: Multi-Echelon Grounding", category="Data & Knowledge", slide_num=11)

    # Left Column: Enterprise Telemetry Dataset Details
    add_card(slide11, Inches(0.8), Inches(1.6), Inches(5.65), Inches(5.2))
    tb_d = slide11.shapes.add_textbox(Inches(1.0), Inches(1.75), Inches(5.25), Inches(4.9))
    tf_d = tb_d.text_frame
    tf_d.word_wrap = True
    p = tf_d.paragraphs[0]
    p.text = "ENTERPRISE TELEMETRY DATASET"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY

    data_pts = [
        ("10 Industrial SKUs", "Raw materials, critical semiconductors, and subassemblies with distinct unit costs ($12–$450), holding fees, and safety stock thresholds."),
        ("7 Global Suppliers", "Tier-1 and Tier-2 suppliers distributed across North America, Europe, and Asia with documented capacity limits, lead times, and risk ratings."),
        ("4 Regional Distribution Hubs", "Hubs in Chicago, Rotterdam, Singapore, and Dallas with specific storage capacities and operating costs."),
        ("16 Multi-Modal Routes", "Maritime corridors, air freight lanes, and overland trucking routes with historical delay distributions and freight costs."),
        ("960 Synthetic Longitudinal Orders", "Transaction records capturing normal demand fluctuations, seasonal surges, and injected geopolitical disruption events.")
    ]
    for title_dp, desc_dp in data_pts:
        pdp = tf_d.add_paragraph()
        pdp.text = f"• {title_dp}: {desc_dp}"
        pdp.font.size = Pt(9)
        pdp.font.color.rgb = COLOR_TEXT_MAIN

    # Right Column: RAG Document Pipeline
    add_card(slide11, Inches(6.85), Inches(1.6), Inches(5.65), Inches(5.2))
    tb_rag = slide11.shapes.add_textbox(Inches(7.05), Inches(1.75), Inches(5.25), Inches(4.9))
    tf_rag = tb_rag.text_frame
    tf_rag.word_wrap = True
    p = tf_rag.paragraphs[0]
    p.text = "UNSTRUCTURED KNOWLEDGE PIPELINE (RAG)"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_PURPLE

    rag_stages = [
        ("STAGE 1: DOCUMENT INGESTION", "Master Service Agreements (MSAs), supplier contracts, SLA annexes, and standard operating procedures (SOPs) stored in Markdown/PDF formats."),
        ("STAGE 2: SEMANTIC CHUNKING", "Chunked into 500-token passages with 50-token overlap, preserving clause hierarchy, section numbers, and numerical tables."),
        ("STAGE 3: DUAL EMBEDDING GENERATION", "Dense embeddings computed via BAAI/bge-base-en-v1.5 (768-dim) paired with sparse inverted term indices for BM25 matching."),
        ("STAGE 4: VECTOR DATABASE STORAGE", "Persisted in PostgreSQL 16 utilizing the pgvector extension with Hierarchical Navigable Small World (HNSW) indexing for sub-10ms search.")
    ]
    for st_title, st_desc in rag_stages:
        pst = tf_rag.add_paragraph()
        pst.text = st_title
        pst.font.size = Pt(9.5)
        pst.font.bold = True
        pst.font.color.rgb = COLOR_PRIMARY
        psd = tf_rag.add_paragraph()
        psd.text = st_desc
        psd.font.size = Pt(8.5)
        psd.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 12 — 6. TOOLS & TECHNOLOGIES
    # =========================================================================
    slide12 = add_blank_slide()
    add_header(slide12, "6. Tools and Technologies: Enterprise Technology Stack", category="Technology Stack", slide_num=12)

    tech_cards = [
        ("AI / ML & Orchestration", ["• LangGraph (StateGraph multi-agent coordination)", "• LangChain Core (prompt management & tooling)", "• Pydantic v2 (typed state contracts & validation)"], COLOR_PURPLE),
        ("LLM / SLM Support", ["• DeepSeek-R1 (Distill-Qwen-14B / 32B for local SLM)", "• Llama-3.1-70B & GPT-4o-mini (Cloud inference)", "• Groq API / Ollama (ultra-low latency serving)"], COLOR_SECONDARY),
        ("Operations Research & Math", ["• Google OR-Tools (Mixed-Integer Linear Programming)", "• CBC / SCIP mathematical solvers", "• Guaranteed global optimum cost allocation"], COLOR_ACCENT),
        ("Database & Vector Storage", ["• PostgreSQL 16 (Enterprise relational storage)", "• pgvector Extension (Cosine similarity HNSW index)", "• SQLAlchemy ORM (async schema management)"], COLOR_PRIMARY),
        ("Backend Framework", ["• Python 3.11 (Core runtime environment)", "• FastAPI (High-performance async REST & SSE)", "• Uvicorn (ASGI web production server)"], COLOR_GOLD),
        ("Frontend & DevOps", ["• React 18 + TypeScript + Tailwind CSS (Vite)", "• Lucide React Icons & Recharts Visualization", "• Docker, Docker Compose, Pytest (19 tests)"], COLOR_SUCCESS)
    ]

    w_tc = Inches(3.7)
    h_tc = Inches(2.4)
    for i, (cat, items_tc, col_tc) in enumerate(tech_cards):
        r = i // 3
        c = i % 3
        left_pos = Inches(0.8 + c * 3.95)
        top_pos = Inches(1.6 + r * 2.65)
        add_card(slide12, left_pos, top_pos, w_tc, h_tc, border_color=col_tc)
        
        tb = slide12.shapes.add_textbox(left_pos + Inches(0.15), top_pos + Inches(0.15), w_tc - Inches(0.3), h_tc - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = cat
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = col_tc
        for it in items_tc:
            pi = tf.add_paragraph()
            pi.text = it
            pi.font.size = Pt(8.5)
            pi.font.color.rgb = COLOR_TEXT_MAIN

    # =========================================================================
    # SLIDE 13 — 7. AGENT ARCHITECTURE
    # =========================================================================
    slide13 = add_blank_slide()
    add_header(slide13, "7. Agent Architecture: Multi-Agent Specialization", category="Agent Architecture", slide_num=13)

    # Top: Supervisor Node
    add_card(slide13, Inches(3.8), Inches(1.6), Inches(5.733), Inches(1.1), border_color=COLOR_PRIMARY, bg_color=RGBColor(241, 245, 249))
    tb_sup = slide13.shapes.add_textbox(Inches(3.9), Inches(1.7), Inches(5.533), Inches(0.9))
    tf_sup = tb_sup.text_frame
    tf_sup.word_wrap = True
    p = tf_sup.paragraphs[0]
    p.text = "SUPERVISOR / ORCHESTRATOR AGENT"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_PRIMARY
    p.alignment = PP_ALIGN.CENTER
    p2 = tf_sup.add_paragraph()
    p2.text = "Dispatches sub-tasks  •  Synchronizes global StateGraph state  •  Manages execution flow"
    p2.font.size = Pt(9)
    p2.font.color.rgb = COLOR_TEXT_MUTED
    p2.alignment = PP_ALIGN.CENTER

    # Middle Layer: 3 Specialist Diagnostic Agents
    specialists = [
        ("INVENTORY ANALYST AGENT", "Monitors stock levels, safety buffer breaches, and consumption velocity across all 4 regional hubs.", COLOR_SECONDARY),
        ("SUPPLIER RISK AGENT", "Evaluates vendor reliability scores, geopolitical threat indices, and historical delivery compliance.", COLOR_PURPLE),
        ("LOGISTICS & ROUTING AGENT", "Detects transit delays, chokepoint congestions (e.g. Red Sea), and evaluates alternative carrier lanes.", COLOR_ACCENT)
    ]
    w_sp = Inches(3.7)
    for i, (title_sp, desc_sp, col_sp) in enumerate(specialists):
        left_pos = Inches(0.8 + i * 3.95)
        add_card(slide13, left_pos, Inches(2.95), w_sp, Inches(1.5), border_color=col_sp)
        tb = slide13.shapes.add_textbox(left_pos + Inches(0.15), Inches(3.05), w_sp - Inches(0.3), Inches(1.3))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_sp
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = col_sp
        p2 = tf.add_paragraph()
        p2.text = desc_sp
        p2.font.size = Pt(8.5)
        p2.font.color.rgb = COLOR_TEXT_MAIN

    # Bottom Layer: Re-Planner & Optimization Solver + Evaluator
    add_card(slide13, Inches(0.8), Inches(4.7), Inches(5.65), Inches(1.8), border_color=COLOR_GOLD)
    tb_opt = slide13.shapes.add_textbox(Inches(0.95), Inches(4.8), Inches(5.35), Inches(1.6))
    tf_opt = tb_opt.text_frame
    tf_opt.word_wrap = True
    p = tf_opt.paragraphs[0]
    p.text = "RE-PLANNER AGENT + GOOGLE OR-TOOLS MILP"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_GOLD
    p2 = tf_opt.add_paragraph()
    p2.text = "• Formulates Mixed-Integer Linear Programming objective:\n  Minimize Landed Cost = Purchasing Cost + Freight Cost + Penalty Fees\n• Subject to: Supplier Capacity, Minimum Order Quantity (MOQ), and Lead Time bounds.\n• Outputs guaranteed optimal integer allocation in < 20 ms."
    p2.font.size = Pt(8.5)
    p2.font.color.rgb = COLOR_TEXT_MAIN

    add_card(slide13, Inches(6.85), Inches(4.7), Inches(5.65), Inches(1.8), border_color=COLOR_SUCCESS)
    tb_ev = slide13.shapes.add_textbox(Inches(7.0), Inches(4.8), Inches(5.35), Inches(1.6))
    tf_ev = tb_ev.text_frame
    tf_ev.word_wrap = True
    p = tf_ev.paragraphs[0]
    p.text = "REFLECTIVE EVALUATOR AGENT & HITL GATE"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_SUCCESS
    p2 = tf_ev.add_paragraph()
    p2.text = "• Adversarially checks re-plan against SLA policies and budget constraints.\n• If invalid: returns actionable feedback to Re-Planner for automated bounded replanning.\n• If valid: formats plan with contract citations and sends to React 18 UI for one-click human approval."
    p2.font.size = Pt(8.5)
    p2.font.color.rgb = COLOR_TEXT_MAIN

    # Footer banner
    add_card(slide13, Inches(0.8), Inches(6.6), Inches(11.733), Inches(0.35), bg_color=COLOR_PRIMARY)
    tb_foot = slide13.shapes.add_textbox(Inches(1.0), Inches(6.62), Inches(11.333), Inches(0.3))
    p_f = tb_foot.text_frame.paragraphs[0]
    p_f.text = "Architecture Principle: Complete decoupling of LLM qualitative reasoning from mathematical numerical calculation."
    p_f.font.size = Pt(9)
    p_f.font.bold = True
    p_f.font.color.rgb = RGBColor(255, 255, 255)
    p_f.alignment = PP_ALIGN.CENTER

    # =========================================================================
    # SLIDE 14 — AGENT COMPONENTS, TOOLS & MEMORY
    # =========================================================================
    slide14 = add_blank_slide()
    add_header(slide14, "Agent Components, Deterministic Tools & Memory Model", category="Components & Tools", slide_num=14)

    # 3 Compact Tables/Cards
    # Card 1: Agent Roles & Responsibilities
    add_card(slide14, Inches(0.8), Inches(1.6), Inches(5.65), Inches(2.55))
    tb_ac = slide14.shapes.add_textbox(Inches(1.0), Inches(1.7), Inches(5.25), Inches(2.3))
    tf_ac = tb_ac.text_frame
    tf_ac.word_wrap = True
    p = tf_ac.paragraphs[0]
    p.text = "AGENT COMPONENTS & RESPONSIBILITIES"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_PRIMARY

    ag_roles = [
        ("Supervisor", "StateGraph routing, sub-task dispatching, turn coordination"),
        ("Inventory Analyst", "SKU stock auditing, reorder threshold checks, lead-time variance"),
        ("Supplier Risk Agent", "Vendor reliability assessment, financial/regional risk rating"),
        ("Logistics Agent", "Freight carrier evaluation, delay tracking, transit rerouting"),
        ("Re-Planner & Evaluator", "MILP constraint formulation, optimization, SLA validation")
    ]
    for r_name, r_desc in ag_roles:
        pr = tf_ac.add_paragraph()
        pr.text = f"• {r_name}: {r_desc}"
        pr.font.size = Pt(8.5)
        pr.font.color.rgb = COLOR_TEXT_MAIN

    # Card 2: Deterministic Tools
    add_card(slide14, Inches(6.85), Inches(1.6), Inches(5.65), Inches(2.55))
    tb_tl = slide14.shapes.add_textbox(Inches(7.05), Inches(1.7), Inches(5.25), Inches(2.3))
    tf_tl = tb_tl.text_frame
    tf_tl.word_wrap = True
    p = tf_tl.paragraphs[0]
    p.text = "DETERMINISTIC TOOLS REGISTRY"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY

    tools_list = [
        ("query_inventory_db", "Fetches live stock, SKU velocity, and safety thresholds"),
        ("solve_procurement_milp", "Invokes Google OR-Tools solver for cost-optimal order splits"),
        ("retrieve_contracts_rag", "Hybrid dense+sparse search over contracts, SLAs, and SOPs"),
        ("simulate_disruption", "Injects synthetic plant shutdowns and transit delays into sandbox"),
        ("record_audit_decision", "Cryptographically signs approved action and logs to PostgreSQL")
    ]
    for t_name, t_desc in tools_list:
        pt = tf_tl.add_paragraph()
        pt.text = f"• {t_name}: {t_desc}"
        pt.font.size = Pt(8.5)
        pt.font.color.rgb = COLOR_TEXT_MAIN

    # Bottom Card: 4-Tier Memory Architecture
    add_card(slide14, Inches(0.8), Inches(4.35), Inches(11.733), Inches(2.5))
    tb_mem = slide14.shapes.add_textbox(Inches(1.0), Inches(4.45), Inches(11.333), Inches(2.3))
    tf_mem = tb_mem.text_frame
    tf_mem.word_wrap = True
    p = tf_mem.paragraphs[0]
    p.text = "4-TIER MULTI-AGENT MEMORY ARCHITECTURE"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_PURPLE

    memories = [
        ("1. Working Memory (Short-Term)", "LangGraph typed state dictionary (`AgentState`) tracking current turn conversation, active disruption flags, and partial allocations across nodes."),
        ("2. Episodic Memory (Scratchpad)", "Agent-specific execution scratchpads capturing intermediate reasoning chains, solver execution parameters, and validator feedback."),
        ("3. Semantic Memory (Knowledge Base)", "PostgreSQL pgvector database storing vectorized supplier contracts, SLA clauses, vendor profiles, and freight lane metadata."),
        ("4. Procedural Memory (Audit Trail)", "Immutable transaction history in PostgreSQL logging approved decisions, human overrides, and historical re-planning effectiveness.")
    ]
    for m_name, m_desc in memories:
        pm = tf_mem.add_paragraph()
        pm.text = f"• {m_name}: {m_desc}"
        pm.font.size = Pt(8.5)
        pm.font.color.rgb = COLOR_TEXT_MAIN

    # =========================================================================
    # SLIDE 15 — 8. AGENT WORKFLOW & ORCHESTRATION
    # =========================================================================
    slide15 = add_blank_slide()
    add_header(slide15, "8. Agent Workflow & Orchestration: StateGraph Execution Loop", category="Workflow", slide_num=15)

    # 7-Step Workflow Diagram across slide
    workflow_steps = [
        ("Step 1", "Disruption Ingest", "Sensor alert / query received by Supervisor", COLOR_PRIMARY),
        ("Step 2", "Parallel Audit", "Inventory, Supplier, and Logistics agents analyze state", COLOR_PURPLE),
        ("Step 3", "Hybrid RAG", "Dual dense+BM25 contract clause extraction", COLOR_SECONDARY),
        ("Step 4", "MILP Solver", "Google OR-Tools computes optimal order split", COLOR_ACCENT),
        ("Step 5", "Evaluation", "Evaluator verifies plan; loops back if invalid", COLOR_GOLD),
        ("Step 6", "HITL Gate", "Manager reviews plan in React 18 UI", COLOR_SUCCESS),
        ("Step 7", "Dispatch & Log", "Orders dispatched & logged to audit DB", COLOR_PRIMARY)
    ]
    w_ws = Inches(1.5)
    for i, (s_num, s_title, s_desc, s_col) in enumerate(workflow_steps):
        left_pos = Inches(0.8 + i * 1.7)
        add_card(slide15, left_pos, Inches(1.6), w_ws, Inches(2.1), border_color=s_col)
        tb = slide15.shapes.add_textbox(left_pos + Inches(0.08), Inches(1.7), w_ws - Inches(0.16), Inches(1.9))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = s_num
        p.font.size = Pt(9)
        p.font.bold = True
        p.font.color.rgb = s_col
        p2 = tf.add_paragraph()
        p2.text = s_title
        p2.font.size = Pt(10)
        p2.font.bold = True
        p2.font.color.rgb = COLOR_TEXT_MAIN
        p3 = tf.add_paragraph()
        p3.text = s_desc
        p3.font.size = Pt(7.5)
        p3.font.color.rgb = COLOR_TEXT_MUTED

    # Bottom Area: Detailed Technical Orchestration Highlights
    add_card(slide15, Inches(0.8), Inches(3.95), Inches(11.733), Inches(2.9))
    tb_orc = slide15.shapes.add_textbox(Inches(1.0), Inches(4.1), Inches(11.333), Inches(2.6))
    tf_orc = tb_orc.text_frame
    tf_orc.word_wrap = True
    p = tf_orc.paragraphs[0]
    p.text = "TECHNICAL ORCHESTRATION MECHANISMS"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY

    orc_pts = [
        ("• Typed State Schema Enforcement (`AgentState`)", "Every node transition consumes and produces a strictly typed Pydantic schema, guaranteeing zero schema drift and deterministic state immutability across asynchronous agent workers."),
        ("• Asynchronous Parallel Fan-Out / Fan-In", "The Inventory Analyst, Supplier Risk, and Logistics agents execute concurrently using Python asyncio, reducing diagnostic perception latency to under 35 milliseconds."),
        ("• Cyclic Self-Correction Edge", "If the Reflective Evaluator detects an unmet SLA or budget violation, the graph executes a conditional edge back to the Re-Planner with targeted feedback, preventing unviable plans from ever reaching the manager."),
        ("• Checkpointed Persistence", "The state graph writes snapshots to PostgreSQL at each node boundary, enabling instant state rollback and fault-tolerant resumption during network failures.")
    ]
    for opt_t, opt_d in orc_pts:
        pop = tf_orc.add_paragraph()
        pop.text = f"{opt_t}: {opt_d}"
        pop.font.size = Pt(8.5)
        pop.font.color.rgb = COLOR_TEXT_MAIN

    # =========================================================================
    # SLIDE 16 — 9. AGENTIC RAG IMPLEMENTATION
    # =========================================================================
    slide16 = add_blank_slide()
    add_header(slide16, "9. Agentic RAG Implementation: Dense + Sparse Fusion", category="RAG Architecture", slide_num=16)

    # 4 Architecture Flow Stages across slide
    rag_steps = [
        ("1. Dynamic Query Expansion", "User Query / Disruption\nAgent derives search filters\nHyDE hypothetical clause expansion", COLOR_PRIMARY),
        ("2. Dual-Stream Retrieval", "Dense: 768-dim BGE in pgvector\nSparse: Inverted Index BM25\nExact SKU & Clause extraction", COLOR_SECONDARY),
        ("3. Reciprocal Rank Fusion", "RRF Score Formula:\nRRF(d) = sum(1 / (60 + r(d)))\nMerges semantic & lexical ranks", COLOR_PURPLE),
        ("4. Grounded Context Synthesis", "Top-K reranked chunks\nContract clause citations\nZero-hallucination prompt assembly", COLOR_SUCCESS)
    ]
    w_rs = Inches(2.7)
    for i, (rt, rd, rc) in enumerate(rag_steps):
        left_pos = Inches(0.8 + i * 2.95)
        add_card(slide16, left_pos, Inches(1.6), w_rs, Inches(1.8), border_color=rc)
        tb = slide16.shapes.add_textbox(left_pos + Inches(0.12), Inches(1.7), w_rs - Inches(0.24), Inches(1.6))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = rt
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = rc
        p2 = tf.add_paragraph()
        p2.text = rd
        p2.font.size = Pt(8.5)
        p2.font.color.rgb = COLOR_TEXT_MAIN

    # Bottom Area: Detailed Technical RAG Capabilities
    add_card(slide16, Inches(0.8), Inches(3.6), Inches(11.733), Inches(3.2))
    tb_rcap = slide16.shapes.add_textbox(Inches(1.0), Inches(3.75), Inches(11.333), Inches(2.9))
    tf_rcap = tb_rcap.text_frame
    tf_rcap.word_wrap = True
    p = tf_rcap.paragraphs[0]
    p.text = "WHY HYBRID AGENTIC RAG IS ESSENTIAL FOR SUPPLY CHAINS"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY

    rag_why = [
        ("• Eliminates Dense Embedding Blind Spots", "Dense vector similarity captures conceptual semantics (e.g. 'penalty terms for delayed delivery'), but frequently fails to match exact alphanumeric codes like 'SKU-4029', 'Section 4.2', or strict currency bounds ($15,000). BM25 guarantees 100% lexical precision for technical tokens."),
        ("• Robust Rank Merging via Reciprocal Rank Fusion (RRF)", "Traditional vector score combination requires fragile heuristic weighting (e.g. 0.7 * dense + 0.3 * sparse). RRF operates purely on ordinal rankings, eliminating score normalization artifacts across diverse query types."),
        ("• Agent-Directed Metadata Filtering", "The agent dynamically inspects disruption context to inject relational SQL filters into the vector search (e.g., `WHERE supplier_id = 'SUP-C' AND document_type = 'contract'`), drastically shrinking the search space and accelerating retrieval to < 15 ms.")
    ]
    for rw_t, rw_d in rag_why:
        prw = tf_rcap.add_paragraph()
        prw.text = f"{rw_t}: {rw_d}"
        prw.font.size = Pt(8.5)
        prw.font.color.rgb = COLOR_TEXT_MAIN

    # =========================================================================
    # SLIDE 17 — RETRIEVAL & GENERATION PROCESS
    # =========================================================================
    slide17 = add_blank_slide()
    add_header(slide17, "Knowledge Retrieval & Grounded Generation Details", category="RAG Mechanics", slide_num=17)

    w_card = Inches(5.65)
    h_card = Inches(5.2)

    # Left Column: Retrieval Engineering
    add_card(slide17, Inches(0.8), Inches(1.6), w_card, h_card, border_color=COLOR_SECONDARY)
    tb_re = slide17.shapes.add_textbox(Inches(1.0), Inches(1.75), w_card - Inches(0.4), h_card - Inches(0.3))
    tf_re = tb_re.text_frame
    tf_re.word_wrap = True
    p = tf_re.paragraphs[0]
    p.text = "RETRIEVAL PIPELINE ENGINEERING"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY

    re_items = [
        ("Pre-Filtering with Metadata", "Applies strict SQL pre-filters on `supplier_id`, `jurisdiction`, and `contract_status` prior to nearest-neighbor graph traversal."),
        ("HNSW Index Configuration", "PostgreSQL pgvector configured with `m = 16`, `ef_construction = 64` ensuring > 98% recall with sub-10ms query execution."),
        ("Reciprocal Rank Fusion Formula", "Calculated as: RRF(d) = Σ [ 1 / (60 + rank_dense(d)) + 1 / (60 + rank_bm25(d)) ], effectively penalizing outliers while rewarding consensus documents."),
        ("Dynamic Top-K Selection", "Retrieves Top-5 most authoritative contract paragraphs, ensuring compact prompt payloads that avoid LLM attention degradation.")
    ]
    for r_t, r_d in re_items:
        pri = tf_re.add_paragraph()
        pri.text = f"• {r_t}: {r_d}"
        pri.font.size = Pt(8.5)
        pri.font.color.rgb = COLOR_TEXT_MAIN

    # Right Column: Generation & Explainability
    add_card(slide17, Inches(6.85), Inches(1.6), w_card, h_card, border_color=COLOR_SUCCESS)
    tb_ge = slide17.shapes.add_textbox(Inches(7.05), Inches(1.75), w_card - Inches(0.4), h_card - Inches(0.3))
    tf_ge = tb_ge.text_frame
    tf_ge.word_wrap = True
    p = tf_ge.paragraphs[0]
    p.text = "GENERATION & ZERO-HALLUCINATION SAFEGUARDS"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_SUCCESS

    ge_items = [
        ("Strict Context-Anchored Prompts", "The system prompt explicitly instructs the LLM: 'State only factual claims supported by the provided context. If unknown, state NOT_SPECIFIED.'"),
        ("Verifiable Source Citations", "Every generated recommendation appends exact clause citations (e.g. '[Supplier C Agreement, Clause 4.2 - Delay Indemnity]'), allowing human auditors to verify claims instantly."),
        ("Separation of Policy and Math", "The LLM explains policy reasons (e.g. why Supplier C was deprioritized due to lead-time penalties), while the order quantities are rendered directly from the MILP solver's deterministic output."),
        ("Tamper-Proof Audit JSON", "Outputs are wrapped in a cryptographically signed JSON envelope and stored in the database for compliance inspection.")
    ]
    for g_t, g_d in ge_items:
        pgi = tf_ge.add_paragraph()
        pgi.text = f"• {g_t}: {g_d}"
        pgi.font.size = Pt(8.5)
        pgi.font.color.rgb = COLOR_TEXT_MAIN

    # =========================================================================
    # SLIDE 18 — 10. SYSTEM IMPLEMENTATION
    # =========================================================================
    slide18 = add_blank_slide()
    add_header(slide18, "10. System Implementation: Full-Stack Architecture", category="System Implementation", slide_num=18)

    # 4 Architectural Layer Cards (2x2 Grid)
    layers = [
        ("1. REACT 18 + TYPESCRIPT FRONTEND", [
            "• Executive Disruption Dashboard: Real-time inventory risk gauges & active alert ticker.",
            "• Interactive Risk Heatmap: Network graph of 7 suppliers, 4 hubs, and 16 freight routes.",
            "• What-If Simulation Sandbox: Sliders to inject supplier outages and lead-time surges.",
            "• Streaming Agent Thoughts: Server-Sent Events (SSE) displaying live agent reasoning."
        ], COLOR_PURPLE),
        ("2. FASTAPI ASYNC BACKEND ENGINE", [
            "• High-Performance ASGI: Built on Python 3.11 with async REST endpoints and SSE streams.",
            "• Pydantic v2 Contract Validation: Validates all incoming payloads and solver responses.",
            "• LangGraph Execution Runtime: Manages agent lifecycle, checkpointing, and thread memory.",
            "• Secure CORS & Middleware: Enterprise-ready authentication and audit logging."
        ], COLOR_SECONDARY),
        ("3. GOOGLE OR-TOOLS MILP SOLVER", [
            "• Exact Mathematical Solver: CBC / SCIP mixed-integer programming algorithms.",
            "• Hard Constraints: Supplier maximum capacity, minimum order quantity (MOQ), delivery deadlines.",
            "• Multi-Objective Cost Function: Landed cost = purchase price + transit fees + SLA penalties.",
            "• Execution Performance: Computes global optimum in 12.4 ms for 10,000 units."
        ], COLOR_ACCENT),
        ("4. POSTGRESQL 16 + PGVECTOR STORAGE", [
            "• Relational Storage: SKUs, suppliers, distribution centers, routes, and historical PO records.",
            "• Vector Store: HNSW-indexed 768-dim embeddings for sub-10ms similarity search.",
            "• Immutable Audit Ledger: Cryptographically hashed decision trails for regulatory compliance.",
            "• Containerized Deployment: Multi-container Docker Compose with health checks."
        ], COLOR_PRIMARY)
    ]

    w_lay = Inches(5.65)
    h_lay = Inches(2.55)
    for i, (title_lay, items_lay, col_lay) in enumerate(layers):
        r = i // 2
        c = i % 2
        left_pos = Inches(0.8 + c * 6.05)
        top_pos = Inches(1.6 + r * 2.7)
        add_card(slide18, left_pos, top_pos, w_lay, h_lay, border_color=col_lay)
        
        tb = slide18.shapes.add_textbox(left_pos + Inches(0.15), top_pos + Inches(0.15), w_lay - Inches(0.3), h_lay - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_lay
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = col_lay
        for it in items_lay:
            pi = tf.add_paragraph()
            pi.text = it
            pi.font.size = Pt(8.5)
            pi.font.color.rgb = COLOR_TEXT_MAIN

    # =========================================================================
    # SLIDE 19 — 11. EXPERIMENTAL EVALUATION
    # =========================================================================
    slide19 = add_blank_slide()
    add_header(slide19, "11. Experimental Evaluation & Verification Methodology", category="Evaluation", slide_num=19)

    # 4 Metric Cards along top
    add_metric_badge(slide19, Inches(0.8), Inches(1.6), Inches(2.7), Inches(1.4), "19 / 19", "Automated Tests Passed", "100% pass rate in 2.40s", COLOR_SUCCESS)
    add_metric_badge(slide19, Inches(3.75), Inches(1.6), Inches(2.7), Inches(1.4), "125 ms", "Baseline Plan Latency", "10k units across 7 vendors", COLOR_SECONDARY)
    add_metric_badge(slide19, Inches(6.7), Inches(1.6), Inches(2.7), Inches(1.4), "100%", "Constraint Satisfaction", "0 capacity or MOQ breaches", COLOR_ACCENT)
    add_metric_badge(slide19, Inches(9.65), Inches(1.6), Inches(2.7), Inches(1.4), "0.0%", "Arithmetic Hallucination", "Decoupled MILP solver", COLOR_PURPLE)

    # Bottom Area: Test Methodology & Coverage Details
    add_card(slide19, Inches(0.8), Inches(3.25), Inches(11.733), Inches(3.6))
    tb_ev = slide19.shapes.add_textbox(Inches(1.0), Inches(3.4), Inches(11.333), Inches(3.3))
    tf_ev = tb_ev.text_frame
    tf_ev.word_wrap = True
    p = tf_ev.paragraphs[0]
    p.text = "COMPREHENSIVE TESTING & VERIFICATION METHODOLOGY"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_PRIMARY

    eval_areas = [
        ("• Automated Test Suite Execution", "All components are rigorously validated using Pytest (`test_extended_verification.py`), executing 19 end-to-end unit and integration tests covering multi-agent state transitions, solver edge cases, RAG retrieval accuracy, and database persistence."),
        ("• Multi-Agent StateGraph Cyclical Loops", "Verified conditional routing edges ensuring that malformed plans, exceeding supplier capacities or breaking delivery deadlines, are correctly intercepted by the Evaluator Agent and recycled for replenishment re-planning."),
        ("• Mathematical Solver Correctness", "Validated Google OR-Tools CBC/SCIP solver across boundary conditions: zero available stock, single-supplier dominance, multi-supplier outages, and minimum order quantity step functions."),
        ("• RAG Citation & Faithfulness Benchmarking", "Verified that 100% of generated legal claims trace back to indexed supplier MSAs and contract clauses with exact document section references."),
        ("• Human-in-the-Loop State Persistence", "Validated state freezing at the HITL approval gate, ensuring that unapproved plans cannot execute or mutate live inventory records.")
    ]
    for ea_t, ea_d in eval_areas:
        pea = tf_ev.add_paragraph()
        pea.text = f"{ea_t}: {ea_d}"
        pea.font.size = Pt(8.5)
        pea.font.color.rgb = COLOR_TEXT_MAIN

    # =========================================================================
    # SLIDE 20 — PERFORMANCE RESULTS
    # =========================================================================
    slide20 = add_blank_slide()
    add_header(slide20, "Performance Results: Empirical Benchmarks & Scenarios", category="Results", slide_num=20)

    # Benchmark Results Table
    headers = ["Scenario / Benchmark Run", "Workload / Disruption Context", "Solver Time", "Total Plan Latency", "Total Cost ($)", "Constraint Violations"]
    rows = [
        ["Decision Run #52 (Baseline)", "10,000 units Product A across 7 suppliers", "12.4 ms", "125.0 ms", "$42,868.81", "0 (100% Feasible)"],
        ["What-If: SUP-C Outage", "Sudden 100% shutdown of primary supplier (SUP-C)", "8.2 ms", "71.0 ms", "$46,089.70", "0 (100% Feasible)"],
        ["What-If: Red Sea Chokepoint", "Maritime route delay: transit time doubled (2x)", "14.1 ms", "148.0 ms", "$44,120.50", "0 (100% Feasible)"],
        ["Stress Test: High Volume", "50,000 units across 10 SKUs and 16 routes", "38.6 ms", "310.0 ms", "$214,500.00", "0 (100% Feasible)"]
    ]
    col_widths = [Inches(2.5), Inches(3.6), Inches(1.3), Inches(1.6), Inches(1.3), Inches(1.433)]
    add_table(slide20, Inches(0.8), Inches(1.6), Inches(11.733), Inches(2.6), headers, rows, col_widths)

    # 2 Analytical Callout Cards below table
    w_card = Inches(5.65)
    h_card = Inches(2.3)

    add_card(slide20, Inches(0.8), Inches(4.5), w_card, h_card, border_color=COLOR_SUCCESS)
    tb_c1 = slide20.shapes.add_textbox(Inches(1.0), Inches(4.6), w_card - Inches(0.4), h_card - Inches(0.2))
    tf_c1 = tb_c1.text_frame
    tf_c1.word_wrap = True
    p = tf_c1.paragraphs[0]
    p.text = "ANALYSIS: EMERGENCY SUPPLIER OUTAGE (SUP-C)"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_SUCCESS

    pts_c1 = [
        "• Response Latency: Computed optimal re-allocation in just 71.0 ms total latency.",
        "• Autonomous Volume Rerouting: Automatically shifted 6,000 units from offline SUP-C to secondary vendors SUP-A, SUP-B, and SUP-E.",
        "• Controlled Cost Impact: Total procurement cost rose from $42,868.81 to $46,089.70 — an incremental delta of only +$3,220.89 (+7.5%), completely avoiding an estimated $120,000 factory shutdown."
    ]
    for pt in pts_c1:
        p_pt = tf_c1.add_paragraph()
        p_pt.text = pt
        p_pt.font.size = Pt(8.5)
        p_pt.font.color.rgb = COLOR_TEXT_MAIN

    add_card(slide20, Inches(6.85), Inches(4.5), w_card, h_card, border_color=COLOR_SECONDARY)
    tb_c2 = slide20.shapes.add_textbox(Inches(7.05), Inches(4.6), w_card - Inches(0.4), h_card - Inches(0.2))
    tf_c2 = tb_c2.text_frame
    tf_c2.word_wrap = True
    p = tf_c2.paragraphs[0]
    p.text = "ANALYSIS: MARITIME CHOKEPOINT DELAY"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY

    pts_c2 = [
        "• Route Disruption Mitigation: When maritime route 4 experienced a 2x delay, the system re-planned transit allocations in 148 ms.",
        "• Multi-Modal Substitution: Substituted deep-sea shipping with overland rail and regional air freight for critical short-dated inventory.",
        "• Full SLA Protection: 100% of deliveries met the required warehouse arrival window with zero stockout penalties."
    ]
    for pt in pts_c2:
        p_pt = tf_c2.add_paragraph()
        p_pt.text = pt
        p_pt.font.size = Pt(8.5)
        p_pt.font.color.rgb = COLOR_TEXT_MAIN

    # =========================================================================
    # SLIDE 21 — 12. COMPARISON WITH BASELINE
    # =========================================================================
    slide21 = add_blank_slide()
    add_header(slide21, "12. Comparison with Baseline: Objective Performance Matrix", category="Baseline Comparison", slide_num=21)

    headers = ["Capability / Feature", "Manual Spreadsheets", "Legacy ERP (SAP / Oracle)", "Monolithic LLM (GPT-4)", "SupplyChainAI (Proposed)"]
    rows = [
        ["Re-Planning Latency", "4 to 24 Hours", "30 to 120 Minutes", "5 to 15 Seconds", "< 200 Milliseconds (125 ms)"],
        ["Mathematical Optimality", "Sub-optimal heuristic", "Rigid hardcoded rules", "Prone to arithmetic errors", "Guaranteed Global Optimum (MILP)"],
        ["Unstructured Contract RAG", "Manual document reading", "None (completely ignored)", "Context window limits", "Hybrid RAG (pgvector + BM25 RRF)"],
        ["Autonomous Self-Correction", "None (Human must notice)", "None (Throws batch error)", "Hallucinatory loops", "Reflective Agentic StateGraph Loop"],
        ["Auditability & Citations", "None / Email chains", "Cryptic numeric codes", "Unverified assertions", "Verifiable Legal Contract Citations"],
        ["Human-in-the-Loop Governance", "Manual approval delay", "Complex bureaucratic workflows", "No built-in approval gate", "Interactive 1-Click React 18 Gate"]
    ]
    col_widths = [Inches(2.5), Inches(2.1), Inches(2.3), Inches(2.2), Inches(2.633)]
    add_table(slide21, Inches(0.8), Inches(1.6), Inches(11.733), Inches(4.3), headers, rows, col_widths)

    # Bottom summary callout
    add_card(slide21, Inches(0.8), Inches(6.15), Inches(11.733), Inches(0.75), bg_color=COLOR_PRIMARY)
    tb_sum = slide21.shapes.add_textbox(Inches(1.0), Inches(6.25), Inches(11.333), Inches(0.55))
    tf_sum = tb_sum.text_frame
    tf_sum.word_wrap = True
    p = tf_sum.paragraphs[0]
    p.text = "Summary: SupplyChainAI bridges the gap between rigid, blind legacy ERP systems and flexible but hallucination-prone generative models, delivering fast, mathematically guaranteed, and contractually grounded decisions."
    p.font.size = Pt(9)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.alignment = PP_ALIGN.CENTER

    # =========================================================================
    # SLIDE 22 — INNOVATION & ADVANTAGES
    # =========================================================================
    slide22 = add_blank_slide()
    add_header(slide22, "Innovation and Advantages: Core Technical Contributions", category="Innovation", slide_num=22)

    w_card = Inches(5.65)
    h_card = Inches(5.2)

    # Left Column: Technical Innovations
    add_card(slide22, Inches(0.8), Inches(1.6), w_card, h_card, border_color=COLOR_PURPLE)
    tb_inn = slide22.shapes.add_textbox(Inches(1.0), Inches(1.75), w_card - Inches(0.4), h_card - Inches(0.3))
    tf_inn = tb_inn.text_frame
    tf_inn.word_wrap = True
    p = tf_inn.paragraphs[0]
    p.text = "CORE TECHNICAL INNOVATIONS"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_PURPLE

    innovations = [
        ("1. Neuro-Symbolic Decoupled Architecture", "Pioneered a robust hybrid model where LLMs handle natural language understanding and strategic planning, while Google OR-Tools executes all numerical calculations, completely eliminating calculation errors."),
        ("2. Cyclical LangGraph State Orchestration", "Implemented a self-healing state graph where the Evaluator Agent adversarially inspects plans and triggers bounded replanning cycles, resolving constraint violations without system crashes."),
        ("3. Domain-Specific Dual-Stream Hybrid RAG", "Engineered an enterprise RAG pipeline blending 768-dim dense semantic embeddings with BM25 sparse matching via Reciprocal Rank Fusion, achieving exact legal clause retrieval."),
        ("4. Seamless Human-in-the-Loop Integration", "Unified autonomous background execution with explicit human oversight, providing complete decision transparency before any transaction executes.")
    ]
    for in_t, in_d in innovations:
        pin = tf_inn.add_paragraph()
        pin.text = f"• {in_t}: {in_d}"
        pin.font.size = Pt(8.5)
        pin.font.color.rgb = COLOR_TEXT_MAIN

    # Right Column: Tangible Business Advantages
    add_card(slide22, Inches(6.85), Inches(1.6), w_card, h_card, border_color=COLOR_SUCCESS)
    tb_adv = slide22.shapes.add_textbox(Inches(7.05), Inches(1.75), w_card - Inches(0.4), h_card - Inches(0.3))
    tf_adv = tb_adv.text_frame
    tf_adv.word_wrap = True
    p = tf_adv.paragraphs[0]
    p.text = "CONCRETE ENTERPRISE ADVANTAGES"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_SUCCESS

    advantages = [
        ("1. 99%+ Reduction in Triage Time", "Reduces procurement re-planning from hours of frantic spreadsheet analysis to sub-200 milliseconds, enabling proactive rather than reactive response."),
        ("2. Guaranteed Cost Minimization", "Mathematical optimization identifies non-obvious multi-supplier splits that minimize total landed cost, saving 5–15% compared to manual heuristics."),
        ("3. Elimination of Stockout Risk", "Automated fallback routing prevents catastrophic plant shutdowns when primary suppliers suffer unexpected outages."),
        ("4. Regulatory Compliance & Audit Readiness", "Every order decision is cryptographically logged with explicit legal clause citations, ensuring complete auditability for corporate governance.")
    ]
    for ad_t, ad_d in advantages:
        pad = tf_adv.add_paragraph()
        pad.text = f"• {ad_t}: {ad_d}"
        pad.font.size = Pt(8.5)
        pad.font.color.rgb = COLOR_TEXT_MAIN

    # =========================================================================
    # SLIDE 23 — SCALABILITY & REAL-WORLD APPLICABILITY
    # =========================================================================
    slide23 = add_blank_slide()
    add_header(slide23, "Scalability Architecture & Real-World Applicability", category="Scalability & Deployment", slide_num=23)

    # 4 Scalability Vectors (Grid 2x2)
    scales = [
        ("HORIZONTAL MICROSERVICE SCALABILITY", [
            "• Stateless Agent Workers: FastAPI and LangGraph instances scale horizontally across distributed container clusters behind a load balancer.",
            "• Asynchronous Non-Blocking IO: Handles hundreds of concurrent disruption queries without thread starvation."
        ], COLOR_SECONDARY),
        ("ENTERPRISE DATA & KNOWLEDGE SCALABILITY", [
            "• High-Capacity Vector Storage: PostgreSQL pgvector with HNSW indexing maintains sub-10ms query times over 1,000,000+ document chunks.",
            "• Partitioned Telemetry Tables: Time-series order and inventory tables partitioned by month for rapid indexing."
        ], COLOR_PURPLE),
        ("MODEL & RUNTIME AGNOSTICISM", [
            "• Hybrid Inference Gateway: Supports local on-premise SLMs (DeepSeek-R1-14B) for air-gapped security or ultra-fast cloud LLMs (Llama-3.1, GPT-4o-mini).",
            "• Cost-Effective Serving: Token-efficient prompt construction keeps operational API costs negligible."
        ], COLOR_ACCENT),
        ("REAL-WORLD ENTERPRISE INTEGRATION", [
            "• Pre-Built ERP Adapters: Standard REST and Webhook connectors for SAP S/4HANA, Oracle SCM Cloud, and Microsoft Dynamics 365.",
            "• Multi-Sector Applicability: Directly deployable across Automotive Assembly, Consumer Electronics, and Pharmaceuticals."
        ], COLOR_GOLD)
    ]

    w_sc = Inches(5.65)
    h_sc = Inches(2.55)
    for i, (title_sc, items_sc, col_sc) in enumerate(scales):
        r = i // 2
        c = i % 2
        left_pos = Inches(0.8 + c * 6.05)
        top_pos = Inches(1.6 + r * 2.7)
        add_card(slide23, left_pos, top_pos, w_sc, h_sc, border_color=col_sc)
        
        tb = slide23.shapes.add_textbox(left_pos + Inches(0.15), top_pos + Inches(0.15), w_sc - Inches(0.3), h_sc - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_sc
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = col_sc
        for it in items_sc:
            pi = tf.add_paragraph()
            pi.text = it
            pi.font.size = Pt(8.5)
            pi.font.color.rgb = COLOR_TEXT_MAIN

    # =========================================================================
    # SLIDE 24 — 13. CONCLUSION
    # =========================================================================
    slide24 = add_blank_slide()
    add_header(slide24, "13. Conclusion: Summary of Research & Contributions", category="Conclusion", slide_num=24)

    conclusions = [
        ("1. Autonomous Supply Chain Resilience",
         "Successfully engineered and validated an autonomous multi-agent framework capable of continuous disruption perception, diagnostic triaging, and real-time procurement re-planning.",
         COLOR_PRIMARY),
        ("2. Pioneered Neuro-Symbolic Mathematical Rigor",
         "Eliminated generative AI hallucinations in critical resource allocation by coupling LangGraph with Google OR-Tools Mixed-Integer Linear Programming, guaranteeing 100% constraint satisfaction.",
         COLOR_SECONDARY),
        ("3. Sub-Second Re-Planning Performance",
         "Demonstrated exceptional empirical latency — computing optimal multi-supplier allocations for 10,000 units in 125 ms, and executing complete emergency supplier rerouting in just 71 ms.",
         COLOR_ACCENT),
        ("4. Grounded Legal & SLA Compliance",
         "Developed an enterprise Hybrid Agentic RAG architecture (dense pgvector + sparse BM25 with Reciprocal Rank Fusion) that grounds every procurement action in verifiable contractual terms.",
         COLOR_PURPLE),
        ("5. Production-Ready Full-Stack Engineering",
         "Delivered an enterprise-grade prototype featuring a modern React 18 frontend, FastAPI backend, containerized PostgreSQL database, and 100% verified test suite (19/19 passing).",
         COLOR_SUCCESS)
    ]

    for i, (title_c, desc_c, col_c) in enumerate(conclusions):
        top_pos = Inches(1.6 + i * 1.05)
        add_card(slide24, Inches(0.8), top_pos, Inches(11.733), Inches(0.95), border_color=col_c)
        
        # Checkmark / Number badge
        badge = slide24.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.95), top_pos + Inches(0.15), Inches(0.65), Inches(0.65))
        badge.fill.solid()
        badge.fill.fore_color.rgb = col_c
        badge.line.fill.background()
        tf_b = badge.text_frame
        p_b = tf_b.paragraphs[0]
        p_b.text = f"0{i+1}"
        p_b.font.size = Pt(13)
        p_b.font.bold = True
        p_b.font.color.rgb = RGBColor(255, 255, 255)
        p_b.alignment = PP_ALIGN.CENTER

        tb = slide24.shapes.add_textbox(Inches(1.75), top_pos + Inches(0.08), Inches(10.6), Inches(0.8))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_c
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = COLOR_PRIMARY
        p2 = tf.add_paragraph()
        p2.text = desc_c
        p2.font.size = Pt(9)
        p2.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 25 — FUTURE WORK
    # =========================================================================
    slide25 = add_blank_slide()
    add_header(slide25, "Future Work: Research Extensions & Industry Roadmap", category="Future Work", slide_num=25)

    future_items = [
        ("Deep Predictive Disruption Forecasting", "Incorporate Temporal Fusion Transformers (TFT) and graph neural networks to forecast supplier risk and demand volatility 30–60 days ahead of physical events.", COLOR_PURPLE),
        ("Real-Time Maritime IoT & AIS Telematics", "Integrate live Automatic Identification System (AIS) maritime vessel tracking and port congestion APIs for automated en-route container rerouting.", COLOR_SECONDARY),
        ("Multi-Tier Deep Supplier Network Mapping", "Extend dependency graph tracking into Tier-2 and Tier-3 sub-suppliers to uncover hidden common-supplier bottlenecks before disruptions occur.", COLOR_ACCENT),
        ("Multi-Objective ESG & Carbon Optimization", "Formulate carbon emission footprints (CO2e) directly into the MILP objective function alongside landed cost and transit lead times.", COLOR_SUCCESS),
        ("Continuous Reinforcement Learning (RLHF)", "Implement Reinforcement Learning from Human Feedback (RLHF) to refine agent prompt policies based on historical manager override patterns.", COLOR_GOLD)
    ]

    for i, (title_fw, desc_fw, col_fw) in enumerate(future_items):
        top_pos = Inches(1.6 + i * 1.05)
        add_card(slide25, Inches(0.8), top_pos, Inches(11.733), Inches(0.95), border_color=col_fw)
        
        badge = slide25.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.95), top_pos + Inches(0.15), Inches(0.65), Inches(0.65))
        badge.fill.solid()
        badge.fill.fore_color.rgb = col_fw
        badge.line.fill.background()
        tf_b = badge.text_frame
        p_b = tf_b.paragraphs[0]
        p_b.text = f"0{i+1}"
        p_b.font.size = Pt(13)
        p_b.font.bold = True
        p_b.font.color.rgb = RGBColor(255, 255, 255)
        p_b.alignment = PP_ALIGN.CENTER

        tb = slide25.shapes.add_textbox(Inches(1.75), top_pos + Inches(0.08), Inches(10.6), Inches(0.8))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_fw
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = COLOR_PRIMARY
        p2 = tf.add_paragraph()
        p2.text = desc_fw
        p2.font.size = Pt(9)
        p2.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 26 — THANK YOU / QUESTIONS & DISCUSSION
    # =========================================================================
    slide26 = add_blank_slide(bg_color=RGBColor(15, 23, 42)) # Deep Navy
    
    # Place College Logo Centered
    if os.path.exists(LOGO_PATH):
        slide26.shapes.add_picture(LOGO_PATH, Inches(5.95), Inches(0.9), height=Inches(1.4))

    # College Name
    tb = slide26.shapes.add_textbox(Inches(1.0), Inches(2.45), Inches(11.333), Inches(0.6))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "RAJALAKSHMI ENGINEERING COLLEGE"
    p.alignment = PP_ALIGN.CENTER
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)

    p2 = tf.add_paragraph()
    p2.text = "Department of Artificial Intelligence and Machine Learning"
    p2.alignment = PP_ALIGN.CENTER
    p2.font.size = Pt(13)
    p2.font.color.rgb = COLOR_GOLD

    # Thank You & Q&A
    tb_ty = slide26.shapes.add_textbox(Inches(1.2), Inches(3.4), Inches(10.933), Inches(1.5))
    tf_ty = tb_ty.text_frame
    tf_ty.word_wrap = True
    p = tf_ty.paragraphs[0]
    p.text = "THANK YOU!"
    p.alignment = PP_ALIGN.CENTER
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = RGBColor(56, 189, 248) # Cyan

    p_qa = tf_ty.add_paragraph()
    p_qa.text = "Questions & Discussion"
    p_qa.alignment = PP_ALIGN.CENTER
    p_qa.font.size = Pt(20)
    p_qa.font.bold = True
    p_qa.font.color.rgb = RGBColor(241, 245, 249)

    # Project title recap banner
    tb_pr = slide26.shapes.add_textbox(Inches(1.5), Inches(5.3), Inches(10.333), Inches(1.2))
    tf_pr = tb_pr.text_frame
    tf_pr.word_wrap = True
    p = tf_pr.paragraphs[0]
    p.text = "SupplyChainAI: An Autonomous Multi-Agent System for Resilient Supply Chain Re-Planning"
    p.alignment = PP_ALIGN.CENTER
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = RGBColor(148, 163, 184)

    p_c = tf_pr.add_paragraph()
    p_c.text = "Final Year Engineering Project  •  Academic Year 2025–2026"
    p_c.alignment = PP_ALIGN.CENTER
    p_c.font.size = Pt(11)
    p_c.font.color.rgb = COLOR_GOLD

    # Save presentation
    output_filename = "SupplyChainAI_Final_Year_Project_Presentation.pptx"
    prs.save(output_filename)
    print(f"Presentation generated successfully: {output_filename}")
    print(f"Total Slides: {len(prs.slides)}")

if __name__ == "__main__":
    create_presentation()
