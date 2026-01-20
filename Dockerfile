FROM python:3.11-slim

WORKDIR /app

# Install token server dependencies only
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

# Copy only the token server
COPY token_server.py .

EXPOSE 10000

# Run the TOKEN SERVER
CMD ["uvicorn", "token_server:app", "--host", "0.0.0.0", "--port", "10000"]
