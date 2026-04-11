# Predicting Maximum Reaction Probability for Context-Aware Health Nudges

> **Summary.** Given 30 days of interaction data from 3,000 members across 25 nudge types, predict which nudge type maximizes the probability of a positive reaction (act_now) for a specific individual. The recommended approach is a two-stage hybrid: (1) an offline logistic regression that learns population-level patterns and produces calibrated probabilities, and (2) an online Thompson Sampling bandit that personalizes nudge selection per member using Beta-distributed posteriors warm-started from the logistic regression. Safety-sensitive nudge types (distress escalation, medication reminders) are excluded from optimization entirely and remain under deterministic clinical rules. Fatigue constraints (daily caps, cooldowns) act as hard guardrails over the model. The design prioritizes interpretability, calibration, and clinical defensibility over marginal accuracy—logistic regression is chosen over gradient boosting or deep learning because every nudge decision must be explainable in a clinical review. Key tradeoffs addressed: where the boundary between rules and ML should sit, how to bound exploration risk in a health context, how to handle cold-start members, and when the model should abstain from nudging altogether.

## 1. Problem Statement

### Objective

Given a member and their recent behavioral history, select the nudge type—from a taxonomy of 25—that maximizes the probability of a positive reaction.

Formally: for member $i$, find

$$\arg\max_{j \in \{1 \ldots 25\}} \; P(\text{act\_now} \mid \text{member}_i, \text{nudge}_j, \text{context}_t)$$

where $\text{context}_t$ captures the member's current state—recent signals, time of day, engagement recency, mood—at the moment the system decides whether and what to nudge.

### Data Regime

The dataset consists of interaction records from 3,000 members, each receiving nudges across 25 types over a 30-day window. With daily caps of 1–2 nudges per member per day, this yields roughly 90,000–150,000 total interactions. The matrix of (member × nudge type) is sparse: most members will have interacted with only 4–8 of the 25 types, and some nudge types will have very few observations across the population.

This sparsity is a defining constraint. It eliminates approaches that require dense per-member-per-type histories and instead favors models that can share statistical strength across similar members, similar nudge types, or both.

### Defining "Reaction"

A **reaction** is an explicit positive commitment: the member selects "act now" (or its equivalent) in response to a delivered nudge. Dismissals and ignored nudges are treated as non-reactions. The binary outcome is:

- $y = 1$: member selected act_now
- $y = 0$: member dismissed, ignored, or the nudge expired

This framing deliberately excludes "ask for help" as a positive signal. While asking for help is a valuable engagement event, it typically indicates the member is not in a position to self-serve on the nudge's suggestion. Treating it as a reaction would conflate genuine commitment with a request for human support, which would distort nudge-type optimization toward nudge types that provoke confusion or distress rather than action.

---

## 2. Nudge Taxonomy

### Proposed 25-Type Taxonomy

The existing system operates with 3 nudge types (meal guidance, weight check-in, support risk). Scaling to 25 requires a taxonomy that is clinically plausible, sufficiently granular for personalization, and narrow enough that each type accumulates enough observations for learning.

The taxonomy below is organized into 5 categories. Each category groups nudge types that share a behavioral domain, which matters for the algorithm: when per-type data is sparse, the model can fall back to category-level estimates.

| #   | Category   | Nudge Type             | Description                                       |
| --- | ---------- | ---------------------- | ------------------------------------------------- |
| 1   | Nutrition  | meal_guidance          | Suggest a meal adjustment based on recent intake  |
| 2   |            | meal_prep_tip          | Proactive meal planning for the next day          |
| 3   |            | hydration_reminder     | Water intake nudge based on activity or weather   |
| 4   |            | snack_swap             | Suggest a healthier snack alternative             |
| 5   |            | portion_awareness      | Portion-related feedback after a logged meal      |
| 6   | Activity   | step_goal_nudge        | Encourage daily step target progress              |
| 7   |            | movement_break         | Suggest a break during long sedentary periods     |
| 8   |            | workout_suggestion     | Recommend a workout based on recent activity      |
| 9   |            | activity_streak        | Celebrate or encourage a consecutive-day streak   |
| 10  |            | recovery_day           | Suggest rest after high-intensity periods         |
| 11  | Wellness   | mood_check_in          | Prompt a mood log when none is recent             |
| 12  |            | sleep_nudge            | Sleep hygiene suggestion based on recent logs     |
| 13  |            | stress_management      | Guided breathing or mindfulness prompt            |
| 14  |            | support_risk           | Escalation to coach for safety-sensitive patterns |
| 15  |            | gratitude_prompt       | Positive psychology micro-intervention            |
| 16  | Compliance | weight_check_in        | Remind to log weight after gap                    |
| 17  |            | medication_reminder    | Prompt for medication adherence log               |
| 18  |            | appointment_prep       | Pre-appointment checklist or context              |
| 19  |            | lab_result_review      | Prompt to review recent lab results               |
| 20  |            | goal_reflection        | Weekly reflection on goal progress                |
| 21  | Social     | peer_milestone         | Share or celebrate a peer's achievement           |
| 22  |            | community_challenge    | Invite to a group challenge                       |
| 23  |            | coach_message_prompt   | Encourage reading a coach's recent message        |
| 24  |            | accountability_partner | Suggest connecting with an accountability buddy   |
| 25  |            | progress_share         | Prompt to share a personal milestone              |

**Important caveat:** This taxonomy is a structural proposal. In production, the final list requires clinical and product validation. The algorithm design does not depend on the specific 25 types—only on the number, the category groupings, and the assumption that types within a category share behavioral affinity.

### Category-Level vs. Type-Level Prediction

A key early decision: should the model predict reaction probability per nudge type (25 targets) or per category (5 targets)?

**Per-type** is more precise—if Alice responds well to hydration reminders but not snack swaps, per-type modeling captures that. But with 3,000 members and 25 types, many (member, type) pairs will have zero or one observation in 30 days. The model can't learn individual preferences from a single data point.

**Per-category** is statistically robust—each category accumulates 5× more data—but loses within-category variation. If all Nutrition nudges are treated as equivalent, the system can't distinguish meal prep tips (which Alice likes) from portion awareness (which she dismisses).

The recommended approach is **hierarchical**: predict at the category level for selection, then use within-category type-level priors (from population data) to pick the specific type. This is detailed in Section 5.

---

## 3. Feature Engineering

Features are grouped into four families. Each family captures a different dimension of the prediction problem, and the separation matters for understanding what drives the model's decisions.

### 3.1 Member Features (Who)

These describe the member's profile and historical engagement. They change slowly (daily or weekly updates).

| Feature                   | Type        | Description                                                                      |
| ------------------------- | ----------- | -------------------------------------------------------------------------------- |
| `goal_type`               | Categorical | Member's stated health goal (e.g., low carb, weight loss, balanced)              |
| `tenure_days`             | Numeric     | Days since account creation                                                      |
| `signal_frequency_7d`     | Numeric     | Average signals logged per day over the last 7 days                              |
| `historical_act_rate`     | Numeric     | Fraction of all past nudges where member selected act_now                        |
| `historical_dismiss_rate` | Numeric     | Fraction of all past nudges where member dismissed                               |
| `preferred_category`      | Categorical | Category with the highest historical act rate                                    |
| `engagement_trend`        | Numeric     | Slope of act rate over last 14 days (positive = improving, negative = declining) |
| `days_since_last_signal`  | Numeric     | Recency of any signal submission                                                 |

### 3.2 Nudge Features (What)

These describe the nudge type being considered. They are population-level statistics, updated daily in batch.

| Feature                      | Type        | Description                                                                               |
| ---------------------------- | ----------- | ----------------------------------------------------------------------------------------- |
| `nudge_category`             | Categorical | One of the 5 categories                                                                   |
| `population_act_rate`        | Numeric     | Global act_now rate for this nudge type across all members                                |
| `category_act_rate`          | Numeric     | Global act_now rate for this category                                                     |
| `avg_relevance_window_hours` | Numeric     | Typical time window in which this nudge type is contextually relevant                     |
| `fatigue_sensitivity`        | Numeric     | How much repeated exposure to this type reduces act rate (estimated from population data) |

### 3.3 Contextual Features (When)

