FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Install dependencies BEFORE copying the app code so these layers cache and are
# reused on a code-only deploy (the common case). Only a change to toolbox/ or the
# requirements file busts them; a change to a .py under skills/campaign does not.
COPY toolbox/ /app/toolbox/
RUN pip install --no-cache-dir -e toolbox/
COPY skills/campaign/wizard/requirements.txt /app/skills/campaign/wizard/requirements.txt
RUN pip install --no-cache-dir -r skills/campaign/wizard/requirements.txt

# App code last: it changes every deploy but triggers no dependency reinstall.
COPY . /app/

# Entry point starts the Slack campaign wizard (slack_wiz service).
CMD ["python", "-m", "skills.campaign.wizard.launch"]
