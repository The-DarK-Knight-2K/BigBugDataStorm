# Technical Judge Question Bank: BigBugDataStorm

As a technical data scientist judge, the goal is to probe the team's understanding of their own architecture, validate their design choices, and test if they have considered industry-standard edge cases. This question bank is divided into six core domains representing the end-to-end solution.

---

## 1. Data Engineering & Medallion Architecture

**Q1: "You mentioned that you never silently drop records and instead route failures to a 'Quarantine' schema. How do you handle scenarios where an outlet's coordinates are quarantined, but you still need to generate a prediction for them in January 2026?"**
> **Expected Answer:** We implemented a fallback imputation strategy. For outlets with zero-coordinates (or out-of-bounds coordinates), we impute the location using the **province centroid** derived from the outlet's `distributor_id`. Crucially, we use an `exclude_from_training` flag: these imputed outlets are scored during inference so we don't miss their volume, but we *exclude them from training* to prevent the model from learning false spatial patterns (target leakage).
> **Probing Follow-up:** "If an outlet is missing a distributor ID, how do you handle seasonality mapping for it?" *(Answer: We fallback to the 'Moderate' seasonality multiplier / global mode).*

**Q2: "Your pipeline uses a daily/monthly synthesized temporal grid for sales. How did you differentiate between an outlet that genuinely sold 0 liters in a month versus an outlet where the data was just missing or corrupted (a blackout)?"**
> **Expected Answer:** We developed a specific blackout detection logic. A genuine 0 is often a single dormant month at the end of the timeline, whereas we flag a "blackout" when there's an artificial gap in the timeline sandwiched between active months. In `clean_transactions.py`, we identify these blackout periods and explicitly exclude them from aggregate calculations (like `hist_mean_monthly` or `recent_3m_avg`) to prevent an unfair downward bias on the outlet's profile.

---

## 2. Feature Engineering & Spatial Methods

**Q3: "You replaced standard K-Means or flat radius counts with DBSCAN for micro-market clustering. Why didn't you just use K-Means, and what specific advantage did DBSCAN give your models?"**
> **Expected Answer:** We found that K-Means forces spherical clusters of roughly equal size, which completely fails to capture real-world retail topographies—like shops strung along a highway or dense, irregular city centers. DBSCAN clusters based purely on *density*, allowing for arbitrary shapes. It also naturally identifies isolated rural outlets as "noise" (assigning them a `micro_market_id = -1`), giving our models a much more accurate spatial context of the neighborhood.
> **Probing Follow-up:** "How did you set the `eps` (epsilon) parameter for DBSCAN? In a country with both highly dense cities and sparse rural areas, a static `eps` can struggle."

**Q4: "I see you used 'Reilly’s Law of Retail Gravitation' (Inverse-Square Gravity) for POI features instead of simple counts. But you added an `Epsilon` of 0.05 km to the denominator. Mathematically, why is that Epsilon critical, and what happens if you remove it?"**
> **Expected Answer:** We added the Epsilon term to prevent division by zero. If a POI and an outlet share the exact same coordinates (distance = 0), `1 / distance^2` mathematically goes to infinity. Setting Epsilon to 0.05 km (50m) caps the maximum possible attraction score, stabilizing the feature and reflecting the physical reality that "at the door" has a finite, but very high, maximum value.

**Q5: "You modeled a 'Physics-Based Capacity Ceiling' based on cooler counts. How do you handle the edge case of an outlet with 0 coolers that still has historical sales volume?"**
> **Expected Answer:** We explicitly handled this edge case. A 0-cooler outlet mathematically yields a 0 volume ceiling, which would cause a divide-by-zero error when we calculate the `capacity_utilization_ratio`. We solve this by clipping the denominator to a minimum of 1.0, and explicitly setting the utilization ratio to 0.0 for these outlets. This allows the model to learn that non-cooler sales (perhaps room-temperature products or bulk storage) behave differently than cooler-constrained sales.

---

## 3. Advanced Modelling (Tobit & Hurdle)

**Q6: "You utilized a Tobit Model for censored regression. Why was traditional OLS (Ordinary Least Squares) or a standard XGBoost inadequate for modeling historical sales in this specific context?"**
> **Expected Answer:** We recognized that historical sales data is **right-censored** by the physical cooler capacity. We don't observe the true *latent demand*; we only observe sales up to the point where the cooler goes empty. Standard regression algorithms treat the physical ceiling as the true maximum demand, which downward-biases the predictions. We used Tobit specifically because it estimates the unobserved latent demand *beyond* the physical threshold, showing us what the outlet could sell if given more capacity.
> **Probing Follow-up:** "Since Tobit is fundamentally a linear/parametric model, how did you integrate its outputs with your non-linear tree ensembles (XGB/LGBM)?" *(Answer: Tobit predictions are used as a meta-feature/input into the tree models, or blended).*

