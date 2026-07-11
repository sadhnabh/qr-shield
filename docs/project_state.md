# QR-Shield Project State

Last updated: 2026-07-03

## Verified checkpoint

- Repository structure created under `qr-shield/`.
- Local virtual environment created with the available Python 3.12.7 runtime.
- Genuine QR generator, capture augmentations, and CSV run logging implemented.
- Three genuine samples generated with seed `42`; their exact parameters are in
  `data/manifest.csv`.
- Tampered-overlay generator implemented with deterministic `clean` and `obvious`
  profiles, sparse print noise, offset, rotation, opacity, scale, and optional edge
  shadow.
- Four tampered samples generated with seed `84`; exact base/attacker identities
  and overlay parameters are recorded in `data/manifest.csv`.
- Seven unit tests passed on 2026-07-03.
- Day 2 ELA module implemented with in-memory JPEG recompression, normalized mean
  error scoring, auto-scaled heatmaps, CLI output, and overwrite protection.
- ELA was run at JPEG quality 90 on one genuine, one clean-overlay, and one
  obvious-overlay sample. Scores were `0.003545`, `0.003775`, and `0.005143`
  respectively. These are three diagnostic observations, not model metrics.
- Eleven unit tests passed after adding the ELA module.
- Generated files use fictional `@qrshieldtest` identities only.
- Generators reject filename collisions instead of overwriting existing images.
- Git initialization is pending because `git` was unavailable on `PATH`.

## Next work

Day 1 generation and Day 2 ELA are complete. The next planned module is frequency-
domain discontinuity extraction (`freq_features.py`). Do not report any metric
unless it was produced by an actual recorded run.
