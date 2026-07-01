import re
from typing import Dict, List, Optional, Set

from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.catalog import load_catalog


CATALOG = load_catalog()
DOCUMENTS = [item["text"] for item in CATALOG]

VECTORIZER = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    lowercase=True,
)

MATRIX = VECTORIZER.fit_transform(DOCUMENTS)


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9+#.]+", " ", str(text).lower()).strip()


def _query_has_any(query: str, terms: List[str]) -> bool:
    q = query.lower()
    return any(term in q for term in terms)


def _is_excluded(item: Dict, exclude_terms: Optional[List[str]]) -> bool:
    if not exclude_terms:
        return False

    name_n = _normalize(item["name"])
    url_n = _normalize(item["url"])

    for term in exclude_terms:
        term_n = _normalize(term)
        if term_n and (term_n in name_n or term_n in url_n):
            return True

    return False


def _family(name: str) -> str:
    n = name.lower()

    if "opq" in n or "occupational personality questionnaire" in n:
        return "opq"

    if "verify" in n or "g+" in n:
        return "verify"

    if "sql" in n:
        return "sql"

    if "java" in n:
        return "java"

    if "spring" in n:
        return "spring"

    if "docker" in n:
        return "docker"

    if "amazon web services" in n or "aws" in n:
        return "aws"

    if "excel" in n:
        return "excel"

    if "word" in n:
        return "word"

    if "svar" in n:
        return "svar"

    return "other"


def _candidate_score(name: str, target: str) -> float:
    name_n = _normalize(name)
    target_n = _normalize(target)

    if not target_n:
        return 0.0

    if name_n == target_n:
        return 100.0

    if target_n in name_n:
        return 95.0

    target_tokens = target_n.split()
    if target_tokens and all(tok in name_n for tok in target_tokens):
        return 90.0

    return float(fuzz.partial_ratio(target_n, name_n))


def _find_best_item(targets: List[str], exclude_terms: Optional[List[str]], used_urls: Set[str]) -> Optional[Dict]:
    best_item = None
    best_score = 0.0

    for item in CATALOG:
        if item["url"] in used_urls:
            continue

        if _is_excluded(item, exclude_terms):
            continue

        for target in targets:
            score = _candidate_score(item["name"], target)
            if score > best_score:
                best_score = score
                best_item = item

    if best_item and best_score >= 82:
        return best_item

    return None


def _add_priority_items(
    result_items: List[Dict],
    used_urls: Set[str],
    priority_groups: List[List[str]],
    exclude_terms: Optional[List[str]],
) -> None:
    for group in priority_groups:
        item = _find_best_item(group, exclude_terms, used_urls)
        if item:
            result_items.append(item)
            used_urls.add(item["url"])


