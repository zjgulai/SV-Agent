# Template and image-model findings

## Outcome

The image-model price and input gates are now closed. The same synthetic `PULSE MIX` reference bytes, prompt, 1:1 ratio, 1K tier and one-image count were submitted exactly once in each of four experiments: two GPT Image 2 runs and two Nano Banana 2 runs. All four jobs reached `succeeded`, produced one downloadable artifact and reconciled against the visible balance.

- Balance: 810 → 800.
- GPT Image 2: 2 + 2 credits.
- Nano Banana 2: 3 + 3 credits.
- Total: 10 credits; no duplicate debit and no retry submission.
- Comparison grid: `artifacts/images/image-model-2x2-grid.png` in order GPT-01, GPT-02, Nano-01, Nano-02.

The earlier `T-GATE` blocked record remains valid as the historical state before Chrome file access was enabled. The four `I-*` records are the later execution facts.

## Frozen input contract

- Reference: `evidence/fixtures/pulse-mix.png`, SHA-256 `34c286145bd1d1875a52f2a7d673442099291cb06fa25fc22f1864a33f8c4974`, 1254×1254 PNG.
- Prompt: `Create a 1:1 TikTok Shop product hero image. Preserve the uploaded package exactly: silver pouch, navy blue lower chevrons, blue lightning icon, text 'PULSE MIX'. Place on clean light gray studio background with soft shadow. Do not add health, energy, ingredient, price, certification, or promotional claims. Do not alter package text.`
- Controls: 1:1, 1K, count 1, one identical reference image.
- Evaluation: package text, blue lightning, navy chevrons, bottom white line, pouch geometry, scene adherence, invented copy, actual media profile and repeat SSIM.

## Result matrix

| Experiment | Model / price | Detected artifact | Reference SSIM | Identity result | Verdict |
|---|---|---|---:|---|---|
| I-GPT-01 | GPT Image 2 / 2 | 1254×1254 PNG | 0.909862 | `PULSE MIX`, lightning, chevrons and white line all retained; gray studio treatment added | pass |
| I-GPT-02 | GPT Image 2 / 2 | 1254×1254 PNG | 0.796853 | all controlled marks retained; pouch was reframed larger than run 1 | pass |
| I-NANO-01 | Nano Banana 2 / 3 | 1024×1024 JPEG bytes in a `.png` asset | 0.966479 after resize | text remained exact, but pouch proportions changed and bottom white line disappeared | fail |
| I-NANO-02 | Nano Banana 2 / 3 | 1024×1024 JPEG bytes in a `.png` asset | 0.970017 after resize | white line returned, but package geometry and label layout still changed | fail |

SSIM is only a pixel similarity diagnostic. It does not replace semantic checks: Nano's high reference SSIM coexists with a product-mark deletion in run 1, while GPT's lower run-2 SSIM is driven mainly by scale and framing even though all named marks remain present.

## Repeatability and latency

- GPT repeat-pair SSIM: 0.807526. Both runs preserved every controlled package mark, but framing and pouch scale varied visibly.
- Nano repeat-pair SSIM: 0.989005. The pair is almost identical overall, yet the bottom white line is inconsistent between repeats. High repeat similarity therefore did not guarantee exact identity preservation.
- Nano completed both jobs while the second GPT task was still progressing. GPT task progress was observed through 95% before terminal completion. This supports a relative speed advantage for Nano in this run, not a general latency SLA.

## Product and engineering defects

1. **Output contract mismatch.** Nano assets were named `.png` and exposed as `image/png`, but file-signature inspection identified baseline JPEG bytes. A downstream pipeline trusting extension or response metadata will mis-handle caching, validation or transcoding.
2. **Resolution semantics are model-dependent.** The same visible `1K` control produced 1254×1254 for GPT and 1024×1024 for Nano. The UI presents a tier, not a stable pixel contract.
3. **Strict product identity is not enforced.** Nano deleted a real package mark in one repeat and changed package proportions in both. The platform has no visible pre-delivery comparison gate.
4. **Progress is synthetic and provider-specific.** GPT exposed a long percentage staircase; Nano completed quickly after only low percentage observations. Percent values are not comparable across providers.
5. **Model label lacks immutable version provenance.** The artifact records a marketing model name but no provider request ID, immutable model revision or seed.

## Reverse-engineering decision

For this exact e-commerce hero-image task, GPT Image 2 dominates Nano Banana 2 on both price and strict package-identity acceptance. Nano is faster and more repeatable at the whole-frame level, but its consistent restyling and the missing mark make it unsuitable as the default path for regulated or exact-SKU imagery.

The valuable component to replicate is not another generic prompt box. Build a provider-neutral image job contract with:

- immutable reference hash, prompt hash, model revision and quote;
- explicit output pixel dimensions and byte-sniffed media type;
- idempotent paid submission plus recoverable Job state;
- package OCR/logo/color/geometry comparison against the reference;
- a strict `accept/review/reject` gate before an image enters the asset library;
- route policy that prefers the cheapest model passing the product-identity threshold.

## Template gate

The template surface still exposes previews and accepts up to nine product images, but no stable same-product A/B pair with a pre-submit quote at or below the approved 30-credit per-run cap was established. The four-run template matrix remains blocked with zero debit. Image-model completion does not change that independent gate.

Verdict: image-model matrix `completed`; GPT runs `pass`; Nano runs `fail` under the strict package-identity contract; template A/B `blocked`.
