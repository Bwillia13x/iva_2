import os
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

class Settings(BaseModel):
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY",""))
    openai_model_code: str = os.getenv("OPENAI_MODEL_CODE","gpt5-codex")
    openai_model_reasoning: str = os.getenv("OPENAI_MODEL_REASONING","gpt-4.1")
    embedding_model: str = os.getenv("EMBEDDING_MODEL","text-embedding-3-large")

    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL","")
    slack_bot_token: str = os.getenv("SLACK_BOT_TOKEN","")
    slack_channel: str = os.getenv("SLACK_CHANNEL","#iva-truth")

    postgres_dsn: str = os.getenv("POSTGRES_DSN","")
    use_postgres: bool = os.getenv("USE_POSTGRES","false").lower()=="true"
    use_pgvector: bool = os.getenv("USE_PGVECTOR","false").lower()=="true"

    use_neo4j: bool = os.getenv("USE_NEO4J","false").lower()=="true"
    neo4j_uri: str = os.getenv("NEO4J_URI","")
    neo4j_user: str = os.getenv("NEO4J_USER","")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD","")

    bing_api_key: str = os.getenv("BING_API_KEY","")
    serpapi_key: str = os.getenv("SERPAPI_KEY","")

    user_agent: str = os.getenv("USER_AGENT","IvaTruthMeter/0.1")
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT","20"))

settings = Settings()
