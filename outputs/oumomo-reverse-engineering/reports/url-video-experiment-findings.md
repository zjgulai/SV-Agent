# URL-to-video experiment findings

## Result

U-B01 was submitted exactly once with the default lowest visible configuration: 真人种草, one extracted image, three parsed claims, English, Mini, 720P, 15 seconds and one output. Quote was 50 credits.

The submission produced a route-specific `Unexpected token '<'` JSON parse error at `/zh/url-to-video`. Despite that frontend error, the backend created a recoverable queue job and debited the account from 860 to 810. The job progressed through 15, 30, 45, 60, 70, 85 and 95 percent, remained at 95 percent at the five-minute cutoff, and was later recovered as `succeeded` from the completed queue without a second submission.

## 2026-08-12 free preflight recheck

The same product URL parsed successfully and exposed product identity/category without a debit. Selecting the visible `性能实测` type, however, did not advance to a configuration, quote or confirmation workspace. As no payment contract or recoverable operation was observable, no U-* follow-up submission was made. This is not evidence that the previous HTML/JSON response defect has been fixed; the route remains blocked until the UI exposes a pre-submit quote and a durable operation identity.

Per the approved forced-stop gate, U-B02, U-B03, U-A01 and U-I01 were not submitted. No additional URL-video credits were consumed.

## Reverse-engineered workflow

1. Parse a public product URL into a title, category, three editable claims and one extracted image.
2. Choose one of six rhetorical video types; 真人种草 is preselected.
3. Configure language, model tier, resolution, duration and quantity.
4. Debit before terminal completion and create a queue task.
5. Report coarse progress values through a global task queue.
6. Keep the durable operation discoverable after the route-level response has failed.
7. Open the completed project preview, expose the compiled generation prompt and download the media artifact.

## Output and prompt forensics

The recovered artifact is a 15.104-second, 720×1280, 24 fps H.264/AAC MP4. Its SHA-256 is `f7fc1372002d4219c0c2d12aabce25b0560470eedf605af7f594f95405529095`; the raw signed media URL and task identifier were not retained.

The visible compiled prompt specifies five three-second beats: afternoon fatigue, portable packet use, powder mixing, a blue drink reveal and an instant-awake close. It also invents a green-and-white checkered packet, a cartoon cup character, `200mg of Caffeine`, complete no-clump dissolution and an instant efficacy result. Those details were not grounded in the editable three-claim input.

Frame-grid review found strong creator, kitchen, vessel and drink continuity. The package remained broadly green across shots, but the generated logo, brand and dosage text were malformed and unreadable. The media therefore demonstrates useful scene consistency but fails product identity, packaging-text and factuality gates.

## Defects and implementation implications

- Frontend response handling is not content-type safe. An HTML error response can coexist with a successful backend task, creating a dangerous retry/duplicate-submit ambiguity.
- Debit occurs before media completion; the UI needs an explicit reserved/charged/refunded ledger state.
- Queue progress reached 95 percent without a terminal result inside five minutes, yet the task later completed. A five-minute client timeout is not a terminal business state; progress and recovery must come from persisted stages.
- The request needs an idempotency key and a durable operation record that the client can recover after any response parse failure.
- A safe clone must show `submitted`, `accepted`, `charged`, `running`, `succeeded/failed/refunded` as separate factual states.

Verdict: `fail`. The task eventually succeeded, but the paid execution boundary, prompt factuality and package fidelity are not reliable enough to copy as implemented.
