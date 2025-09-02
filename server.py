import os
import requests
from flask import Flask, request, jsonify, send_file
from fpdf import FPDF
from PIL import Image
from enma import Enma, Sources

app = Flask(__name__)

@app.route("/api/nh_to_pdf", methods=["GET"])
def nh_to_pdf():
    try:
        nh_code = request.args.get("id")
        if not nh_code:
            return jsonify({"error": "Missing ?id parameter"}), 400

        # Setup Enma
        enma = Enma[Sources]()
        enma.source_manager.set_source(Sources.NHENTAI)
        doujin = enma.get(identifier=nh_code)

        if not doujin:
            return jsonify({"error": "Doujin not found"}), 404

        title = doujin.title.english if doujin.title else f"NH-{nh_code}"

        # Build PDF
        pdf = FPDF()
        for i, page in enumerate(doujin.pages):
            resp = requests.get(page.url)
            if resp.status_code != 200:
                continue

            # Detect file type
            content_type = resp.headers.get("Content-Type", "").lower()
            if "png" in content_type:
                ext = "png"
            elif "jpeg" in content_type or "jpg" in content_type:
                ext = "jpg"
            elif "webp" in content_type:
                ext = "webp"
            else:
                ext = "jpg"

            tmpfile = f"page_{i}.{ext}"
            with open(tmpfile, "wb") as f:
                f.write(resp.content)

            # Convert webp → png
            if ext == "webp":
                img = Image.open(tmpfile).convert("RGB")
                tmpfile_png = f"page_{i}.png"
                img.save(tmpfile_png, "PNG")
                tmpfile = tmpfile_png

            pdf.add_page()
            pdf.image(tmpfile, x=10, y=10, w=180)

        filename = f"{nh_code}.pdf"
        pdf.output(filename)

        result = {
            "code": nh_code,
            "title": title,
            "pages": len(doujin.pages),
            "size_bytes": os.path.getsize(filename),
            "download_url": f"/api/download/{filename}"
        }
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download/<path:filename>", methods=["GET"])
def download(filename):
    if not filename or not os.path.exists(filename):
        return jsonify({"error": "File not found"}), 404
    return send_file(filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
