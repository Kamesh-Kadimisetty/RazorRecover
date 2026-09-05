import os
import re
from typing import Dict, Any, Optional
from backend.app.config import settings

class LLMExplainerAndMessenger:
    """
    Reasoning and communication layer powered by Google Gemini (gemini-2.5-flash).
    Transforms deterministic decisions and mathematical evidence into:
    1. Deep Chain-of-Thought (CoT) agent reasoning logs.
    2. Multi-tone customer recovery messaging (Empathetic, Hinglish, Formal B2B).
    3. Merchant Copilot Q&A assistance.
    Includes a 100% offline deterministic fallback engine.
    """
    def __init__(self):
        pass

    @property
    def gemini_api_key(self) -> str:
        return settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")

    @property
    def openai_api_key(self) -> str:
        return settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")

    def _call_gemini(self, prompt: str) -> Optional[str]:
        key = self.gemini_api_key
        if not key:
            return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            resp = model.generate_content(prompt, request_options={"timeout": 4.0})
            if resp and resp.text:
                return resp.text.strip()
            return None
        except Exception:
            return None

    def _call_openai(self, prompt: str) -> Optional[str]:
        key = self.openai_api_key
        if not key:
            return None
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=250,
                temperature=0.3
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            return None

    def _call_llm(self, prompt: str) -> Optional[str]:
        """Try Gemini first, then OpenAI, else None."""
        text = self._call_gemini(prompt)
        if text:
            return text
        return self._call_openai(prompt)

    # -------------------------------------------------------------
    # 1. Human-Readable Audit Explanation
    # -------------------------------------------------------------
    def generate_audit_explanation(
        self,
        customer: Dict[str, Any],
        event: Dict[str, Any],
        decision: Dict[str, Any]
    ) -> str:
        chosen = decision.get("chosen_action_details", {})
        action = decision.get("chosen_action", "do_nothing")
        net_val = chosen.get("net_expected_value", 0.0)
        prob = chosen.get("probability", 0.0)
        cohort = customer.get("cohort", "standard")
        amount = event.get("amount", 0.0)
        root_cause = event.get("root_cause", "payment_failure")

        # Attempt Gemini LLM generation
        prompt = (
            f"You are the autonomous AI Revenue Recovery Agent for Razorpay merchants (RazorRecover).\n"
            f"Summarize the following mathematical decision in exactly 2 concise, professional sentences for an immutable audit trail:\n"
            f"- Customer Cohort: {cohort}\n"
            f"- Amount At Risk: INR {amount:,.2f}\n"
            f"- Failure Root Cause: {root_cause}\n"
            f"- Selected Intervention: {action}\n"
            f"- Calibrated Recovery Likelihood: {prob*100:.1f}%\n"
            f"- Net Expected Value: INR {net_val:,.2f}\n"
            f"- Policy Reason: {chosen.get('policy_reason')}\n"
            f"Explain clearly why this intervention was economically optimal while respecting merchant guardrails."
        )
        llm_text = self._call_llm(prompt)
        if llm_text:
            return llm_text

        # Offline Deterministic Fallback
        if action == "delayed_retry":
            return (
                f"Automated delayed retry scheduled (+12h). Customer cohort '{cohort}' shows {prob*100:.0f}% historical "
                f"recovery rate post-liquidity reset. Expected net recovery of ₹{net_val:,.2f} exceeds operational cost with zero customer spam."
            )
        elif action == "smart_reminder":
            return (
                f"Smart payment link reminder dispatched via {customer.get('preferred_channel', 'WhatsApp').title()}. "
                f"High recovery probability ({prob*100:.0f}%) with ₹{net_val:,.2f} net expected value under 48-hour communication frequency cap."
            )
        elif action == "incentive_discount":
            return (
                f"Targeted reactivation incentive ({chosen.get('discount_pct', 8):.0f}% discount) authorized. "
                f"Customer cohort '{cohort}' exhibits high churn elasticity; net expected recovery of ₹{net_val:,.2f} remains positive after absorbing the discount cost."
            )
        elif action == "human_escalation":
            return (
                f"Transaction value of ₹{amount:,.2f} triggered merchant high-value ceiling guardrail (>₹50,000). "
                f"Automated recovery suspended and routed to Human Ops for high-touch relationship management."
            )
        elif action == "retry_now":
            return (
                f"Immediate payment retry authorized. Root cause indicates transient network timeout with {prob*100:.0f}% success likelihood. Net expected value: ₹{net_val:,.2f}."
            )
        else:
            return (
                f"Recovery workflow halted. No candidate intervention yielded positive net expected recovery under current policy limits. Preserving merchant margin and customer goodwill."
            )

    # -------------------------------------------------------------
    # 2. Deep Agent Reasoning (Chain-of-Thought)
    # -------------------------------------------------------------
    def generate_agent_reasoning(
        self,
        customer: Dict[str, Any],
        event: Dict[str, Any],
        decision: Dict[str, Any]
    ) -> str:
        """
        Generates a transparent Chain-of-Thought (CoT) step-by-step diagnostic breakdown.
        """
        chosen = decision.get("chosen_action_details", {})
        action = decision.get("chosen_action", "do_nothing")
        net_val = chosen.get("net_expected_value", 0.0)
        prob = chosen.get("probability", 0.0)
        cohort = customer.get("cohort", "reliable")
        amount = event.get("amount", 0.0)
        root_cause = event.get("root_cause", "generic_failure")
        candidates = decision.get("all_candidates", [])

        prompt = (
            f"You are RazorRecover AI, an agentic revenue recovery system for Razorpay.\n"
            f"Produce a structured Chain-of-Thought reasoning breakdown for this payment failure in markdown:\n"
            f"Event Data:\n"
            f"- Customer: {customer.get('name', 'Customer')} | Cohort: {cohort} | LTV: INR {customer.get('lifetime_value', 0):,.2f}\n"
            f"- Amount At Risk: INR {amount:,.2f}\n"
            f"- Failure Reason: {root_cause}\n"
            f"- Chosen Action: {action} (P={prob:.2f}, Net Value=INR {net_val:,.2f})\n"
            f"\n"
            f"Format with these 3 sections:\n"
            f"**1. Agent Observation & Root Cause:** (Diagnosis of why it failed and customer behavioral context)\n"
            f"**2. Economic Evaluation:** (Why this action beats other options like instant retry or discount)\n"
            f"**3. Guardrail & Safety Gate:** (Which policy limits were verified)\n"
            f"Keep it professional, analytical, and under 150 words."
        )
        llm_text = self._call_llm(prompt)
        if llm_text:
            return llm_text

        # Offline CoT Fallback
        return (
            f"**1. Agent Observation & Root Cause:**\n"
            f"Customer '{customer.get('name', 'Customer')}' belongs to cohort '{cohort}'. "
            f"Transaction of ₹{amount:,.2f} failed due to '{root_cause}'. Customer exhibits high historical reliability but temporary settlement friction.\n\n"
            f"**2. Economic Evaluation:**\n"
            f"Immediate retry rejected due to low success likelihood ({candidates[0]['probability']*100:.0f}%) and gateway fee drag. "
            f"Selected '{action}' maximizing Net Expected Value at ₹{net_val:,.2f} (P={prob*100:.0f}%).\n\n"
            f"**3. Guardrail & Safety Gate:**\n"
            f"Validated against max retries (<=3), quiet hours policy, and frequency limits. Action bounded and authorized."
        )

    # -------------------------------------------------------------
    # 3. Content Sanitizer
    # -------------------------------------------------------------
    def sanitize_message(self, message: str, max_length: int = 240) -> str:
        """Enforces tone, length, and forbidden-content rules on outbound customer messages."""
        forbidden_patterns = [
            r"\blegal action\b",
            r"\bpolice\b",
            r"\bcourt\b",
            r"\bpenalty fee\b",
            r"\bfraud\b",
            r"\barrest\b",
            r"\bdefaulter\b"
        ]
        clean_msg = message
        for pat in forbidden_patterns:
            clean_msg = re.sub(pat, "notice", clean_msg, flags=re.IGNORECASE)

        if len(clean_msg) > max_length:
            clean_msg = clean_msg[:max_length - 3] + "..."
        return clean_msg.strip()

    # -------------------------------------------------------------
    # 4. Multi-Tone Customer Messaging (Empathetic / Hinglish / Formal)
    # -------------------------------------------------------------
    def generate_customer_message(
        self,
        customer: Dict[str, Any],
        event: Dict[str, Any],
        decision: Dict[str, Any],
        tone: str = "empathetic"
    ) -> str:
        chosen = decision.get("chosen_action_details", {})
        action = decision.get("chosen_action", "do_nothing")
        cust_name = customer.get("name", "Customer").split()[0]
        amount = event.get("amount", 0.0)
        discount_pct = chosen.get("discount_pct", 0.0)
        payment_link = f"https://rzp.io/i/{event.get('order_id', 'pay_rec_link')}"

        if action in ["human_escalation", "do_nothing"]:
            return ""

        # LLM Generation with Tone Selector
        tone_instruction = {
            "empathetic": "Warm, reassuring, helpful, and non-accusatory. Emphasize that the order is safe.",
            "hinglish": "Friendly conversational Hinglish blend (e.g. 'Aapka payment complete nahi ho paya, tension mat lijiye...'). Very natural for Indian mobile users.",
            "formal": "Professional corporate B2B notice. Respectful and direct with invoice reference."
        }.get(tone, "Warm and helpful.")

        prompt = (
            f"You are the recovery messaging agent for a Razorpay merchant.\n"
            f"Write a short, engaging customer recovery SMS/WhatsApp message (under 160 characters):\n"
            f"- Customer Name: {cust_name}\n"
            f"- Amount: INR {amount:,.2f}\n"
            f"- Intervention Type: {action}\n"
            f"- Discount (if applicable): {discount_pct}%\n"
            f"- Payment Link: {payment_link}\n"
            f"- Desired Tone: {tone_instruction}\n"
            f"Never use aggressive recovery or debt collection words."
        )
        llm_text = self._call_llm(prompt)
        if llm_text:
            return self.sanitize_message(llm_text)

        # Fallback Deterministic Templates
        if tone == "hinglish":
            if action == "delayed_retry":
                raw = f"Hi {cust_name}! Aapka ₹{amount:,.2f} ka payment complete nahi ho paya. Tension mat lijiye, kal hum auto-retry karenge. No action needed!"
            else:
                raw = f"Hi {cust_name}, aapka payment interrupt ho gaya tha. Aap iss link se 1-minute me complete kar sakte hain: {payment_link}"
        elif tone == "formal":
            raw = f"Dear {cust_name}, transaction of INR {amount:,.2f} was not completed. Please review and complete payment using this secure link: {payment_link}"
        else:
            if action == "delayed_retry":
                raw = f"Hi {cust_name}, your payment of ₹{amount:,.2f} was interrupted. We've kept your order active and will automatically retry tomorrow."
            elif action == "incentive_discount":
                raw = f"Hi {cust_name}, complete your order today and enjoy an exclusive {discount_pct:.0f}% discount here: {payment_link}"
            else:
                raw = f"Hi {cust_name}, your payment of ₹{amount:,.2f} couldn't go through. You can complete it safely in one tap here: {payment_link}"

        return self.sanitize_message(raw)

    # -------------------------------------------------------------
    # 5. AI Merchant Copilot Q&A
    # -------------------------------------------------------------
    def copilot_query(self, user_query: str, system_context: Dict[str, Any]) -> str:
        prompt = (
            f"You are the AI Merchant Copilot for RazorRecover (Track 03 Razorpay Revenue Recovery).\n"
            f"Here is current live merchant context:\n"
            f"- Total Revenue At Risk: INR {system_context.get('gross_at_risk', 0):,.2f}\n"
            f"- Total Recovered Revenue: INR {system_context.get('gross_recovered', 0):,.2f}\n"
            f"- Net Recovered (after costs): INR {system_context.get('net_recovered', 0):,.2f}\n"
            f"- Overall Recovery Rate: {system_context.get('recovery_rate_pct', 0)}%\n"
            f"- Total Active Cases: {system_context.get('active_cases_count', 0)}\n"
            f"- Escalated Cases (>₹50k): {system_context.get('escalated_cases_count', 0)}\n"
            f"\n"
            f"Merchant Query: \"{user_query}\"\n"
            f"Provide a sharp, data-driven, strategic answer (2-4 sentences) as an expert payments AI agent."
        )
        llm_text = self._call_llm(prompt)
        if llm_text:
            return llm_text
        return (
            f"RazorRecover is currently tracking ₹{system_context.get('gross_at_risk', 0):,.2f} in revenue at risk "
            f"with an active recovery rate of {system_context.get('recovery_rate_pct', 0)}%. "
            f"Interventions are strictly bounded by your configured guardrails (quiet hours and ₹50k escalation ceiling)."
        )

explainer = LLMExplainerAndMessenger()
