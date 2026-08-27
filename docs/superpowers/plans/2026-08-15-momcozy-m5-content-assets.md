# Momcozy M5 Content Assets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a locally stored, auditable Momcozy M5 media library in which every generated image or video has its own folder containing the final file, prompt, provenance, configuration and quality review.

**Architecture:** Keep commercial brand assets separate from the Oumomo clean-room research evidence tree. A small, tracked Python validator defines the bundle contract and rejects sensitive third-party identifiers; generated media and per-asset records live in the gitignored `outputs/momcozy-content-assets/` data-asset root. Production is gated by visible Oumomo quotes and task recovery, while every paid submission is reconciled against the visible credit balance.

**Tech Stack:** Python 3.12 standard library, `unittest`, local filesystem, SHA-256, Oumomo visible Chrome UI.

## Global Constraints

- Work on `main`; do not create a worktree. The project guide requires `main`, and the user approved this implementation.
- Do not commit this batch unless the user makes a new explicit commit request.
- `outputs/momcozy-content-assets/` is a local data-asset root and remains gitignored; raw media, account identifiers, raw task IDs, signed URLs and cookies never enter Git.
- The only approved M5 claims for new visible text are `Momcozy M5 Smart`, `Wearable Breast Pump`, `App Control`, `3 modes`, `9 levels`, and `4 washable parts`, based on the official product page observed 2026-08-15. Do not use price, discount, award, medical, guarantee, comparison or unverified performance copy.
- Every paid Oumomo submission records visible quote, balance before and after, one-click submission, a SHA-256 task identifier, a recovered terminal state and an artifact hash. Never resolve an unknown submission by clicking again.
- Stop the paid batch if task recovery fails, balance movement cannot be reconciled, a model configuration changes after quote, or generated media cannot be downloaded and hashed.

---

### Task 1: Add the reusable asset-bundle contract and validator

**Files:**
- Create: `tools/momcozy_assets/__init__.py`
- Create: `tools/momcozy_assets/contracts.py`
- Create: `tools/momcozy_assets/validate.py`
- Create: `tools/momcozy_assets/tests/test_contracts.py`

**Interfaces:**
- Consumes: an asset directory containing `asset.*`, `prompt.md`, `recipe.json`, `provenance.json`, `qa.md`, and `hashes.sha256`.
- Produces: `validate_bundle(path: Path) -> list[str]` and CLI exit status `0` only when all bundles are structurally valid and free of sensitive identifiers.

- [x] **Step 1: Write a failing validator test**

```python
def test_validate_bundle_accepts_complete_image_bundle(tmp_path: Path) -> None:
    bundle = tmp_path / "IMG-M5-003-app-control-4x5"
    write_complete_bundle(bundle, asset_name="asset.png")
    assert validate_bundle(bundle) == []
```

- [x] **Step 2: Add negative tests for contract and privacy failures**

```python
def test_validate_bundle_rejects_missing_prompt_and_raw_task_id(tmp_path: Path) -> None:
    bundle = tmp_path / "IMG-M5-003-app-control-4x5"
    write_complete_bundle(bundle, asset_name="asset.png")
    (bundle / "prompt.md").unlink()
    (bundle / "provenance.json").write_text('{"task_id":"raw"}', encoding="utf-8")
    assert validate_bundle(bundle) == [
        "missing required file: prompt.md",
        "forbidden provenance key: task_id",
    ]
```

- [x] **Step 3: Implement the minimal contract**

`recipe.json` must require `asset_id`, `asset_type` (`image` or `video`), `model`, `aspect_ratio`, `resolution`, `quote_credits`, `credit_before`, `credit_after`, `observed_at`, `prompt_sha256`, `config_sha256`, and `terminal_state`. `provenance.json` must require the SHA-256 `task_id_hash`, public product-page URL, and reference asset SHA-256 list. `qa.md` must include the exact headings `Product identity`, `Text and claims`, `Technical check`, and `Commercial disposition`.

- [x] **Step 4: Run the focused tests**

Run: `rtk uv run --project apps/api python -m unittest discover -s tools/momcozy_assets/tests -v`

Expected: all contract tests pass.

### Task 2: Create the M5 campaign library and archive the existing images

