from PIL import Image
from io import BytesIO

def predict_image(file_bytes: bytes):
    Image.open(BytesIO(file_bytes)).convert("RGB")
    label = "sample_model"
    candidates = [{"label": "sample_model", "score": 0.92}, {"label": "alt_model", "score": 0.73}]
    price_low, price_high = 50000, 70000
    return {"topLabel": label, "candidates": candidates, "priceRange": [price_low, price_high]}
