FROM python:3.12-alpine

WORKDIR /app

COPY seed.py requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "seed.py"]
