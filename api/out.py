from flask import Flask, send_file, abort
import os

app = Flask(__name__)

@app.route("/api/out/<filename>")
def out(filename):
    path = f"/tmp/{filename}"
    if not os.path.exists(path):
        return abort(404)
    return send_file(path, mimetype="image/png")