**Q7: "Explain your rationale for using a Two-Stage Hurdle model for zero-inflation. Why not just let the gradient boosting trees handle the zeros naturally?"**
> **Expected Answer:** We observed that tree models struggle when a massive portion of the target variable is exactly zero, as they attempt to split continuous distributions and end up predicting tiny fractional volumes for dead shops. We utilized a Hurdle model because it separates the problem into two distinct business questions: 1) Probability of being active (a Binary Classifier), and 2) Conditional volume given they are active (a Regressor). This allows us to use different feature sets to drive the binary "dormancy" prediction versus the continuous "volume" prediction.

---

## 4. Operations Research & Optimization

**Q8: "For budget allocation, you used a Tier-Capped Greedy Knapsack algorithm instead of a standard Linear Programming (LP) solver like PuLP or Gurobi. Why use a greedy heuristic here?"**
> **Expected Answer:** We chose a greedy Knapsack approach because, given 20,000 outlets, an exact LP solver can be computationally expensive. More importantly, a raw ROI-based LP tends to over-allocate the entire budget to a tiny fraction of top-performing supermarkets, completely starving rural areas. Our "Tier-Capped" greedy approach allows us to efficiently enforce strict business rules—like distributor caps and minimum spend floors per tier—while still sorting investments by marginal ROI.
> **Probing Follow-up:** "How do you define the 'value' or 'ROI' of allocating budget to a specific outlet in your Knapsack formulation?"

---

## 5. GenAI & Explainability (XAI)

**Q9: "Your Next.js dashboard uses Gemini to translate SHAP values into plain English. SHAP values are marginal contributions in log-odds or scaled units. How do you ensure the LLM doesn't hallucinate incorrect business drivers from abstract mathematical values?"**
> **Expected Answer:** We ensure accuracy through strict prompt engineering and context structuring. We don't just send raw SHAP arrays to Gemini; we pre-process the SHAP values into a structured JSON payload that maps feature names to directional impacts and real-world values (e.g., "Feature: competitors_1km, SHAP: -0.4, Real Value: 40"). We use strict System Prompts locking Gemini into interpreting *only* the provided data matrix as a Senior Business Analyst, banning all ML jargon and external assumptions.
> **Probing Follow-up:** "What happens when the Gemini API goes down or hits rate limits during a live field operation?" *(Answer: We built a deterministic, rule-based fallback generator that parses the data locally via SQLite to ensure the rep always gets a negotiation plan).*

**Q10: "If a business stakeholder asks: 'Your model predicts 5,000L for this outlet, but last January they only sold 2,000L.' How does your system explain that delta?"**
> **Expected Answer:** Our dashboard's XAI module directly highlights the specific feature drifts or spatial advantages that drove that delta. For example, the GenAI briefing might explain a massive positive SHAP contribution from `hospital_gravity_score` because a new hospital opened nearby. Alternatively, it might explain that while `capacity_utilization_ratio` was maxed out previously at 2,000L, our Tobit model recognized high latent demand, justifying a 5,000L target if we use the marketing budget to provide a Cooler Grant.

---

## 6. Business Application & Technical Bridging

**Q11: "How does your technical optimization of the 5M LKR budget align with realistic business constraints, such as not alienating specific regional distributors?"**
> **Expected Answer:** While a pure mathematical ROI optimization might dump the entire 5M LKR budget into the top 10 supermarkets in Colombo, we knew that wouldn't survive contact with the real business. We built a 'Tier-Capped' approach. We enforce minimum spend floors across tiers (High, Medium, Low) and strict distributor concentration caps. This guarantees a balanced portfolio investment across the province, growing small shops while uncapping high-volume outlets, which is much more palatable to regional sales managers and avoids distributor monopolies.

**Q12: "Your Next.js dashboard uses GenAI to explain model outputs. Why build an entirely custom frontend instead of just presenting the ML outputs in a standard BI tool like Tableau or PowerBI?"**
> **Expected Answer:** We realized that the best ML model is useless if the frontline sales rep doesn't understand it. BI tools show charts; we needed to provide *actionable strategy*. By feeding our SHAP values through Gemini, we translate abstract metrics (like `cooler_utilization = 0.94`) into a plain-English negotiation plan (e.g., 'Offer a Cooler Grant to unlock 650L of lost sales'). Furthermore, our Next.js app runs on a highly optimized SQLite database, requiring zero cloud database infrastructure. This makes it incredibly fast, portable, and easily deployable for field teams compared to heavy enterprise BI software.

**Q13: "In your system architecture, you have a 'Baseline Safety Floor' overriding the ML predictions in some cases. Doesn't this mean you don't trust your own models? Why is this necessary for the business?"**
> **Expected Answer:** We trust our models to find hidden demand, but we also understand the massive business cost of an ML hallucination. If a historically strong outlet has a short data anomaly or is a cold-start, tree models might severely under-predict demand. Sending an empty delivery truck to a strong customer loses guaranteed revenue and damages the relationship. The Baseline Safety Floor is a rule-based safety net that guarantees we never under-supply an outlet below its proven historical capability. We explicitly engineered the system to prioritize revenue protection over pure algorithmic purity.
