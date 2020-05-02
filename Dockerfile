FROM python:3.8-alpine
WORKDIR /app
ADD ./requirements.txt .
RUN pip install -r requirements.txt
ADD . /app
CMD ["/usr/local/bin/python", "/app/exporter.py"]
