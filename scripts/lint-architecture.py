#!/usr/bin/env python3
"""架构护栏检查脚本 —— 确保代码不违反项目架构规则。

检查项：
1. main.py 不得直接导入 service 层模块（download/downloader, audio/*, summary/*）
2. 视图层（router.py）不得包含 ORM 模型定义或直接调用外部 CLI（ffmpeg/yt-dlp）
3. 每个子包的 __init__.py 必须导出其公开类
4. 数据库模型只能在 db/models.py 中定义

用法:  python scripts/lint-architecture.py
"""

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "app"

# 模块分类
SERVICE_MODULES = {
    "app.download.downloader",
    "app.audio.extractor",
    "app.audio.transcriber",
    "app.summary.summarizer",
}

EXTERNAL_CALLS = {"ffmpeg", "yt_dlp", "youtube_dl"}

PUBLIC_CLASSES = {
    "app.download": ["VideoDownloader", "TaskCreateRequest", "TaskResponse", "TaskListResponse"],
    "app.audio": ["AudioExtractor", "WhisperTranscriber"],
    "app.summary": ["VideoSummarizer"],
    "app.tasks": ["SummaryPipeline"],
    "app.db": ["VideoTask", "Base", "engine", "async_session", "get_db"],
}

ERRORS: list[str] = []
OK_COUNT = 0


def find_imports(tree: ast.AST) -> list[str]:
    """提取模块中所有 import 的目标模块名。"""
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def find_class_defs(tree: ast.AST) -> list[str]:
    """提取模块中定义的类名。"""
    return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def find_function_calls(tree: ast.AST) -> list[str]:
    """提取模块中直接的函数/类调用（检查 create_subprocess_exec 等）。"""
    calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
    return calls


def check_file(filepath: Path, rules: list[str]) -> None:
    global OK_COUNT
    try:
        source = filepath.read_text(encoding="utf-8")
    except Exception:
        return

    try:
        tree = ast.parse(source)
    except SyntaxError:
        ERRORS.append(f"[PARSE ERROR] {filepath.relative_to(PROJECT_ROOT)}")
        return

    imports = find_imports(tree)
    class_defs = find_class_defs(tree)
    calls = find_function_calls(tree)
    rel = filepath.relative_to(PROJECT_ROOT)

    # --- 规则 1: main.py 不能直接导入 service 模块 ---
    if "rule1" in rules and filepath.name == "main.py":
        for imp in imports:
            if imp in SERVICE_MODULES:
                ERRORS.append(
                    f"[RULE 1] {rel}: main.py 直接导入了 service 模块 '{imp}'，"
                    f"应通过 router 层间接调用"
                )

    # --- 规则 2: router.py 不能定义 ORM 模型，不能直接调用外部 CLI ---
    if "rule2" in rules and filepath.name == "router.py":
        if class_defs:
            # 检查是否定义了类似 ORM 模型的类（有 __tablename__ 或继承 Base）
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == "Base":
                            ERRORS.append(
                                f"[RULE 2] {rel}: router.py 定义了 ORM 模型 "
                                f"'{node.name}'，应移到 db/models.py"
                            )
        for call in calls:
            if any(ext in call.lower() for ext in EXTERNAL_CALLS):
                ERRORS.append(
                    f"[RULE 2] {rel}: router.py 直接调用了外部工具 '{call}'，"
                    f"应通过 service 层封装"
                )

    # --- 规则 3: __init__.py 需要导出公开类 ---
    if "rule3" in rules and filepath.name == "__init__.py":
        pkg = str(filepath.parent.relative_to(PROJECT_ROOT)).replace("/", ".").replace("\\", ".")
        pkg_module = pkg.replace("app.", "")
        if pkg_module in PUBLIC_CLASSES:
            expected = PUBLIC_CLASSES[pkg_module]
            init_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        init_names.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        init_names.add(alias.name)

            for cls in expected:
                if cls not in init_names:
                    # Check if __all__ contains it
                    found_in_all = False
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name) and target.id == "__all__":
                                    if isinstance(node.value, (ast.List, ast.Tuple)):
                                        for elt in node.value.elts:
                                            if isinstance(elt, ast.Constant) and elt.value == cls:
                                                found_in_all = True
                    if not found_in_all:
                        ERRORS.append(
                            f"[RULE 3] {rel}: __init__.py 未导出 '{cls}'，"
                            f"请在 __init__.py 中显式导入或加入 __all__"
                        )

    # --- 规则 4: ORM 模型只能在 db/models.py 定义 ---
    if "rule4" in rules and filepath.name != "models.py":
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id in ("Base", "DeclarativeBase"):
                        ERRORS.append(
                            f"[RULE 4] {rel}: 在非 db/models.py 文件中定义了 ORM 模型 "
                            f"'{node.name}'，所有模型必须定义在 app/db/models.py"
                        )

    OK_COUNT += 1


def main() -> int:
    python_files = list(APP_DIR.rglob("*.py"))
    if not python_files:
        print("错误：未找到 Python 文件")
        return 1

    for f in python_files:
        check_file(f, rules=["rule1", "rule2", "rule3", "rule4"])

    if ERRORS:
        print(f"\n[FAIL] Found {len(ERRORS)} architecture violations:\n")
        for err in ERRORS:
            print(f"  {err}")
        print(f"\nScanned {OK_COUNT} files, {len(ERRORS)} violations.")
        return 1
    else:
        print(f"\n[PASS] All {OK_COUNT} files pass architecture checks.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
