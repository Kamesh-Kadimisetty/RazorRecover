# RazorRecover: Technical System Architecture

## Overview
**RazorRecover** is an autonomous revenue recovery decision engine built for the **Razorpay AI Buildathon (Track 03: AI Revenue Recovery)**. It bridges the gap between raw payment failure detection and closed-loop financial recovery by diagnosing failure root causes, predicting intervention-specific recovery probabilities, optimizing expected net recovery under deterministic policy guardrails, and measuring net rupees recovered across a locked batch against industry baselines.

---

## 1. Core Engineering Principle: Decoupled Intelligence

A core tenet of RazorRecover is that **the LLM is never given direct authority over financial actions or money movement**.

```text
Payment Failure Event
        │
        ▼
Deterministic Root-Cause Classification
        │
        ▼
Feature Extraction (Customer, Event, Cohort, Timing)
        │
        ▼
Calibrated Tabular ML Model (P(Recovery | Action))
        │
        ▼
Expected Net Recovery Optimizer
[E(Net Value) = Amount × P(Rec) - Direct Cost - Discount - Churn Penalty]
        │
        ▼
Deterministic Policy Guardrails & Stopping Rules
(Max retries, quiet hours, discount caps, ₹50,000 human ops ceiling)
        │
        ▼
BOUNDED ACTION EXECUTION
        │
   ┌────┴────────────────────────┐
   ▼                             ▼
Razorpay API / Link        LLM Explainer & Messenger
(Financial Execution)      (Audit Rationale + Content-Sanitized Copy)
```

---

## 2. Mathematical Formulation

### 2.1 Recovery Probability Model
Given customer features $\mathbf{x}_{\text{cust}}$ (tenure, LTV, historical recovery rate, payment success rate), event features $\mathbf{x}_{\text{event}}$ (amount, failure code, attempt number, hour of day), and candidate intervention $a \in \mathcal{A}$:
$$\hat{P}(\text{recovery} \mid \mathbf{x}, a) = \sigma\left(\mathbf{w}^T \phi(\mathbf{x}, a)\right)$$
Where $\phi(\mathbf{x}, a)$ is the calibrated feature representation.

### 2.2 Expected Net Recovery Value
For every candidate action $a$:
$$\text{Expected Net Value}(a) = \text{Amount} \times \hat{P}(\text{recovery} \mid \mathbf{x}, a) - \text{DirectCost}(a) - \text{Discount}(a) - \text{Penalty}(a)$$

Where:
- $\text{DirectCost}(\text{retry\_now}) = ₹5.0$ (Gateway retry fee and infrastructure load).
- $\text{DirectCost}(\text{delayed\_retry}) = ₹2.0$.
- $\text{DirectCost}(\text{smart\_reminder}) = ₹1.5$ (WhatsApp API fee) or $₹0.5$ (SMS fee).
- $\text{Discount}(\text{incentive\_discount}) = \text{Amount} \times \delta$, with $\delta \le 10\%$.
- $\text{DirectCost}(\text{human\_escalation}) = ₹150.0$ (Internal ops labor cost).
- $\text{DirectCost}(\text{do\_nothing}) = 0$.

### 2.3 Policy Constrained Optimization
$$\max_{a \in \mathcal{A}} \text{Expected Net Value}(a) \quad \text{subject to} \quad \mathcal{C}(a, \mathbf{x}) = \text{True}$$
If $\forall a \in \mathcal{A}, \text{Expected Net Value}(a) \le 0$, the engine halts recovery ($\text{action} = \text{do\_nothing}$) to prevent customer churn and negative expected returns.

---

## 3. Behavioral Customer Cohorts

RazorRecover models 5 empirical customer behavioral cohorts:

| Cohort | Characteristics | Primary Root Cause | Optimal Intervention |
| :--- | :--- | :--- | :--- |
| **Reliable Payer** | 92% base success rate, high LTV (₹35k–₹150k) | Transient bank timeout or OTP drop | Smart delayed retry (+12h) |
| **Temporarily Cash-Constrained** | 68% base success rate, sensitive to liquidity timing | Insufficient balance | Delayed retry (+24h–48h / salary cycle) |
| **Subscription Loyalist** | 94% base success rate, high churn risk if spammed | Autopay / card renewal friction | Gentle WhatsApp payment link |
| **High Churn Risk** | 48% base success rate, price sensitive | User abandonment / drop-off | Targeted discount incentive (8%) |
| **Habitual Late Payer** | 62% base success rate, procrastinates | Pending invoice / payment link | Multi-touch smart reminder |

---

## 4. Dual-Mode Architecture

To allow zero-friction local development and evaluation without requiring live API keys, RazorRecover operates in **Dual-Mode**:

```text
                 ┌──────────────────┐
                 │   Event Source   │
                 └────────┬─────────┘
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
      Simulator Mode           Razorpay Test Mode
      (MODE=simulator)         (MODE=razorpay)
             │                         │
             └────────────┬────────────┘
                          ▼
            Common Webhook Processor
       (HMAC signature + Idempotency check)
                          │
                          ▼
            Closed-Loop Recovery Engine
```

1. **`MODE=simulator` (Default)**: Generates exact Razorpay webhook payloads matching documented JSON schemas. Anyone can clone the repo and run full end-to-end demonstrations immediately.
2. **`MODE=razorpay`**: Validates `X-Razorpay-Signature` via HMAC SHA256 and calls official Razorpay Payment Links API.

Both modes execute the exact same downstream decision, policy, and evaluation pipelines.

---

## 5. Deterministic Policy Guardrails & Stopping Rules

1. **Max Retries Ceiling**: Halts retries if `attempt_number >= 3`.
2. **Minimum Retry Spacing**: Enforces at least 6 hours between automated debit attempts.
3. **Quiet Hours Guardrail**: Communications during 22:00–08:00 are queued and shifted to 08:30 AM the next day.
4. **Discount Cap**: Incentive discounts are strictly capped at $\le 10\%$.
5. **High-Value Escalation**: Transactions $\ge ₹50,000$ bypass autonomous charging and are assigned to human ops.
6. **Customer Consent**: Accounts with `opt_out = True` cannot receive marketing or recovery messages.
7. **Immediate Stopping Rule**: All pending interventions are immediately cancelled once a payment is captured, refunded, or order cancelled.

---

## 6. Immutable Audit Trail

Every state transition is stored with timestamp, actor, input summary, decision, and rationale:
- `RecoveryDetector`: Revenue risk detection and root cause classification.
- `ModelScorer`: Candidate action probability vector calculation.
- `Optimizer`: Expected net value calculations across candidate interventions.
- `PolicyGuardrail`: Compliance check results and rule triggers.
- `RazorRecoverExecutor`: Bounded action scheduling and execution receipts.
- `SimulatorOutcomeTracker`: Payment capture event and closed-loop verification.
