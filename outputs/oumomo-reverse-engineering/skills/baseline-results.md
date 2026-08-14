# Skill baseline results

## Result

All three no-Skill baselines passed. Therefore the Skill must not add hypothetical discipline rules for these behaviors; it should add Oumomo-specific playbooks and deterministic evidence validation.

| Scenario | No-Skill decision | Result | Missing reusable capability |
|---|---|---|---|
| BSL-01 | Chose recovery-first; explicitly said 95%/parse error does not prove failure | pass | No Oumomo manifest/ledger validator |
| BSL-02 | Chose inventory, frozen baselines, budget reserve, single-variable screening and repeats | pass | No feature-specific caps/gates/evidence schema |
| BSL-03 | Blocked publish and separated facts, OCR, voice and product identity | pass | No concrete fact/media evidence contract |

## Authoring consequence

The main SKILL.md remains concise and does not restate generic experimental discipline. `references/evidence-contract.md` supplies the missing record schema and stop semantics; `references/feature-playbooks.md` supplies Oumomo-specific routes/gates; `scripts/validate_evidence.py` makes budget, continuity, required fields, hashes and sensitive-field checks deterministic.
