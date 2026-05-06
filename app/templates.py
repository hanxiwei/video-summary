from pathlib import Path

from fastapi.templating import Jinja2Templates

templates_dir = Path(__file__).parent / "web" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