def _get_priority_groups(query: str) -> List[List[str]]:
    q = query.lower()
    groups: List[List[str]] = []

    leadership_query = _query_has_any(
        q,
        ["senior leadership", "executive", "cxo", "director", "leadership benchmark", "leadership"],
    )

    java_backend_query = _query_has_any(
        q,
        ["java", "spring", "backend", "back-end", "full-stack", "full stack", "microservice", "microservices"],
    )

    rust_networking_query = _query_has_any(
        q,
        ["rust", "networking", "linux", "systems engineer", "infrastructure"],
    )

    contact_center_query = _query_has_any(
        q,
        ["contact center", "contact centre", "call center", "call centre", "customer support", "spoken english", "accent"],
    )

    finance_query = _query_has_any(
        q,
        ["financial analyst", "finance", "accounting", "statistics", "numerical reasoning"],
    )

    sales_query = _query_has_any(
        q,
        ["sales", "reskill", "re-skill", "talent audit", "restructuring"],
    )

    safety_query = _query_has_any(
        q,
        ["plant", "operator", "chemical", "safety", "dependability", "procedure compliance", "reliability"],
    )

    healthcare_query = _query_has_any(
        q,
        ["healthcare", "medical", "hipaa", "patient", "spanish"],
    )

    admin_query = _query_has_any(
        q,
        ["admin", "administrative", "assistant", "excel", "word", "spreadsheet"],
    )

    graduate_query = _query_has_any(
        q,
        ["graduate", "trainee", "campus", "management trainee", "final-year", "final year"],
    )

    personality_requested = _query_has_any(
        q,
        ["personality", "behaviour", "behavior", "traits", "culture fit", "fit"],
    )

    cognitive_requested = _query_has_any(
        q,
        ["cognitive", "ability", "aptitude", "reasoning", "g+"],
    )

    if leadership_query:
        groups.extend([
            ["Occupational Personality Questionnaire OPQ32r"],
            ["OPQ Universal Competency Report 2.0", "OPQ Universal Competency Report 1.0", "OPQ Universal Competency Report"],
            ["OPQ Leadership Report"],
            ["Enterprise Leadership Report 2.0", "Enterprise Leadership Report 1.0", "Enterprise Leadership Report"],
        ])

    if java_backend_query:
        groups.extend([
            ["Core Java (Advanced Level) (New)", "Core Java (Advanced Level)", "Core Java Advanced"],
            ["Spring (New)", "Spring"],
            ["SQL (New)", "SQL"],
            ["Amazon Web Services (AWS) Development (New)", "Amazon Web Services", "AWS Development"],
            ["Docker (New)", "Docker"],
            ["SHL Verify Interactive G+", "Verify Interactive G+"],
            ["Occupational Personality Questionnaire OPQ32r"],
        ])

        if "rest" in q and "drop rest" not in q and "without rest" not in q:
            groups.append(["RESTful Web Services (New)", "RESTful Web Services", "Java Web Services"])

        if "java web services" in q or "web services" in q:
            groups.append(["Java Web Services (New)", "Java Web Services"])

    if rust_networking_query:
        groups.extend([
            ["Smart Interview Live Coding"],
            ["Linux Programming"],
            ["Networking and Implementation", "Networking"],
            ["SHL Verify Interactive G+", "Verify Interactive G+"],
            ["Occupational Personality Questionnaire OPQ32r"],
        ])

    if contact_center_query:
        groups.extend([
            ["SVAR Spoken English (US)", "SVAR Spoken English", "SVAR"],
            ["Contact Center Call Simulation", "Contact Center Simulation"],
            ["Entry Level Customer Service", "Entry Level Customer Serv"],
            ["Customer Service Phone Simulation", "Customer Service"],
        ])

    if finance_query:
        groups.extend([
            ["SHL Verify Interactive - Numerical Reasoning", "Numerical Reasoning"],
            ["Financial Accounting"],
            ["Basic Statistics"],
            ["Graduate Scenarios"],
            ["Occupational Personality Questionnaire OPQ32r"],
        ])

    if sales_query:
        groups.extend([
            ["Global Skills Assessment"],
            ["Global Skills Development Report", "GSA Development Report"],
            ["Occupational Personality Questionnaire OPQ32r"],
            ["OPQ MQ Sales Report", "OPQ Sales Report"],
            ["Sales Transformation"],
        ])

    if safety_query:
        groups.extend([
            ["Dependability and Safety Instrument", "DSI"],
            ["Safety & Dependability", "Safety and Dependability"],
            ["Workplace Health and Safety"],
        ])

    if healthcare_query:
        groups.extend([
            ["HIPAA"],
            ["Medical Terminology"],
            ["Microsoft Word 365 Essentials", "Microsoft Word"],
            ["Data Entry"],
            ["Occupational Personality Questionnaire OPQ32r"],
        ])

    if admin_query:
        groups.extend([
            ["Microsoft Excel 365", "MS Excel", "Excel"],
            ["Microsoft Word 365", "MS Word", "Word"],
            ["Excel Simulation", "Microsoft Excel Simulation"],
            ["Word Simulation", "Microsoft Word Simulation"],
            ["Occupational Personality Questionnaire OPQ32r"],
        ])

    if graduate_query:
        groups.extend([
            ["SHL Verify Interactive G+", "Verify Interactive G+"],
            ["Occupational Personality Questionnaire OPQ32r"],
            ["Graduate Scenarios"],
        ])

    if personality_requested:
        groups.append(["Occupational Personality Questionnaire OPQ32r"])

    if cognitive_requested:
        groups.append(["SHL Verify Interactive G+", "Verify Interactive G+"])

    return groups


def _expand_query(query: str) -> str:
    q = query.lower()
    expansions = []

    if "gsa" in q:
        expansions.append("Global Skills Assessment Global Skills Development Report")

    if "opq" in q:
        expansions.append(
            "Occupational Personality Questionnaire OPQ32r "
            "OPQ Leadership Report OPQ Universal Competency Report OPQ Sales Report"
        )

    if "java" in q or "backend" in q:
        expansions.append(
            "Core Java Advanced Spring SQL Amazon Web Services Docker "
            "SHL Verify Interactive G+ Occupational Personality Questionnaire OPQ32r"
        )

    if "leadership" in q or "executive" in q or "cxo" in q or "director" in q:
        expansions.append(
            "Occupational Personality Questionnaire OPQ32r "
            "OPQ Universal Competency Report OPQ Leadership Report Enterprise Leadership Report"
        )

    if "sales" in q:
        expansions.append(
            "Global Skills Assessment Global Skills Development Report OPQ MQ Sales Report Sales Transformation"
        )

    if "graduate" in q or "trainee" in q:
        expansions.append(
            "SHL Verify Interactive G+ Occupational Personality Questionnaire OPQ32r Graduate Scenarios"
        )

    return query + " " + " ".join(expansions)


