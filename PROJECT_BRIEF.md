# BHS Mortgage Workflow Demo — Project Brief

## What this is

A Streamlit app that demonstrates an AI-driven mortgage broker workflow, built as a sales demo for an upcoming call with the owner of BHS Mortgages (a small mortgage broker in Philadelphia). The goal is a free workflow audit engagement in exchange for a testimonial and referrals — first paying client conversion is the broader goal.

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
│   └── income.py                       # estimate_monthly_income from pay stub
└── ui/
├── sidebar.py                      # Stepper + borrower summary + stip list with progress bar
├── intake.py                       # Stage 1: borrower form
└── documents.py                    # Stage 2: drag-drop upload, batch processing, doc cards

Default model: `claude-opus-4-5` (set on `LLMService.DEFAULT_MODEL`). If this errors, check current model strings in Anthropic API docs and update.

## Workflow stages (from the LoanFile state machine)

1. `intake` — Borrower info form. On submit, calls StipListGenerator → generates required-doc list. ✅ BUILT
2. `documents` — Drag-drop multi-file upload. Each doc: classify → extract → mark stip received. Batch summary shows matched/unmatched per file. ✅ BUILT
3. `review` — Show what's still missing, file completeness summary. NOT BUILT YET
4. `followup` — Generate borrower follow-up message (email/SMS draft) requesting missing docs. NOT BUILT YET
5. `scrub` — Pre-submission AI scrub: review the assembled file for common kickback reasons (income reconciliation, doc freshness, signature gaps, large unsourced deposits). NOT BUILT YET
6. `done` — Submission-ready summary.

## Key design decisions

- **Prompts in `.txt` files**, loaded by `LLMService.load_prompt()`. Edit prompts without touching code.
- **Curly braces in prompts must be doubled `{{ }}`** for literal JSON braces — single braces are reserved for `.format()` placeholders like `{profile}`, `{today}`, etc.
- **Date awareness:** stip generator and classifier both receive `today`, `prior_year`, `two_years_back`. This was added after a bug where the model picked stale years for W-2 stips. Stips name the *role* (e.g. "Most recent W-2"), with `accepted_years` field carrying the year-specificity.
- **Confidence-based status:** classifier returns `match_confidence` of high/medium/low. High/medium → stip flips to `received` (✅), low → `needs_review` (⚠️). Progress bar only counts `received`.
- **Service objects are session-scoped** (built once in `app.py`, stored in `st.session_state.services`).
- **Streamlit drag-drop styling** uses CSS targeting `data-testid` selectors — internal to Streamlit, may break on future versions, acceptable risk for a demo.

## What's already working

- Borrower intake form with sensible defaults
- Stip list generation tailored to borrower type (W-2 employee vs. self-employed vs. retired produces meaningfully different lists)
- Drag-and-drop multi-file upload with custom-styled drop zone
- Batch processing with progress bar
- Per-document classification + extraction
- Pay stub extraction with Fannie Mae freshness check + auto-calculated monthly income (3 methods)
- Generic extraction for non-pay-stub docs
- Sidebar stepper showing workflow progress
- Sidebar stip list with ✅/⚠️/◯ status icons + progress bar
- Borrower-name-mismatch detection
- Date-aware year matching (W-2 for current year matches "Most recent W-2" stip)
- Diagnostic batch summary panel after each upload showing per-file outcomes

## What's next (priority order)

1. **Stage 3: Completeness Review.** No new LLM calls needed. Show what's received vs. missing, group by category, surface any `needs_review` items. Should feel like a "file dashboard" view.
2. **Stage 4: Borrower Follow-up Message.** New service `FollowupGenerator`. Takes the missing-stip list and generates a friendly, specific email/SMS draft asking the borrower for the missing items. Show the draft in the UI with an "approve and send" button (button is mock — no real send for the demo).
3. **Stage 6: Pre-Submission Scrub.** New service `PreSubmissionScrubber`. Runs after all stips are received. Reviews the assembled extracted data and flags common kickback reasons: income reconciliation across pay stub + W-2, doc freshness, large unsourced deposits on bank statements, missing signatures. Output is a structured report.
4. **(Stretch) Stage 7: Borrower status chat.** Skip unless time allows.

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