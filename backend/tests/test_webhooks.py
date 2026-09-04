import unittest
import hmac
import hashlib
import json
from backend.app.api.webhooks import verify_razorpay_signature

class TestWebhookSecurity(unittest.TestCase):

    def test_signature_verification_success(self):
        secret = "test_secret_key_123"
        body = b'{"event":"payment.failed","amount":5000}'
        valid_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        self.assertTrue(verify_razorpay_signature(body, valid_sig, secret))

    def test_signature_verification_failure_tampered(self):
        secret = "test_secret_key_123"
        body = b'{"event":"payment.failed","amount":5000}'
        tampered_body = b'{"event":"payment.failed","amount":999999}'
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        self.assertFalse(verify_razorpay_signature(tampered_body, sig, secret))

    def test_signature_verification_wrong_secret(self):
        body = b'{"event":"payment.failed","amount":5000}'
        sig = hmac.new(b"secret_A", body, hashlib.sha256).hexdigest()
        self.assertFalse(verify_razorpay_signature(body, sig, "secret_B"))

if __name__ == "__main__":
    unittest.main()
