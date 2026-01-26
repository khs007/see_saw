# scam_detector/scam_detector.py - BACKWARD COMPATIBLE VERSION
"""
Enhanced Scam Detection Module for FinGuard
Detects fraudulent messages, phishing attempts, and scam patterns
BACKWARD COMPATIBLE with existing imports
"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate


class ScamAnalysis(BaseModel):
    """Schema for scam detection results"""
    is_scam: bool = Field(..., description="Whether the message is likely a scam")
    risk_level: str = Field(..., description="Risk level: LOW, MEDIUM, HIGH, CRITICAL")
    confidence: float = Field(..., description="Confidence score 0.0 to 1.0")
    scam_type: Optional[str] = Field(None, description="Type of scam detected")
    red_flags: list[str] = Field(default_factory=list, description="List of suspicious indicators")
    recommendation: str = Field(..., description="User recommendation")


class ScamDetector:
    """
    Detects scams using multiple approaches:
    1. LLM-based pattern recognition
    2. Rule-based red flag detection
    3. Optional ML model (if available)
    """
    
    def __init__(self):
        self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        self.ml_model = self._load_ml_model()
        
        # Common scam indicators
        self.red_flag_keywords = {
            'urgent': ['urgent', 'immediately', 'expire', 'limited time', 'act now', 'hurry'],
            'money_request': ['send money', 'transfer', 'payment required', 'pay now', 'deposit'],
            'personal_info': ['otp', 'pin', 'password', 'cvv', 'card number', 'account number'],
            'threats': ['block', 'suspend', 'legal action', 'police', 'arrest', 'fine'],
            'prizes': ['won', 'winner', 'lottery', 'prize', 'congratulations', 'selected'],
            'impersonation': ['bank', 'government', 'income tax', 'police', 'courier'],
            'suspicious_links': ['bit.ly', 'tinyurl', 'click here', 'verify account', 'update kyc']
        }
    
    def _load_ml_model(self):
        """Load ML model if available"""
        try:
            import joblib
            model_path = "model/scam_bundle.pkl"
            if os.path.exists(model_path):
                print("[ScamDetector] ✅ ML model loaded")
                return joblib.load(model_path)
            else:
                print("[ScamDetector] ⚠️ ML model not found, using LLM-only mode")
                return None
        except Exception as e:
            print(f"[ScamDetector] ⚠️ Failed to load ML model: {e}")
            return None
    
    def detect_scam(self, message: str, context: Optional[Dict[str, Any]] = None) -> ScamAnalysis:
        """
        Main scam detection function
        
        Args:
            message: The message/text to analyze
            context: Optional context (sender info, links, etc.)
            
        Returns:
            ScamAnalysis object with detection results
        """
        # Step 1: Rule-based red flag detection
        red_flags = self._detect_red_flags(message)
        
        # Step 2: LLM-based analysis
        llm_analysis = self._llm_analyze(message, red_flags)
        
        # Step 3: ML model prediction (if available)
        ml_score = None
        if self.ml_model and context:
            ml_score = self._ml_predict(message, context)
        
        # Step 4: Combine results
        final_analysis = self._combine_results(llm_analysis, red_flags, ml_score)
        
        return final_analysis
    
    def _detect_red_flags(self, message: str) -> list[str]:
        """Detect red flag keywords in message"""
        message_lower = message.lower()
        flags = []
        
        for category, keywords in self.red_flag_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    flags.append(f"{category}: '{keyword}'")
        
        return flags
    
    def _llm_analyze(self, message: str, red_flags: list[str]) -> Dict[str, Any]:
        """Use LLM to analyze message for scam patterns"""
        
        scam_prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are a cybersecurity expert specializing in scam detection.

Analyze the message for scam indicators:

**Common Scam Types:**
- Phishing (fake banks, government impersonation)
- OTP/PIN requests
- Fake prize/lottery scams
- Investment fraud
- Romance scams
- Fake delivery/courier scams
- KYC update scams
- Social engineering attacks

**Red Flags:**
- Urgency and pressure tactics
- Requests for sensitive information (OTP, PIN, passwords)
- Too-good-to-be-true offers
- Spelling/grammar errors in official-looking messages
- Suspicious links or numbers
- Threats of account suspension/legal action
- Unsolicited contact requesting money

Provide a detailed analysis with risk assessment.
"""),
            ("human", """
Message to analyze:
{message}

Detected red flags:
{red_flags}

Analyze this message and determine if it's a scam.
""")
        ])
        
        chain = scam_prompt | self.llm.with_structured_output(ScamAnalysis)
        
        try:
            result = chain.invoke({
                "message": message,
                "red_flags": "\n".join(red_flags) if red_flags else "None detected"
            })
            return result.model_dump()
        except Exception as e:
            print(f"[ScamDetector] ❌ LLM analysis failed: {e}")
            # Fallback to rule-based
            return self._fallback_analysis(message, red_flags)
    
    def _ml_predict(self, message: str, context: Dict[str, Any]) -> float:
        """Use ML model for prediction if available"""
        try:
            from scipy.sparse import hstack
            
            bundle = self.ml_model
            model = bundle["model"]
            tfidf_scam = bundle["tfidf_scam"]
            tfidf_response = bundle.get("tfidf_response")
            safe_features = bundle.get("safe_numerical_features", [])
            
            # Transform text
            X_scam = tfidf_scam.transform([message])
            
            # Handle response text if available
            response_text = context.get("response_text", "")
            if tfidf_response:
                X_resp = tfidf_response.transform([response_text])
            else:
                X_resp = None
            
            # Numerical features
            numeric_values = [context.get(f, 0) for f in safe_features]
            
            # Combine features
            if X_resp is not None:
                X = hstack([X_scam, X_resp, [numeric_values]])
            else:
                X = hstack([X_scam, [numeric_values]])
            
            # Predict
            proba = model.predict_proba(X)[0][1]
            return float(proba)
            
        except Exception as e:
            print(f"[ScamDetector] ⚠️ ML prediction failed: {e}")
            return None
    
    def _fallback_analysis(self, message: str, red_flags: list[str]) -> Dict[str, Any]:
        """Fallback analysis when LLM fails"""
        flag_count = len(red_flags)
        
        if flag_count >= 4:
            risk_level = "CRITICAL"
            confidence = 0.9
            is_scam = True
        elif flag_count >= 2:
            risk_level = "HIGH"
            confidence = 0.75
            is_scam = True
        elif flag_count == 1:
            risk_level = "MEDIUM"
            confidence = 0.5
            is_scam = True
        else:
            risk_level = "LOW"
            confidence = 0.3
            is_scam = False
        
        return {
            "is_scam": is_scam,
            "risk_level": risk_level,
            "confidence": confidence,
            "scam_type": "Unknown (LLM analysis failed)",
            "red_flags": red_flags,
            "recommendation": "⚠️ Analysis incomplete. Exercise caution and verify with official sources."
        }
    
    def _combine_results(
        self, 
        llm_result: Dict[str, Any], 
        red_flags: list[str],
        ml_score: Optional[float]
    ) -> ScamAnalysis:
        """Combine all analysis results"""
        
        # If ML score available, adjust confidence
        if ml_score is not None:
            # Weight: 60% LLM, 40% ML
            combined_confidence = (llm_result["confidence"] * 0.6) + (ml_score * 0.4)
            llm_result["confidence"] = combined_confidence
            
            # Adjust risk level based on combined score
            if combined_confidence >= 0.85:
                llm_result["risk_level"] = "CRITICAL"
            elif combined_confidence >= 0.65:
                llm_result["risk_level"] = "HIGH"
            elif combined_confidence >= 0.4:
                llm_result["risk_level"] = "MEDIUM"
            else:
                llm_result["risk_level"] = "LOW"
        
        # Ensure red flags are included
        llm_result["red_flags"] = red_flags
        
        return ScamAnalysis(**llm_result)


