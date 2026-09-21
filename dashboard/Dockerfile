FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Dashboard requirements (superset of data-science)
COPY data-science/requirements.txt /tmp/ds-requirements.txt
RUN pip install --no-cache-dir streamlit folium -r /tmp/ds-requirements.txt

COPY dashboard/ /app/dashboard/
COPY data-science/ /app/data-science/

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
