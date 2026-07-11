# QR-Shield

QR-Shield is a synthetic-data research project for detecting QR-code sticker overlay attacks using image forensics and content verification.

The project combines multiple forensic techniques with QR payload verification to distinguish between genuine and tampered QR codes.

> **Note:** This project never uses real payment identities or downloaded QR datasets. All QR codes, identities, and images are generated locally using fictional placeholder data.

---

## Features

- Generate synthetic genuine QR codes
- Generate synthetic tampered QR codes with sticker overlays
- Error Level Analysis (ELA)
- Frequency-domain feature extraction (FFT/DCT)
- Finder pattern geometry validation
- QR content verification
- Multi-layer fusion engine
- Flask-based web interface
- Deployed on Render for online testing

---

## Live Demo

**Render Deployment**

https://qr-shield-e8s2.onrender.com

---

## Project Structure

```
qr-shield/
│
├── app/                 # Flask application
├── frontend/            # Frontend assets
├── src/                 # Core detection pipeline
├── tests/               # Unit tests
├── docs/                # Documentation
├── sample_qr/           # Sample QR codes for testing
├── uploads/             # Uploaded files
├── requirements.txt
└── README.md
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/sadhnabh/qr-shield.git
cd qr-shield
```

Create a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

---

## Generate Genuine QR Codes

```powershell
python -m src.data_generation.generate_qr --count 10 --seed 42
```

Generated images are stored in:

```
data/genuine/
```

---

## Generate Tampered QR Codes

```powershell
python -m src.data_generation.generate_tampered --count 10 --seed 84
```

Generated images are stored in:

```
data/tampered/
```

Each generation appends metadata to:

```
data/manifest.csv
```

including:

- generation seed
- augmentation settings
- synthetic identities
- timestamp

---

## Run Tests

```powershell
python -m pytest
```

---

## Image Forensics

### Error Level Analysis

```powershell
python -m src.layer1_forensics.ela data/genuine/example.png data/tampered/example.png
```

Outputs are saved to:

```
results/ela/
```

---

### Frequency Features

```powershell
python -m src.layer1_forensics.freq_features data/genuine/example.png
```

---

### Finder Pattern Validation

```powershell
python -m src.layer1_forensics.finder_pattern data/genuine/example.png
```

Annotated validation images are saved automatically.

---

## Running the Web Application

Start the Flask server:

```powershell
python app/app.py
```

Open your browser:

```
http://127.0.0.1:5000
```

Upload a QR image and the application will classify it as:

- Genuine
- Tampered

along with the forensic analysis results.

---

## Sample QR Codes

Sample QR codes are provided in the `sample_qr/` folder.

Use these files to test the application without generating your own dataset.

Example files:

```
sample_qr/
├── genuine_1.png
├── genuine_2.png
├── tampered_1.png
└── tampered_2.png
```

---

## Technologies Used

- Python 3.11
- Flask
- OpenCV
- NumPy
- Pillow
- Pyzbar
- qrcode
- Gunicorn
- PyTest

---

## Future Improvements

- Deep learning-based classification
- Heatmap visualization
- Confidence scoring
- Batch QR verification
- REST API support

---

## Author

**Sadhna**

Internship Project – QR-Shield