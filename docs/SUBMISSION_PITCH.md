# RazorRecover: 5-Minute Pitch Video Script & Presentation Guide

**Track 03:** AI Revenue Recovery  
**Target Program:** Razorpay AI Builder Internship  
**Candidate:** RazorRecover Team  

---

## Pitch Structure (5:00 Minutes Total)

### [0:00 – 0:30] The Problem: Detection is Not Recovery
> **Visual:** Screen showing a standard merchant dashboard with thousands of failed payments and blunt "Payment Failed" notifications.
>
> **Script:**
> "Every month, Indian merchants lose crores in revenue because a transaction fails, a mandate is declined, or a checkout link expires.
> 
> But here is the real issue: today’s payment systems stop at detection. They say: *'Payment failed. Retry now or send an email.'*
> 
> If a customer failed due to insufficient balance, retrying immediately fails 88% of the time, burns gateway fees, and annoys the customer. If a loyal subscriber had an OTP timeout, spamming them with aggressive reminders causes churn.
> 
> True recovery is not an automation problem. It is an **economic decision problem**."

---

### [0:30 – 1:00] The Solution: Introducing RazorRecover
> **Visual:** High-level architecture slide highlighting the Decoupled Intelligence loop.
>
> **Script:**
> "Meet **RazorRecover** — an autonomous revenue recovery decision engine built for Track 03.
> 
> Instead of blunt retries, RazorRecover does five things autonomously:
> 1. **Diagnoses Root Cause** from raw payment error codes and gateway metadata.
> 2. **Predicts Recovery Likelihood** across five candidate interventions using a calibrated tabular ML model.
> 3. **Optimizes Expected Net ₹ Value**, subtracting direct costs, discount spend, and churn fatigue penalties.
> 4. **Enforces Hard Policy Guardrails**, ensuring stopping rules, quiet hours, and high-value ceilings are respected.
> 5. **Executes Bounded Interventions** via Razorpay APIs and records an immutable audit trail."

---

### [1:00 – 2:30] Live Product Demonstration
> **Visual:** Live screen recording of the Merchant Command Center at `http://localhost:8000`.
>
> **Step 1: Dashboard Overview (1:00 – 1:20)**
> "Here is the RazorRecover Merchant Command Center. You can see our real-time metrics: Gross at Risk, Gross Recovered, Net Recovered after costs, and our 67.5% recovery rate.
> 
> The system operates in **Dual-Mode**: running seamlessly with live Razorpay Test Mode keys, or using our built-in Razorpay Webhook Simulator for zero-friction evaluation."
>
> **Step 2: Trigger Failure & Watch Decision (1:20 – 1:50)**
> "Let’s simulate a real scenario: a ₹4,999 payment failure for a 'Cash-Constrained' customer with an `INSUFFICIENT_FUNDS` error.
> 
> We click 'Inject Event'. The webhook is ingested, signature validated, and idempotency checked.
> 
> Opening the Case Inspector, notice what happened:
> - Instant retry had only a 12% probability and negative expected value after retry costs.
> - But **Delayed Retry (+12h)** had a 65% probability, yielding a net expected recovery of **₹3,247**.
> - The Policy Engine verified retry limits and quiet hours.
> - The Action Executor scheduled the delayed retry and drafted a non-intrusive notification.
> - The LLM generated a human-readable explanation in the audit log explaining the exact mathematical rationale."
>
> **Step 3: Closed-Loop Outcome (1:50 – 2:30)**
> "Now, when the retry succeeds or the customer completes the link, Razorpay fires `payment.captured`.
> 
> We trigger the recovery: immediately, stopping rules activate, any future reminders are cancelled, the case flips to green, and our net recovered rupees increment in real-time. The loop is closed."

---

### [2:30 – 3:30] Engineering & AI Architecture
> **Visual:** System architecture diagram and candidate evaluation matrix.
>
> **Script:**
> "Let’s discuss what makes our AI architecture defensible and production-ready.
> 
> **First, the LLM does NOT make financial decisions.**
> Giving an LLM direct control over money movement or retry frequency is dangerous. In RazorRecover:
> - The ML Tabular Model and Expected Value Optimizer calculate the financial decision deterministically.
> - The LLM is used strictly post-decision to generate transparent merchant audit logs and tone-adaptive customer messages.
> - And crucially, we have a **100% offline deterministic template fallback** — if external LLM APIs timeout or rate limit, the system never breaks.
> 
> **Second, Guardrails are hardcoded:**
> - Max 3 retries.
> - Minimum 6-hour spacing.
> - Quiet hours between 10 PM and 8 AM.
> - 10% maximum discount cap.
> - And any transaction above ₹50,000 automatically halts autonomous charging and routes to Human Ops."

---

### [3:30 – 4:20] The Evaluation: Measured Recovery Across 1,000 Cases
> **Visual:** Batch Evaluation tab showing comparative results across 1,000 cases.
>
> **Script:**
> "The Buildathon brief explicitly asked: *'Do not only identify the problem. Show measured money recovered across a batch.'*
> 
> We built a standalone benchmark suite running 1,000 held-out revenue-at-risk cases across 5 behavioral customer cohorts with identical ground-truth counterfactuals:
> 
> - **Baseline A (Always Retry):** Recovers only ₹15.1 Lakhs, with an 81.4% failure and waste rate.
> - **Baseline B (Generic Reminder):** Recovers ₹44.7 Lakhs, but spams 41% of users unnecessarily.
> - **Baseline C (Static Rules):** Recovers ₹40.7 Lakhs.
> - **RazorRecover:** Recovers **₹44.6 Lakhs Net**, delivering:
>   - **+₹3,89,941 incremental net revenue uplift (+9.6%)** over static rules.
>   - **89 wasteful interventions eliminated**.
>   - **100% safety and compliance adherence**."

---

### [4:20 – 5:00] Conclusion
> **Visual:** Summary slide with key links, GitHub repository, and internship pitch.
>
> **Script:**
> "RazorRecover transforms revenue recovery from a dumb retry script into an intelligent, economically optimized, and bounded financial system.
> 
> It provides:
> - Real Razorpay event lifecycle integration.
> - Transparent mathematical decisioning.
> - Zero-friction Dual-Mode architecture.
> - And empirically proven net revenue uplift.
> 
> Thank you, and I look forward to presenting RazorRecover to the Razorpay panel!"
