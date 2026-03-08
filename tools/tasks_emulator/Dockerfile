FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir flask requests

COPY emulator.py .

EXPOSE 8123

CMD ["python", "emulator.py"]
