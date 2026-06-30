import os

# Shared secrets for campaign execution (Claude planning, Gmail send, Hunter,
# Supabase). Read at import so a misconfigured deploy fails fast.
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_OAUTH_CLIENT_ID = os.environ["GOOGLE_OAUTH_CLIENT_ID"]
GOOGLE_OAUTH_CLIENT_SECRET = os.environ["GOOGLE_OAUTH_CLIENT_SECRET"]
HUNTER_API_KEY = os.environ["TOOLBOX_TOKEN_HUNTER"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SECRET_KEY = os.environ["SUPABASE_SECRET_KEY"]
