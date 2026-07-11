# Technique References

## Error Level Analysis

Krawetz, Neal. *A Picture's Worth: Digital Image Analysis and Forensics*.
Black Hat Briefings USA, 2007, section 3.4.2, “Error Level Analysis.”
https://www.hackerfactor.com/papers/bh-usa-07-krawetz-wp.pdf

QR-Shield's `ela.py` follows the described core method: save an image at a known
JPEG error level and calculate its difference from the input. The normalized mean
absolute RGB difference and auto-scaled heatmap are this project's implementation.

