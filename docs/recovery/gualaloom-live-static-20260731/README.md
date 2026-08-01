# Guala Loom live-static custody — 2026-07-31

This directory is an exact recovery copy of the two HTML files and 28
referenced visual assets that were live in `s3://dsf-ai-site` on
2026-07-31.

Custody is not design acceptance. The live Guala Loom control layout is
rejected. Only the art and asset files are accepted for reuse. In particular,
the separate microphone start/stop, camera start/stop, and cards start/stop
controls must not be promoted as the next production control design.

The two HTML files are preserved because the S3 bucket has no versioning and
they did not exist in repository history. They are reference sources for the
truthful observational and sensory bindings, not the production source of
record.

The `cards/` directory contains exactly the 26 A-Z cards present in S3.
There were no number-card objects and no number-card wiring in the live HTML
at custody time. The authoritative missing number set is exactly ten cards:
numerals 1 through 10. Number artwork must not be invented.

To verify this copy:

```bash
cd docs/recovery/gualaloom-live-static-20260731
sha256sum -c CUSTODY_MANIFEST.sha256
```

Static-origin protection required before the next backend deploy:

- Do not let `tools/deploy_dsf_ai.sh` Step 8 sync the repository's obsolete
  `dsf_ai_service/static/gualaloom.html` or `loomscan.html` over S3.
- Exclude those two keys and their accepted art/card assets during a
  backend-only cutover.
- Publish replacements only from a separately reviewed static manifest after
  the rejected control layout is replaced with true toggle controls.
- Enable S3 versioning before the next static publication so an accidental
  overwrite remains recoverable.
