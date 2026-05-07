# BHS Mortgage Workflow Demo — Project Brief

## What this is

A Streamlit app that demonstrates an AI-driven mortgage broker workflow with two complementary views:
1. **Processor view** — The original workflow for loan processors reviewing and assembling files
2. **Borrower view** — A borrower-facing portal for document upload with real-time AI validation

Built as a sales demo for an upcoming call with the owner of BHS Mortgages (a small mortgage broker in Philadelphia). The goal is a free workflow audit engagement in exchange for a testimonial and referrals — first paying client conversion is the broader goal.

## Why this codebase exists

The owner has heard "AI will transform mortgage" for years and seen nothing concrete in her own workflow. This demo's job is to make her see one specific, working slice of what an AI-driven loan-file workflow looks like — built specifically for mortgage brokers, not a generic chatbot. The differentiation vs. ChatGPT is encoded mortgage-specific judgment (Fannie Mae freshness rules, year-specific doc matching, stip-list-aware classification), workflow integration (state advances visibly through stages), and consistent structured output.

## Audience for the demo

A mortgage broker owner. Not technical. Cares about: time saved by her processor, fewer kickbacks from wholesale lenders, faster clear-to-close times, fewer borrower calls asking "where are we?" Does NOT care about: model architecture, prompt engineering details, infrastructure.

## Architecture (current)

mortgage-doc-demo/
├── app.py                              # thin router
├── requirements.txt                    # streamlit, anthropic, pillow
├── prompts/
│   ├── stip_generation.txt             # generates required-doc list from borrower profile
│   ├── document_classification.txt     # identifies doc type + matches to stip list
│   ├── paystub_extraction.txt          # detailed pay stub field extraction
│   └── generic_extraction.txt          # fallback for non-pay-stub docs
├── models/
│   ├── borrower.py                     # Borrower dataclass
│   ├── stip.py                         # Stip dataclass (with accepted_years, accepted_doc_age_days)
│   └── loan_file.py                    # LoanFile dataclass + UploadedDoc
├── services/
│   ├── llm_service.py                  # Base class: client, prompt loading, JSON parsing, doc blocks
│   ├── stip_generator.py               # Generates stip list per borrower
│   ├── classifier.py                   # Classifies uploaded doc + matches to stip
│   ├── paystub_extractor.py            # Detailed pay stub extraction
│   └── generic_extractor.py            # Generic doc extraction fallback
├── utils/
│   ├── dates.py                        # parse_date_str, freshness_status (Fannie Mae 30-day rule)
│   ├── income.py                       # estimate_monthly_income from pay stub
│   ├── borrower_language.py            # Translates processor vocab to borrower-friendly language
│   └── borrower_messages.py            # Success/error message templates for borrowers
├── services/
│   └── borrower_validator.py           # Validates borrower uploads (accept vs. reject logic)
└── ui/
    ├── sidebar.py                      # View toggle + stepper + borrower summary + stip list
    ├── intake.py                       # Stage 1: processor borrower form
    ├── documents.py                    # Stage 2: processor inbox-and-review
    └── borrower/                       # Borrower-facing views
        ├── __init__.py                 # BorrowerView router
        ├── intake.py                   # Borrower intake form
        ├── welcome.py                  # Document checklist welcome
        ├── upload.py                   # Upload with real-time validation
        └── submitted.py                # Confirmation and status summary

Default model: `claude-opus-4-5` (set on `LLMService.DEFAULT_MODEL`). If this errors, check current model strings in Anthropic API docs and update.

## Workflow stages (from the LoanFile state machine)

1. `intake` — Borrower info form. On submit, calls StipListGenerator → generates required-doc list. ✅ BUILT
2. `documents` — Inbox-and-review flow. Processor reviews documents that arrived from borrower portal. AI pre-classifies and extracts data; processor verifies and accepts. ✅ BUILT
3. `review` — Show what's still missing, file completeness summary. ✅ BUILT
4. `followup` — Generate borrower follow-up message (email/SMS draft) requesting missing docs. ✅ BUILT
5. `scrub` — Pre-submission AI scrub: review the assembled file for common kickback reasons (income reconciliation, doc freshness, signature gaps, large unsourced deposits). ✅ BUILT
6. `done` — Submission-ready summary. ✅ BUILT

