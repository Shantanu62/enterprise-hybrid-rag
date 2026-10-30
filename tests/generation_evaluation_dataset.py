
GENERATION_EVALUATION_DATASET = [
    {
        "question": "How should sensitive customer data be protected?",
        "expected_facts": [
            "Sensitive customer data must be encrypted during transmission.",
            "Sensitive customer data must be encrypted during storage.",
            "Access to confidential information must follow least privilege."
        ],
        "answerable": True,
    },
    {
        "question": "How many days of annual leave do full-time employees receive?",
        "expected_facts": [
            "Full-time employees receive 20 days of paid annual leave.",
            "Another document mentions 18 days of paid annual leave.",
            "The documents contain different leave entitlement figures."
        ],
        "answerable": True,
    },
    {
        "question": "How do employees submit an IT support request?",
        "expected_facts": [
            "IT support requests should be submitted through the internal help desk."
        ],
        "answerable": True,
    },
    {
        "question": "What is the company parental leave policy?",
        "expected_facts": [],
        "answerable": False,
    },
    {
        "question": "What authentication method must employees use?",
        "expected_facts": [
            "Employees must use multi-factor authentication for company accounts."
        ],
        "answerable": True,
    },
    {
        "question": "How much notice is required for planned leave?",
        "expected_facts": [
            "Employees should provide at least three working days of notice for planned leave."
        ],
        "answerable": True,
    },
    {
        "question": "How many days per week can employees work remotely?",
        "expected_facts": [
            "Employees may work remotely up to two days per week."
        ],
        "answerable": True,
    },
    {
        "question": "What should employees do if they receive phishing emails?",
        "expected_facts": [
            "Employees must report suspected phishing emails to the security team."
        ],
        "answerable": True,
    },
]
