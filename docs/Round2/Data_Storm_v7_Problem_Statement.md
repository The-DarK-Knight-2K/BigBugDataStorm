# DATA STORM V 7.0
**Critical Analysis - Inspired Solutions**

**Data Storm v7.0 - Final Round**

**Organized By:** Rotaract Club of University of Moratuwa
**Powered By:** OCTAVE - John Keells Group

---

## Table of Contents

| Section | Page |
| :--- | :--- |
| 1. Background | 2 |
| 1.1. Bridge from Preliminary Round | 2 |
| 1.2. Business Context | 2 |
| 1.2. Current Scope | 3 |
| 2. Advanced Problem Statement | 4 |
| 2.1. Spatial Distance-Decay Modeling | 4 |
| 2.2. Competitive Catchment Density | 4 |
| 2.3. Marketing Spend Optimization | 5 |
| 3. Data Description | 6 |
| 4. Advanced Technical and Architecture Requirements | 7 |
| 4.1. Functional Explainable AI (XAI) Integration | 7 |
| 5. Final Deliverables | 8 |
| 6. Evaluation Metrics | 11 |

---

## 1. Background

### 1.1. Bridge from Preliminary Round
Welcome to the Final Round of Data Storm v7.0. Out of highly competitive preliminary submissions, your team has successfully proven its core data science logic, programmatic data forensics, and foundational Lakehouse architecture.

In Phase 1, your focus was on uncovering historical data anomalies and establishing an initial unconstrained baseline. Now, the challenge has evolved. Your task is to transform those preliminary pipelines into an enterprise-grade decision engine. Leadership is no longer looking for a standalone predictive metric; they expect a comprehensive solution that converts volume potential into actionable trade marketing strategies. This solution must be backed by intuitive user interfaces, automated explainability, and seamless decision-support capabilities.

### 1.2. Business Context
A leading beverage manufacturer in Sri Lanka operates a massive distribution network spanning over 80,000 traditional retail outlets from bustling urban grocery stores in Colombo to small "kades" (corner shops) and local eateries in rural outstations.

Currently, sales teams allocate trade marketing budgets, coolers, and promotional discounts based on historical sales averages. However, leadership realizes this is fundamentally flawed. Historical sales only reflect what an outlet did sell, not what it could sell. A high-traffic town-center kade might be underperforming due to poor stock management or credit constraints, while a small village shop might already be maxed out.

The company wants to shift from historical-based resource allocation to Potential-Based Allocation. They need to predict the Maximum Monthly Purchase Potential of every traditional trade outlet to optimize trade spend and cooler deployments.

### 1.2. Current Scope
For this challenge, we are focusing on 20,000 traditional trade outlets (kades, groceries, eateries, pharmacies, etc.) serviced by 10 key distributors across 4 key provinces in Sri Lanka.

| Province | # Distributors | Distributor IDs |
| :--- | :--- | :--- |
| Western | 3 | 'DIST_W_01', 'DIST_W_02', 'DIST_W_03' |
| Central | 3 | 'DIST_C_01', 'DIST_C_02', 'DIST_C_03' |
| North-Western | 2 | 'DIST_NW_01', 'DIST_NW_02' |
| Southern | 2 | 'DIST_S_01', 'DIST_S_02' |

---

## 2. Advanced Problem Statement

Your main objective is to build an analytical solution that estimates the maximum possible sales volume for January 2026 while considering real-world business limitations and decision-making factors. In Phase 1, you mainly focused on identifying unusual patterns in historical data and building an initial analytical solution. In this phase, your solution should go beyond prediction and help support actual business decisions.

Your solution should consider the following challenges (Well done if you have already done these, but you can always improve your work):

### 2.1. Spatial Distance-Decay Modeling
Simply counting nearby Points of Interest (POIs) within a fixed radius is not enough for a strong real-world model. Instead, you should treat distance as an important factor. This means closer places should have a stronger influence than distant ones. For example, a bus stops 20 meters away should have a much bigger impact on demand than one 400 meters away, even though both are "within range."