## Key design decisions

### Core Architecture

- **Prompts in `.txt` files**, loaded by `LLMService.load_prompt()`. Edit prompts without touching code.
- **Curly braces in prompts must be doubled `{{ }}`** for literal JSON braces — single braces are reserved for `.format()` placeholders like `{profile}`, `{today}`, etc.
- **Date awareness:** stip generator and classifier both receive `today`, `prior_year`, `two_years_back`. This was added after a bug where the model picked stale years for W-2 stips. Stips name the *role* (e.g. "Most recent W-2"), with `accepted_years` field carrying the year-specificity.
- **Confidence-based status:** classifier returns `match_confidence` of high/medium/low. High/medium → stip flips to `received` (✅), low → `needs_review` (⚠️). Progress bar only counts `received`.
- **Service objects are session-scoped** (built once in `app.py`, stored in `st.session_state.services`). Services are shared between processor and borrower views.

### Two-View Architecture

- **View toggle in sidebar:** Radio button allows switching between "Processor" and "Borrower" views
- **Shared state:** Both views share the same `LoanFile` object and AI services
- **Shared validation logic:** `BorrowerValidator` orchestrates document validation used by borrower upload flow
- **Independent navigation:** Processor view has `stage` (intake → documents → review → followup → scrub → done), borrower view has `borrower_stage` (intake → welcome → upload → submitted)
- **Two entry paths:**
  - Borrower self-identifies (starts at borrower intake form)
  - Loan officer captures info first (borrower starts at welcome screen)

### Processor View (Inbox-and-Review Flow)

- **Inbox-and-review flow (Stage 2):** Documents arrive from a simulated borrower portal into an inbox (`pending_docs`). The processor reviews each doc one by one — AI has already classified and extracted data, processor just verifies and clicks Accept. Documents that fail automatic validation at upload time (e.g., stale pay stubs) go directly to `rejected_docs` and never reach the processor's queue — borrower is auto-notified to resubmit. This flow positions the processor as supervisor of AI's work, not data entry clerk.
- **Demo controls:** A "Simulate borrower upload" button in the sidebar (labeled clearly as a demo control) pops reserved documents into the inbox mid-demo to show real-time arrival. An `InboxSeeder` service pre-populates the inbox when advancing from stage 1 to stage 2, loading sample docs from `sample_docs/pending/`, `sample_docs/reserved/`, and `sample_docs/rejected/`.
- **Rejected-at-upload section:** Stage 2 shows a separate section for rejected documents with reasons (e.g., "Pay stub is 47 days old, exceeds Fannie Mae 30-day window"). This demonstrates that bad documents never consume processor time — the system handles rejection and borrower notification automatically.

### Borrower View (Self-Service Upload Flow)

- **Plain language throughout:** No mortgage jargon. Stip names are translated (e.g., "Government-issued photo ID" → "A photo of your driver's license or passport")
- **Four screens:**
  1. **Intake:** Friendly form to capture name, loan purpose, amount, employment type. Skipped if processor already captured info.
  2. **Welcome:** Shows friendly checklist of required documents with progress bar
  3. **Upload:** Drag-drop zone for multiple files with per-document real-time processing and feedback
  4. **Submitted:** Confirmation screen with dynamic messaging based on completion status
- **Real-time validation:** Each uploaded file is immediately validated using `BorrowerValidator`:
  - Success: Friendly message (e.g., "Got it — this looks like a pay stub from Acme Corp, dated 2026-04-15. We've added it to your file.")
  - Rejection: Friendly error with actionable guidance (e.g., "This pay stub is from 2026-03-17, which is over 30 days old. Lenders need pay stubs within the last 30 days. Could you upload your most recent one?")
- **Validation rules (in order):**
  1. Name mismatch → reject
  2. Low confidence or no stip match → reject
  3. Stale pay stub (>30 days) → reject
  4. All checks pass → add to `pending_docs` for processor review, mark stip as `needs_review`
