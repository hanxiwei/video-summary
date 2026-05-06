import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{PROJECT_ROOT}/video_summary.db")
DOWNLOADS_DIR: Path = Path(os.getenv("DOWNLOADS_DIR", str(PROJECT_ROOT / "downloads")))

DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
