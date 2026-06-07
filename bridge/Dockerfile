FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
ENV GUALALOOM_API_URL="https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com"
EXPOSE 8080
CMD ["python", "server.py", "--transport", "sse", "--port", "8080"]
