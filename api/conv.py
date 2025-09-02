from flask import Flask, request, jsonify
from PIL import Image, UnidentifiedImageError
import requests, hashlib, os
from io import BytesIO

app = Flask(__name__)

@app.route("/conv")
def conv():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing ?url=<image_url>"}), 400

    try:
        resp = requests.get(url, timeout=10, stream=True)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": f"Failed to fetch URL: {str(e)}"}), 400

    try:
        img = Image.open(resp.raw).convert("RGBA")
    except UnidentifiedImageError:
        return jsonify({"error": "URL does not contain a valid image"}), 400

    # Generate deterministic name (hash of URL)
    h = hashlib.sha256(url.encode()).hexdigest()[:16]
    out_path = f"/tmp/{h}.png"

    # Save to tmp (Vercel only allows /tmp write)
    img.save(out_path, format="PNG", optimize=True)

    # Build the serving URL
    base_url = request.host_url.rstrip("/")
    output_url = f"{base_url}/api/out/{h}.png"

    return jsonify({"output": output_url})
