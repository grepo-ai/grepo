import os
from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv


load_dotenv()


Langfuse(
    public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
    host="https://us.cloud.langfuse.com",
    timeout=60,
)


# Get the configured client instance
# langfuse = get_client()


# Initialize the Langfuse handler
langfuse_handler = CallbackHandler()
