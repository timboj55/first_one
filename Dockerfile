FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY lead_agent ./lead_agent
COPY agent_config.json .
ENV LEAD_AGENT_DB=/data/lead_agent.sqlite3 PORT=8080
VOLUME ["/data"]
EXPOSE 8080
CMD ["python", "-m", "lead_agent", "serve"]
