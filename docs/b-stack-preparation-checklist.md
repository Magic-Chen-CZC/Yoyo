# B Stack Preparation Checklist

This document lists what should be prepared later when the current SQL-first B implementation is replaced with real production data and configuration.

## Current phase summary
- Database choice: PostgreSQL
- Current knowledge strategy: SQL-first
- Attraction basics and attraction introduction content should live in PostgreSQL fields first
- Live search is reserved for real-time travel changes only
- RAG is deferred for now and can be introduced later if SQL-backed knowledge becomes insufficient

## 1. Real PostgreSQL tables to prepare later

### Attraction basics table
Suggested fields:
- `id`
- `name`
- `aliases`
- `category`
- `latitude`
- `longitude`
- `recommended_duration_minutes`
- `tags`
- `city_code`

### Attraction introduction / guide content fields
Suggested fields:
- `short_intro`
- `history`
- `highlights`
- `visitor_tips`
- `practical_notes`
- `family_friendly_notes`
- `photo_spot_notes`
- `language_variants` (optional)

### User profile table
Suggested fields:
- `user_id`
- `preferred_language`
- `interests`
- `travel_style`
- `walking_preference`
- `pace_preference`
- `audience_type`
- `answer_length_preference`

### Optional supporting tables
If available later, these are useful:
- attraction FAQ table
- attraction policy / operational notes table
- guide style configuration table
- user preference override table

## 2. Data exposure rules to define later
Please define later:
- which tables QA and Guide generation are allowed to query
- which fields are safe to pass into the model prompt
- which fields must remain internal-only
- whether user profile fields can be used for personalization by default

### Prompt-safe SQL field guidance
The main rule is:
- **not every SQL field should be sent to the model**
- queryable fields and prompt-safe fields are not always the same thing

#### Safe attraction fields for prompt use
These are generally safe and useful for model prompting:
- `name`
- `aliases`
- `category`
- `recommended_duration_minutes`
- `short_intro`
- `history`
- `highlights`
- `visitor_tips`
- `practical_notes`
- `photo_spot_notes`
- `tags` (if curated and user-facing)

Note:
- `family_friendly_notes` is currently kept in SQL but **excluded from prompt-safe projection** for this phase.

#### Safe profile fields for prompt use
These are generally safe and useful for personalization:
- `preferred_language`
- `interests`
- `travel_style`
- `walking_preference`
- `pace_preference`
- `audience_type`
- `answer_length_preference`
- `guide_style_preference`

`guide_style_preference` currently uses four style buckets:
- `NF` — idealist / meaning- and resonance-oriented
- `NT` — rational / logic- and system-oriented
- `SJ` — guardian / practical and orderly
- `SP` — artisan / vivid and experience-oriented

#### Usually keep internal-only
These should normally not be passed directly into the model prompt unless there is a clear product reason:
- phone / email / account identifiers beyond the minimum needed key
- internal moderation flags
- internal operations notes
- internal ranking / business priority fields
- unpublished review status fields
- raw sync / ETL / ingestion fields
- internal debugging metadata
- admin-only annotations

#### Recommended implementation rule
When real PostgreSQL data is connected later:
- first query the database record
- then project only the prompt-safe subset into model context
- do not pass the raw row or ORM object directly into prompt construction

## 3. Live search / external provider setup
Useful future inputs:
- Tavily API key or final live-search provider key
- official source preference rules
- list of trusted domains if domain filtering is needed

## 4. RAG productionization configuration checklist
The current codebase already has the RAG scaffold and productionized state semantics/tests. To finish the remaining real-environment validation work later, prepare the following.

### Required env/config values
Add these to `.env` before real backend validation:
- `rag_enabled=true`
- `rag_pgvector_dsn=<real PostgreSQL DSN with pgvector enabled>`
- `rag_embedding_provider=openrouter`
- `rag_embedding_base_url=https://openrouter.ai/api/v1`
- `rag_embedding_api_key=<OpenRouter-compatible embedding key>`
- `rag_embedding_dimension=<must match the selected embedding model>`
- optional if you want to override defaults:
  - `rag_embedding_model`
  - `rag_collection_name`

Recommended local starting value:
- `rag_pgvector_dsn=postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/yoyo`

### Infra / dependency prerequisites
Make sure the target environment has:
- PostgreSQL reachable from the app
- pgvector extension enabled
- LlamaIndex + pgvector runtime dependencies installed successfully
- network access from the app to the embedding provider

### Minimal real-environment validation steps
Once the env values above are configured:
1. Start app with the real `.env`
2. Call `POST /api/v1/rag/index-runs/rebuild`
3. Confirm `GET /api/v1/rag/index-runs/latest` returns:
   - `status = succeeded`
   - `availability = ready`
   - `reason = ok`
4. Run an attraction-explain QA query deep enough to trigger RAG fallback
5. Confirm QA metadata shows:
   - `retrieval_strategy = sql_then_rag`
   - `rag_backend_ready = true`
   - `rag_query_status = ok`
   - non-empty `rag.chunks`

### What is already code-complete vs still pending
Already code/test-complete:
- backend readiness/config semantics
- rebuild/index-run admin semantics
- QA top-level RAG metadata projection
- degraded/fallback behavior when backend is disabled or misconfigured

Still pending real-environment validation:
- backend-enabled pgvector retrieval in a real configured environment
- embedding -> indexing -> query end-to-end with real credentials and real backend connectivity

## 5. TTS productionization configuration checklist
Guide audio now uses a real TTS-oriented contract and batch-level on-demand generation. To finish real TTS validation later, prepare the following.

### Required env/config values
Add these to `.env` before real TTS validation:
- `tts_provider=dashscope`
- `tts_base_url=https://dashscope.aliyuncs.com/api/v1`
- `tts_api_key=<DashScope API key>`
- `tts_voice=<Qwen TTS voice name, for example Cherry>`
- optional overrides:
  - `tts_model` (default `qwen3-tts-flash`)
  - `tts_audio_format`
  - `tts_storage_dir`

### Runtime assumptions for the current implementation
- audio is generated for the currently returned `cycle_content` batch, not synchronously for all segments of the stop
- if `tts_api_key` is missing, audio is marked `unavailable`
- if `tts_api_key` is present, guide audio is generated on demand and cached to local storage
- Qwen TTS synthesis currently uses DashScope's `MultiModalConversation.call(...)`; if the upstream request is rejected or response does not contain audio bytes, the current batch should still return text successfully while audio degrades safely to `unavailable`

### Minimal real-environment validation steps
Once the env values above are configured:
1. Start app with the real `.env`
2. Create itinerary + guide session
3. Run guide generation job and call `POST /api/v1/guide/content/{guide_session_id}`
4. Confirm response includes `audio_segments`
5. Confirm the current batch returns `status = ready` with file paths/URLs populated after synthesis
6. Verify latency is acceptable for a single returned batch and that full-stop eager generation is not happening

## 6. Future RAG evolution path
RAG is no longer just a deferred idea: the scaffold and semantics are in place, but real backend validation is still pending. If deeper evolution is needed later, prepare:
- attraction guide documents
- FAQ documents
- historical/cultural reference materials
- operations notes / long-form guide scripts
- source format information (Markdown / PDF / DOCX / CSV / webpages)

Recommended vector storage direction:
- PostgreSQL + pgvector

## 7. Current implementation assumption
Until real data / credentials are ready:
- mock PostgreSQL attraction data will be used where allowed
- mock PostgreSQL profile data will be used where allowed
- attraction explanation and guide generation rely on SQL-backed content fields first
- live search remains the only dynamic external information source
- RAG and TTS productionization can degrade safely when the required backend credentials are absent
