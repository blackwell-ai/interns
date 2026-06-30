FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY . /app/

RUN pip install --no-cache-dir -e toolbox/
RUN pip install --no-cache-dir -r skills/campaign/server/requirements.txt

# Entry point starts the Slack campaign wizard (slack_wiz service).
CMD ["python", "-m", "skills.campaign.server.launch"]
