# QR-Shield

QR-Shield is a synthetic-data research project for detecting QR-code sticker
overlays. It combines image-forensics signals with independent payee-identity
verification.

The project never uses real payment identities or downloaded QR datasets. All
sample identities and images are generated locally from fictional placeholders.

## Day 1: generate genuine QR images

Create and activate a Python 3.11 virtual environment, then install the current
development dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Generate ten reproducible samples:

```powershell
python -m src.data_generation.generate_qr --count 10 --seed 42
```

Generate a balanced clean/obvious tampered-overlay batch:

```powershell
python -m src.data_generation.generate_tampered --count 10 --seed 84
```

Images are written to `data/genuine/` or `data/tampered/`. Each invocation
appends one run record to `data/manifest.csv`, including the count, seed, sampled
augmentation settings, and synthetic identities.

Run the tests with:

```powershell
python -m pytest
```

Generate ELA heatmaps for existing synthetic samples:

```powershell
python -m src.layer1_forensics.ela data/genuine/example.png data/tampered/example.png
```

ELA outputs are saved under `results/ela/`; existing heatmaps are not replaced.

Print FFT/DCT and QR-boundary features:

```powershell
python -m src.layer1_forensics.freq_features data/genuine/example.png
```

Print finder-geometry features and save annotated validation images:

```powershell
python -m src.layer1_forensics.finder_pattern data/genuine/example.png
```
