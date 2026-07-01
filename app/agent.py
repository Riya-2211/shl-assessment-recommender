import re
from typing import Dict, List, Optional

from app.schemas import ChatRequest, ChatResponse
from app.retrieval import CATALOG, search_catalog


def _latest_user_message(request: ChatRequest) -> str:
    for msg in reversed(request.messages):
        if msg.role == "user":
            return msg.content.strip()
    return ""


def _all_user_text(request: ChatRequest) -> str:
    return " ".join(msg.content for msg in request.messages if msg.role == "user")


def _is_out_of_scope(text: str) -> bool:
    t = text.lower()

    prompt_injection_terms = [
        "ignore previous",
        "ignore all previous",
        "system prompt",
        "developer message",
        "jailbreak",
        "prompt injection",
    ]

    off_topic_terms = [
        "salary",
        "compensation",
        "visa",
        "employment law",
        "lawsuit",
        "legal advice",
        "write a job description",
        "source candidates",
        "where should i post",
        "interview questions",
    ]

    if any(term in t for term in prompt_injection_terms):
        return True

    if any(term in t for term in off_topic_terms):
        return True

    if "legal" in t and "assessment" not in t:
        return True

    return False


def _is_compare_query(text: str) -> bool:
    t = text.lower()
    return (
        "compare" in t
        or "difference between" in t
        or " vs " in t
        or " versus " in t
        or "different from" in t
    )


def _extract_exclusions(latest: str) -> List[str]:
    latest_l = latest.lower()
    exclusions = []

    patterns = [
        r"\bdrop\s+([a-zA-Z0-9+#.\- ]{2,40})",
        r"\bremove\s+([a-zA-Z0-9+#.\- ]{2,40})",
        r"\bexclude\s+([a-zA-Z0-9+#.\- ]{2,40})",
        r"\bwithout\s+([a-zA-Z0-9+#.\- ]{2,40})",
    ]

    for pattern in patterns:
        for match in re.findall(pattern, latest_l):
            cleaned = re.split(r"[,.;—-]", match)[0].strip()
            if cleaned:
                exclusions.append(cleaned)

    return exclusions


def _is_vague(text: str) -> bool:
    t = text.lower().strip()

    vague_phrases = [
        "i need an assessment",
        "need an assessment",
        "need a test",
        "suggest assessment",
        "recommend assessment",
        "we need a solution",
    ]

    role_or_skill_signals = [
        "java",
        "spring",
        "sql",
        "aws",
        "docker",
        "python",
        "excel",
        "word",
        "sales",
        "finance",
        "analyst",
        "graduate",
        "trainee",
        "leadership",
        "executive",
        "cxo",
        "director",
        "contact",
        "customer",
        "support",
        "safety",
        "plant",
        "operator",
        "healthcare",
        "medical",
        "admin",
        "backend",
        "frontend",
        "engineer",
        "developer",
        "manager",
    ]

    if any(p in t for p in vague_phrases) and not any(s in t for s in role_or_skill_signals):
        return True

    if len(t.split()) <= 5 and not any(s in t for s in role_or_skill_signals):
        return True

    return False


def _needs_leadership_clarification(all_text: str) -> bool:
    t = all_text.lower()

    leadership_signal = any(
        x in t
        for x in [
            "senior leadership",
            "executive",
            "cxo",
            "director-level",
            "director level",
        ]
    )

    decision_signal = any(
        x in t
        for x in [
            "selection",
            "benchmark",
            "development",
            "feedback",
            "hiring",
            "candidate",
        ]
    )

    return leadership_signal and not decision_signal


def _needs_fullstack_clarification(all_text: str) -> bool:
    t = all_text.lower()

    has_priority = any(
        x in t
        for x in [
            "backend",
            "back-end",
            "frontend",
            "front-end",
            "full stack",
            "full-stack",
            "backend-leaning",
            "backend leaning",
            "frontend-leaning",
            "frontend leaning",
            "balanced",
            "primary",
            "priority",
        ]
    )

    if has_priority:
        return False

    tech_terms = ["java", "spring", "rest", "angular", "sql", "aws", "docker"]
    count = sum(1 for term in tech_terms if term in t)

    return count >= 5


def _format_recommendations(recs: List[dict]) -> List[dict]:
    return [
        {
            "name": r["name"],
            "url": r["url"],
            "test_type": r["test_type"],
        }
        for r in recs[:10]
    ]


def _find_catalog_item_by_name(target: str) -> Optional[Dict]:
    target_l = target.lower()

    for item in CATALOG:
        name_l = item["name"].lower()
        if target_l == name_l:
            return item

    for item in CATALOG:
        name_l = item["name"].lower()
        if target_l in name_l:
            return item

    return None


