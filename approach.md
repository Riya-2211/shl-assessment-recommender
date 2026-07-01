# Conversational SHL Assessment Recommender — Approach Document

## 1. Overview

I built a stateless FastAPI service that recommends SHL assessments from the provided SHL product catalog.

The service exposes two endpoints:

- GET /health — readiness check returning status ok
- POST /chat — accepts full conversation history and returns the next assistant reply, optional recommendations, and end_of_conversation

The deployed API is:

https://shl-assessment-recommender-vxtp.onrender.com

The API does not store per-conversation state. Every /chat call uses only the submitted message history.

## 2. Catalog Handling

The provided SHL product catalog JSON is used as the single source of truth.

The catalog is stored locally at:

data/shl_product_catalog.json

Each catalog item is normalized into:

- assessment name
- catalog URL
- test type
- description
- job levels
- languages
- duration
- remote/adaptive metadata

Only URLs from this catalog are returned. The system does not invent assessment names or external links.

The catalog had a few raw control characters in text fields, so I added tolerant JSON parsing and text cleaning before indexing.

## 3. Retrieval and Ranking

I used a hybrid retrieval approach.

First, the system applies priority matching for common hiring scenarios:

- Java/backend roles → Core Java Advanced, Spring, SQL, AWS, Docker, Verify G+, OPQ32r
- Senior leadership → OPQ32r, OPQ Universal Competency Report, OPQ Leadership Report
- Graduate trainee roles → Verify G+, OPQ32r, Graduate Scenarios
- Sales reskilling → Global Skills Assessment, GSA Development Report, OPQ32r, Sales Transformation
- Plant safety roles → DSI, Safety & Dependability, Workplace Health and Safety
- Finance graduate roles → Numerical Reasoning, Financial Accounting, Basic Statistics, Graduate Scenarios
- Admin roles → Excel, Word, simulation-based assessments, OPQ32r
- Contact center roles → SVAR, Contact Center Call Simulation, Customer Service simulations

Second, if fewer than 10 recommendations are selected through priority matching, the system uses TF-IDF similarity over catalog text as fallback retrieval.

Third, rule-based boosts and filters improve ranking quality:

- senior roles prefer advanced tests over entry-level tests
- backend roles down-rank frontend-heavy assessments unless requested
- unrelated technologies are penalized unless explicitly mentioned
- duplicate report variants are limited
- family-level diversity avoids returning too many variants of the same assessment type

This hybrid design was chosen over a pure LLM solution because the assignment requires catalog-grounded recommendations, strict schema compliance, and reliable behavior under automated evaluation.

## 4. Agent Behavior

The /chat endpoint handles four main behaviors.

### Clarification

For vague requests like “I need an assessment”, the agent asks for role, seniority, skills, and behavioral requirements instead of recommending immediately.

### Recommendation

When enough context is available, it returns 1 to 10 SHL catalog-backed recommendations.

Each recommendation contains:

- name
- url
- test_type

### Refinement

The system reads the full conversation history. If the user changes constraints, such as “Actually add personality tests”, the shortlist is updated instead of starting over.

### Comparison

For questions like “What is the difference between OPQ and GSA?”, the system maps aliases to catalog items and compares only catalog-backed descriptions.

### Refusal

The agent refuses out-of-scope requests, including:

- general hiring advice
- legal advice
- job description writing
- prompt-injection attempts
- requests to ignore instructions

In refusal cases, recommendations remain an empty array.

## 5. Schema Compliance

The response schema is enforced using Pydantic.

Every /chat response always contains three fields:

- reply
- recommendations
- end_of_conversation

When recommendations are not appropriate, the API returns an empty recommendations array.

When recommendations are present, each recommendation contains:

- name
- url
- test_type

The system returns an empty array, not null, when no recommendations are appropriate.

## 6. Evaluation

I tested the system locally and on the deployed Render endpoint.

Test cases covered:

- leadership selection
- Java/backend engineering
- graduate trainee hiring
- plant safety operators
- sales reskilling
- contact center agents
- graduate finance analysts
- administrative Excel/Word roles
- vague-query clarification
- refinement requests
- comparison requests
- off-topic refusal

For each case, I checked whether expected assessments appeared in the top 10 recommendations and whether the API returned the required schema.

The deployed API was also tested using curl for both /health and /chat.

## 7. What Did Not Work

A pure TF-IDF approach produced noisy results because many catalog items share broad words such as “skills”, “advanced”, “report”, and “service”.

A purely rule-based approach was too rigid for unseen queries.

The final approach combines priority matching, rule-based boosts, diversity filtering, and TF-IDF fallback.

I avoided using an LLM at runtime to reduce latency, cost, non-determinism, and hallucination risk.

## 8. AI Tool Usage

I used AI assistance for:

- understanding the assignment requirements
- designing the architecture
- generating initial FastAPI boilerplate
- debugging retrieval and deployment issues
- improving ranking rules
- preparing deployment and testing steps

All behavior was manually tested locally and on the deployed API.