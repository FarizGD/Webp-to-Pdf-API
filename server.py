import os
import requests
from flask import Flask, request, jsonify, send_file, after_this_request
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

        # Setup Enma with NHentai
        enma = Enma[Sources]()
        enma.source_manager.set_source(Sources.NHENTAI)
        doujin = enma.get(identifier=nh_code, with_symbolic_links=True)

        if not doujin:
            return jsonify({"error": "Doujin not found"}), 404

        title = doujin.title.english if doujin.title else f"NH-{nh_code}"

        if not doujin.chapters:
            return jsonify({"error": "No chapters found"}), 404

        # First chapter = whole doujin
        chapter_ref = doujin.chapters[0]
        chapter = enma.fetch_chapter_by_symbolic_link(chapter_ref)

        pdf = FPDF()
        for i, page in enumerate(chapter.pages):
            url = page.uri
            resp = requests.get(url)
            if resp.status_code != 200:
                continue

            # Detect file extension
            content_type = resp.headers.get("Content-Type", "").lower()
            if "png" in content_type:
                ext = "png"
            elif "jpeg" in content_type or "jpg" in content_type:
                ext = "jpg"
            elif "webp" in content_type:
                ext = "webp"
            else:
                ext = "jpg"

            tmpfile = f"/tmp/page_{i}.{ext}"
            with open(tmpfile, "wb") as f:
                f.write(resp.content)

            # Convert WEBP → PNG
            if ext == "webp":
                img = Image.open(tmpfile).convert("RGB")
                tmpfile_png = f"/tmp/page_{i}.png"
                img.save(tmpfile_png, "PNG")
                tmpfile = tmpfile_png

            pdf.add_page()
            pdf.image(tmpfile, x=10, y=10, w=180)

        filename = f"/tmp/{nh_code}.pdf"
        pdf.output(filename)

        # Build absolute URL for download
        base_url = request.host_url.rstrip("/")
        result = {
            "code": nh_code,
            "title": title,
            "pages": len(chapter.pages),
            "size_bytes": os.path.getsize(filename),
            "download_url": f"{base_url}/api/download/{nh_code}.pdf"
        }
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download/<path:filename>", methods=["GET"])
def download(filename):
    filepath = os.path.join("/tmp", filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    @after_this_request
    def cleanup(response):
        try:
            os.remove(filepath)
        except Exception:
            pass
        return response

    return send_file(filepath, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