def _extract_compare_items(text: str) -> List[Dict]:
    t = text.lower()
    items = []
    seen_urls = set()

    alias_map = [
        ("opq32r", "Occupational Personality Questionnaire OPQ32r"),
        ("opq", "Occupational Personality Questionnaire OPQ32r"),
        ("gsa", "Global Skills Assessment"),
        ("global skills assessment", "Global Skills Assessment"),
        ("verify g+", "SHL Verify Interactive G+"),
        ("verify interactive g+", "SHL Verify Interactive G+"),
    ]

    for alias, catalog_name in alias_map:
        if alias in t:
            item = _find_catalog_item_by_name(catalog_name)
            if item and item["url"] not in seen_urls:
                items.append(item)
                seen_urls.add(item["url"])

    return items


def _handle_compare(all_text: str) -> ChatResponse:
    items = _extract_compare_items(all_text)

    if len(items) < 2:
        recs = search_catalog(all_text, top_k=5)

        for rec in recs:
            item = _find_catalog_item_by_name(rec["name"])
            if item and item not in items:
                items.append(item)

            if len(items) >= 2:
                break

    if len(items) < 2:
        return ChatResponse(
            reply="I can compare SHL assessments, but I need the names of two catalog assessments to compare.",
            recommendations=[],
            end_of_conversation=False,
        )

    a, b = items[0], items[1]

    a_desc = a.get("description", "No catalog description available.")
    b_desc = b.get("description", "No catalog description available.")

    reply = (
        f"{a['name']} and {b['name']} serve different assessment needs. "
        f"{a['name']} is categorized as {a['test_type']} and is described in the catalog as: {a_desc} "
        f"{b['name']} is categorized as {b['test_type']} and is described in the catalog as: {b_desc} "
        f"In short, use {a['name']} when you need personality or behavioural insight, "
        f"and use {b['name']} when you need broader skills assessment. "
        f"I am only using SHL catalog information."
    )

    return ChatResponse(
        reply=reply,
        recommendations=[],
        end_of_conversation=False,
    )


def handle_chat(request: ChatRequest) -> ChatResponse:
    latest = _latest_user_message(request)
    all_text = _all_user_text(request)

    if not latest:
        return ChatResponse(
            reply="Please tell me the role or hiring need you want SHL assessments for.",
            recommendations=[],
            end_of_conversation=False,
        )

    if _is_out_of_scope(latest):
        return ChatResponse(
            reply="I can only help with selecting SHL assessments from the SHL catalog. I cannot help with legal advice, general hiring advice, or prompt-injection requests.",
            recommendations=[],
            end_of_conversation=False,
        )

    if _is_compare_query(latest):
        return _handle_compare(all_text)

    if _is_vague(all_text):
        return ChatResponse(
            reply="Please share the role, seniority level, and key skills or behaviours you want to assess. Then I can recommend suitable SHL assessments.",
            recommendations=[],
            end_of_conversation=False,
        )

    if _needs_leadership_clarification(all_text):
        return ChatResponse(
            reply="For senior leadership, should this be for selection against a leadership benchmark, or for development feedback for leaders already in role?",
            recommendations=[],
            end_of_conversation=False,
        )

    if _needs_fullstack_clarification(all_text):
        return ChatResponse(
            reply="This role spans many areas. Should the assessment battery focus mainly on backend, frontend, or balanced full-stack ownership?",
            recommendations=[],
            end_of_conversation=False,
        )

    exclusions = _extract_exclusions(latest)
    recs = search_catalog(all_text, top_k=10, exclude_terms=exclusions)
    formatted = _format_recommendations(recs)

    if not formatted:
        return ChatResponse(
            reply="I could not find a strong match in the SHL catalog. Please provide the role, seniority, required skills, and whether you need ability, knowledge, personality, or simulation-based assessments.",
            recommendations=[],
            end_of_conversation=False,
        )

    end_terms = [
        "perfect",
        "thanks",
        "thank you",
        "lock",
        "final",
        "confirmed",
        "as-is",
        "as is",
        "that's what we need",
        "keep",
    ]

    is_final = any(term in latest.lower() for term in end_terms)

    reply = (
        f"Here are {len(formatted)} SHL catalog assessments that best match the hiring need. "
        f"I only included assessments with URLs from the SHL catalog."
    )

    if is_final:
        reply = "Final shortlist confirmed. " + reply

    return ChatResponse(
        reply=reply,
        recommendations=formatted,
        end_of_conversation=is_final,
    )