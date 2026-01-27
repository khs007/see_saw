"""
Language Detection and Multilingual Response Handler
Detects user's language preference and generates responses accordingly
"""

from typing import Optional, Dict, Literal
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate


class LanguageDetection(BaseModel):
    """Detected language from user query"""
    primary_language: Literal["hindi", "hinglish", "english", "tamil", "telugu", "bengali", "marathi", "gujarati"] = Field(
        ...,
        description="Primary language used in the query"
    )
    script: Literal["devanagari", "roman", "tamil", "telugu", "bengali", "gujarati", "mixed"] = Field(
        ...,
        description="Script used (devanagari for Hindi, roman for English/Hinglish)"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    should_respond_in: str = Field(
        ...,
        description="Language/style to use in response"
    )


class LanguageHandler:
    """Handles language detection and response formatting"""
    
    def __init__(self):
        self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        
        # Language indicators
        self.language_patterns = {
            'hinglish': {
                'keywords': ['kya', 'hai', 'hota', 'kaise', 'kyun', 'aur', 'ya', 'ko', 'ka', 'ki', 
                           'me', 'mein', 'se', 'tak', 'par', 'pe', 'bhi', 'toh', 'nahin', 'nahi'],
                'script': 'roman'
            },
            'hindi': {
                'keywords': ['क्या', 'है', 'होता', 'कैसे', 'क्यों', 'और', 'या', 'को', 'का', 'की',
                           'में', 'से', 'तक', 'पर', 'भी', 'तो', 'नहीं'],
                'script': 'devanagari'
            },
            'english': {
                'keywords': ['what', 'how', 'why', 'when', 'where', 'is', 'are', 'the', 'a', 'an',
                           'for', 'to', 'in', 'on', 'at', 'with'],
                'script': 'roman'
            }
        }
    
    def detect_language(self, query: str) -> LanguageDetection:
        """
        Detect language from user query
        
        Args:
            query: User's query text
            
        Returns:
            LanguageDetection with language info
        """
        query_lower = query.lower()
        
        # Quick rule-based detection for common cases
        hinglish_count = sum(1 for kw in self.language_patterns['hinglish']['keywords'] if kw in query_lower)
        hindi_count = sum(1 for kw in self.language_patterns['hindi']['keywords'] if kw in query)
        english_count = sum(1 for kw in self.language_patterns['english']['keywords'] if kw in query_lower)
        
        # Hinglish detection (Hindi words in Roman script)
        if hinglish_count >= 2:
            return LanguageDetection(
                primary_language="hinglish",
                script="roman",
                confidence=0.9,
                should_respond_in="hinglish"
            )
        
        # Hindi detection (Devanagari script)
        if hindi_count >= 2:
            return LanguageDetection(
                primary_language="hindi",
                script="devanagari",
                confidence=0.9,
                should_respond_in="hindi"
            )
        
        # English detection
        if english_count >= 2:
            return LanguageDetection(
                primary_language="english",
                script="roman",
                confidence=0.9,
                should_respond_in="english"
            )
        
        # Use LLM for ambiguous cases
        return self._llm_detect_language(query)
    
    def _llm_detect_language(self, query: str) -> LanguageDetection:
        """Use LLM to detect language when rules fail"""
        
        detection_prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are a language detection expert for Indian languages.

Detect the language from the user's query:

**Languages to detect:**
- english: Pure English
- hinglish: Hindi words written in Roman script (e.g., "kya hai", "kaise")
- hindi: Hindi in Devanagari script (क्या है)
- tamil: Tamil script
- telugu: Telugu script
- bengali: Bengali script
- marathi: Marathi (usually Devanagari)
- gujarati: Gujarati script

**Script detection:**
- roman: English letters (a-z)
- devanagari: Hindi/Marathi script
- tamil: Tamil script
- telugu: Telugu script
- bengali: Bengali script
- gujarati: Gujarati script
- mixed: Mix of scripts

**Response language:**
- If hinglish → respond in "hinglish" (natural Hindi-English mix in Roman)
- If hindi → respond in "hindi" (Devanagari)
- If english → respond in "english"
- For other languages → respond in "hinglish" as fallback

Examples:
"fd kya hota hai" → hinglish, roman, respond in hinglish
"एफडी क्या है" → hindi, devanagari, respond in hindi
"what is FD" → english, roman, respond in english
"""),
            ("human", "Query: {query}")
        ])
        
        chain = detection_prompt | self.llm.with_structured_output(LanguageDetection)
        
        try:
            result = chain.invoke({"query": query})
            return result
        except Exception as e:
            print(f"[LanguageHandler] ❌ LLM detection failed: {e}")
            # Fallback to English
            return LanguageDetection(
                primary_language="english",
                script="roman",
                confidence=0.5,
                should_respond_in="english"
            )
    
    def format_vernacular_response(
        self,
        explanation: Dict,
        language_pref: str,
        spending_data: Dict
    ) -> str:
        """
        Format explanation in user's preferred language
        
        Args:
            explanation: ConceptExplanation dict
            language_pref: Target language (hinglish/hindi/english)
            spending_data: User's spending data
            
        Returns:
            Formatted response in target language
        """
        
        if language_pref == "hinglish":
            return self._format_hinglish(explanation, spending_data)
        elif language_pref == "hindi":
            return self._format_hindi(explanation, spending_data)
        else:
            return self._format_english(explanation, spending_data)
    
    def _format_hinglish(self, exp: Dict, data: Dict) -> str:
        """Format response in natural Hinglish"""
        
        print(f"[Hinglish Formatter] Starting Hinglish formatting...")
        print(f"[Hinglish Formatter] Concept: {exp.get('concept', 'Unknown')}")
        
        response = f"💡 **{exp['concept']} ko samajhte hain**\n\n"
        
        # Simple explanation in Hinglish
        response += f"**Yeh kya hai:**\n"
        simple_exp = self._translate_to_hinglish(exp['simple_explanation'])
        print(f"[Hinglish Formatter] Simple explanation translated")
        response += simple_exp + "\n\n"
        
        # Personalized context
        response += f"**Aapki situation ke liye:**\n"
        context_exp = self._translate_to_hinglish(exp['personalized_context'])
        print(f"[Hinglish Formatter] Context translated")
        response += context_exp + "\n\n"
        
        # Practical example
        if exp.get('practical_example'):
            response += f"**Example:**\n"
            example_exp = self._translate_to_hinglish(exp['practical_example'])
            print(f"[Hinglish Formatter] Example translated")
            response += example_exp + "\n\n"
        
        # Key points
        if exp.get('key_points'):
            response += "**Yaad rakhne wali baatein:**\n"
            for i, point in enumerate(exp['key_points'], 1):
                translated_point = self._translate_to_hinglish(point)
                response += f"{i}. {translated_point}\n"
            response += "\n"
            print(f"[Hinglish Formatter] Key points translated")
        
        # Recommendation
        response += f"**Meri salah:**\n"
        recommendation = self._translate_to_hinglish(exp['recommendation'])
        print(f"[Hinglish Formatter] Recommendation translated")
        response += recommendation + "\n"
        
        # Risk note
        if exp.get('risk_note'):
            risk_note = self._translate_to_hinglish(exp['risk_note'])
            response += f"\n⚠️ {risk_note}\n"
        
        print(f"[Hinglish Formatter] ✅ Hinglish formatting complete")
        
        # Spending summary
        total = data.get('total_spent', 0)
        income = data.get('income', 0)
        if total > 0:
            savings = income - total
            savings_rate = (savings / income * 100) if income > 0 else 0
            response += f"\n📊 **Aapka current finance:**\n"
            response += f"• Monthly kharch: ₹{total:,.0f}\n"
            response += f"• Estimated bachत: ₹{savings:,.0f} ({savings_rate:.1f}%)\n"
        
        return response
    
    def _translate_to_hinglish(self, text: str) -> str:
        """
        Translate English text to natural Hinglish using LLM
        
        Args:
            text: English text to translate
            
        Returns:
            Hinglish translation
        """
        
        # Don't translate very short text
        if len(text.strip()) < 10:
            return text
        
        translation_prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are a Hinglish translator. Convert English to NATURAL, CONVERSATIONAL Hinglish that sounds like a friendly Indian person talking.

**CRITICAL RULES:**
1. Use Roman script ONLY (NO Devanagari)
2. Sound NATURAL - like talking to a friend
3. Mix Hindi and English words in EVERY sentence
4. Use common Hindi words: kya, hai, aapke, liye, bachत, kharch, aur, ka, ke, ko

**Keep in English:**
- Financial terms: FD, PPF, mutual fund, SIP, interest, returns, investment
- Technical terms: portfolio, risk, tenure
- Numbers: ₹5000, 7%, 30%

**Must Use Hindi Words:**
- is/are → hai/hain
- you → aap/aapka/aapke
- your → aapka/aapke/aapki
- for → ke liye
- and → aur
- or → ya
- but → lekin/par
- can → sakte/sakti
- should → chahiye
- good → achha/achhi
- safe → safe (keep)
- savings → bachत
- spending → kharch

**Examples:**
"This is safe" → "Yeh safe hai"
"Based on your spending" → "Aapke kharch ke basis par"
"You can save 30%" → "Aap 30% bachat kar sakte hain"
"It's locked for 3 years" → "Yeh 3 saal ke liye locked hai"
"Perfect for conservative investors" → "Conservative investors ke liye bilkul perfect"
"You should invest" → "Aapko invest karna chahiye"
"Your monthly spending" → "Aapka monthly kharch"

**Bad Translation (AVOID):**
"Your spending is high" → "Your spending high hai" ❌
**Good Translation:**
"Your spending is high" → "Aapka kharch zyada hai" ✅

IMPORTANT: Translate the ENTIRE text, not just parts. Make it sound natural and friendly!
"""),
            ("human", "Translate this ENTIRE text to natural Hinglish:\n\n{text}")
        ])
        
        chain = translation_prompt | self.llm
        
        try:
            result = chain.invoke({"text": text})
            translated = result.content.strip()
            
            # Debug log
            print(f"[Hinglish] Original: {text[:100]}...")
            print(f"[Hinglish] Translated: {translated[:100]}...")
            
            return translated
        except Exception as e:
            print(f"[Hinglish Translation] ❌ Error: {e}")
            return text  # Return original if translation fails
    
    def _format_hindi(self, exp: Dict, data: Dict) -> str:
        """Format response in Hindi (Devanagari)"""
        
        # For now, use English - you can add proper Hindi translation later
        # This requires a Hindi-capable LLM or translation service
        
        print("[LanguageHandler] ⚠️ Hindi (Devanagari) translation not yet implemented")
        print("[LanguageHandler]    Falling back to Hinglish")
        
        return self._format_hinglish(exp, data)
    
    def _format_english(self, exp: Dict, data: Dict) -> str:
        """Format response in English (existing format)"""
        
        response = f"💡 **Understanding {exp['concept']}**\n\n"
        response += f"**What it means:**\n{exp['simple_explanation']}\n\n"
        response += f"**For your situation:**\n{exp['personalized_context']}\n\n"
        
        if exp.get('practical_example'):
            response += f"**Practical Example:**\n{exp['practical_example']}\n\n"
        
        if exp.get('key_points'):
            response += "**Key Points to Remember:**\n"
            for i, point in enumerate(exp['key_points'], 1):
                response += f"{i}. {point}\n"
            response += "\n"
        
        response += f"**My Suggestion:**\n{exp['recommendation']}\n"
        
        if exp.get('risk_note'):
            response += f"\n⚠️ {exp['risk_note']}\n"
        
        total = data.get('total_spent', 0)
        income = data.get('income', 0)
        if total > 0:
            savings = income - total
            savings_rate = (savings / income * 100) if income > 0 else 0
            response += f"\n📊 **Your Current Finances:**\n"
            response += f"• Monthly Spending: ₹{total:,.0f}\n"
            response += f"• Estimated Savings: ₹{savings:,.0f} ({savings_rate:.1f}%)\n"
        
        return response


# Singleton
_language_handler = None

def get_language_handler() -> LanguageHandler:
    """Get or create language handler singleton"""
    global _language_handler
    if _language_handler is None:
        _language_handler = LanguageHandler()
        print("[LanguageHandler] ✅ Singleton initialized")
    return _language_handler