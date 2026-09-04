import os
import re
from typing import Dict, Any, Optional
from backend.app.config import settings

class LLMExplainerAndMessenger:
    """
    Reasoning and communication layer.
    Transforms deterministic decisions and mathematical evidence into:
    1. Human-readable audit trail explanations.
    2. Personalized customer recovery communications with content guardrails.
    Includes a 100% offline deterministic fallback engine.
    """
    def __init__(self):
        self.gemini_available = bool(settings.GEMINI_API_KEY)
        self.openai_available = bool(settings.OPENAI_API_KEY)

    def _call_gemini(self, prompt: str) -> Optional[str]:
        if not self.gemini_available:
            return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.text.strip() if response and response.text else None
        except Exception:
            return None

    def _call_openai(self, prompt: str) -> Optional[str]:
        if not self.openai_available:
            return None
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
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

        # Attempt LLM generation if key exists
        if self.gemini_available or self.openai_available:
            prompt = (
                f"You are the Audit Explainer for RazorRecover, an autonomous revenue recovery engine. "
                f"Summarize the following mathematical decision in exactly 2 concise, professional sentences for a merchant audit trail:\n"
                f"- Customer cohort: {cohort}\n"
                f"- Amount at risk: INR {amount}\n"
                f"- Root cause: {root_cause}\n"
                f"- Selected action: {action}\n"
                f"- Recovery probability: {prob:.2f}\n"
                f"- Net Expected Value: INR {net_val}\n"
                f"- Policy reason: {chosen.get('policy_reason')}\n"
                f"Explain why this intervention was economically optimal while respecting merchant policy."
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
    # 2. Content & Policy Guardrails for Messages
    # -------------------------------------------------------------
    def sanitize_message(self, message: str, max_length: int = 240) -> str:
        """
        Enforces tone, length, and forbidden-content rules on outbound customer messages.
        Prevents aggressive collection wording, unauthorized promises, and phishing tropes.
        """
        forbidden_patterns = [
            r"\blegal action\b",
            r"\bpolice\b",
            r"\bcourt\b",
            r"\bpenalty fee\b",
            r"\bfraud\b",
            r"\barrest\b",
            r"\burpass\b"
        ]
        clean_msg = message
        for pat in forbidden_patterns:
            clean_msg = re.sub(pat, "notice", clean_msg, flags=re.IGNORECASE)

        # Length cap
        if len(clean_msg) > max_length:
            clean_msg = clean_msg[:max_length - 3] + "..."
        return clean_msg.strip()

    # -------------------------------------------------------------
    # 3. Customer Message Generation (LLM + Template Fallback)
    # -------------------------------------------------------------
    def generate_customer_message(
        self,
        customer: Dict[str, Any],
        event: Dict[str, Any],
        decision: Dict[str, Any]
    ) -> str:
        chosen = decision.get("chosen_action_details", {})
        action = decision.get("chosen_action", "do_nothing")
        cust_name = customer.get("name", "Customer").split()[0]
        amount = event.get("amount", 0.0)
        discount_pct = chosen.get("discount_pct", 0.0)
        payment_link = f"https://rzp.io/i/{event.get('order_id', 'pay_rec_link')}"

        if action in ["human_escalation", "do_nothing"]:
            return ""

        # Attempt LLM generation if available
        if self.gemini_available or self.openai_available:
            prompt = (
                f"Write a friendly, empathetic customer recovery SMS/WhatsApp message (under 160 characters):\n"
                f"- Customer Name: {cust_name}\n"
                f"- Amount: INR {amount}\n"
                f"- Action: {action}\n"
                f"- Discount: {discount_pct}%\n"
                f"- Payment Link: {payment_link}\n"
                f"Tone: Helpful, non-accusatory, professional Indian business context. Do not use threatening language."
            )
            llm_text = self._call_llm(prompt)
            if llm_text:
                return self.sanitize_message(llm_text)

        # Deterministic Templates (Guaranteed offline fallback)
        if action == "delayed_retry":
            raw = (
                f"Hi {cust_name}, your recent payment of ₹{amount:,.2f} couldn't be processed. "
                f"We've kept your order active and will automatically retry tomorrow. No action is required from your side."
            )
        elif action == "smart_reminder":
            raw = (
                f"Hi {cust_name}, your payment of ₹{amount:,.2f} was interrupted. "
                f"You can quickly complete it in one tap here: {payment_link}. Thank you!"
            )
        elif action == "incentive_discount":
            raw = (
                f"Hi {cust_name}, we noticed your payment didn't go through. "
                f"Enjoy an exclusive {discount_pct:.0f}% discount if you complete your order today: {payment_link}"
            )
        elif action == "retry_now":
            raw = (
                f"Hi {cust_name}, we encountered a brief banking network issue while processing your ₹{amount:,.2f} payment. "
                f"We are reprocessing it now."
            )
        else:
            raw = ""

        return self.sanitize_message(raw)

explainer = LLMExplainerAndMessenger()
