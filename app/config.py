import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent

# DeepSeek Chat API（AI 摘要用）
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# OpenAI Whisper API（语音转写用）
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{PROJECT_ROOT}/video_summary.db")
DOWNLOADS_DIR: Path = Path(os.getenv("DOWNLOADS_DIR", str(PROJECT_ROOT / "downloads")))

DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