To do this properly, you should apply non-linear methods such as distance-decay functions (for example, Gravity Models, Gaussian decay, or exponential decay). These methods gradually reduce the influence of a location as distance increases, instead of treating everything equally inside a boundary. If you already implemented distance-decay in the preliminary round, you should further improve and fine-tune it in this phase.

### 2.2. Competitive Catchment Density
You should also consider how many competing outlets exist around each location. This helps estimate how "crowded" or "isolated" a store is in its local market. An outlet located in a dense commercial area with many nearby competitors will behave differently from one in a less crowded or rural-like area with little competition.

Your task is to use external location data to estimate this level of competition and market saturation. Based on this, adjust your model to reflect whether an outlet operates in a highly competitive cluster or in a relatively untapped market area.

### 2.3. Marketing Spend Optimization
Assume the company has allocated a fixed promotional budget of LKR 5 million for the Western Province for January 2026.

Your task is to create a program or optimization model that uses your predicted sales potential values to decide how this budget should be distributed among distributors and outlets. This may include assigning discounts, merchandising (Billboards, posters) incentives, or promotional spending to selected outlets. 

The goal is to maximize the additional sales volume gained compared to normal historical sales patterns, while ensuring the total spending does not exceed the LKR 5 million budget.

---

## 3. Data Description

Finalists will continue utilizing the exact same internal datasets provided in Phase 1:
1. `transactions_history_final.csv`: Granular outlet-level data.
2. `outlet_master.csv`: Outlet related data.
3. `outlet_master.csv`: Longitude and Latitude for each outlet. (Note: As stated in the document)
4. `distributor_seasonality_details.csv`: Month specific seasonality for distributors.
5. `holiday_list.csv`: List of holidays

However, expectations for the External Data Layer (Gold Enrichment) are significantly raised.

---

## 4. Advanced Technical and Architecture Requirements

All requirements from the Preliminary Round remain fully in effect. Your solution must continue to follow a clear Medallion Lakehouse architecture (Bronze → Silver → Gold), ensure strict pipeline idempotency, and apply reusable data quality checks at every stage. Any corrupted or invalid records must be systematically routed to a dedicated Rejected Records Store for traceability and debugging.

### 4.1. Functional Explainable AI (XAI) Integration
In this phase, Generative AI should not be treated as a backend logging tool. Instead, it must become a user-facing layer that explains model decisions in simple business terms.

You are required to embed a Dynamic Explainability (XAI) module directly into your solution pipeline. This module should be used for each outlet:
* Its predicted sales score
* Key model drivers (feature importance / weights)
* Local environment signals (e.g., POI density, competitor intensity)
* Operational constraints (e.g., cooler capacity, supply limits, historical performance patterns)

Then, an LLM-based component should transform this technical information into a clear, human-readable explanation. The output should be explained, in simple business language:
* Why did the model give that outlet its specific score
* Which factors increased or decreased the prediction
* How local conditions and constraints influenced the result

The goal is to translate complex statistical and spatial signals into an intuitive narrative that non-technical business leaders can easily understand and trust.

---

## 5. Final Deliverables

This challenge reflects a real-world end-to-end data science and data engineering problem. There is no hidden "correct answer" to optimize toward. Instead, evaluation will be based entirely on the quality of your approach, including your pipeline design, analytical rigor, and business reasoning.

The final teams will be required to submit the following five deliverables:

1. **The "Latent Potential" Output (CSV):** A single file containing your final, uncapped volume predictions (`teamname_predictions.csv`). It must include `Outlet_ID` and your predicted `Maximum_Monthly_Liters` for the month of January 2026.
2. **The Marketing Spent Allocation Output (CSV):** A single file containing trade allocation for the outlets in Western province (`teamname_budget_allocations.csv`). It must contain `Outlet_ID` and another column with your recommended Trade Spend Allocation (LKR) from the optimization task.
3. **The Enterprise Codebase (GitHub Link or Zipped Repo):** Your complete code (Python scripts / Jupyter Notebooks) used for data cleaning, POI scraping, and modeling. You must include a `README.md` with clear instructions on how to run your pipeline end to end. (Extended version of your preliminary round code base)
4. **The Outlet Intelligence Web App:** A functional web application that allows business users to explore and interact with the model outputs. Teams are free to choose any technology stack. The app must be runnable locally with setup instructions provided in the `README.md`.
    The app should support:
    a. Browsing outlet-level predictions across the full dataset.
    b. Filtering by distributor and/or province.
    c. Drilling into a specific outlet to view its predicted potential and the reasoning behind the score.
