"""
Personalized Financial Concept Explainer
Explains financial concepts based on user's spending patterns and risk profile
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime


class RiskProfile(BaseModel):
    """User's financial risk profile"""
    risk_tolerance: str = Field(..., description="conservative, moderate, aggressive")
    spending_pattern: str = Field(..., description="frugal, balanced, liberal")
    monthly_income: Optional[float] = None
    savings_rate: Optional[float] = None
    investment_experience: str = Field(default="beginner", description="beginner, intermediate, advanced")


class ConceptExplanation(BaseModel):
    """Structured financial concept explanation"""
    concept: str = Field(..., description="The financial concept being explained")
    simple_explanation: str = Field(..., description="Simple, relatable explanation")
    personalized_context: str = Field(..., description="How it relates to user's situation")
    practical_example: str = Field(..., description="Real-world example using user's spending data")
    recommendation: str = Field(..., description="Personalized suggestion based on risk profile")
    key_points: List[str] = Field(default_factory=list, description="3-5 key takeaways")
    risk_note: Optional[str] = Field(None, description="Risk-specific considerations")


class FinancialConceptExplainer:
    """
    Explains financial concepts in a personalized, context-aware manner
    """
    
    def __init__(self):
        self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.3)
        
        # Common financial concepts and their core meanings
        self.concept_database = {
            'fd': {
                'full_form': 'Fixed Deposit',
                'core_concept': 'Safe Growth',
                'category': 'savings',
                'aliases': ['fixed deposit', 'fixed-deposit', 'fd kya hai']
            },
            'mutual_fund': {
                'full_form': 'Mutual Fund',
                'core_concept': 'Pooled Investment Growth',
                'category': 'investment',
                'aliases': ['mutual funds', 'mf', 'mutual fund kya hai']
            },
            'sip': {
                'full_form': 'Systematic Investment Plan',
                'core_concept': 'Regular Small Investments',
                'category': 'investment',
                'aliases': ['systematic investment plan', 'sip kya hai', 'sip samjhao']
            },
            'ppf': {
                'full_form': 'Public Provident Fund',
                'core_concept': 'Long-term Tax-free Savings',
                'category': 'savings',
                'aliases': ['public provident fund', 'ppf kya hai']
            },
            'elss': {
                'full_form': 'Equity Linked Savings Scheme',
                'core_concept': 'Tax-saving Market Investment',
                'category': 'investment',
                'aliases': ['equity linked savings', 'elss kya hai']
            },
            'nps': {
                'full_form': 'National Pension System',
                'core_concept': 'Retirement Security',
                'category': 'retirement',
                'aliases': ['national pension system', 'nps kya hai']
            },
            'term_insurance': {
                'full_form': 'Term Life Insurance',
                'core_concept': 'Family Protection',
                'category': 'insurance',
                'aliases': ['term life insurance', 'term plan', 'life insurance']
            },
            'health_insurance': {
                'full_form': 'Health Insurance',
                'core_concept': 'Medical Cost Protection',
                'category': 'insurance',
                'aliases': ['mediclaim', 'health cover', 'medical insurance']
            },
            'emi': {
                'full_form': 'Equated Monthly Installment',
                'core_concept': 'Fixed Monthly Loan Payment',
                'category': 'loan',
                'aliases': ['equated monthly installment', 'monthly installment']
            },
            'stocks': {
                'full_form': 'Stocks/Shares',
                'core_concept': 'Company Ownership Units',
                'category': 'investment',
                'aliases': ['shares', 'equity', 'stock market']
            }
        }
    
    def infer_risk_profile(self, spending_data: Dict[str, Any]) -> RiskProfile:
        """
        Infer user's risk profile from spending patterns
        
        Args:
            spending_data: User's spending history from finance DB
            
        Returns:
            RiskProfile object
        """
        total_spending = spending_data.get('total_spent', 0)
        income = spending_data.get('income', total_spending * 1.5)  # Estimate if not provided
        
        # Calculate savings rate
        savings_rate = max(0, (income - total_spending) / income * 100) if income > 0 else 0
        
        # Analyze spending categories
        categories = spending_data.get('by_category', {})
        essential_spend = sum(categories.get(cat, 0) for cat in ['food', 'transport', 'bills', 'health'])
        discretionary_spend = sum(categories.get(cat, 0) for cat in ['shopping', 'entertainment'])
        
        # Determine spending pattern
        if discretionary_spend / total_spending > 0.4 if total_spending > 0 else False:
            spending_pattern = "liberal"
        elif discretionary_spend / total_spending < 0.2 if total_spending > 0 else True:
            spending_pattern = "frugal"
        else:
            spending_pattern = "balanced"
        
        # Determine risk tolerance
        if savings_rate > 30:
            risk_tolerance = "moderate"  # Has buffer, can take some risk
        elif savings_rate > 15:
            risk_tolerance = "conservative"  # Building safety net
        elif savings_rate < 5:
            risk_tolerance = "conservative"  # Needs security first
        else:
            risk_tolerance = "conservative"  # Default to safety
        
        return RiskProfile(
            risk_tolerance=risk_tolerance,
            spending_pattern=spending_pattern,
            monthly_income=income,
            savings_rate=savings_rate,
            investment_experience="beginner"  # Can be updated from user history
        )
    
    def explain_concept(
        self, 
        concept_query: str, 
        user_spending_data: Dict[str, Any],
        user_profile: Optional[RiskProfile] = None
    ) -> ConceptExplanation:
        """
        Explain a financial concept in a personalized way
        
        Args:
            concept_query: The financial term/concept user asked about
            user_spending_data: User's spending history
            user_profile: User's risk profile (inferred if not provided)
            
        Returns:
            ConceptExplanation with personalized explanation
        """
        # Infer risk profile if not provided
        if user_profile is None:
            user_profile = self.infer_risk_profile(user_spending_data)
        
        # Detect concept from query
        concept_key = self._detect_concept(concept_query)
        concept_info = self.concept_database.get(concept_key, {
            'full_form': concept_query.upper(),
            'core_concept': 'Financial Product',
            'category': 'general'
        })
        
        # Build context
        context = self._build_context(user_spending_data, user_profile)
        
        # Generate explanation using LLM
        explanation_prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are a financial advisor who explains concepts in simple, relatable terms.

