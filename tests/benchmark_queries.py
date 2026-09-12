"""
Gold-Standard Benchmark Dataset for Land Acquisition Retrieval Evaluation.
Contains 30 diverse test queries with ground-truth target documents and survey numbers.
"""

BENCHMARK_QUERIES = [
    {
        "id": 1,
        "query": "What is the status of Survey 142/3A?",
        "expected_survey": "142/3A",
        "expected_doc_ids": ["doc_001_notification", "doc_002_award", "doc_003_possession"],
        "category": "survey_lookup"
    },
    {
        "id": 2,
        "query": "What is the area of Survey 142/3A?",
        "expected_survey": "142/3A",
        "expected_doc_ids": ["doc_001_notification", "doc_002_award"],
        "category": "structured_fact"
    },
    {
        "id": 3,
        "query": "What compensation was awarded for Survey 142/3A?",
        "expected_survey": "142/3A",
        "expected_doc_ids": ["doc_002_award"],
        "category": "compensation"
    },
    {
        "id": 4,
        "query": "What documents are available for Survey 142/3A?",
        "expected_survey": "142/3A",
        "expected_doc_ids": ["doc_001_notification", "doc_002_award", "doc_003_possession"],
        "category": "document_list"
    },
    {
        "id": 5,
        "query": "Show acquisition documents for Hinjewadi village.",
        "expected_village": "Hinjewadi",
        "expected_doc_ids": ["doc_001_notification", "doc_002_award", "doc_003_possession", "doc_004_khasra", "doc_005_nh44_summary"],
        "category": "village_filter"
    },
    {
        "id": 6,
        "query": "Find documents for Project PRJ-NH44-EXP.",
        "expected_project": "PRJ-NH44-EXP",
        "expected_doc_ids": ["doc_001_notification", "doc_002_award", "doc_003_possession", "doc_005_nh44_summary"],
        "category": "project_filter"
    },
    {
        "id": 7,
        "query": "What notification was issued for PRJ-NH44-EXP project?",
        "expected_project": "PRJ-NH44-EXP",
        "expected_doc_ids": ["doc_001_notification"],
        "category": "category_project_combo"
    },
    {
        "id": 8,
        "query": "What does the award say about possession for Survey 142/3A?",
        "expected_survey": "142/3A",
        "expected_doc_ids": ["doc_002_award", "doc_003_possession"],
        "category": "possession"
    },
    {
        "id": 9,
        "query": "List all parcels under Project PRJ-NH44-EXP",
        "expected_project": "PRJ-NH44-EXP",
        "expected_doc_ids": ["doc_001_notification", "doc_005_nh44_summary"],
        "category": "project_multi_parcel"
    },
    {
        "id": 10,
        "query": "What is the status of Survey 999/999 in Nonexistent Village?",
        "expected_survey": "999/999",
        "expected_doc_ids": [],
        "category": "no_match"
    },
    {
        "id": 11,
        "query": "Show Section 11 Notification for Hinjewadi",
        "expected_village": "Hinjewadi",
        "expected_doc_ids": ["doc_001_notification"],
        "category": "category_village_combo"
    },
    {
        "id": 12,
        "query": "What compensation was paid for Survey 145/1?",
        "expected_survey": "145/1",
        "expected_doc_ids": ["doc_001_notification", "doc_004_khasra"],
        "category": "survey_lookup"
    },
    {
        "id": 13,
        "query": "Find SLAO Award details for Hinjewadi village",
        "expected_village": "Hinjewadi",
        "expected_doc_ids": ["doc_002_award"],
        "category": "category_village_combo"
    },
    {
        "id": 14,
        "query": "Get land record for Khasra 145-1 in Hinjewadi",
        "expected_survey": "145/1",
        "expected_doc_ids": ["doc_004_khasra"],
        "category": "survey_normalization"
    },
    {
        "id": 15,
        "query": "Show possession panchnama for Survey No. 142/3A",
        "expected_survey": "142/3A",
        "expected_doc_ids": ["doc_003_possession"],
        "category": "survey_normalization"
    },
    {
        "id": 16,
        "query": "Find notifications in Wakad village",
        "expected_village": "Wakad",
        "expected_doc_ids": ["doc_006_wakad_notification"],
        "category": "village_filter"
    },
    {
        "id": 17,
        "query": "Show Section 4 notification for Project PRJ-MTHL-002",
        "expected_project": "PRJ-MTHL-002",
        "expected_doc_ids": ["doc_006_wakad_notification"],
        "category": "project_category_combo"
    },
    {
        "id": 18,
        "query": "What is the area of Survey 148/2?",
        "expected_survey": "148/2",
        "expected_doc_ids": ["doc_001_notification"],
        "category": "structured_fact"
    },
    {
        "id": 19,
        "query": "Who is the landowner for Survey 142/3A?",
        "expected_survey": "142/3A",
        "expected_doc_ids": ["doc_002_award"],
        "category": "landowner_lookup"
    },
    {
        "id": 20,
        "query": "Show all records for Mulshi tehsil",
        "expected_doc_ids": ["doc_001_notification", "doc_002_award", "doc_003_possession", "doc_004_khasra"],
        "category": "tehsil_filter"
    },
    {
        "id": 21,
        "query": "What is the status of Gat No. 88/1B in Wakad?",
        "expected_survey": "88/1B",
        "expected_doc_ids": ["doc_006_wakad_notification"],
        "category": "survey_normalization"
    },
    {
        "id": 22,
        "query": "Find documents issued in 2024",
        "expected_doc_ids": ["doc_001_notification", "doc_002_award", "doc_003_possession"],
        "category": "date_filter"
    },
    {
        "id": 23,
        "query": "What is the total compensation amount for Hinjewadi parcels?",
        "expected_village": "Hinjewadi",
        "expected_doc_ids": ["doc_002_award"],
        "category": "compensation"
    },
    {
        "id": 24,
        "query": "Show valuation and award documents for PRJ-NH44-EXP",
        "expected_project": "PRJ-NH44-EXP",
        "expected_doc_ids": ["doc_002_award"],
        "category": "category_project_combo"
    },
    {
        "id": 25,
        "query": "Is possession completed for Survey 142/3A?",
        "expected_survey": "142/3A",
        "expected_doc_ids": ["doc_003_possession"],
        "category": "possession"
    },
    {
        "id": 26,
        "query": "Find revenue 7/12 extract for Hinjewadi",
        "expected_village": "Hinjewadi",
        "expected_doc_ids": ["doc_004_khasra"],
        "category": "category_village_combo"
    },
    {
        "id": 27,
        "query": "Show preliminary Section 4 notification for Survey 88-1B",
        "expected_survey": "88/1B",
        "expected_doc_ids": ["doc_006_wakad_notification"],
        "category": "survey_normalization"
    },
    {
        "id": 28,
        "query": "List documents for nonexistent project PRJ-UNKNOWN-999",
        "expected_project": "PRJ-UNKNOWN-999",
        "expected_doc_ids": [],
        "category": "no_match"
    },
    {
        "id": 29,
        "query": "Find acquisition award for Khasra 142/3A",
        "expected_survey": "142/3A",
        "expected_doc_ids": ["doc_002_award"],
        "category": "survey_category_combo"
    },
    {
        "id": 30,
        "query": "Show all survey numbers in Hinjewadi under PRJ-NH44-EXP",
        "expected_project": "PRJ-NH44-EXP",
        "expected_village": "Hinjewadi",
        "expected_doc_ids": ["doc_001_notification", "doc_005_nh44_summary"],
        "category": "multi_filter"
    }
]
