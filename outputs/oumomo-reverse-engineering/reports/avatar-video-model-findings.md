# Avatar and video-model gate findings

## Avatar video

The avatar surface exposes five named site avatars: Maya, Ben, Simone, Talia and Roy, plus avatar-library and local-upload paths. The lowest visible configuration was 9:16, 15 seconds, 快速模式, 720p and one output. Its quote was 75 credits.

The approved per-run cap is 30 credits, so the avatar matrix is blocked before submission. No credit was consumed.

## Video-model router

The dashboard exposes eight model identities: Seedance 2.0, Seedance 2.0 Mini, Seedance 2.5, Gemini Omni, MiniMax H3, Kling V3, Veo 3.1 and Sora2. The default Seedance 2.0 configuration was 快速模式, 480P, 10 seconds, 9:16, quoted at 30 credits.

The price gate passes, but the approved comparison requires the same synthetic reference image for every model. Browser file-upload permission is disabled, so no valid controlled run can be executed yet. No credit was consumed.

## Reverse-engineering implications

- Treat avatar selection, script/voice input, quote and media generation as separate contracts.
- Store avatar identity/version and authorization provenance; a display name is not sufficient.
- Route video models through typed capability metadata for duration, ratio, resolution, reference modes and price.
- A cross-model benchmark is invalid unless input bytes, prompt, seed policy, output count and scoring rubric are frozen.
- Provider/model success must remain separate from factuality, likeness authorization, packaging fidelity and media-QA acceptance.

Verdict: avatar `blocked_by_price_cap`; video-model matrix `blocked_by_input_gate`.
