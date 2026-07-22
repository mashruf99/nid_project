# AI Usage Documentation

This document explains which AI tools were used while building this project, how they
were used, and how the resulting code was verified before being included in the final
submission, as required by the project's AI Usage guidelines.

---

## 1. AI Tools Used

- **Claude (Anthropic)** : Claude used as the primary coding assistant throughout development process:
  designing the initial project structure, reviewing and debugging code, explaining
  trade-offs between different OCR/AI approaches, and helping diagnose live runtime
  errors during testing.
- **Google Gemini (`gemini-3.1-flash-lite`)** : Google Gemini used as the production AI model inside the
  application itself (not as a coding assistant) — this is the vision model that
  performs the actual OCR + translation + field extraction from the NID images.

---

## 2. Example Prompts Used

Below are representative prompts used during development (paraphrased from the actual
conversation):

- *"AS a senior software engineer what are the edge case I should look after while building image to text extractor system."*
- *"When race-case condition occurs?"*
- *"What AI models are best for OCR system for free tier?"*
- *"What is efficient prompting approach to extract NID data from 1 single prompt to convert bangla text into english."*
- *"I'm getting a 502 error when calling the endpoint.. here is the exact error message
  from the response body what's causing it?"*
- *"Should I use Baidu OCR? What's your opinion on the best approach, given I'm
  currently using Groq?"*

The prompting approach was iterative: instead of asking for a finished product in one
shot, the workflow was **Planning → debugging → report the exact error message → get a targeted
fix → polishing code -> re-test**. This kept each AI-assisted change small, verifiable, and tied to a
concrete, reproducible symptom (a real HTTP status code and error body), rather than
speculative code generation.

---

## 3. How AI-Generated Code Was Verified

Every AI-suggested change was verified through actual execution, not accepted blindly:

1. **Local execution against the running FastAPI server** (`uvicorn app.main:app
   --reload`) — every fix was tested by actually calling the `/api/v1/extract-nid`
   endpoint (via Swagger UI and `curl`) with real NID images before being accepted.
2. **Reading and understanding the actual error responses** — when the AI-suggested
   code failed (for example, a `502` from Groq, a `404 model_not_found`, a `413`
   rate-limit error, or a `403 PERMISSION_DENIED` from Gemini), the raw error message
   and status code were captured and fed back for diagnosis rather than assumed to be
   fixed.
3. **Automated tests** (`tests/test_api.py`) were written to lock in the validation
   behavior (missing images, wrong file type, corrupted image, health check) so that
   future changes cannot silently break these guarantees. These tests were run with
   `pytest` and confirmed passing before considering the validation layer complete.
4. **Manual code reading** — every file suggested by the AI was read fully before
   being merged into the project, rather than pasted in unread. This was necessary
   because AI-suggested code did contain real bugs during this process (see below),
   which were only caught through review and testing, not by trusting the AI output.
5. **Cross-checking library/API behavior against official sources** — for
   provider-specific issues (e.g., which Gemini/Groq model names were currently active,
   which had been deprecated), current model availability was verified directly against
   the provider's own API (`GET /v1/models`) rather than relying solely on the AI's
   suggestion, since model lineups change frequently and can be stale in an AI's
   training data.

---

## 4. AI-Generated Code That Was Modified, and Why

Several rounds of AI-suggested code required correction before being accepted:

| Issue Found | Why It Needed Modification |
|---|---|
| Inconsistent indentation in `storage.py` (`__init__`/`save` at 5 spaces vs. other methods at 4 spaces) | Caused a real `IndentationError` in VS Code / at runtime; had to be normalized to consistent 4-space indentation across the class. |
| Duplicate/unreachable `self._save(records)` call outside the `with self._lock:` block in `storage.py` | This line executed outside the file lock, re-introducing the exact race condition the lock was meant to prevent, and referenced a variable that could go out of scope. It was removed. |
| Undefined `retry_side` variable used in `validation.py`'s return statement | The variable was referenced before being assigned anywhere in the function, which would raise a `NameError` on every request. Logic to compute `retry_side` from `FRONT_FIELDS`/`BACK_FIELDS` was added before it was used. |
| Hardcoded/deprecated AI model names (`llama-4-scout-17b-16e-instruct`, `gemini-2.5-flash`) | Both models were confirmed deprecated/shut down for new usage during actual testing (via live `404`/`NOT_FOUND` errors from the providers). Model names were made configurable via environment variables (`GROQ_MODEL` / `GEMINI_MODEL`) specifically so they could be swapped without code changes when this happens again. |
| Reasoning-model `<think>...</think>` blocks breaking JSON parsing | When a reasoning-capable model (`qwen/qwen3.6-27b` on Groq) was the only vision-capable option available, its raw output included a large reasoning block before the actual JSON. The parser was extended to detect and strip this block, and to raise a clear error if the response was truncated mid-reasoning, instead of failing with an opaque `JSONDecodeError`. |
| Unused/shadowing import in `main.py` (`from pydantic import fields`) | This import was never used and was shadowed later in the same file by a local variable also named `fields`, which was confusing and a latent bug risk. It was removed. |
| Missing rate-limit-aware error handling for the AI provider call | Initial code only distinguished a generic `502`. Explicit handling for `429`/rate-limit and `413`/request-too-large responses was added so the API returns an actionable error message instead of a generic failure. |
| Provider switch from Groq to Gemini | After confirming (via the provider's own error messages) that Groq's free-tier token-per-minute limit could not reliably support two-image NID extraction, `nid_extractor.py` was rewritten to call Google Gemini instead — chosen for its more generous free-tier limits and native multimodal support — while keeping every other file (`main.py`, `schemas.py`, `storage.py`, `validation.py`) untouched, since they depend only on the function signature of `extract_nid_data()`, not on which provider implements it. |

---

## 5. Summary

AI assistance was used throughout this project primarily as a **pair-programming and
debugging aid** — for scaffolding code, explaining trade-offs, and diagnosing runtime
errors — while every change was independently run, tested, and read before being
accepted. Several real bugs (indentation errors, an undefined variable, a race
condition, deprecated model names, and a parsing failure caused by a reasoning model)
were only caught because the code was actually executed against live requests rather
than assumed correct, and are documented above for transparency.