These describe the member's current state at the moment of nudge delivery. They change per evaluation.

| Feature                          | Type           | Description                                              |
| -------------------------------- | -------------- | -------------------------------------------------------- |
| `hour_of_day`                    | Numeric (0–23) | Local hour when nudge would be delivered                 |
| `day_of_week`                    | Categorical    | Monday through Sunday                                    |
| `hours_since_last_nudge`         | Numeric        | Time since last nudge of any type                        |
| `hours_since_last_same_category` | Numeric        | Time since last nudge of the same category               |
| `current_mood`                   | Categorical    | Most recent mood signal (low / neutral / high / unknown) |
| `recent_signal_count_24h`        | Numeric        | Number of signals logged in the last 24 hours            |
| `active_streak_days`             | Numeric        | Consecutive days with at least one act_now               |

### 3.4 Interaction Features (Who × What × When)

These capture member-specific nudge preferences that static features miss. They are the most predictive but also the most prone to sparsity.

| Feature                        | Type    | Description                                                                                                             |
| ------------------------------ | ------- | ----------------------------------------------------------------------------------------------------------------------- |
| `member_category_act_rate`     | Numeric | This member's act rate for this specific category                                                                       |
| `member_category_act_count`    | Numeric | Number of times this member has acted on this category (used to weight the rate)                                        |
| `member_time_of_day_act_rate`  | Numeric | This member's act rate split by morning / afternoon / evening                                                           |
| `member_engagement_x_category` | Numeric | Interaction between engagement trend and category (captures: is this member's interest in Nutrition rising or falling?) |

**Feature engineering tradeoff:** More interaction features improve personalization but increase sparsity and overfitting risk. At 30 days of data, the interaction features are useful only for members with 10+ interactions. For newer or less active members, the model should rely on member-level and population-level features and ignore interaction features (or regularize them heavily). This is handled naturally by L2 regularization in logistic regression.

---

## 4. Synthetic Data Generation

Since real interaction data does not exist yet, the algorithm needs to be validated against synthetic data that mirrors plausible engagement patterns. The generation strategy must produce data that is realistic enough to stress-test the algorithm's learning dynamics—cold start, sparsity, archetype divergence—without over-fitting to any single assumed behavior.

### 4.1 Member Archetypes

3,000 members are distributed across 4 behavioral archetypes. Each archetype defines a base reaction probability and an engagement trajectory over 30 days.

| Archetype | % of Members | Count | Base Act Rate | Trajectory    | Characterization                                   |
| --------- | ------------ | ----- | ------------- | ------------- | -------------------------------------------------- |
| Engaged   | 30%          | 900   | ~55%          | Stable        | Logs signals regularly, responds to most nudges    |
| Passive   | 25%          | 750   | ~25%          | Stable-low    | Logs intermittently, mostly dismisses              |
| Declining | 25%          | 750   | ~40% → 15%    | Linear decay  | Starts engaged, gradually disengages over 30 days  |
| Sporadic  | 20%          | 600   | ~35%          | High variance | Alternates between active weeks and inactive weeks |

Each member also receives:

- A randomly assigned `goal_type` (distribution: 40% weight loss, 35% low carb, 25% balanced)
- A randomly assigned **category affinity vector**: 5 weights (summing to 1.0) representing how receptive the member is to each nudge category. For example, a member might have Nutrition: 0.35, Activity: 0.25, Wellness: 0.15, Compliance: 0.15, Social: 0.10—meaning they are most likely to act on Nutrition nudges
- A randomly assigned **preferred time of day** (morning, afternoon, evening) with a +10% act rate boost when nudges arrive during that window

### 4.2 Delivery Simulation

For each member on each simulated day:

1. **Signal generation.** Members generate 0–3 signals per day (type distribution based on goal type). Engaged members log daily; sporadic members skip 2–4 day stretches.
2. **Candidate selection.** The system generates 1–2 nudge candidates per day from the 25 types, weighted by the member's recent signals and gaps (mimicking rule-based triggering).
3. **Fatigue enforcement.** Same-type cooldown (24 hours) and daily cap (2) are applied, identical to the existing rule engine. Safety nudges (support_risk) bypass these limits.
4. **Delivery.** Surviving candidates are delivered with a timestamp (hour of day randomized with bias toward member's preferred time).

### 4.3 Reaction Generation

For each delivered nudge, the reaction outcome is sampled from:

$$P(\text{act\_now}) = \text{clamp}\Big(\underbrace{b_i}_{\text{archetype base}} \times \underbrace{a_{ij}}_{\text{category affinity}} \times \underbrace{r(t)}_{\text{recency decay}} \times \underbrace{c(t)}_{\text{context modifier}} + \epsilon, \;\; 0.02, \;\; 0.95\Big)$$

Where:

- $b_i$ is the member's archetype base rate (possibly time-varying for declining archetype)
- $a_{ij}$ is the member's affinity weight for nudge $j$'s category
- $r(t) = e^{-\lambda \cdot \text{hours\_since\_last\_relevant\_signal}}$ captures the intuition that nudges are more effective when the triggering signal is recent. Recommended $\lambda = 0.05$, which gives a half-life of ~14 hours—a nudge sent 14 hours after the triggering signal has half the recency boost of one sent immediately
- $c(t)$ is a contextual modifier combining time-of-day preference match ($\pm 10\%$) and fatigue from recent same-category nudges ($-5\%$ per nudge in last 48h)
- $\epsilon \sim \text{Uniform}(-0.05, 0.05)$ adds noise
- $\text{clamp}(\cdot)$ restricts the final result (including noise) to $[0.02, 0.95]$ to prevent degenerate probabilities

The final outcome is a Bernoulli draw: $y \sim \text{Bernoulli}(P)$.

This generation process produces data where the "ground truth" optimal nudge varies by member, by time, and by context—exactly the structure the algorithm must learn to recover.

---

## 5. Algorithm Design

### Design Philosophy

The algorithm is a two-stage hybrid that separates concerns:

- **Stage 1 (Offline)** trains a logistic regression model on accumulated interaction data to establish population-level patterns and provide interpretable feature weights. This model answers: _"For a member with these characteristics receiving this nudge type in this context, what is the base probability of reaction?"_

- **Stage 2 (Online)** runs a contextual bandit (Thompson Sampling) that personalizes nudge selection per member in real time. The bandit starts with priors derived from Stage 1 and refines them with each observed interaction. This component answers: _"Given what we've learned about this specific member, which nudge type should we try next?"_

The two stages are complementary. Logistic regression is good at extracting population-level insights (e.g., "nudges sent in the morning have 12% higher act rates") but cannot adapt to individual preferences fast enough. Thompson Sampling adapts quickly to individuals but struggles with cold start and has no inherent feature understanding. Together, they cover both needs.

### 5.1 Stage 1: Offline Logistic Regression

**Model formulation.** The logistic regression predicts:

$$P(y = 1 \mid \mathbf{x}) = \sigma(\mathbf{w}^T \mathbf{x} + b) = \frac{1}{1 + e^{-(\mathbf{w}^T \mathbf{x} + b)}}$$

where $\mathbf{x}$ is the feature vector constructed from Sections 3.1–3.4 for a given (member, nudge type, context) triple, and $\mathbf{w}$ are learned weights.

**Why logistic regression and not something more powerful?**

This is a deliberate, domain-driven choice. See Section 6 (Tradeoff 2) for the full reasoning. In brief:

1. **Interpretability.** Each feature weight $w_k$ has a direct interpretation: a one-unit increase in feature $k$ changes the log-odds of reaction by $w_k$. In a health context, being able to say _"the model favors morning nudges because the coefficient for hour_of_day is +0.08 per standard deviation"_ is not a nice-to-have—it is a requirement for clinical and product review.

2. **Calibration.** Logistic regression outputs are proper probabilities (after standard calibration). This matters because the algorithm uses these probabilities as priors for the bandit, and poorly calibrated priors cause the bandit to explore too much or too little.

3. **Data efficiency.** At 90K–150K interactions with ~30 features, logistic regression with L2 regularization is well within its operating regime. Gradient-boosted trees or neural networks would not meaningfully improve accuracy at this scale, and their marginal gains come with operational costs that are not justified.

**Training protocol:**

- **Data split.** 80% train / 20% validation, stratified by member archetype (to ensure declining and sporadic members are represented in validation)
- **Regularization.** L2 with strength $\lambda$ selected via 5-fold cross-validation on the training set
- **Categorical encoding.** One-hot for low-cardinality features (goal_type, nudge_category, day_of_week); target encoding for interaction features where one-hot would create too many sparse columns
- **Calibration.** Platt scaling on a held-out calibration set (10% of training data) if calibration curve shows systematic bias
- **Class imbalance.** If the overall act rate is significantly below 50% (likely—base rates range from 25% to 55%), use class weights inversely proportional to frequency. Do not oversample; it distorts calibration.

**Retraining cadence:** Weekly, using the last 30 days of data (rolling window). Monitored via AUC-ROC and calibration drift between consecutive model versions.

### 5.2 Stage 2: Online Contextual Bandit (Thompson Sampling)

**Why a bandit on top of logistic regression?**

Logistic regression captures population patterns but treats all members with similar features identically. Two members with the same goal type, tenure, and signal frequency may have very different nudge preferences. The bandit layer learns these individual differences by observing each member's actual reactions—without needing to define those differences as features upfront.

**Model structure.** For each (member, nudge category) pair, maintain a Beta distribution:

$$\theta_{ic} \sim \text{Beta}(\alpha_{ic}, \beta_{ic})$$

where $c \in \{1, \ldots, 5\}$ indexes the 5 nudge categories. This represents the system's belief about member $i$'s probability of reacting positively to a nudge from category $c$.

**Initialization (warm start from Stage 1).** For a new or cold-start member, initialize the Beta parameters using the logistic regression's predicted probability $\hat{p}_{ic}$ for that member-category pair:

$$\alpha_{ic}^{(0)} = \hat{p}_{ic} \times n_0, \quad \beta_{ic}^{(0)} = (1 - \hat{p}_{ic}) \times n_0$$

where $n_0$ is a **prior strength** parameter (recommended: $n_0 = 5$). This means the bandit starts each member as though it has already seen 5 pseudo-observations distributed according to the logistic regression's prediction. A higher $n_0$ means the bandit trusts the logistic regression more and explores less initially; a lower $n_0$ means it explores more aggressively from the start.

**Selection (at nudge delivery time).** When the system needs to select a nudge category for member $i$:

1. For each eligible category $c$ (after fatigue and safety filtering):
   - Sample $\tilde{\theta}_{ic} \sim \text{Beta}(\alpha_{ic}, \beta_{ic})$
2. Select $c^* = \arg\max_c \tilde{\theta}_{ic}$
3. Within category $c^*$, select the specific nudge type with the highest population act rate (or use a secondary within-category bandit if data permits)

This is Thompson Sampling: the sampling step naturally balances exploitation (categories with high $\alpha / (\alpha + \beta)$ are sampled high more often) with exploration (categories with high uncertainty—low $\alpha + \beta$—have high-variance samples that occasionally win). No explicit exploration parameter ($\epsilon$) is needed, though we add safety bounds anyway (see Section 7).

**Update (after member reacts).** When member $i$ reacts to a nudge from category $c$:

- If act*now: $\alpha*{ic} \leftarrow \alpha\_{ic} + 1$
- If dismiss or ignore: $\beta_{ic} \leftarrow \beta_{ic} + 1$

This is a single addition operation per interaction—no retraining, no batch job, no model serialization. The posterior updates are immediate and stateless beyond the stored $(\alpha, \beta)$ pairs.

**Observation window for "ignore."** A nudge is classified as ignored (and triggers a $\beta$ update) if the member has not taken any action within a defined timeout—recommended 4 hours. This window must be long enough that the member plausibly saw the nudge (they might be away from the app) but short enough that the bandit can learn within the same day. Setting the timeout too short (e.g., 30 minutes) causes false negatives—members who would have acted but hadn't opened the app yet are recorded as ignores. Setting it too long (e.g., 24 hours) delays posterior updates and slows learning. 4 hours is a pragmatic middle ground; in production, this should be calibrated against observed app-open latency data.

**Convergence properties.** With 30 days of data and 1–2 nudges/day, each member accumulates ~30–60 interactions. Distributed across 5 categories, that is ~6–12 observations per category on average. Combined with the prior strength of 5, the effective sample size per category is ~11–17. This is modest but sufficient for the bandit to meaningfully differentiate a member's top 1–2 categories from their bottom 1–2. Finer per-type discrimination within categories requires more data or a longer observation window.

### 5.3 Cold-Start Handling

Cold start—new members with no interaction history—is the most critical phase for this system because:

1. **First impressions shape retention.** A member who dismisses their first 3 nudges is unlikely to engage with the 4th. The cost of getting the first few nudges wrong is higher than the cost of getting the 50th wrong.
2. **No personalization signal exists.** The bandit has nothing to update from, so it falls back entirely to the logistic regression prior.
3. **Feature sparsity.** New members have no historical act rate, no preferred category, no engagement trend. Several features are undefined or zero.

**Strategy: phased warm-up.**

| Phase         | Interactions Seen | Behavior                                                                                                                                                                                                          |
| ------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cold (0–2)    | None or 1–2       | Use logistic regression prediction with member-level features only (goal type, any onboarding preferences). Select the category with the highest population act rate for this member's goal type. No exploration. |
| Warming (3–7) | 3–7               | Bandit posteriors begin to accumulate. Logistic regression prior still dominates ($n_0 = 5$ means ~40–70% of effective weight is prior). Limited exploration allowed.                                             |
| Steady (8+)   | 8+                | Bandit posteriors dominate. Member's actual reaction history has more weight than population-level prediction. Full exploration budget available.                                                                 |

**Tradeoff:** Setting $n_0$ too high (e.g., 20) means the bandit takes 20+ interactions before it overrides a bad prior—at 1–2 nudges/day, that is 10+ days of sub-optimal personalization. Setting $n_0$ too low (e.g., 2) means the bandit explores aggressively from day 1, risking early disengagement. $n_0 = 5$ is a compromise: 3–5 days to begin personalizing, with the logistic regression providing a reasonable default in the meantime.

### 5.4 Safety Carve-Outs

Not all nudge types should be subject to ML-driven optimization.

**The support_risk nudge (type 14) is categorically excluded from the bandit.** Its delivery is governed entirely by deterministic clinical rules: is the member showing distress signals? Have they dismissed help repeatedly? Are they in a pattern that warrants coach escalation?

Optimizing support_risk for act_now probability would be actively harmful: the system might learn that members in distress rarely act on escalation nudges (because they are in crisis, not because the nudge is irrelevant) and stop sending them. The optimization objective—maximize reaction—is misaligned with the clinical objective—ensure safety-sensitive members reach a human.

**Proposed exclusion set for the full taxonomy:**

- `support_risk` (type 14) — always escalated by clinical rules
- `medication_reminder` (type 17) — scheduled by clinical protocol, not preference
- `appointment_prep` (type 18) — time-bound, not preference-driven
- `lab_result_review` (type 19) — triggered by data availability, not optimization

These 4 types are delivered when their clinical trigger fires, regardless of the bandit's opinion. The bandit only optimizes across the remaining 21 types.

**Category imbalance after exclusions.** Removing these 4 types is not uniform across categories. Compliance loses 3 of its 5 types (medication, appointment, lab review), leaving only `weight_check_in` and `goal_reflection`. Wellness loses 1 (`support_risk`), keeping 4. Nutrition, Activity, and Social are unaffected. This means within-category type selection in Compliance is nearly trivial (pick from 2), while Nutrition has 5 options. The bandit's category-level posteriors remain valid—Compliance as a category just has less within-category variety. If this proves limiting, the two remaining Compliance types could be merged into a broader "self-monitoring" meta-type, though this is a product taxonomy decision, not an algorithm concern.

---

## 6. Key Tradeoffs

This section documents the architectural and modeling decisions that a senior or staff-level engineer should evaluate before committing to the design. Each tradeoff is framed as a choice between options, with the reasoning for the recommended path and the conditions under which the recommendation would change.

### Tradeoff 1: Rules vs. ML — Where Should the Boundary Be?

**The question:** With a working rule engine already in place, which parts of nudge selection should be replaced or augmented by a predictive model, and which should remain rule-driven?

**Recommendation:** The rule engine stays authoritative for three functions:

1. **Safety routing.** Whether a member's signals warrant escalation to a human is a clinical judgment, not an optimization target.
2. **Eligibility determination.** Whether a member qualifies for a nutrition nudge (e.g., they logged a meal) is a factual check, not a preference prediction.
3. **Constraint enforcement.** Daily caps, cooldown periods, and fatigue limits are product policies that override model output.

The model adds value in one specific place: **given a set of eligible nudge types that pass all safety checks and constraints, which one should we send?** Today, the rule engine uses a static priority order (support risk > meal guidance > weight check-in). The model replaces this static ranking with a personalized ranking based on predicted reaction probability.

**Why not let the model handle everything?** Because rule logic is auditable, deterministic, and debuggable in incident review. If a member complains about an inappropriate nudge, you can trace the rule that fired and why. If a model made the decision, the explanation is "the model predicted 0.63 reaction probability," which satisfies nobody in a clinical review meeting.

**When this might change:** If the nudge taxonomy grows beyond 25 types and the rule engine becomes unwieldy—too many priority orderings, too many edge cases—then migrating more of the selection logic into the model becomes justified. But even then, safety routing should remain deterministic.

### Tradeoff 2: Logistic Regression vs. Gradient Boosting vs. Deep Learning

**The question:** Given the feature set and data scale, which model architecture maximizes the right properties?

| Property                        | Logistic Regression        | XGBoost / LightGBM                 | Neural Network      |
| ------------------------------- | -------------------------- | ---------------------------------- | ------------------- |
| Accuracy (AUC) at 90K–150K rows | ~0.72–0.78                 | ~0.74–0.80                         | ~0.73–0.79          |
| Calibration quality             | Native (after Platt)       | Requires post-hoc                  | Poor without effort |
| Interpretability                | Direct: weights = log-odds | Indirect: SHAP, partial dependence | Opaque              |
| Training time                   | Seconds                    | Minutes                            | Minutes–hours       |
| Serving complexity              | Dot product                | Tree traversal                     | GPU/batching        |
| Failure mode transparency       | Clear                      | Moderate                           | Low                 |
| Regulatory defensibility        | High                       | Moderate                           | Low                 |

**Recommendation:** Logistic regression, unambiguously.

The accuracy gap is 2–4 AUC points. In a system where the model's output is used as a prior for a bandit (not as a final decision), this gap matters even less—the bandit will correct personalization errors through its own learning. Meanwhile, the interpretability and calibration advantages of LR are not marginal preferences; they are requirements in a health product where nudge selection decisions may need to be reviewed, explained, or audited.

**When this might change:** At 10× the data scale (1M+ interactions), with a mature ML operations team, and with a product that has moved beyond early validation into a regime where marginal accuracy improvements translate to measurable retention gains. That is not the current situation.

### Tradeoff 3: Online Bandit vs. Periodic Batch Retraining

**The question:** Should the system adapt to individual preferences in real time (bandit) or retrain a batch model on a schedule (e.g., weekly)?

| Aspect                    | Online Bandit                            | Batch Retraining                          |
| ------------------------- | ---------------------------------------- | ----------------------------------------- |
| Personalization latency   | Immediate (next nudge)                   | 1 week (next retrain cycle)               |
| Infrastructure complexity | Moderate (stateful per-member)           | Lower (stateless model serving)           |
| Debugging                 | Harder (posteriors evolve continuously)  | Easier (model is frozen between retrains) |
| Cold-start responsiveness | High (adapts from interaction 3–5)       | Low (must wait for retrain)               |
| Operational risk          | Higher (online state can drift, corrupt) | Lower (retrain from clean data)           |
| Personalization depth     | Deep (individual-level posteriors)       | Shallow (feature-based only)              |

**Recommendation:** Online bandit with weekly batch retraining as a safety net.

The bandit is the primary personalization mechanism because member preferences shift faster than a weekly retrain cycle. A member who logs 3 meals in a day and acts on the nutrition nudge has given a strong signal that the system should lean toward nutrition. Waiting a week to incorporate that signal means 7–14 missed opportunities.

The weekly retrain updates the logistic regression that provides the bandit's priors. This means new members benefit from the latest population patterns, and the prior itself stays calibrated as the population evolves.

**When this might change:** If operational burden becomes the bottleneck—the team cannot reliably maintain stateful per-member posteriors across deployments, migrations, and failures—then falling back to batch-only retraining with more interaction features (to approximate personalization) is a reasonable simplification. The system loses personalization velocity but gains operational simplicity.

### Tradeoff 4: Exploration Risk in a Health Context

**The question:** Thompson Sampling explores inherently—it occasionally selects a sub-optimal nudge type to learn about the member's preferences. In e-commerce, a sub-optimal recommendation costs a click. In health, a poorly timed or irrelevant nudge can erode trust, cause disengagement, or—for mood-sensitive members—cause harm. How much exploration is acceptable?

**Recommendation:** Bounded exploration with member-state-aware gates.

The exploration budget is capped at 10% of nudge deliveries, decaying as the bandit's posteriors converge (measured by $\alpha + \beta$ exceeding a threshold). Beyond this global cap, exploration is _suppressed entirely_ for members in specific states:

- **Recent low-mood signal:** Member's last mood log was "low" within 72 hours. The system should not experiment; it should deliver the most-likely-to-help nudge or escalate.
- **Declining engagement trend:** Member's engagement slope is negative over the last 14 days. Exploration risks accelerating disengagement.
- **First 48 hours after onboarding:** The member is forming their initial impression of the product. Every nudge should be high-confidence.

For all other members, Thompson Sampling's natural exploration is permitted. The prior strength parameter ($n_0 = 5$) provides implicit exploration control: with 5 pseudo-observations per category, the bandit's initial uncertainty is moderate rather than extreme, preventing wild early exploration.

**This is a staff-level judgment call, not a technical optimization.** There is no "correct" exploration rate. The right answer depends on the product's risk tolerance, the clinical team's comfort level, and empirical observation of member reactions to exploratory nudges during the A/B test phase.

### Tradeoff 5: Per-Type vs. Per-Category vs. Hierarchical Modeling

**The question:** Should the bandit maintain posteriors for each of the 25 nudge types individually, or for the 5 categories?

**Data sufficiency analysis:**

With 3,000 members × ~45 nudges per member (30 days × 1.5/day average), the dataset contains ~135K interactions. Distributed across:

- **25 types:** ~5,400 per type on average, but highly uneven. Popular types may have 10K+; niche types may have <1K. Per-member-per-type, a typical member sees 3–4 of the 25 types, with 1–3 observations each. This is insufficient for per-member-per-type bandit learning.
- **5 categories:** ~27K per category. Per-member-per-category, a typical member accumulates 6–12 observations per category over 30 days. Combined with $n_0 = 5$ prior, this gives ~11–17 effective observations—enough for meaningful differentiation between top and bottom categories.

**Recommendation:** Category-level bandits (5 Beta distributions per member) with type-level selection within the chosen category based on population act rates.

This is a pragmatic compromise. The bandit learns which _category_ works for each member; within that category, the specific type is selected by the simpler heuristic of population-level effectiveness. As the data accumulates beyond 30 days (e.g., 90+ days), the system can migrate to per-type bandits for the top 2–3 categories where the member has sufficient data.

**A hierarchical Bayesian approach** (where type-level posteriors share a category-level prior) is the theoretically correct solution. It handles sparsity gracefully by letting within-category types borrow strength from each other. However, it adds meaningful implementation complexity (approximate inference, non-conjugate updates) and debugging difficulty. For a first deployment, the two-level heuristic is recommended, with hierarchical modeling as a planned iteration if category-level personalization proves valuable.

### Tradeoff 6: When the Model Should Abstain

**The question:** Should the model always recommend a nudge when asked, or should it sometimes say "don't nudge this member right now"?

**Recommendation:** The model should abstain—output a "no nudge" decision—when:

1. **All candidate probabilities are below a floor** (e.g., $P < 0.15$ for every eligible category). If the model predicts that nothing will resonate, sending a nudge anyway adds noise and fatigue.
2. **The member is in an active escalation.** A member who has been routed to a coach should not receive automated nudges until the escalation is resolved.
3. **Signal density is too low for meaningful context.** A member who has not logged any signals in 7+ days is not giving the system enough information to personalize. A generic check-in (compliance category) is acceptable, but optimizing across all categories is unwarranted.

**Why abstention matters:** A model that always recommends something is easier to build but harder to trust. In a health context, a nudge with 10% predicted reaction probability is not a "weak suggestion"—it is a signal that the system does not understand what this member needs right now. Sending it anyway trains the member to ignore nudges, which reduces signal quality for future learning. Abstention preserves the system's credibility.

### Tradeoff 7: Real-Time State vs. Operational Simplicity

**The question:** Maintaining per-member Beta posteriors ($\alpha_{ic}, \beta_{ic}$ for each member-category pair) means the system carries per-member state that must survive deployments, database migrations, and failures. Is this operational burden justified?

**State size:** 3,000 members × 5 categories × 2 parameters = 30,000 floating-point values. Trivially small in storage terms.

**Operational concern:** The issue is not size but lifecycle. Posteriors are the model's learned knowledge about each member. If they are accidentally reset, the system forgets everything and reverts to population priors. If they are corrupted (e.g., during a migration), the system may make confidently wrong predictions.

**Recommended mitigations:**

- Store posteriors in the same database as nudge history, not in a separate cache or in-memory store
- Include a `last_updated_at` timestamp and a `total_observations` counter alongside each posterior for monitoring
- On deployment, verify posterior integrity by checking that $\alpha + \beta \geq n_0$ for all active members
- Weekly: recompute posteriors from scratch (replay all member interactions since their join date) and compare against the live values. If divergence exceeds a threshold, alert and optionally replace.

**When this might not be justified:** If the team is small, the system is pre-product-market-fit, and the primary goal is to prove that nudge personalization matters at all. In that case, start with batch-only logistic regression (no bandit layer) and add the bandit once personalization is validated as a product lever.

### Tradeoff 8: Feedback Loop Bias

**The question:** The bandit creates a self-reinforcing loop. Categories that the bandit believes are good get shown more often, which generates more data for those categories, which reinforces the bandit's belief—even if the belief was initially wrong. Meanwhile, categories the bandit avoids accumulate almost no data, so their posteriors remain uncertain and they are rarely tested. This is the "rich get richer" problem inherent to all bandit algorithms.

**Why this matters in health:** If the bandit locks onto Nutrition early (because the LR prior slightly favors it) and suppresses Wellness, a member who would have benefited from mood check-ins never receives one. The system produces confidently wrong predictions without knowing it.

**Mitigations:**

1. **Thompson Sampling's built-in exploration** partially addresses this: high-uncertainty categories (low $\alpha + \beta$) produce high-variance samples that occasionally win, forcing occasional exposure. But this exploration is stochastic and not guaranteed for any specific category.
2. **Minimum exposure guarantee (proposed):** For the first 14 days of a member's tenure, ensure each category is shown at least once. This can be implemented as a "burn-in" phase where the bandit is overridden to cycle through categories before entering optimization mode.
3. **Posterior monitoring:** If any category's $\alpha + \beta$ is still near $n_0$ (the initial prior) after 14 days, flag it—this means the bandit has avoided that category entirely, and the system has no information about the member's true preference.

**Residual risk:** Even with mitigations, the bandit will over-allocate attention to early winners. This is an inherent cost of online learning. The weekly LR retrain helps because it updates the population prior from the full dataset (not just bandit-selected observations), providing an external correction signal.

### Tradeoff 9: LR Retrain Impact on Existing Posteriors

**The question:** When the logistic regression retrains weekly, new members get posteriors initialized from the updated model. But existing members have posteriors that were initialized from the _old_ LR and have since accumulated real observations. Should those posteriors be re-initialized?

**Recommendation:** Do not re-initialize existing posteriors.

The posteriors for an existing member reflect their actual behavior—they contain real observations ($\alpha_{ic} + \beta_{ic} - n_0$ of them). Overwriting these with new LR predictions would discard learned personalization to replace it with a population average. The whole point of the bandit is to diverge from the population model.

The old LR prior is "baked into" existing posteriors as the initial $n_0$ pseudo-observations. As real observations accumulate, the prior's influence diminishes naturally. After 15+ interactions, the prior accounts for less than 25% of the posterior's effective weight.

**Exception:** If a posterior integrity check (see Tradeoff 7) detects corruption, or if a major model architecture change invalidates the feature space, a full posterior reset is justified. This should be treated as a disruptive event, logged in the audit trail, and communicated to the product team.

---

## 7. Constraints and Guardrails

The model operates within a set of hard constraints that cannot be overridden by predicted probabilities, regardless of how confident the model is. These constraints exist because the system operates in a health context where product and clinical policies take precedence over engagement optimization.

### 7.1 Fatigue Rules (Hard Constraints)

- **Daily cap:** Maximum 2 auto-delivered nudges per member per calendar day. The model may propose a 3rd; the constraint layer drops it. Safety nudges (support_risk) bypass this limit.
- **Type cooldown:** 24 hours after a member acts on or dismisses a nudge of a given type, that type is ineligible. The model may predict high reaction probability for a recently dismissed type; the constraint layer overrides.
- **Category cooldown (proposed):** With 25 types, a new constraint is needed: maximum 1 nudge from the same category per 12 hours. Without this, the model could send 2 nutrition nudges back-to-back (one meal guidance, one snack swap), which would feel like nagging even though they are technically different types.

### 7.2 Safety Exclusions

The following nudge types are delivered exclusively by deterministic clinical rules and are never subject to bandit optimization:

- `support_risk` — distress escalation
- `medication_reminder` — clinical protocol
- `appointment_prep` — time-bound clinical event
- `lab_result_review` — data availability trigger

When these types fire, they consume a slot in the daily cap (except support_risk) but are not counted as bandit interactions, and their outcomes do not update the bandit posteriors.

### 7.3 Confidence Floor

If the bandit's maximum sampled $\tilde{\theta}$ across all eligible categories is below 0.15, the system outputs "no nudge" rather than selecting the least-bad option. This floor is set deliberately low (15%) because Thompson Sampling's stochastic nature means sampled values can be transiently low even for categories where the true rate is reasonable. A floor of 0.15 catches only categories where the system genuinely has no reason to believe the nudge will be acted on.

### 7.4 Exploration Budget

- **Global cap:** Maximum 10% of a member's nudges over any 7-day window may be exploratory. A nudge is classified as "exploratory" if the selected category was not the one with the highest posterior mean $\alpha / (\alpha + \beta)$. Thompson Sampling produces exploratory selections naturally through sampling variance; the cap limits how many are permitted to reach the member.
- **Decay:** As a member's posteriors converge (total observations $\alpha + \beta > 20$ for all categories), the exploration cap drops to 5%, and eventually to 0% once posteriors are firm. At that point, the bandit acts greedily—always selecting the category with the highest posterior mean.
- **Suppression triggers:** Exploration is fully suppressed for members with a recent low-mood signal, declining engagement trend, or who are within 48 hours of onboarding. See Section 6, Tradeoff 4.

### 7.5 Constraint Layering Summary

The flow from model output to delivered nudge:

```
1. [Rule Engine]       Identify eligible nudge types based on member signals and clinical rules
2. [Fatigue Filter]    Remove types/categories that violate cooldown, daily cap, or category cooldown
3. [Safety Check]      If a safety-critical type fired, deliver it immediately (bypass steps 4–6)
4. [Bandit Selection]  Sample θ for each eligible category; select highest
5. [Exploration Gate]  If selected category is exploratory and budget exceeded, fall back to greedy
6. [Confidence Floor]  If max θ < 0.15, output "no nudge"
7. [Delivery]          Send the selected nudge type to the member
8. [Posterior Update]  After member reacts (or after timeout), update α/β for the delivered category
```

---

## 8. Evaluation Framework

### 8.1 Offline Evaluation (Pre-Deployment)

These metrics validate the logistic regression and the synthetic data generation before any real member sees a bandit-selected nudge.

| Metric                         | Target                 | Purpose                                                                                       |
| ------------------------------ | ---------------------- | --------------------------------------------------------------------------------------------- |
| **AUC-ROC**                    | ≥ 0.75                 | Discriminative power: can the model rank likely reactors above non-reactors?                  |
| **Log-loss**                   | ≤ 0.55                 | Calibration-sensitive: penalizes both overconfidence and underconfidence                      |
| **Calibration error**          | ≤ 0.03 (mean absolute) | Predicted probabilities must approximate true frequencies in each bin                         |
| **Precision@3**                | ≥ 0.60                 | For each member, are the top 3 recommended categories actually the member's best 3?           |
| **Feature importance ranking** | Clinically plausible   | The top features should match domain intuition (engagement trend, category affinity, recency) |

**Calibration is the most important offline metric.** The model's probabilities are used as bandit priors. A model that ranks correctly but assigns wrong probabilities (e.g., predicts 0.70 for everything) will cause the bandit to either under-explore (all priors are confidently high) or over-explore (all priors are confidently low). AUC can be excellent while calibration is terrible; both must be checked.

### 8.2 Online Evaluation (Post-Deployment)

These metrics measure whether the bandit-augmented system actually improves member outcomes in production.

| Metric                       | Measurement                                                                    | Interpretation                                                                                                                                |
| ---------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **Act-now rate (CTR)**       | Fraction of delivered nudges where member selected act_now                     | Primary success metric. Target: 5% absolute lift over rule-based baseline within 30 days                                                      |
| **Cumulative regret**        | Sum of (best-possible act rate − actual act rate) over time                    | Measures how quickly the bandit converges to the optimal policy. Should decrease monotonically                                                |
| **Per-cohort lift**          | CTR for bandit group vs. control group, segmented by archetype                 | Ensures the bandit helps all member types, not just engaged members at the expense of passive ones                                            |
| **Exploration rate**         | Fraction of nudges classified as exploratory (selected category ≠ greedy best) | Should start ~8–10% and decay below 5% within 14 days for established members                                                                 |
| **Mean posterior variance**  | Average $\text{Var}(\text{Beta}(\alpha, \beta))$ across all active members     | Proxy for learning progress. Should decrease over time. Sudden increases indicate distribution shift                                          |
| **Dismiss rate by category** | Fraction of nudges dismissed per category                                      | Monitors whether certain categories are persistently ineffective; high dismiss rate may warrant removing a category from the optimization set |

### 8.3 A/B Test Design

**Groups:**

- **Control:** Existing rule-based engine with static priority ordering
- **Treatment:** Bandit-augmented engine where eligible candidates are re-ranked by Thompson Sampling

**Randomization unit:** Member-level (not nudge-level). Each member is assigned to control or treatment at enrollment and stays there for the test duration. Nudge-level randomization would create inconsistent experiences within a single member's journey.

**Sample size:** With 3,000 members split 50/50, 1,500 per group. Assuming a baseline act rate of ~35% (weighted across archetypes), a minimum detectable effect of 5% absolute lift (35% → 40%), and $\alpha = 0.05$, $\beta = 0.20$ (80% power):

$$n \geq \frac{(z_{\alpha/2} + z_\beta)^2 \cdot [p_1(1-p_1) + p_2(1-p_2)]}{(p_2 - p_1)^2} \approx \frac{(1.96 + 0.84)^2 \cdot [0.35 \times 0.65 + 0.40 \times 0.60]}{0.05^2} \approx 1,380 \text{ per group}$$

1,500 per group is sufficient for a 5% lift. For a smaller lift (3%), the test would need ~3,800 per group (underpowered at current scale). **This means the A/B test can only detect meaningful effects (≥ 5% lift), not marginal ones.** If the bandit improves CTR by 2%, the test will not be conclusive, and the decision to ship will require product judgment rather than statistical proof.

**Duration:** Minimum 14 days to allow bandit posteriors to converge for treatment group members. Recommended 21–28 days to capture weekly engagement cycles and declining-archetype dynamics.

**Guardrails during test:**

- If the treatment group's act rate drops below the control group's by > 3% for 3 consecutive days, halt the test and investigate
- Monitor support_risk escalation volume in both groups—should be identical (safety logic is unchanged)
- Monitor dismiss rate in both groups by category—look for categories where the bandit systematically over-selects despite high dismissal

---

## 9. Pseudocode and Key Formulas

### 9.1 Feature Extraction

```
function extract_features(member, nudge_type, context):
    // Member features
    m = {
        goal_type:              one_hot(member.goal_type),
        tenure_days:            days_since(member.created_at),
        signal_freq_7d:         count(member.signals, last=7d) / 7,
        hist_act_rate:          member.act_count / max(member.total_nudges, 1),
        hist_dismiss_rate:      member.dismiss_count / max(member.total_nudges, 1),
        preferred_category:     one_hot(mode(member.acted_categories)),
        engagement_trend:       linear_slope(member.daily_act_rates, last=14d),
        days_since_last_signal: days_since(member.latest_signal_at)
    }

    // Nudge features
    n = {
        nudge_category:               one_hot(nudge_type.category),
        population_act_rate:          global_act_rate(nudge_type),
        category_act_rate:            global_act_rate(nudge_type.category),
        fatigue_sensitivity:          estimated_decay_rate(nudge_type)
    }

    // Contextual features
    c = {
        hour_of_day:                  context.local_hour,
        day_of_week:                  one_hot(context.day_of_week),
        hours_since_last_nudge:       hours_since(member.last_nudge_at),
        hours_since_same_category:    hours_since(member.last_nudge_at[nudge_type.category]),
        current_mood:                 one_hot(member.latest_mood or "unknown"),
        signal_count_24h:             count(member.signals, last=24h),
        active_streak_days:           consecutive_act_days(member)
    }

    // Interaction features
    x = {
        member_cat_act_rate:          member.act_rate[nudge_type.category],
        member_cat_act_count:         member.act_count[nudge_type.category],
        member_tod_act_rate:          member.act_rate[bucket(context.local_hour)],
        engagement_x_category:        m.engagement_trend * n.category_act_rate
    }

    return concat(m, n, c, x)
```

### 9.2 Logistic Regression Training

```
function train_lr_model(interaction_history):
    X, y = [], []
    for each (member, nudge_type, context, outcome) in interaction_history:
        features = extract_features(member, nudge_type, context)
        X.append(features)
        y.append(1 if outcome == "act_now" else 0)

    // L2-regularized logistic regression
    model = LogisticRegression(
        penalty="l2",
        C=select_via_cross_validation(X, y, folds=5),
        class_weight="balanced",      // handle class imbalance
        max_iter=1000
    )
    model.fit(X, y)

    // Post-hoc calibration check
    cal_X, cal_y = held_out_calibration_set(X, y, fraction=0.1)
    if calibration_error(model, cal_X, cal_y) > 0.03:
        model = apply_platt_scaling(model, cal_X, cal_y)

    return model
```

### 9.3 Bandit Initialization

```
function initialize_posteriors(member, lr_model):
    N0 = 5                             // prior strength
    posteriors = {}

    for each category in OPTIMIZABLE_CATEGORIES:
        // Use LR to predict act probability for this member-category pair
        // using a "representative" nudge type and current context
        features = extract_features(member, representative_type(category), current_context())
        p_hat = lr_model.predict_probability(features)

        posteriors[category] = Beta(
            alpha = p_hat * N0,
            beta  = (1 - p_hat) * N0
        )

    return posteriors
```

### 9.4 Thompson Sampling Selection

```
function select_nudge(member, eligible_categories, posteriors, exploration_budget):
    // Safety check: suppress exploration for vulnerable members
    exploration_allowed = (
        member.latest_mood != "low" or hours_since(member.latest_mood_at) > 72
    ) and (
        member.engagement_trend >= 0
    ) and (
        member.tenure_days > 2
    )

    // Sample from each category's posterior
    sampled = {}
    for each category in eligible_categories:
        sampled[category] = posteriors[category].sample()    // draw θ ~ Beta(α, β)

    selected = argmax(sampled)
    greedy   = argmax({c: posteriors[c].mean() for c in eligible_categories})

    // Exploration gate
    is_exploratory = (selected != greedy)
    if is_exploratory:
        if not exploration_allowed or exploration_budget.exceeded(member):
            selected = greedy    // fall back to greedy selection

    // Confidence floor
    if sampled[selected] < 0.15:
        return NO_NUDGE

    // Within-category type selection
    nudge_type = highest_population_act_rate_type(selected, eligible_types)

    exploration_budget.record(member, is_exploratory=(selected != greedy))
    return nudge_type
```

### 9.5 Posterior Update

```
function update_posteriors(member, category, outcome):
    if outcome == "act_now":
        posteriors[member][category].alpha += 1
    else:    // dismiss, ignore, or expired
        posteriors[member][category].beta += 1
```

### 9.6 Key Mathematical Formulas

**Logistic regression prediction:**

$$P(y = 1 \mid \mathbf{x}) = \frac{1}{1 + e^{-(\mathbf{w}^T\mathbf{x} + b)}}$$

**Beta posterior mean (expected act probability for member $i$, category $c$):**

$$\mathbb{E}[\theta_{ic}] = \frac{\alpha_{ic}}{\alpha_{ic} + \beta_{ic}}$$

**Beta posterior variance (uncertainty about member $i$'s preference for category $c$):**

$$\text{Var}(\theta_{ic}) = \frac{\alpha_{ic} \cdot \beta_{ic}}{(\alpha_{ic} + \beta_{ic})^2 (\alpha_{ic} + \beta_{ic} + 1)}$$

**Thompson Sampling update rule:**

$$\alpha_{ic} \leftarrow \alpha_{ic} + \mathbb{1}[y = 1], \quad \beta_{ic} \leftarrow \beta_{ic} + \mathbb{1}[y = 0]$$

**Warm-start initialization from logistic regression:**

$$\alpha_{ic}^{(0)} = \hat{p}_{ic} \cdot n_0, \quad \beta_{ic}^{(0)} = (1 - \hat{p}_{ic}) \cdot n_0$$

where $\hat{p}_{ic} = P(y=1 \mid \mathbf{x}_{ic})$ from the trained LR model and $n_0$ is the prior strength parameter.

**Synthetic data reaction probability:**

$$P_{\text{react}} = \text{clamp}\left(b_i \cdot a_{ij} \cdot e^{-\lambda \cdot \Delta t} \cdot c(t) + \epsilon, \; 0.02, \; 0.95\right), \quad \lambda = 0.05$$

**A/B test minimum sample size (per group):**

$$n \geq \frac{(z_{\alpha/2} + z_{\beta})^2 \cdot [p_1(1-p_1) + p_2(1-p_2)]}{(p_2 - p_1)^2}$$

---

## 10. Limitations and Open Questions

1. **The 25-type taxonomy is hypothetical.** The algorithm design is structurally sound regardless of the specific types, but the category groupings—which drive the bandit's level of abstraction—need clinical validation. If types within a category have very different behavioral profiles (e.g., hydration reminders vs. portion awareness), the category-level bandit will average over meaningful differences.

2. **30 days is short.** The bandit converges to a useful policy within this window for engaged and passive members, but declining members may churn before the system learns their preferences. Investing in cold-start accuracy is more impactful than improving steady-state convergence.

3. **No contextual features from external data.** The feature set relies entirely on in-app signals. In production, incorporating weather (for hydration, activity nudges), time zone, calendar events, or wearable data would substantially improve contextual prediction. The algorithm's architecture supports this—additional features slot into the logistic regression without structural changes.

4. **The exploration-exploitation tradeoff has no theoretical optimum in this domain.** Thompson Sampling is optimal for certain reward structures but assumes stationary preferences. If a member's category affinity shifts (e.g., they start a new exercise program and suddenly respond to Activity nudges), the bandit's posteriors lag. Periodic posterior decay (e.g., multiply $\alpha$ and $\beta$ by 0.95 weekly) could address this but introduces another tuning parameter.

5. **Evaluation depends on the synthetic data fidelity.** The offline metrics are only as meaningful as the synthetic data's resemblance to real behavior. If real members engage in ways not captured by the 4 archetypes—for example, members whose engagement is cyclical with menstrual or seasonal patterns—the model validated on synthetic data may underperform in production.

6. **Multi-arm effects are not modeled.** The bandit treats each nudge delivery as independent. In reality, the sequence matters: a nutrition nudge followed by an activity nudge may be more effective than two nutrition nudges in a row, independent of the individual nudges' quality. Modeling sequence effects requires a different framework (e.g., reinforcement learning with state), which is a significant complexity increase for uncertain payoff at this data scale.

7. **Graceful degradation is assumed but not detailed.** If the bandit's posterior store is lost (database corruption, migration error), the system should fall back to LR-only predictions with fresh posteriors initialized from the current model. If the LR model itself fails to retrain (bad data, infrastructure failure), the previous week's model should remain in serving with an alert. If both are unavailable, the system falls back to the existing rule engine's static priority ordering. This three-tier fallback (bandit → LR-only → rules) should be explicitly wired into the serving path, not left as an assumption.

8. **Privacy and data governance.** Per-member behavioral preference models—even simple Beta posteriors—constitute derived behavioral profiles under most health data frameworks. In a HIPAA-regulated context, these posteriors are PHI (protected health information) because they encode inferences about a member's health engagement patterns and can be linked to an identified individual. They must be stored, transmitted, and access-controlled with the same safeguards as the member's raw signal data. Deletion requests (right to be forgotten) must include posterior state, not just raw interaction history. This does not affect the algorithm design, but it constrains the operational implementation: posteriors cannot live in an unencrypted cache, cannot be logged in plaintext for debugging, and must be covered by the system's data retention policy.

---

## 11. Deployment Strategy

Shipping a model that influences health-related member interactions is fundamentally different from shipping a recommendation model for e-commerce or media. A bad nudge at best annoys a member; at worst it erodes trust during a vulnerable moment. The deployment strategy must account for this by prioritizing reversibility, gradual exposure, and continuous validation at every stage.

### 11.1 Phased Rollout

Deployment proceeds through four gates, each requiring explicit sign-off before advancing. No gate is time-bound—advancement depends on metrics clearing thresholds.

**Phase 0 — Shadow Mode (no member impact)**

The bandit runs in parallel with the existing rule engine on every nudge decision. Both systems produce a recommendation; only the rule engine's recommendation is delivered. The bandit's recommendation and its rationale (sampled θ values, selected category, exploration flag) are logged for offline comparison.

Purpose:

- Validate that the bandit's scoring path runs within latency budget (< 50ms p99)
- Compare bandit selections against rule-engine selections to build intuition for divergence rate
- Verify that posterior updates accumulate correctly over time (no drift, no NaN, no unbounded growth)
- Confirm that the constraint layer (fatigue, safety exclusions, confidence floor) correctly filters bandit outputs

Exit criteria: 7 days of clean shadow operation with < 0.1% error rate in the scoring path, no latency regressions, and bandit divergence rate within expected range (15–40% of decisions differ from rule engine).

**Phase 1 — Limited Exposure (5% of members)**

A randomly selected 5% cohort receives bandit-selected nudges. The remaining 95% stays on the rule engine. Member assignment is sticky—once assigned a group, the member stays there for the duration of the phase.

Purpose:

- First real-world signal on act-now rate lift
- Early detection of unexpected failure modes (e.g., the bandit over-indexes on a single category for cold-start members)
- Validate that the monitoring and alerting pipeline catches real issues

Exit criteria: 14 days with no triggered guardrails (see Section 11.5), act-now rate for the treatment cohort is not statistically worse than control (one-sided test, α = 0.10), and no increase in support_risk escalation volume.

**Phase 2 — Expanded Exposure (25% → 50%)**

Ramp to 25%, hold for 7 days. If metrics hold, ramp to 50% and begin the formal A/B test described in Section 8.3. This is where the primary hypothesis—5% absolute lift in act-now rate—is tested with statistical power.

Exit criteria: A/B test reaches significance (p < 0.05 for primary metric) or reaches maximum duration (28 days) without significance (in which case, the result is inconclusive and a product decision follows).

**Phase 3 — General Availability (100%)**

Roll out to all members. The rule engine remains available as a fallback (see Section 11.6) but is no longer actively scoring for production traffic.

### 11.2 Serving Architecture

The system has two distinct computational paths with very different operational characteristics.

**Offline path — Logistic Regression training**

- **Cadence:** Weekly batch job (e.g., Sunday 02:00 UTC)
- **Input:** Previous 30 days of interaction data (features + outcomes) across all members
- **Output:** A serialized model artifact (coefficients + feature metadata) versioned with a timestamp
- **Storage:** Model registry (could be as simple as a versioned object store or a dedicated ML registry like MLflow). Every model version is retained for at least 90 days for rollback
- **Validation gate:** Before the new model is promoted to serving, it must pass automated checks against a holdout set: AUC ≥ 0.73, calibration error ≤ 0.04, and no feature with importance > 0.30 that wasn't in the previous model (guards against data leakage). If any check fails, the previous model stays in serving and the team is alerted

**Online path — Thompson Sampling at scoring time**

- **Read:** Load the member's current Beta posteriors (5 pairs of α, β — one per category). This is a single-row database read, not a model inference call
- **Compute:** Sample from each Beta distribution, apply constraint filters, select the winning category. Total compute is negligible (5 random samples + comparisons). The expensive part is the constraint evaluation (fatigue check, safety check), not the bandit itself
- **Write:** After outcome observation (act_now within session, or timeout after 4 hours), update the relevant α or β by +1. This is a single-row write
- **Latency budget:** The entire scoring path—posterior read, sampling, constraint evaluation, and response—must complete within 100ms at p99. The bandit adds < 5ms to the existing rule engine's latency; the bottleneck is the database read for current posteriors

**Key architectural decision:** Posteriors live in the primary database, not in a separate model-serving layer. At 3,000 members × 5 categories, this is 15,000 rows of (member_id, category, α, β, last_updated)—trivially small. There is no need for a dedicated feature store, vector database, or model-serving infrastructure at this scale. The complexity cost of a separate serving layer far outweighs any performance benefit. If the member population grows to 100K+, a caching layer (read-through cache with TTL matching the posterior update frequency) becomes worthwhile.

### 11.3 Training Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│  Weekly Training Pipeline                                    │
│                                                              │
│  1. Extract   → Pull 30-day interaction window from DB       │
│  2. Transform → Compute features (Section 3) for each        │
│                 (member, nudge_type, context) tuple           │
│  3. Train     → Fit logistic regression on labeled outcomes   │
│  4. Validate  → Run holdout checks (AUC, calibration, etc.)  │
│  5. Promote   → If checks pass, swap model artifact in       │
│                 serving; if not, alert and keep previous       │
│  6. Warm-start→ For new members (joined since last retrain),  │
│                 initialize posteriors from new LR predictions │
│                 (existing members' posteriors are untouched)  │
└─────────────────────────────────────────────────────────────┘
```

**Retrain does not reset posteriors for existing members.** The LR model provides priors; once a member's posteriors have been updated by real observations, the LR model's role for that member is finished. The only exception is if a member has had zero interactions for 30+ days (lapsed member)—in that case, posteriors are re-initialized from the latest LR model on their next visit, treating them as a warm cold-start.

### 11.4 Migration from Rule Engine to Bandit

The transition from a purely rule-based system to a bandit-augmented one must be invisible to the member and reversible for the operator.

**Backward compatibility contract:**

- The bandit is an additional scoring layer that sits between the rule engine's candidate generation and the delivery step. It does not replace the rule engine; it re-ranks the rule engine's output
- If the bandit layer is disabled (via a feature flag), the system behaves identically to the pre-bandit state. No schema changes, no data migrations, no side effects
- Safety-critical paths (support_risk escalation, medication reminders) are never routed through the bandit. They bypass it architecturally, not just by configuration

**Feature flag design:**

- `bandit_enabled` (boolean): Master switch. Off = bandit scoring is skipped entirely
- `bandit_rollout_pct` (0–100): Percentage of members whose nudges are scored by the bandit. Used during Phase 1–2
- `bandit_exploration_enabled` (boolean): Allows disabling exploration independently of the bandit itself. Useful if exploration is causing issues but greedy bandit selection is working well

All flags are hot-reloadable (no deploy required to change). Changes take effect on the next nudge decision, not retroactively.

### 11.5 Production Monitoring and Alerting

Monitoring covers three layers: infrastructure, model behavior, and member outcomes.

**Infrastructure monitors:**

| Signal                   | Threshold        | Action                                       |
| ------------------------ | ---------------- | -------------------------------------------- |
| Scoring latency (p99)    | > 100ms          | Page on-call; investigate DB read latency    |
| Posterior write failures | > 0.5% of writes | Alert; check DB connectivity and constraints |
| Model artifact staleness | > 10 days        | Alert; investigate training pipeline failure |
| Posterior value anomaly  | α or β > 500     | Alert; possible update loop or missing decay |

**Model behavior monitors:**

| Signal                           | Threshold                         | Action                                                                                  |
| -------------------------------- | --------------------------------- | --------------------------------------------------------------------------------------- |
| Category concentration (Gini)    | > 0.85 for any member over 7 days | Alert; bandit may be stuck in a local optimum. Consider posterior reset for that member |
| Exploration rate                 | < 1% globally when expected > 5%  | Alert; posteriors may have converged prematurely. Check for data quality issues         |
| Bandit vs. rule-engine agreement | < 50% or > 95%                    | Informational; extreme divergence or convergence may indicate misconfiguration          |
| Confidence floor trigger rate    | > 60% of decisions                | Alert; model may be systematically underconfident. Check LR calibration                 |

**Member outcome monitors:**

| Signal                       | Threshold                                | Action                                                            |
| ---------------------------- | ---------------------------------------- | ----------------------------------------------------------------- |
| Act-now rate (7-day rolling) | Drops > 5% below pre-deployment baseline | Auto-disable bandit (flip feature flag), alert team               |
| Dismiss rate by category     | Any category > 70% dismiss rate          | Remove category from bandit optimization set, alert clinical team |
| Escalation volume            | > 2σ above historical mean               | Investigate immediately; may indicate nudge-induced distress      |
| Member NPS / satisfaction    | Drop > 10 points in treatment cohort     | Halt rollout expansion, review nudge content quality              |

### 11.6 Rollback Plan

The system supports three levels of rollback, any of which can be triggered within minutes:

1. **Disable exploration only** (`bandit_exploration_enabled = false`). The bandit still selects nudges based on posterior means (greedy mode) but stops exploring. This is the least disruptive rollback—members see the bandit's best guess, just without any experimental nudges. Use this if exploration is causing elevated dismiss rates but overall performance is acceptable.

2. **Disable bandit entirely** (`bandit_enabled = false`). The scoring path reverts to the rule engine. Posteriors are retained in the database but not read or updated. Use this if bandit-selected nudges are underperforming the baseline or if a model behavior anomaly is detected.

3. **Roll back LR model** (promote previous model version from the registry). Use this if a newly retrained LR model causes calibration regression or unexpected posterior initialization for new members. The bandit continues to operate with the previous model's priors.

All three rollback mechanisms are independent and composable. A rollback does not discard state—posteriors and model artifacts are preserved for post-mortem analysis.

### 11.7 Capacity and Scaling Considerations

At the current scale (3,000 members, 5 categories, ~2 nudges/day/member), the system's computational footprint is negligible:

- **Posterior storage:** 15,000 rows × ~50 bytes per row = ~750 KB
- **Scoring throughput:** ~6,000 scoring requests/day = ~0.07 QPS average, ~1 QPS peak. A single application server handles this without dedicated infrastructure
- **Training data volume:** 30 days × 3,000 members × ~2 interactions/day = ~180,000 training examples. Logistic regression trains in seconds on a single CPU
- **Model artifact size:** Logistic regression with ~15 features produces a coefficient vector that serializes to < 10 KB

**Scaling inflection points:**

- **10K members:** No architectural changes needed. Posterior table grows to 50K rows—still trivially small
- **100K members:** Add a read-through cache for posteriors to avoid per-request DB reads. Training data grows to ~6M rows; LR still trains in minutes but consider switching to incremental/online learning to avoid full-window retraining
- **1M+ members:** Posterior storage and update become a meaningful write load. Consider sharding posteriors by member_id hash. Training may benefit from distributed compute. At this scale, evaluate whether the category-level bandit is still the right abstraction or whether per-type bandits (with 25 arms instead of 5) are feasible given the observation volume
