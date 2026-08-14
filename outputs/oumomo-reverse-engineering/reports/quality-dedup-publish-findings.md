# Quality, deduplication and publish dry-run findings

## Controlled degradation corpus

U-B01 was copied into a six-variant local corpus with one immutable source hash and per-variant transform parameters and output hashes:

| ID | Transform | Observable technical effect |
|---|---|---|
| D-00 | original | 9,389,487 bytes; 720×1280; H.264/AAC; 15.104s |
| D-01 | strong compression | 436,903 bytes; same dimensions and streams |
| D-02 | wrong aspect ratio | 240×240 crop; H.264/AAC |
| D-03 | muted | no audio stream |
| D-04 | audio/video offset | AAC shifted by 0.5s |
| D-05 | key visual obscured | 85% black cover during the 6–9s product-mixing beat |

The generator uses argument arrays with `shell=False`, records the transformation before evaluation and returns `unavailable` without media artifacts when ffmpeg is absent. This makes the corpus suitable for testing whether a quality scorer reacts to the intended defect rather than to different source content.

## Quality-score gate

`Q-GATE` selected the completed U-B01 project from the quality-check page. The selection immediately rerouted to `/zh/tiktok-slide-show`; no score, quote or confirmation screen was reachable. Local upload could not be used because browser file-URL permission is disabled. The planned repeated six-condition scoring matrix was therefore not submitted and consumed zero credits.

The page claims TikTok official pre-check support, originality/compliance/quality analysis, recommendations and account-protection value. These remain `Vendor claim`; no response schema, official receipt, score threshold, repeatability or degradation sensitivity was observed.

## Deduplication gate

`D-GATE` reproduced the same route defect: selecting U-B01 on the deduplication page navigated to `/zh/tiktok-slide-show`. No quote or before/after artifact was produced and zero credits were consumed.

The page displays a fixed example with `92.27%成功率`, filtering, resize, visual adjustment, effects and metadata rewriting. Because no controlled before/after run exists, this cannot support an algorithmic-causality claim. Current evidence only proves the marketed UI contract and the broken project-selection callback.

## Publish dry-run

`P-DRY` successfully selected U-B01 while remaining on the publish route. The visible contract includes:

- video and cover edit;
- TikTok account selection and OAuth authorization;
- title and tags;
- required product and 30-character alphanumeric product name;
- pre-check and AI-label toggles;
- immediate or scheduled publication;
- final publish action.

The run stopped before TikTok OAuth authorization, account binding, product selection and the final publish action. No external account state changed and no credit was consumed.

## Engineering conclusions

1. Quality scoring cannot be trusted without repeated identical-input scores and controlled degradation sensitivity.
2. Deduplication cannot be inferred from output diversity; it requires an explicit source → transformed-output pair and preservation checks for speech, text, product identity and facts.
3. Project selection is not a shared reliable primitive: publish works, while quality and dedup reroute incorrectly.
4. A safe publish domain needs a server-side draft, explicit account/product authorization, preview, preflight findings, AI disclosure, scheduled timestamp and a final confirmation token.
5. `official`, `account weight`, `distribution priority` and fixed success percentages remain vendor claims until an auditable external receipt and reproducible evaluation exist.

Verdict: quality score `blocked`; deduplication `blocked`; publish field contract `pass` at dry-run depth only.