**Files:**
- Create locally: `outputs/momcozy-content-assets/2026-08-15-m5-smart/campaign-brief.md`
- Create locally: `outputs/momcozy-content-assets/2026-08-15-m5-smart/product-facts.json`
- Create locally: `outputs/momcozy-content-assets/2026-08-15-m5-smart/reference-library/manifest.json`
- Create locally: `outputs/momcozy-content-assets/2026-08-15-m5-smart/IMG-M5-001-clean-hero-1x1/`
- Create locally: `outputs/momcozy-content-assets/2026-08-15-m5-smart/IMG-M5-002-workday-app-control-9x16/`

**Interfaces:**
- Consumes: the two already completed Oumomo image outputs, the three approved official product-reference image files, and the public M5 product page.
- Produces: two complete local asset bundles and a shared reference manifest. Each bundle is self-describing without storing a signed Oumomo URL or raw task number.

- [x] **Step 1: Create the campaign brief and fact freeze**

Write the approved claims, prohibited claims, master visual palette (`ivory`, `soft blush`, `warm daylight`), intended channels (`TikTok Shop`, PDP, paid social), and the source page observed on 2026-08-15. The brief must label all performance, safety, health, price and offer language as out of scope unless a later reviewed fact explicitly authorizes it.

- [x] **Step 2: Import completed image files without overwriting them**

Download each completed project through the visible Oumomo project UI. Copy the extracted PNG into the matching `asset.png`, preserve the original download only in the user Downloads location, and compute SHA-256 after import. Do not delete existing downloads or project items.

- [x] **Step 3: Write each bundle's prompt, recipe, provenance, QA and hashes**

The recipe records the visible model, dimensions, quantity, price and balance transition. `prompt.md` records the exact user-visible prompt plus a one-paragraph creative rationale. Provenance stores only the task SHA-256, reference image hashes and the public product source. QA records actual observations; a missing OCR or video check is written as `not yet assessed`, never treated as passing.

- [x] **Step 4: Validate the current image library**

Run: `rtk uv run --project apps/api python -m tools.momcozy_assets.validate outputs/momcozy-content-assets/2026-08-15-m5-smart`

Expected: exactly two valid image bundles and no sensitive-data findings.

### Task 3: Free-gate video routes and lock the paid production matrix

**Files:**
- Create locally: `outputs/momcozy-content-assets/2026-08-15-m5-smart/production-matrix.json`
- Modify locally: `outputs/momcozy-content-assets/2026-08-15-m5-smart/campaign-brief.md`

**Interfaces:**
- Consumes: the current Oumomo balance, visible video-model form configuration and quote, current product references and the local asset contract.
- Produces: a price-correct production matrix with one prompt and one planned folder ID per candidate asset.

- [x] **Step 1: Inspect candidate video models without submitting work**

For each usable video route, record whether it accepts the same M5 references, exposes duration/aspect-ratio/resolution, displays a stable quote and has a recoverable project/task destination. Do not submit a paid task during this step.

- [x] **Step 2: Select the one stable video route**

Choose the lowest-cost route that preserves product references and produces a vertical 9:16 output. If none passes all four checks, mark video production blocked and allocate the remainder to GPT Image-2 images rather than retrying unknown video submissions.

- [x] **Step 3: Calculate the exact spend allocation**

The first 20-credit video completed and reconciled from 666 to 646 credits. Batch B then used six more 20-credit videos and reconciled 646 to 526. At the visible 20-credit video and 2-credit image prices, the current exact allocation is 25 additional videos plus 13 additional images, totalling 526 credits. It remains subject to batch-level action-time confirmation and quality stop rules.

Let `P` be the visible per-video quote and keep 12 core image concepts at two credits each. Choose the greatest non-negative `video_count` for which `666 - (P * video_count)` is non-negative and even; turn the remaining even balance into image outputs at two credits each. If `P` is odd, choose an even `video_count`. The matrix must total exactly 666 credits, or state why an exact total is impossible before any payment.

- [x] **Step 4: Freeze the creative list**

Use only these concepts, with one explicit output per ID:

