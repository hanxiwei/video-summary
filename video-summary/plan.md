根据你提供的项目现状分析，你的 **视频摘要工具** 已经完成了从下载、转写到 AI 总结的完整 MVP 链路，代码模块化良好，测试覆盖充分。

接下来，如果你想制作一个 **和上面对话里“Harness 工程”完全一致的项目**，目标就不是重复实现这个 demo，而是：  
**把这个 demo 升级成一个“由 Harness 方法驱动的、可持续维护、可扩展、高质量的商业级项目”**，并且可以复现文档中提到的“万能视频下载总结器”的全部亮点（包括 SEO、国际支付、多文件下载、并行任务等）。

下面是一份 **项目计划**，分为 **5 个里程碑**，每一步都对应 Harness 工程的一个核心实践。你可以按顺序执行，也可以直接跳过已完成的步骤。

---

## 里程碑 0：项目基线确认（已完成 ✅）

- [x] 视频下载（yt-dlp + 后台任务）
- [x] 音频提取（ffmpeg）+ Whisper 转写
- [x] AI 摘要生成（gpt-4o-mini，长文本分段总结）
- [x] 前端界面（Jinja2 + HTMX + Tailwind）
- [x] 自动化测试（pytest，22 个通过）

**你现在处于**：功能可用，但缺少 Harness 工程的结构化环境（规则、护栏、反馈闭环、扩展能力）。

---

## 里程碑 1：搭建 Harness 工作环境（上下文架构 + 护栏）

### 目标

让 AI 和你在后续开发中有清晰的“宪章”，防止代码混乱、遗留技术债。

### 具体任务

1. **编写 `AGENTS.md` 文件**（项目根目录）  
   内容参考上面的模板，但根据你的项目定制：

   ```markdown
   # 项目：Video Summary（视频摘要工具）

   - 技术栈：Python 3.11+，FastAPI，SQLAlchemy async，aiosqlite，OpenAI API
   - 目录结构：app/ (main, api, services, models, templates, static)，docs/，tests/
   - 代码规范：所有异步函数需加 `async def`；每个 service 必须有类型注解；禁止在视图层直接调用数据库
   - 任务拆分原则：每个功能点单独一个分支，使用 `docs/plans/` 下的计划文件
   - 依赖外部服务：yt-dlp、ffmpeg、OpenAI（Whisper + Chat）
   - 相关文档：见 `docs/architecture.md`，`docs/api.md`
   ```

2. **添加架构护栏**（参考文档“架构护栏”一节）
   - 写一个自定义 `lint-architecture.py` 脚本，检查：
     - `main.py` 不能直接导入 `services/whisper.py`
     - `api/v1/*` 内不能包含数据库模型定义
     - 新增的 service 必须被 `__init__.py` 导出
   - 集成到 `pyproject.toml` 的 `[tool.pytest.ini_options]` 或 pre-commit hook。

3. **建立 Git 存档点规范**
   - 每完成一个功能（或修复一个 bug）后，强制 `git commit -m "feat: xxx"`。
   - 使用 `git tag` 标记每个里程碑（例如 `v0.1-download`, `v0.2-whisper`）。

---

## 里程碑 2：增强执行能力（MCP + Skills）

### 目标

让 AI 能自动查文档、抓取网页、运行浏览器测试，减少人工介入。

### 具体任务

1. **配置 MCP（以 Cursor 为例）**
   - 启用 `firecrawl` MCP：让 AI 能够抓取 yt-dlp 最新参数文档。
   - 启用 `context7` MCP：自动获取 OpenAI API 最新更新。

2. **开发/导入 Agent Skills**
   - 利用 `superpowers` 框架中的 `web-testing` skill，让 AI 自动打开浏览器测试下载流程。
   - 写一个 `transcript-quality` skill：让 AI 对比不同 Whisper 参数下的转写质量，自动推荐参数。