# ============================================================
# BACKWARD COMPATIBILITY FUNCTIONS
# ============================================================

def load_scam_bundle():
    """
    DEPRECATED: For backward compatibility only.
    
    The new scam detector automatically loads the ML model on initialization.
    This function is kept for backward compatibility with existing code.
    """
    print("[load_scam_bundle] ⚠️ DEPRECATED: This function is no longer needed.")
    print("[load_scam_bundle]    The scam detector auto-initializes on first use.")
    print("[load_scam_bundle]    You can safely remove this import from app/main.py")
    
    # Return None - won't break existing code
    return None


def predict_scam(payload: dict) -> float:
    """
    DEPRECATED: For backward compatibility only.
    
    Use get_scam_detector().detect_scam() instead.
    """
    print("[predict_scam] ⚠️ DEPRECATED: Use get_scam_detector().detect_scam() instead")
    
    detector = get_scam_detector()
    
    scam_text = payload.get("scam_text", "")
    response_text = payload.get("response_text", "")
    
    # Build context from payload
    context = {
        "response_text": response_text
    }
    
    # Add any numerical features
    for key, value in payload.items():
        if key not in ["scam_text", "response_text"] and isinstance(value, (int, float)):
            context[key] = value
    
    result = detector.detect_scam(scam_text, context)
    
    # Return just the confidence score for backward compatibility
    return result.confidence


# Singleton instance
_detector = None

def get_scam_detector() -> ScamDetector:
    """Get or create scam detector singleton"""
    global _detector
    if _detector is None:
        _detector = ScamDetector()
        print("[ScamDetector] ✅ Singleton initialized")
    return _detector