```text
VID-M5-001 workday desk: adult mother at a bright home desk; product close-up; App Control visual only
VID-M5-002 on-the-go case: cream carry case to product reveal; clean neutral travel setting
VID-M5-003 product detail: rotating macro of M5 controls and transparent cup; no claim overlays
VID-M5-004 phone pairing: hand uses phone near product; no app screen UI fabrication
VID-M5-005 morning routine: daylight countertop product setup; no medical context
VID-M5-006 wardrobe freedom: fully clothed adult lifestyle context; product and bra are non-explicit
IMG-M5-003 app-control PDP 4:5
IMG-M5-004 carry-case PDP 4:5
IMG-M5-005 controls macro 1:1
IMG-M5-006 product-and-parts 4:5
IMG-M5-007 desk lifestyle 9:16
IMG-M5-008 travel lifestyle 9:16
IMG-M5-009 clean hero 1:1
IMG-M5-010 product-detail PDP 4:5
IMG-M5-011 comparison-free carousel cover 1:1
IMG-M5-012 TikTok safe-area cover 9:16
IMG-M5-013 neutral lifestyle ad 4:5
IMG-M5-014 packaging and case 1:1
```

The remaining video IDs repeat the six approved concepts as controlled framing variants (`wide`, `product-close`, `hand-detail`) and must carry their own folder and prompt. No product claim is introduced by a variant.

### Task 4: Generate, recover, archive and quality-check paid assets in reconciled batches

**Files:**
- Create locally per output: `outputs/momcozy-content-assets/2026-08-15-m5-smart/<ASSET-ID>/`
- Modify locally after every terminal task: `outputs/momcozy-content-assets/2026-08-15-m5-smart/production-matrix.json`

**Interfaces:**
- Consumes: one frozen production-matrix entry, visible credit quote and balance, and approved reference images.
- Produces: one validated asset folder with a terminal task, local media file and reconciled ledger information.

- [x] **Step 1: Prepare one batch from frozen matrix entries**

For each task, populate its prompt and recipe before submission, record balance before and quote, and set `submit_count` to `0`. Use only the prompt for that entry and the explicitly frozen approved reference-image set; the set is recorded by SHA-256 in the artifact provenance.

- [x] **Step 2: Obtain action-time approval for the batch total**

Show the model, task IDs, task count and total credits for the imminent batch. Do not click a generation button until the user confirms that exact batch.

- [x] **Step 3: Submit each task once and recover its terminal state**

Batch B used six separately confirmed 20-credit Seedance 2.0 Mini submissions. Every task reached the visible `completed` state, and the visible balance reconciled from 646 to 526. The original reference-recovery issue is closed for this batch; it remains a stop condition for any later batch.

After a single click, use the visible task queue and project management UI. Record `completed`, `failed`, or `unknown`; on `unknown`, do not click again. Verify the visible balance change before opening the next task.

- [x] **Step 4: Download and build the individual folder**

Download only completed files through the visible project UI. Put one rendered file in `asset.png` or `asset.mp4`, write all contract files, calculate SHA-256, and capture media metadata. For video, add `technical.json` with duration, dimensions, frame rate, codec and audio presence.

- [x] **Step 5: Apply the commercial quality gate**

Mark an asset `approved`, `revision-needed`, or `rejected` based on product identity, crop/safe area, readable text, unsupported claims, unwanted logos, non-explicit adult portrayal, and technical validity. Keep rejected files and their review; do not overwrite a prior asset folder.

- [x] **Step 6: Validate after every completed batch**

Run: `rtk uv run --project apps/api python -m tools.momcozy_assets.validate outputs/momcozy-content-assets/2026-08-15-m5-smart`

Expected: all terminal assets have valid folders; the sum of reconciled deltas matches the visible balance transition.

**Batch B quality result:** six completed videos were archived one per folder. `VID-M5-002`, `VID-M5-004` and `VID-M5-006` are `revision-needed` pending product/wordmark review; `VID-M5-005` is `revision-needed` because a third-party laptop logo appeared; `VID-M5-003` and `VID-M5-007` are rejected because the render introduced fabricated overlay text and altered branding. Rejected files remain preserved as prompt-control evidence and are not approved for commercial use.

