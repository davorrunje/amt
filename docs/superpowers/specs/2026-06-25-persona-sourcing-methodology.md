# Persona Sourcing Methodology

**Date:** 2026-06-25
**Status:** Living document (update as the corpus and personas evolve)
**Related:** `corpus/sources.yaml` (download manifest), `docs/superpowers/turing-voice-guide.md`
(distilled output), `src/turing/personas/` (the prompts), the archive-sourcing design spec.

## Purpose

Define **which** transcribed documents inform the Turing personas and **how** they are
turned into persona prompts. This is deliberately separate from `corpus/sources.yaml`,
which is only the download manifest (what to fetch + OCR). A document may be downloaded
for the record without being used for the personas, and vice-versa.

## Principle: register vs. substance

Two different things are drawn from the corpus, from different documents:

- **Register (voice)** — how Turing actually writes: diction, rhythm, directness, dry
  humour, the absence of effusiveness. Best sourced from **informal correspondence**.
- **Substance (views)** — what he thought about specific questions. Sourced from his
  **published/technical** work, most of which is already well known and public-domain.

The "too cheerful" problem is a **register** problem, so correspondence is the priority.

## Document selection (current)

| Ref | Used for | Why |
|-----|----------|-----|
| **AMT/D/4** — letters/postcards to Robin Gandy, 1952-4 | **Register (primary)** | Informal letters to a student/colleague: plain, blunt, dry. The core voice source. |
| AMT/C/7 — diffusion-reaction theory of morphogenesis (with Wardlaw) | Substance only | Technical prose; not representative of conversational register. |
| AMT/C/10 — morphogenesis MS, Part III | Substance only | As above. |
| AMT/B/25 — publication/lecture | (pending) | Currently fails transcription; revisit when fixed. |
| Published works (1950 *Mind* paper, 1948 report, BBC talks) | Substance + some register | Public-domain; referenced directly, not transcribed into `corpus/`. |

**Selection criteria for adding new persona-voice sources:** prefer personal/informal
correspondence (AMT/D; personal letters in AMT/A and AMT/K), addressed to individuals,
written in the first person, away from formal mathematical exposition. Add the catalogue
references to `corpus/sources.yaml`, then record the ones used for voice in the table above.

## Method (how documents become persona prompts)

1. **Transcribe** — add refs to `corpus/sources.yaml`; run `./tools/source.sh` (fetches +
   OCRs only the missing items). Transcriptions land in `corpus/<ref>.md` (gitignored).
2. **Read and annotate** — read the selected register sources. Note recurring features:
   characteristic diction, sentence length/rhythm, how he opens and closes, how he gives
   criticism, his humour, and—critically—what he never does (gush, flatter, exclaim).
3. **Distil** — update `docs/superpowers/turing-voice-guide.md` with those observations,
   citing the source ref. Describe patterns; do **not** paste verbatim copyrighted text
   into committed files (the guide characterises the voice, it does not reproduce letters).
4. **Rewrite** — adjust `src/turing/personas/base.md` and the audience overlays to match
   the guide. Preserve the guardrails (extrapolated/modern-aware, never claims to be the
   real man, no fabricated citations) — only the register changes.
5. **Validate** — produce before/after sample exchanges per persona on a fixed prompt;
   judge the tone shift by hand (no automated tone metric). Keep persona unit tests passing.
6. **Iterate** — as more correspondence is transcribed, refine the guide and prompts.

## Constraints

- **No verbatim archive content in committed files.** The voice guide and personas are our
  own derived descriptions; `corpus/*.md` transcriptions stay local/gitignored.
- **Guardrails are non-negotiable** and survive every rewrite.
- **Tone is a human judgment** — the methodology supports the decision, it does not automate it.
