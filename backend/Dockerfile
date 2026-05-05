FROM python:3.10

WORKDIR /app

# 🔥 cache optimization
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

# 🔥 copy rest code
COPY . .

# QR folder
RUN mkdir -p /app/qr_codes

EXPOSE 5001

CMD ["python", "app.py"]