5. **The Comprehensive Methodology and Technical Paper (PDF):** A comprehensive technical document (max 10 pages, including the cover page) explicitly detailing your end-to-end analytical pipeline.
    This document must explicitly address the following:
    a. **Data Engineering and Scraping Pipeline:** Detail your approach to acquiring external POI data (web scraping, Overpass API, etc.). What specific features did you engineer to proxy footfall and market potential?
    b. **Data Cleaning:** Provide a summary of your initial data quality assessment. Document the exact programmatic steps you took to clean the "dirty" master data and neutralize the system artifacts.
    c. **The Mathematical Framework:** Explain your core logic. What statistical, causal, or probabilistic methods did you use to handle the left-censored demand and "uncap" the artificial ceilings?
    d. **Spend Optimization Logic:** Mathematical constraints and allocation strategies applied to the 5M budget.
    e. **GenAI Transparency Log:** A dedicated section outlining how, where, and why you utilized Generative AI (e.g., Gemini, Copilot, ChatGPT) during the hackathon. We want to see how you used AI as an advanced thought partner, including your most effective prompts.
6. **The Executive Pitch Deck (PDF):** A presentation deck outlining your approach, designed for a non-technical C-suite audience and should include:
    a. Explain how your framework successfully unmasked the outlet potential without relying on dense mathematical jargon.
    b. Clearly demonstrate how you have strategically divided the trade marketing spend across the Western province outlet network using your new Potential-Based Allocation model.
    c. Quantify the strategic business impact, highlighting projected incremental volume gains, regional growth opportunities, and the overall financial efficiency of your proposed distribution strategy.
    d. A brief overview of how this allocation strategy can be practically rolled out to the sales teams and distributors on the ground.
    
    *Strictly capped at 10 slides. Finalists will present this deck on a 10-minute pitch, followed by a 5-minute live system demonstration and technical Q&A session.*

---

## 6. Evaluation Metrics

The judging panel of data scientists, data engineers and business leaders will evaluate teams on following criteria:

| Criteria | Weight |
| :--- | :--- |
| Methodology and Framework Design | 30% |
| Data Engineering and Feature Creation | 30% |
| Business Viability and Explainability | 25% |
| Generative AI Utilization and Workflow | 15% |

**1. Data Engineering and Feature Creation (30%)**
* Is the codebase demonstrably structured into distinct Bronze, Silver, and Gold layers with an effective quarantine pattern?
* Are data quality checks parameterized, reusable, and applied consistently across multiple internal and external data tables?
* How robust is the POI pipeline, and did the team successfully translate spatial proximity into non-linear signals (gravity/decay models) rather than flat counts?

**2. Methodology and Base Math (30%)**
* How successfully did the team conceptualize and isolate unobserved "Latent Potential" from historical records?
* What advanced modeling approaches (e.g., Tobit regression, hurdle models, spatial clustering) were deployed to solve right/left-censored data mechanics?
* Are the physical constraints of traditional retail trade (cooler replenishment cycles) logically represented within the math?

**3. Business Viability and UI Delivery (25%)**
* Does the 5M LKR promotional spend allocation logic make practical commercial sense to maximize absolute volume lifts?
* Is the web application highly functional, intuitive, and capable of displaying localized intelligence quickly?
* Did the team present a clear, compelling corporate narrative during their live pitch that justifies algorithmic outputs to non-technical leadership?

**4. Generative AI Utilization and Workflow (15%)**
* Did the team build a working, dynamic XAI prompt integration inside the web app that generates accurate, highly contextualized business reasoning?
* Is the GenAI Transparency Log comprehensive, clear, and honest about prompts used across the development pipeline?
* Is there explicit evidence that the team rigorously validated and iteratively engineered AI output rather than blindly accepting generated logic?
