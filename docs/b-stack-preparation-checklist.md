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

## 4. Future RAG evolution path
RAG is not part of the current implementation, but if needed later, prepare:
- attraction guide documents
- FAQ documents
- historical/cultural reference materials
- operations notes / long-form guide scripts
- source format information (Markdown / PDF / DOCX / CSV / webpages)

Recommended future vector storage direction:
- PostgreSQL + pgvector

## 5. Current implementation assumption
Until real data is ready:
- mock PostgreSQL attraction data will be used
- mock PostgreSQL profile data will be used
- attraction explanation and guide generation will rely on SQL-backed content fields
- live search remains the only dynamic external information source
