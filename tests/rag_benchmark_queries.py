"""
RAG Evaluation Benchmark Queries (30 Questions)
Covering:
- Direct survey status lookups
- Parcel area & numerical accuracy
- Compensation award queries
- Conflict / discrepancy handling
- Insufficient evidence / out-of-bounds queries
- Village / project aggregations
"""

BENCHMARK_QUERIES = [
    # 1-5: Specific Survey Status Queries
    {
        "id": "q1",
        "query": "What is the status of Survey 142/3A?",
        "expected_survey": "142/3A",
        "category": "survey_status",
        "requires_evidence": True,
        "expected_facts": ["142/3A"]
    },
    {
        "id": "q2",
        "query": "What is the acquisition status of survey number 142/3A in Vadadala?",
        "expected_survey": "142/3A",
        "category": "survey_status",
        "requires_evidence": True,
        "expected_facts": ["Vadadala", "142/3A"]
    },
    {
        "id": "q3",
        "query": "Has Survey 101 been acquired yet?",
        "expected_survey": "101",
        "category": "survey_status",
        "requires_evidence": True,
        "expected_facts": ["101"]
    },
    {
        "id": "q4",
        "query": "What is the current status of parcel 105/2?",
        "expected_survey": "105/2",
        "category": "survey_status",
        "requires_evidence": True,
        "expected_facts": ["105/2"]
    },
    {
        "id": "q5",
        "query": "What is the status of Survey 88 in Vadadala village?",
        "expected_survey": "88",
        "category": "survey_status",
        "requires_evidence": True,
        "expected_facts": ["88"]
    },

    # 6-10: Area & Numerical Queries
    {
        "id": "q6",
        "query": "What is the area of Survey 142/3A in hectares?",
        "expected_survey": "142/3A",
        "category": "numerical_area",
        "requires_evidence": True,
        "expected_facts": ["142/3A", "area"]
    },
    {
        "id": "q7",
        "query": "How much extent of land is being acquired in survey 142/3A?",
        "expected_survey": "142/3A",
        "category": "numerical_area",
        "requires_evidence": True,
        "expected_facts": ["142/3A"]
    },
    {
        "id": "q8",
        "query": "What is the land area of survey number 102/1?",
        "expected_survey": "102/1",
        "category": "numerical_area",
        "requires_evidence": True,
        "expected_facts": ["102/1"]
    },
    {
        "id": "q9",
        "query": "What is the total area for survey 109?",
        "expected_survey": "109",
        "category": "numerical_area",
        "requires_evidence": True,
        "expected_facts": ["109"]
    },
    {
        "id": "q10",
        "query": "Show me the area in hectares for parcel 142/3A.",
        "expected_survey": "142/3A",
        "category": "numerical_area",
        "requires_evidence": True,
        "expected_facts": ["142/3A"]
    },

    # 11-15: Award Amount & Compensation Queries
    {
        "id": "q11",
        "query": "What is the total award amount for Survey 142/3A?",
        "expected_survey": "142/3A",
        "category": "compensation",
        "requires_evidence": True,
        "expected_facts": ["142/3A"]
    },
    {
        "id": "q12",
        "query": "How much compensation was awarded for Survey 142/3A?",
        "expected_survey": "142/3A",
        "category": "compensation",
        "requires_evidence": True,
        "expected_facts": ["142/3A"]
    },
    {
        "id": "q13",
        "query": "What is the awarded amount for survey parcel 104?",
        "expected_survey": "104",
        "category": "compensation",
        "requires_evidence": True,
        "expected_facts": ["104"]
    },
    {
        "id": "q14",
        "query": "What compensation is calculated for land survey 142/3A?",
        "expected_survey": "142/3A",
        "category": "compensation",
        "requires_evidence": True,
        "expected_facts": ["142/3A"]
    },
    {
        "id": "q15",
        "query": "Show compensation awarded to owners of survey 106.",
        "expected_survey": "106",
        "category": "compensation",
        "requires_evidence": True,
        "expected_facts": ["106"]
    },

    # 16-20: Conflict & Discrepancy Queries
    {
        "id": "q16",
        "query": "Are there any area discrepancies or conflicts reported for Survey 142/3A?",
        "expected_survey": "142/3A",
        "category": "conflict_handling",
        "requires_evidence": True,
        "expected_facts": ["142/3A"]
    },
    {
        "id": "q17",
        "query": "Is there a conflict between database values and document text for survey 142/3A?",
        "expected_survey": "142/3A",
        "category": "conflict_handling",
        "requires_evidence": True,
        "expected_facts": ["142/3A"]
    },
    {
        "id": "q18",
        "query": "What conflicts exist for compensation amounts in Vadadala village?",
        "expected_survey": None,
        "category": "conflict_handling",
        "requires_evidence": True,
        "expected_facts": ["Vadadala"]
    },
    {
        "id": "q19",
        "query": "Does document text match the PostgreSQL database record for parcel 142/3A?",
        "expected_survey": "142/3A",
        "category": "conflict_handling",
        "requires_evidence": True,
        "expected_facts": ["142/3A"]
    },
    {
        "id": "q20",
        "query": "List all detected numerical conflicts for land parcels in project IND-PROJ-2024.",
        "expected_survey": None,
        "category": "conflict_handling",
        "requires_evidence": True,
        "expected_facts": []
    },

    # 21-25: Insufficient Evidence & Out-of-Scope Queries
    {
        "id": "q21",
        "query": "What is the status of non-existent Survey 9999/XYZ?",
        "expected_survey": "9999/XYZ",
        "category": "insufficient_evidence",
        "requires_evidence": False,
        "expected_coverage": "INSUFFICIENT"
    },
    {
        "id": "q22",
        "query": "What is the solar panel energy output for Survey 142/3A?",
        "expected_survey": "142/3A",
        "category": "insufficient_evidence",
        "requires_evidence": False,
        "expected_coverage": "INSUFFICIENT"
    },
    {
        "id": "q23",
        "query": "Who is the personal phone number of the land officer?",
        "expected_survey": None,
        "category": "insufficient_evidence",
        "requires_evidence": False,
        "expected_coverage": "INSUFFICIENT"
    },
    {
        "id": "q24",
        "query": "What will be the market price of land in Vadadala in the year 2030?",
        "expected_survey": None,
        "category": "insufficient_evidence",
        "requires_evidence": False,
        "expected_coverage": "INSUFFICIENT"
    },
    {
        "id": "q25",
        "query": "What is the weather forecast for Survey 142/3A today?",
        "expected_survey": None,
        "category": "insufficient_evidence",
        "requires_evidence": False,
        "expected_coverage": "INSUFFICIENT"
    },

    # 26-30: Village / General Land Acquisition Context
    {
        "id": "q26",
        "query": "What document categories exist for project IND-PROJ-2024?",
        "expected_survey": None,
        "category": "general_context",
        "requires_evidence": True,
        "expected_facts": []
    },
    {
        "id": "q27",
        "query": "Which village is Survey 142/3A located in?",
        "expected_survey": "142/3A",
        "category": "general_context",
        "requires_evidence": True,
        "expected_facts": ["142/3A"]
    },
    {
        "id": "q28",
        "query": "What is the district and tehsil for survey 142/3A?",
        "expected_survey": "142/3A",
        "category": "general_context",
        "requires_evidence": True,
        "expected_facts": ["142/3A"]
    },
    {
        "id": "q29",
        "query": "Summarize all legal document evidence available for Survey 142/3A.",
        "expected_survey": "142/3A",
        "category": "general_context",
        "requires_evidence": True,
        "expected_facts": ["142/3A"]
    },
    {
        "id": "q30",
        "query": "What notifications have been issued for land acquisition in Vadadala?",
        "expected_survey": None,
        "category": "general_context",
        "requires_evidence": True,
        "expected_facts": ["Vadadala"]
    }
]