- **Friendly message templates:** `utils/borrower_messages.py` provides doc-type-specific success messages and reason-specific error messages

## What's already working

### Processor View
- Borrower intake form with sensible defaults
- Stip list generation tailored to borrower type (W-2 employee vs. self-employed vs. retired produces meaningfully different lists)
- Inbox-and-review document flow (Stage 2):
  - Documents pre-seeded from borrower portal simulation
  - Pending review queue with received timestamps
  - One-at-a-time review screen with AI classification + extraction pre-run
  - Accept & file workflow
  - Rejected-at-upload section showing auto-rejected documents
  - Manual upload affordance for exception cases (email/fax/text docs)
  - Simulate borrower upload button for mid-demo theatrics
- Per-document classification + extraction
- Pay stub extraction with Fannie Mae freshness check + auto-calculated monthly income (3 methods)
- Generic extraction for non-pay-stub docs
- Completeness review dashboard (Stage 3) with category breakdown
- AI-generated borrower follow-up messages (Stage 4)
- Pre-submission quality scrub with kickback detection (Stage 5)
- Submission-ready summary (Stage 6)
- Sidebar stepper showing workflow progress with inbox count
- Sidebar stip list with ✅/⚠️/◯ status icons + progress bar
- Borrower-name-mismatch detection
- Date-aware year matching (W-2 for current year matches "Most recent W-2" stip)
- Document versioning (replace/remove capabilities on filed documents)

### Borrower View
- View toggle in sidebar (Processor/Borrower)
- Borrower intake form with friendly language (name, loan purpose, amount, employment type)
- Welcome screen with friendly document checklist and progress bar
- Upload screen with drag-drop zone for multiple files
- Real-time per-document validation with friendly success/error messages
- Document-type-specific success messages (pay stub, W-2, bank statement, photo ID)
- Reason-specific error messages (stale pay stub, name mismatch, low confidence, no stip match)
- Submitted confirmation screen with dynamic messaging based on file completion
- Automatic translation of stip names to borrower-friendly language
- BorrowerValidator service orchestrating validation logic
- Accepted documents flow to processor's pending queue
- Rejected documents flow to rejected section with friendly error messages

## What's next (if needed)

All core workflow stages and borrower-facing flow are complete. Potential enhancements:

1. **Borrower email notifications.** Currently borrower sees errors inline during upload. Could add email notification when documents are rejected.
2. **Processor override buttons.** Currently processor can only Accept documents. Could add Reject and Override buttons for edge cases.
3. **Document preview.** Show thumbnail or PDF preview in review screens.
4. **Borrower status chat.** Allow borrower to ask "where are we?" and get AI-generated status updates.
5. **Production hardening.** Error handling, loading states, edge case validation.

## Running the app

```bash
source venv/bin/activate
streamlit run app.py

Requires `ANTHROPIC_API_KEY` env var set.

## Constraints

- **Demo is in 1 week.** Optimize for visible workflow progression and the "oh" moments, not for production correctness.
- **Single-user, in-memory state.** No database, no auth, no real persistence. State lives in `st.session_state.loan_file`.
- **No real integrations.** No LOS connection, no email sending, no portal. Everything is simulated within the Streamlit app.
- **Test data:** real sample pay stubs, W-2s, bank statements found via Google for "sample [doc] PDF".

## Coding style

- Object-oriented services and views (each stage = one view class).
- Dataclasses for models; no Pydantic.
- Prompts external in `.txt` files.
- Type hints on service-layer interfaces; lighter on internal UI helpers.
- No tests yet (one-week demo timeline). Defer test infrastructure unless something becomes brittle.

## Where to start in this Claude Code session

Before touching anything, please:
1. Run `streamlit run app.py` and verify intake + documents stages work end-to-end with a sample pay stub and a sample W-2.
2. Read `models/loan_file.py`, `services/llm_service.py`, `services/classifier.py`, and `ui/documents.py` to get the shape.
3. Then propose a plan for Stage 3 (Completeness Review) before writing code.