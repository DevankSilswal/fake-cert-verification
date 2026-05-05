from flask import Flask, request, jsonify, send_from_directory
from pymongo import MongoClient, ReturnDocument
import hashlib
import os
from dotenv import load_dotenv
from flask_cors import CORS
from datetime import datetime, timezone
import uuid
import qrcode

load_dotenv()
app = Flask(__name__)
CORS(app)

# ================= CONFIG =================
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise Exception("❌ MONGO_URI not found in .env")

client = MongoClient(MONGO_URI)
db = client["certverify"]
collection = db["certificates"]

# ================= UTIL =================
def generate_hash(data):
    return hashlib.sha256(data).hexdigest()

# ================= HOME =================
@app.route("/")
def home():
    return jsonify({"status": "Backend Running ✅"})

# ================= UPLOAD =================
@app.route("/upload", methods=["POST"])
def upload():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        student_name = request.form.get("student_name")
        course = request.form.get("course")

        if not student_name or not course:
            return jsonify({"error": "Missing student or course"}), 400

        data = file.read()
        hash_value = generate_hash(data)

        # Duplicate check
        if collection.find_one({"hash": hash_value}):
            return jsonify({"error": "Certificate already exists"}), 400

        # ================= QR GENERATION =================
        os.makedirs("qr_codes", exist_ok=True)

        qr_url = f"http://localhost:8501/?verify={hash_value}"
        qr = qrcode.make(qr_url)

        qr_path = f"qr_codes/{hash_value[:8]}.png"
        qr.save(qr_path)

        # ================= SAVE =================
        cert = {
            "certificate_id": str(uuid.uuid4()),
            "student_name": student_name,
            "course": course,
            "hash": hash_value,
            "qr_code": qr_path,
            "verification_count": 0,
            "verification_logs": [],
            "upload_date": str(datetime.now(timezone.utc))
        }

        result = collection.insert_one(cert)
        cert["_id"] = str(result.inserted_id)

        return jsonify(cert), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================= VERIFY FILE =================
@app.route("/verify", methods=["POST"])
def verify():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        data = file.read()

        hash_value = generate_hash(data)

        cert = collection.find_one_and_update(
            {"hash": hash_value},
            {
                "$inc": {"verification_count": 1},
                "$push": {
                    "verification_logs": {
                        "date": str(datetime.now(timezone.utc)),
                        "ip": request.remote_addr
                    }
                }
            },
            return_document=ReturnDocument.AFTER
        )

        if cert:
            cert["_id"] = str(cert["_id"])
            return jsonify({"valid": True, "certificate": cert})

        return jsonify({"valid": False})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================= VERIFY QR =================
@app.route("/verify-hash", methods=["POST"])
def verify_hash():
    try:
        data = request.get_json()

        if not data or "hash" not in data:
            return jsonify({"error": "Hash missing"}), 400

        hash_value = data["hash"]

        cert = collection.find_one_and_update(
            {"hash": hash_value},
            {
                "$inc": {"verification_count": 1},
                "$push": {
                    "verification_logs": {
                        "date": str(datetime.now(timezone.utc)),
                        "ip": request.remote_addr
                    }
                }
            },
            return_document=ReturnDocument.AFTER
        )

        if cert:
            cert["_id"] = str(cert["_id"])
            return jsonify({"valid": True, "certificate": cert})

        return jsonify({"valid": False})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================= SERVE QR =================
@app.route('/qr_codes/<path:filename>')
def serve_qr_code(filename):
    return send_from_directory('qr_codes', filename)


# ================= GET ALL =================
@app.route("/certificates", methods=["GET"])
def certificates():
    try:
        docs = []
        for doc in collection.find():
            doc["_id"] = str(doc["_id"])
            docs.append(doc)

        return jsonify(docs)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)