def _rule_boost(query: str, item: Dict) -> float:
    query_l = query.lower()
    name_l = item["name"].lower()
    text_l = item["text"].lower()

    boost = 0.0

    direct_terms = [
        "java",
        "spring",
        "sql",
        "aws",
        "docker",
        "python",
        "javascript",
        "angular",
        "excel",
        "word",
        "hipaa",
        "medical",
        "networking",
        "linux",
        "customer",
        "sales",
        "safety",
        "graduate",
        "leadership",
        "backend",
        "frontend",
        "microservices",
        "rest",
        "finance",
        "accounting",
        "statistics",
    ]

    for term in direct_terms:
        if term in query_l:
            if term in name_l:
                boost += 5.0
            elif term in text_l:
                boost += 1.0

    if _query_has_any(query_l, ["senior", "lead", "manager", "4 years", "5 years", "experienced"]):
        if "advanced" in name_l:
            boost += 4.0
        if "entry level" in name_l:
            boost -= 5.0

    if _query_has_any(query_l, ["senior", "lead", "manager", "experienced"]):
        if "verify interactive g+" in name_l or name_l == "shl verify interactive g+":
            boost += 7.0
        if "occupational personality questionnaire opq32r" in name_l:
            boost += 7.0

    if _query_has_any(query_l, ["leadership", "executive", "cxo", "director", "benchmark"]):
        if "occupational personality questionnaire opq32r" == name_l:
            boost += 50.0
        if "opq universal competency report" in name_l:
            boost += 45.0
        if "opq leadership report" in name_l:
            boost += 45.0
        if "leadership" in name_l:
            boost += 15.0
        if item.get("test_type") == "K":
            boost -= 30.0

    if _query_has_any(query_l, ["backend", "back-end"]):
        if any(x in name_l for x in ["angular", "react", "html", "css", "javascript"]):
            boost -= 8.0

    unrelated_tech = [
        "sap",
        "abap",
        "oracle",
        "dba",
        "pl/sql",
        ".net",
        "c#",
        "php",
        "teradata",
        "cobol",
        "mainframe",
        "perl",
        "visual basic",
        "fortran",
    ]

    for bad in unrelated_tech:
        if bad in name_l and bad not in query_l:
            boost -= 25.0

    if "report" in name_l and "report" not in query_l:
        if not _query_has_any(query_l, ["leadership", "executive", "cxo", "director", "sales"]):
            boost -= 15.0

    if "hipo" in name_l and "hipo" not in query_l:
        boost -= 30.0

    return boost


def _to_response_item(item: Dict) -> Dict:
    return {
        "name": item["name"],
        "url": item["url"],
        "test_type": item["test_type"],
        "description": item.get("description", ""),
        "keys": item.get("keys", []),
    }


def search_catalog(
    query: str,
    top_k: int = 10,
    exclude_terms: Optional[List[str]] = None,
) -> List[Dict]:
    exclude_terms = exclude_terms or []
    expanded_query = _expand_query(query)

    result_items: List[Dict] = []
    used_urls: Set[str] = set()

    priority_groups = _get_priority_groups(expanded_query)
    _add_priority_items(result_items, used_urls, priority_groups, exclude_terms)

    query_vec = VECTORIZER.transform([expanded_query])
    similarities = cosine_similarity(query_vec, MATRIX).flatten()

    scored = []

    for idx, item in enumerate(CATALOG):
        if item["url"] in used_urls:
            continue

        if _is_excluded(item, exclude_terms):
            continue

        score = float(similarities[idx]) + _rule_boost(expanded_query, item)

        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)

    family_counts = {}
    for item in result_items:
        fam = _family(item["name"])
        family_counts[fam] = family_counts.get(fam, 0) + 1

    is_leadership_query = _query_has_any(
        expanded_query,
        ["leadership", "executive", "cxo", "director", "benchmark"],
    )

    for _, item in scored:
        if len(result_items) >= top_k:
            break

        if item["url"] in used_urls:
            continue

        name_l = item["name"].lower()
        fam = _family(item["name"])

        if "report" in name_l and "report" not in expanded_query.lower():
            if not is_leadership_query and fam in ["opq", "verify"]:
                continue

        max_allowed = {
            "opq": 4 if is_leadership_query else 1,
            "verify": 1,
            "sql": 2,
            "java": 2,
            "spring": 1,
            "docker": 1,
            "aws": 1,
            "excel": 2,
            "word": 2,
            "svar": 1,
            "other": 10,
        }

        if family_counts.get(fam, 0) >= max_allowed.get(fam, 10):
            continue

        result_items.append(item)
        used_urls.add(item["url"])
        family_counts[fam] = family_counts.get(fam, 0) + 1

    return [_to_response_item(item) for item in result_items[:top_k]]