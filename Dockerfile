FROM python:3.13-slim

WORKDIR /app

COPY . /app

EXPOSE 8765

CMD ["python3", "main.py", "--serve", "--host", "0.0.0.0", "--port", "8765"]
