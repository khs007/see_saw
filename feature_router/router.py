from llm.run_agent import run_agent



SCAM_KEYWORDS = ["scam", "fraud", "otp", "phishing","check","link"]
finance_keywords = [
        "spent", "paid", "bought", "expense", "budget",
        "rupees", "₹", "rs", "transaction", "balance",
        "income", "salary", "received"
    ]

def router_feature(req):
    if any(keyword in req for keyword in finance_keywords):
        return "finance_handler"
    return run_agent(req)
    



