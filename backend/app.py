from flask import Flask, request, jsonify
import hashlib, datetime, io, os
from pymongo import MongoClient
from PIL import Image
import pytesseract

app = Flask(__name__)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/")
client = MongoClient(MONGO_URI)
db = client['certverify']
collection = db['certs']

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get('file')
    issuer = request.form.get('issuer', '')
    if not f:
        return jsonify({"error": "no file"}), 400
    data = f.read()
    h = sha256_bytes(data)
    rec = {"filename": f.filename, "hash": h, "issuer": issuer, "uploaded_at": datetime.datetime.utcnow()}
    collection.insert_one(rec)
    return jsonify({"status": "ok", "hash": h})

@app.route("/verify", methods=["POST"])
def verify():
    f = request.files.get('file')
    if not f:
        return jsonify({"error": "no file"}), 400
    data = f.read()
    h = sha256_bytes(data)
    found = collection.find_one({"hash": h})
    return jsonify({"hash": h, "registered": bool(found)})

@app.route("/ocr", methods=["POST"])
def ocr():
    f = request.files.get('file')
    if not f:
        return jsonify({"error":"no file"}), 400
    img = Image.open(io.BytesIO(f.read())).convert('L')
    text = pytesseract.image_to_string(img)
    return jsonify({"text": text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
