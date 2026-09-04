import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "RazorRecover"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Operation Mode: "simulator" (default, zero-key development) or "razorpay" (live test mode)
    MODE: str = os.getenv("MODE", "simulator")
    
    # Razorpay Test Credentials (Optional in simulator mode)
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "whsec_razorrecover_test_secret_123")
    
    # AI / LLM Keys (Optional - deterministic fallback is active if absent)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./razorrecover.db")
    
    # Deterministic Merchant Policy Guardrails
    MAX_RETRIES: int = 3
    MIN_RETRY_INTERVAL_HOURS: int = 6
    MAX_DISCOUNT_PCT: float = 10.0
    MAX_MESSAGES_PER_48H: int = 2
    QUIET_HOURS_START: int = 22  # 10:00 PM
    QUIET_HOURS_END: int = 8     # 08:00 AM
    HUMAN_ESCALATION_THRESHOLD_INR: float = 50000.0  # ₹50,000 threshold
    
    # Intervention Cost Model (INR)
    COST_RETRY_NOW: float = 5.0             # Gateway retry fee & load cost
    COST_RETRY_DELAYED: float = 2.0         # Queued retry handling cost
    COST_REMINDER_SMS: float = 0.5          # SMS gateway cost
    COST_REMINDER_WHATSAPP: float = 1.5     # WhatsApp Business API message fee
    COST_ESCALATION_OPS: float = 150.0      # Human operations review cost
    CUSTOMER_PENALTY_OVERSPAM: float = 40.0 # Churn risk fatigue penalty
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
