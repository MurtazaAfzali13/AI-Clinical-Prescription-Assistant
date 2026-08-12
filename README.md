## 🧠 Multi-Agent CDSS Architecture

The core graph is a **dynamically routed, conditionally parallel multi-agent system (MAS)**. It utilizes a Smart Supervisor to minimize latency and API costs, running complex clinical analyses only when necessary. The pipeline features deterministic math tools, namespace-isolated RAG, and a fail-closed reflection gate to strictly prevent LLM hallucinations.

```mermaid
flowchart TD
    START(["▶ START"]) --> EXT

    EXT["📝 <b>extractor</b><br/><span style='font-size:11px'>raw note → structured JSON</span>"]
    EXT --> MODE{"⚙️ <b>mode_router</b><br/><span style='font-size:11px'>use_copilot_mode?</span>"}

    MODE -- "False (Fast Mode)" --> FAST_SFT["💊 <b>safety_checker</b><br/><span style='font-size:11px'>DDI check only (1-2s)</span>"]
    FAST_SFT --> REV

    MODE -- "True (Copilot Mode)" --> SUP["🎯 <b>supervisor</b><br/><span style='font-size:11px'>dynamic fan-out routing</span>"]

    SUP -.-> SFT["💊 <b>safety_checker</b><br/><span style='font-size:11px'>Pinecone: drug-interactions</span>"]
    SUP -.-> LAB["🧬 <b>lab_context</b><br/><span style='font-size:11px'>Supabase: eGFR, weight, age</span>"]
    SUP -.-> CON["🛑 <b>contraindication</b><br/><span style='font-size:11px'>Pinecone: disease conflicts</span>"]
    SUP -.-> GDL["📚 <b>guideline</b><br/><span style='font-size:11px'>Pinecone: clinical protocols</span>"]

    LAB -. "renal adjustment" .-> DOS["🧮 <b>dose_validator</b><br/><span style='font-size:11px'>deterministic Python math</span>"]

    SFT --> GATE
    DOS --> GATE
    CON --> GATE
    GDL --> GATE

    GATE{"⚖️ <b>reflection_gate</b><br/><span style='font-size:11px'>wait for all parallel nodes</span>"}
    GATE -- "Warnings Found" --> ALT["💡 <b>alternative_therapy</b><br/><span style='font-size:11px'>suggest safer options</span>"]
    GATE -- "All Clear" --> REF

    ALT --> REF["🛡️ <b>reflection_node</b><br/><span style='font-size:11px'>resolve conflicts (fail closed)</span>"]

    REF --> REV["📊 <b>reviewer</b><br/><span style='font-size:11px'>format EvidenceObjects</span>"]

    REV --> END(["⏹ END"])

    classDef node fill:#f3e8ff,stroke:#a855f7,stroke-width:1.5px,color:#3b0764,font-weight:600,rx:8,ry:8;
    classDef decision fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#3b0764,font-weight:700;
    classDef terminal fill:#a855f7,stroke:#6b21a8,stroke-width:2px,color:#ffffff,font-weight:700;
    class EXT,SUP,SFT,LAB,DOS,CON,GDL,ALT,REF,REV,FAST_SFT node;
    class MODE,GATE decision;
    class START,END terminal;
⚠️ Note on dose_validator: This node explicitly does not use LLMs for mathematical calculations. It relies on the lab_context node to fetch patient weight and renal function (eGFR), and then executes a deterministic Python tool to calculate the exact dosage. This eliminates the risk of AI math hallucinations.

⚡ Specialized Clinical Agents & Pipeline Nodes
📝 1. Extractor Node
The entry point of the pipeline. Transforms the physician's free-text or dictated note into a strict structured JSON payload (PrescriptionExtraction). It normalizes drug names, frequencies, and extracted patient demographics before routing.

🎯 2. Mode Router & Supervisor Node — cost & latency optimizer
Evaluates the use_copilot_mode flag. If False (Fast Mode), the graph bypasses heavy LLM reasoning and strictly checks for Drug-Drug Interactions (DDI), executing in ~1.5 seconds. If True (Copilot Mode), the Supervisor dynamically decides which specialized clinical agents to wake up based on patient complexity (e.g., pediatric vs. adult, chronic vs. acute).

🧬 3. Clinical Context (Lab) Node — Supabase Integration
Executes secure, RLS-bypassing database queries to fetch the patient's full clinical context. Retrieves recent lab results (eGFR, Liver enzymes), age, weight, and active comorbidities. No LLM generation occurs here; it strictly passes validated SQL data to the graph state.

💊 4. Safety & Contraindication Nodes — Pinecone Isolated RAG
Performs vector similarity searches against medical databases. To prevent context contamination, searches are strictly isolated by namespaces (namespace="drug-interactions" and namespace="contraindications"). Returns exact guideline citations and confidence scores.

🧮 5. Dose Validator Node — deterministic safety
Waits for the lab_context node to complete. Uses extracted weight and renal data to run absolute, deterministic Python math functions to calculate safe dosage ranges. Flags any prescription exceeding standard limits.

💡 6. Alternative Therapy Node — actionable UI alerts
Triggered by the reflection_gate only if warnings are detected in the parallel agents. Instead of simply blocking a prescription, it queries the clinical-guidelines namespace to suggest safer, medically approved alternatives (e.g., suggesting Linagliptin if Metformin is flagged for low eGFR).

🛡️ 7. Reflection Node — The Attending Physician
Acts as the ultimate safety guardrail (Fan-in node). Reviews the outputs from all parallel agents to resolve contradictions. Implements a Fail Closed architecture: if agents disagree or evidence is weak, it defaults to blocking the prescription, enforcing a Human-in-the-Loop (HITL) mandatory override.

📊 8. Reviewer Agent
Formats the final graph state into strict EvidenceObject structures. Ensures every warning sent to the Next.js frontend includes a definitive source, clinical_reason, and confidence_score to populate the UI Accordion components cleanly.