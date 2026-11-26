# Requirements — Week 5: Semantic search form

Source: challenge curriculum, "Week 5: Semantic search form" (Alex Ramasheuski, 2025-09-02), screenshot provided by
the owner on 2026-11-25. Translated to English. This file is the input for design docs and specs; it is not edited
except to fix the export.

## Task (as given)

Create a search component in the SPA that sends a natural-language query to the Chatbot Lambda; the Lambda converts
the query (NL → SQL / vector) through a Bedrock Agent and returns the results.

## Week goals (as given)

| # | Goal |
|---|---|
| W5-G1 | The search field shows relevant rows from Postgres in < 1 s |
| W5-G2 | The test "which users are similar to …" returns the correct TOP-5 |

## Implementation steps (as given)

| # | Step |
|---|---|
| S1 | In React add a form, a debounced request and a results table |
| S2 | In the Chatbot Lambda: if the query contains the keyword "sql", apply Bedrock LLM → SQL; otherwise get a Bedrock embedding and run a similarity search with pgvector |
| S3 | Configure the timeouts of API Gateway (29 s) and Lambda (30 s) |
| S4 | Log latency and the number of tokens |

## Materials (as given)

RAG text-to-SQL with Bedrock Claude 3 Sonnet · JWT claims access inside Lambda · Similarity search examples in pgvector.

## Project requirement (as given, project page)

The administrator can open a separate page, type a request to the AI in "human" language in a text field and get
statistics and analytics about the user base — example: "how many users aged 25 to 35 live in Poland and weigh more
than 70 kg".

## Traceability

Design: [semantic-search](../design/semantic-search.md). Deviations (accepted by the owner 2026-11-25): no Bedrock Agent
(Q-21 → ADR-021), Nova Micro instead of Claude 3 Sonnet (Q-22 → ADR-022), < 1 s only for the vector path.

| Requirement | Spec | Acceptance criteria | Tasks |
|---|---|---|---|
| Task: search component → Chatbot Lambda → NL → SQL / vector | [12](../specs/12-chat-api.md), [13](../specs/13-chat-page.md) | AC-12.1, AC-12.7, AC-12.9, AC-13.3 | T05-02, T05-03, T05-04 |
| W5-G1 relevant rows in < 1 s | [12](../specs/12-chat-api.md) | AC-12.8 (vector path, warm) | T05-03 |
| W5-G2 "which users are similar to …" → correct TOP-5 | [12](../specs/12-chat-api.md) | AC-12.7 | T05-02, T05-03 |
| S1 form, debounced request, results table | [13](../specs/13-chat-page.md) | AC-13.1 … AC-13.5 | T05-04, T05-03 |
| S2 "sql" → Bedrock LLM → SQL, else embedding + pgvector similarity | [12](../specs/12-chat-api.md) | AC-12.1, AC-12.2, AC-12.7, AC-12.9, AC-12.10 | T05-01, T05-02, T05-03 |
| S3 timeouts API Gateway 29 s, Lambda 30 s | [12](../specs/12-chat-api.md) | AC-12.4, AC-12.5 | T05-01 |
| S4 log latency and token count | [12](../specs/12-chat-api.md) | AC-12.11 | T05-02, T05-03 |
| Project: admin-only page, statistics in "human" language | [12](../specs/12-chat-api.md), [13](../specs/13-chat-page.md) | AC-12.6, AC-12.9, AC-13.4 | T05-02, T05-04 |
| Materials: JWT claims inside Lambda | [12](../specs/12-chat-api.md) | AC-12.1, AC-12.6 | T05-02 |
