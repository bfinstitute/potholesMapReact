import re
from typing import Optional


INTENT_PATTERNS = {
    "community_need": [
        r"most common health issues",
        r"health issues",
        r"mental health (indicators|signals).*(increase|decrease|trend)",
        r"behavioral health",
        r"chronic disease",
        r"public health indicators",
        r"community need",
    ],
    "community_conditions_311": [
        r"housing[- ]related complaints",
        r"mold|pests?|sanitation",
        r"environmental hazards?",
        r"311",
        r"community distress",
        r"unsafe housing",
        r"noise complaints?",
    ],
    "service_landscape": [
        r"what .*services.*available",
        r"mental health services",
        r"behavioral health providers",
        r"organizations.*(youth|housing|mental)",
        r"fewer services",
        r"service coverage",
        r"service landscape",
    ],
    "need_service_gap": [
        r"need.*service.*gap",
        r"gaps?",
        r"needs highest but services",
        r"largest service gaps?",
        r"not matched by service",
        r"high need.*limited services",
        r"underfunded relative to impact",
    ],
    "funding_intelligence": [
        r"funding",
        r"investment",
        r"funded organizations?",
        r"funding gaps?",
        r"philanthropic",
        r"who funds what",
        r"funding opportunity",
    ],
    "context_demographics": [
        r"demographics?",
        r"poverty rate",
        r"income distribution",
        r"lack health insurance",
        r"insurance coverage",
        r"social determinants",
        r"age distribution",
        r"race|ethnicity",
    ],
    "missing_sensitive_data": [
        r"\ber visits?\b",
        r"crisis response",
        r"substance use",
        r"overdose",
        r"suicide attempts?",
    ],
}


def detect_intent(prompt: str) -> Optional[str]:
    prompt_lower = prompt.lower()
    priority_order = [
        "missing_sensitive_data",
        "funding_intelligence",
        "need_service_gap",
        "community_conditions_311",
        "service_landscape",
        "context_demographics",
        "community_need",
    ]
    for intent_name in priority_order:
        patterns = INTENT_PATTERNS.get(intent_name, [])
        for pattern in patterns:
            if re.search(pattern, prompt_lower):
                return intent_name
    return None