**Your Style:**
- Use analogies and metaphors from everyday life
- Connect concepts to user's actual spending behavior
- Match recommendations to their risk tolerance
- Be encouraging but honest about risks
- Use concrete numbers from their spending data

**Risk Alignment:**
- Conservative: Focus on safety, guaranteed returns, capital protection
- Moderate: Balance between growth and safety, diversification
- Aggressive: Emphasize growth potential, accept volatility

**Avoid:**
- Jargon without explanation
- Generic advice that could apply to anyone
- Making promises about returns
- Overwhelming with technical details
"""),
            ("human", """
Explain this financial concept to the user:

**Concept:** {concept_name} ({full_form})
**Core Meaning:** {core_concept}
**Category:** {category}

**User's Financial Profile:**
- Risk Tolerance: {risk_tolerance}
- Spending Pattern: {spending_pattern}
- Monthly Income: ₹{monthly_income:,.0f}
- Savings Rate: {savings_rate:.1f}%
- Investment Experience: {investment_experience}

**User's Spending Context:**
{spending_context}

**User's Question:** {user_query}

Provide a personalized explanation that:
1. Explains the concept in simple terms (avoid just translating the name)
2. Shows how it relates to THEIR specific situation
3. Gives a practical example using their actual spending numbers
4. Suggests if/how they should consider it based on their risk profile
5. Highlights 3-5 key points they should remember
""")
        ])
        
        chain = explanation_prompt | self.llm.with_structured_output(ConceptExplanation)
        
        try:
            result = chain.invoke({
                "concept_name": concept_key.replace('_', ' ').title(),
                "full_form": concept_info['full_form'],
                "core_concept": concept_info['core_concept'],
                "category": concept_info['category'],
                "risk_tolerance": user_profile.risk_tolerance,
                "spending_pattern": user_profile.spending_pattern,
                "monthly_income": user_profile.monthly_income or 0,
                "savings_rate": user_profile.savings_rate or 0,
                "investment_experience": user_profile.investment_experience,
                "spending_context": context,
                "user_query": concept_query
            })
            
            return result
            
        except Exception as e:
            print(f"[ConceptExplainer] ❌ Error: {e}")
            return self._fallback_explanation(concept_query, concept_info, user_profile)
    
    def _detect_concept(self, query: str) -> str:
        """Detect which financial concept is being asked about"""
        query_lower = query.lower()
        
        # Check main keys and aliases
        for key, info in self.concept_database.items():
            # Check main key
            if key in query_lower:
                return key
            
            # Check full form
            if info['full_form'].lower() in query_lower:
                return key
            
            # Check aliases
            if 'aliases' in info:
                for alias in info['aliases']:
                    if alias in query_lower:
                        return key
        
        # Check for partial matches
        for key in self.concept_database.keys():
            if key.replace('_', ' ') in query_lower:
                return key
        
        return 'unknown'
    
    def _build_context(self, spending_data: Dict[str, Any], profile: RiskProfile) -> str:
        """Build spending context string"""
        total = spending_data.get('total_spent', 0)
        categories = spending_data.get('by_category', {})
        
        context = f"Monthly spending: ₹{total:,.0f}\n"
        
        if categories:
            context += "Top spending categories:\n"
            sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
            for cat, amount in sorted_cats:
                context += f"  • {cat.capitalize()}: ₹{amount:,.0f}\n"
        
        context += f"\nThey are a {profile.spending_pattern} spender with "
        context += f"{profile.risk_tolerance} risk tolerance.\n"
        
        if profile.savings_rate:
            context += f"Current savings rate: {profile.savings_rate:.1f}% of income\n"
        
        return context
    
    def _fallback_explanation(
        self, 
        query: str, 
        concept_info: Dict[str, str],
        profile: RiskProfile
    ) -> ConceptExplanation:
        """Fallback explanation when LLM fails"""
        
        risk_recommendations = {
            'conservative': "Focus on safety and guaranteed returns. This might be suitable if you prioritize capital protection.",
            'moderate': "Consider a balanced approach. This could work if you're comfortable with some risk for better returns.",
            'aggressive': "This may offer growth potential but comes with risk. Suitable if you have a long investment horizon."
        }
        
        return ConceptExplanation(
            concept=concept_info.get('full_form', query),
            simple_explanation=f"{concept_info.get('full_form', query)} is a {concept_info.get('category', 'financial')} product. {concept_info.get('core_concept', 'Financial instrument')} - it helps you manage your money effectively.",
            personalized_context=f"Based on your {profile.spending_pattern} spending pattern and {profile.risk_tolerance} risk profile, this product may or may not suit your needs.",
            practical_example="Consult a financial advisor for specific guidance based on your situation.",
            recommendation=risk_recommendations.get(profile.risk_tolerance, "Consult a financial advisor for personalized advice."),
            key_points=[
                "Understand the product before investing",
                "Consider your financial goals",
                "Assess your risk tolerance",
                "Don't invest money you can't afford to lose"
            ],
            risk_note=f"This explanation is generic. For {profile.risk_tolerance} investors like you, personalized advice is recommended."
        )


# Singleton instance
_explainer = None

def get_concept_explainer() -> FinancialConceptExplainer:
    """Get or create concept explainer singleton"""
    global _explainer
    if _explainer is None:
        _explainer = FinancialConceptExplainer()
        print("[ConceptExplainer] ✅ Singleton initialized")
    return _explainer