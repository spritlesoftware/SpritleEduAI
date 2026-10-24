import logging, os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper(), force=True,
                    format="%(asctime)s %(levelname)-5s %(name)-14s | %(message)s", datefmt="%H:%M:%S")
for n in ("httpx", "httpcore", "google_genai", "google.adk", "chromadb", "urllib3", "PIL", "grpc", "asyncio", "hpack", "watchfiles", "multipart", "gtts"):
    logging.getLogger(n).setLevel(logging.WARNING)


def get(name):
    return logging.getLogger(f"edupilot.{name}")