3. **实现 AI 自主修复循环**
   - 在 `tests/` 下增加一个 `test_ai_recovery.py`：让 AI 故意引入一个已知错误（如音频切片参数错误），然后自己读取日志并尝试修复，最后验证通过。
   - 将这个流程集成到 CI（GitHub Actions）中作为可选步骤。

---

## 里程碑 3：功能扩展（任务编排 + 反馈机制）

### 目标

添加文档中“万能视频下载总结器”的额外功能，同时保持代码整洁。

### 计划新增功能（按优先级）

| 功能                                | Harness 实践                 | 实现方式提示                                                                    |
| ----------------------------------- | ---------------------------- | ------------------------------------------------------------------------------- |
| **多格式字幕下载（.srt/.vtt）**     | 拆分小任务，先出方案         | 在 `services/downloader.py` 中增加提取自动生成字幕的逻辑；前端增加下载按钮      |
| **B站防盗链处理（403 错误）**       | AI 自己查文档 + 人工纠偏     | 让 AI 分析 403 原因，增加 `--add-header "Referer: ..."` 参数                    |
| **SEO 优化**                        | 复用 SEO audit skill         | 使用文档中提到的 `SEO audit` skill，生成 `sitemap.xml`、`robots.txt`、meta 标签 |
| **Stripe 国际支付（限制免费次数）** | 任务编排，先做支付接口再挂载 | 新增 `services/payment.py`，集成 Stripe Checkout；在首页显示剩余次数            |
| **并行任务（多视频同时下载）**      | 使用 sub-agent               | 将当前 `BackgroundTasks` 换成 Celery 或 `asyncio.gather`，控制最大并发数        |

**每个功能开发流程**：

1. 新建一个 `docs/plans/feature-xxx.md`，写出详细方案。
2. 新开一个 AI 对话窗口，把 `AGENTS.md` 和方案文档贴进去。
3. 让 AI 按任务列表生成代码（一次只做一个小点）。
4. 运行测试 → AI 自修复 → 人工验收 → 提交代码 + 更新文档。

---

## 里程碑 4：部署与监控（反馈闭环 + 护栏外延）

### 目标

让项目真正上线可用，并具备自动恢复能力。

### 具体任务

1. **部署到云服务器（如 阿里云/腾讯云/Lightsail）**
   - 使用 Docker 打包：写 `Dockerfile`（Python + ffmpeg + yt-dlp）。
   - 配置 Nginx 反向代理 + HTTPS（Let's Encrypt）。
   - 设置 systemd 或 supervisor 保持进程常驻。

2. **添加健康检查与自动重启**
   - FastAPI 加 `/health` 端点，检查数据库连接和 OpenAI API key 有效性。
   - 部署后配置一个外部监控（如 UptimeRobot），失败时发送通知。

3. **日志与报警**
   - 使用 `loguru` 替代 print，按天分割。
   - 集成 Sentry 或自建 webhook：当下载/转写失败次数超过阈值时，自动向 Discord/钉钉发送告警。

4. **用户数据隔离**（可跳过 MVP 阶段，但要留接口）
   - 后续加入简单的 JWT 用户系统，每个用户独立任务队列。

---

## 里程碑 5：持续迭代与 Harness 进化

### 目标

形成“AI + 规则 + 反馈”的闭环，让项目越改越好。

### 周期性动作（每周/每次迭代）

1. **代码健康扫描**
   - 运行 `alias lint-all="pylint app/ && python scripts/check-arch.py"`
   - 让 AI 分析 lint 报告并生成修复计划。

2. **技术债回收**
   - 参照 OpenAI 的“垃圾回收”机制：让 AI 每周扫描代码库，找出重复代码、未使用函数、过时注释，自动提交 PR。

3. **文档同步**
   - 每次合并 PR 后，自动运行一个脚本，让 AI 对比代码变更和 `docs/` 下的文档，如有不一致，由 AI 更新文档并提交。

4. **回归测试增强**
   - 记录线上 bug，将其还原为新的 pytest 用例（由 AI 辅助编写），确保不会再犯。
