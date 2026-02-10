"""
Langfuse tracing. Requires LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY.
Set LANGFUSE_BASE_URL to match your project region or you may get 401 invalid host:
  US: https://us.cloud.langfuse.com   EU: https://cloud.langfuse.com
"""

import os

from langfuse.langchain import CallbackHandler

# SDK uses LANGFUSE_BASE_URL; default to US cloud if unset to avoid 401 invalid host.
os.environ.setdefault("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")

langfuse_handler = None
_public = os.environ.get("LANGFUSE_PUBLIC_KEY")
_secret = os.environ.get("LANGFUSE_SECRET_KEY")

if _public and _secret:
    langfuse_handler = CallbackHandler()
