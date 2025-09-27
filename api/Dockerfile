FROM python:3.9

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir --upgrade fastapi[standard] psycopg

EXPOSE 80

CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "80"]