---
name: factframe-safe-product-import
description: Build, change, diagnose, or verify FactFrame public Schema.org Product URL ingestion, including URL validation, SSRF protection, DNS and HTTP bounds, structured parsing, image filtering, and import provenance. Do not use for private-network crawling, browser automation, or arbitrary webpage extraction.
---

# FactFrame Safe Product Import

Read `docs/index.md`, the Product Truth context, current connector port/adapter, import API and worker, then [references/network-and-persistence.md](references/network-and-persistence.md).

## Security contract

- Validate before enqueue and again in the Worker.
- Accept only public HTTP/HTTPS, standard ports, and URLs without credentials, query, or fragment.
- Resolve all A/AAAA records within bounds; reject the whole target if any address is not globally routable.
- Connect to a validated IP while preserving the original hostname for Host and TLS SNI.
- Disable environment proxies and redirects. Bound DNS, connect/read, total time, body size, and candidate images.
- Match MIME types exactly. Parse direct JSON or Schema.org Product JSON-LD only; do not execute JavaScript or ask a model to fill missing fields.
- Revalidate every projected image URL with the same SSRF policy.
- Persist bounded projections, digests, stages, and safe error codes—not raw pages, headers, cookies, DNS/IP details, or secret-bearing URLs.
- A successful fetch creates a new proposed observation; it does not confirm a Product Fact.

## SOP

1. Record the smallest failing security or parsing case before changing code.
2. Trace URL normalization, enqueue validation, Worker revalidation, DNS resolution, pinned connection, MIME/body bounds, parser projection, and append-only persistence.
3. Preserve the port/adapter boundary; the connector returns an ingress DTO and never creates trusted Facts directly.
4. Reuse the Product Source for the same normalized URL, but append a new Snapshot and proposed `source_field` facts for each successful observation.
5. Map external failures to stable, URL-free Problem Details.
6. Run connector unit tests, import/timeline PostgreSQL integration, Ruff, and Mypy.

## Stop conditions

Stop rather than weakening policy when a target needs a private/loopback/link-local address, non-standard port, redirect chain, tokenized query, login state, JavaScript execution, or general crawling. Offer manual Product Truth input instead. Network success does not prove source accuracy, ownership, commercial permission, or claim eligibility.
