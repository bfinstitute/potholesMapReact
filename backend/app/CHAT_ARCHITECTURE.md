# Civic chatbot architecture (Buffi)

## Current flow (Phase 1)

1. **HTTP** — `POST /chat` receives `message` (and optionally `messages` for multi-turn if enabled).
2. **Guardrail** — `formal_guardrail_reply` may block unsafe input; no LLM calls.
3. **Retrieval & handlers** — `integrated.get_groq_response` runs intent-style regex routes, `rag_pipeline.get_rag_response`, SQL/agent paths, and dataset handlers. It returns a tuple `(response_text, plot_object, highlight_data_df)` where **facts** are embedded in `response_text` or in the dataframe for the map.
4. **Synthesis** — `civic_synthesis.synthesize_civic_structured_response` sends **only** the user question plus **retrieved_context** (the handler/RAG text) and optional **metrics** to Groq with `response_format: json_object`. The model produces narrative fields (`answer`, `reasoning_summary`, `recommendations`, etc.) grounded in that evidence.
5. **Response** — The API returns `response` (primary string, equals `structured.answer` for compatibility), `structured` (full JSON schema), and `highlight_data` for the map.

## Design rules

- **Deterministic first**: counts, filters, joins, and future scores live in Python/SQL/pandas — not in free-form LLM output.
- **LLM second**: explanation, recommendations, follow-ups, and uncertainty — with explicit **limitations** when data is missing.
- **Schema**: See `civic_response_schema.py` (`CivicStructuredResponse`).

## Phase 2 (planned, not implemented here)

- Intent router module (ZIP / neighborhood / district / funding / gap themes).
- Deterministic metrics: need score, service coverage, overlap, funding distribution, under/over-served flags.
- Pass those metrics into synthesis (already accepts a `metrics` dict).
- Optional `map_action` populated from geography resolution instead of LLM guesswork.

## Environment

- `GROQ_API_KEY` — required for synthesis when `CIVIC_SYNTHESIS_ENABLED=1` (default).
- `CIVIC_SYNTHESIS_ENABLED=0` — skip second LLM; wrap handler text in the schema with minimal narrative.
- `CIVIC_SYNTHESIS_MODEL` — defaults to `llama-3.1-8b-instant`.