**Batch D quality result:** twelve separately confirmed GPT Image-2 outputs were submitted once at 2 credits each and reconciled from 500 to 476 credits. All reached `completed`, were downloaded through the project UI, and passed the bundle validator. `IMG-M5-016` through `IMG-M5-019` add four 3:2 horizontal PDP/landing-page assets; `IMG-M5-020` and `IMG-M5-021` add front/profile 1:1 product cards; `IMG-M5-022` and `IMG-M5-023` add 2:3 product and packing details; `IMG-M5-024` through `IMG-M5-027` add 9:16 travel, device-free desk, evening and controls assets. All twelve are `approved` for internal asset selection, subject to final brand review before publication. The successful 3:2 default is 1248 x 832, 1:1 is 1024 x 1024, 2:3 is 832 x 1248, and 9:16 is 720 x 1280. Continue using the one-click, terminal-state, hash and QA gates; any future paid batch needs an exact new confirmation.

**Batch E-A quality result:** the user confirmed an 80-credit batch. Two 30-credit Seedance 2.0 videos reconciled 476 to 416 and are retained as `revision-needed` vertical drafts pending final product-detail and wordmark review. Ten 2-credit GPT Image-2 images reconciled 416 to 396. `IMG-M5-028` through `IMG-M5-035` are eight native 16:9 desktop/PDP/lifestyle assets, `IMG-M5-036` is a native 2:3 catalog hero, and `IMG-M5-037` is a native 9:16 social static cover. The planned 4:5 catalog concept was not submitted because the visible form had no native 4:5 option; it was replaced by 2:3 without changing the image count or batch cost. All ten images are `approved` for internal asset selection, subject to final brand review before publication.

**Batch F archive result:** after the user explicitly authorized the final 396 credits, 40 completed GPT Image-2 project groups were recovered through the visible project UI: 39 groups of five images plus one group of three. The visible balance reconciled 396 to 0. All 198 images were downloaded, each extracted into its own `IMG-M5-038` through `IMG-M5-077` variant bundle and validated with the same privacy-safe asset contract. The 198-image credit chain is continuous at 2 credits per image. Technical and eight-item visual-sample evidence is recorded in `outputs/momcozy-content-assets/2026-08-15-m5-smart/batch-f-archive-closeout.md`; all Batch F images remain on commercial hold pending per-file brand review rather than being bulk-approved.

### Task 5: Close out the local library and report usable inventory

**Files:**
- Create locally: `outputs/momcozy-content-assets/2026-08-15-m5-smart/library-index.json`
- Create locally: `outputs/momcozy-content-assets/2026-08-15-m5-smart/production-report.md`

**Interfaces:**
- Consumes: validated asset folders and Oumomo visible account balance.
- Produces: one browseable local index and an accurate summary of available, revision-needed, rejected and blocked assets.

- [x] **Step 1: Derive the index from bundle metadata**

List only `asset_id`, type, aspect ratio, intended channel, product, status, local relative file path, artifact SHA-256 and prompt SHA-256. Exclude task IDs, account data and remote media URLs.

- [x] **Step 2: Reconcile the final credit balance**

State initial balance, every asset's delta, final visible balance and any unspent remainder. If the balance is not zero, state the exact blocker rather than creating low-value filler content.

- [x] **Step 3: Run final validator and sensitive-data scan**

Run:

```bash
rtk uv run --project apps/api python -m tools.momcozy_assets.validate outputs/momcozy-content-assets/2026-08-15-m5-smart
rtk rg -n -i 'raw_task_id|task_id["'"']?\\s*:|signed_url|authorization|cookie|phone' outputs/momcozy-content-assets/2026-08-15-m5-smart
```

Expected: validator exits `0`; the sensitive-data scan returns no matches.

## Self-Review

- The plan covers a self-contained folder for every rendered image/video, reproducible prompt and configuration records, shared reference hashes, claim boundaries, paid-task reconciliation, artifact downloading, technical/creative QA and a final asset index.
- The live quote and user action-time approval gates prevent an accidental charge. The hard stop conditions prevent repeated or untraceable submissions.
- The production root is deliberately separate from the clean-room research tree and remains ignored, so no customer content, private task identifiers or generated media are committed.
