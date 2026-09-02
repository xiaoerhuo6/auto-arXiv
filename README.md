# auto-arXiv

> 自动爬取 arXiv 每天新论文，用 LLM 按研究方向分类，推送通知到邮箱/微信。

自动从 arXiv 获取你感兴趣领域的每日新论文，通过 LLM 分析论文与你的研究方向的契合程度，分为四类处理，并通过邮箱或微信推送结果。

## 分类体系

| 分类 | 含义 | 处理方式 |
|------|------|----------|
| 1 | 与我无关 | 丢弃，不通知 |
| 2 | 相关但不重要 | 摘要总结 → 推送通知 |
| 3 | 强相关且值得研究 | 摘要总结 → 推送通知 → 加入待阅读清单 |
| 4 | 不相关但很重要 | 摘要总结 → 推送通知 → 说明潜在联系 |

## 目录结构

`
auto-arXiv/
├── config.yaml               # 用户配置文件（已加入 .gitignore，不上传）
├── requirements.txt          # Python 依赖
├── .gitignore
├── README.md
├── auto_arxiv/               # 核心代码
│   ├── __init__.py
│   ├── config.py             # 配置加载器
│   ├── arxiv_fetcher.py      # arXiv API 爬取（按优先级顺序抓取）
│   ├── classifier.py         # LLM 分类 + 摘要生成
│   ├── storage.py            # SQLite 数据库
│   ├── main.py               # 主调度流程
│   └── notifiers/            # 推送模块
│       ├── __init__.py
│       ├── email_notifier.py # 邮箱推送（SMTP）
│       └── wechat_notifier.py# 微信推送（Server酱 / PushPlus）
├── reports/                  # 生成的日报（本地，不入库）
│   ├── report_YYYY-MM-DD.md
│   └── reading_list.md       # 待阅读清单（累积）
└── data/                     # SQLite 数据库（本地，不入库）
    └── arxiv.db
`

## 快速开始

### 1. 安装依赖

`ash
pip install -r requirements.txt
`

### 2. 配置

复制 config.yaml.example 为 config.yaml，然后编辑：

`yaml
research_profile:
  description: |
    用自然语言描述你的研究方向，越详细分类越准确。
    例如：我研究宇宙学，特别是暗能量、哈勃常数张力和
    大尺度结构。也关注天文统计方法和机器学习在天文中的应用。

arxiv_categories:
  - astro-ph.CO    # 优先分类，按此顺序抓取
  - astro-ph.IM
  - cs.LG

llm:
  api_key: "sk-your-api-key"   # 或设环境变量 ARXIV_LLM_API_KEY
  model: "deepseek-chat"

notifications:
  email:
    enabled: true
    smtp_server: "smtp.qq.com"
    smtp_port: 465
    use_ssl: true
    sender: "your@email.com"
    password: "your-smtp-password"
    receiver: "your@email.com"
  wechat:
    enabled: false
    provider: "serverchan"  # serverchan 或 pushplus
    send_key: "your-key"
`

> **安全提示**：config.yaml 包含你的 API Key 和邮箱密码，已加入 .gitignore，不会上传到 GitHub。

### 3. 运行

`ash
python -m auto_arxiv.main
`

### 4. 定时运行（Windows 任务计划程序）

创建每天定时任务：

- 程序：你的 python.exe 路径
- 参数：-m auto_arxiv.main
- 起始位置：你的项目路径
- 触发器：每天 09:00（arXiv 新论文通常在北京时间上午更新）

## 优先级抓取

论文按 config.yaml 中 rxiv_categories 列表的顺序逐个分类抓取。排在前面的分类优先填满，确保你最重要的研究方向不会被投稿量大的分类淹没。例如 stro-ph.CO 即使每天投稿量不如 cs.LG，也会优先被获取。

## 推送方式

### 邮箱
支持任何 SMTP 邮箱服务。以 QQ 邮箱为例：
1. 登录 QQ 邮箱 → 设置 → 账户 → 开启 POP3/SMTP 服务
2. 生成授权码，填入 config.yaml 的 mail.password 字段

### 微信
- **Server酱**：[https://sct.ftqq.com](https://sct.ftqq.com) — 注册获取 SendKey
- **PushPlus**：[https://www.pushplus.plus](https://www.pushplus.plus) — 注册获取 Token

## 输出

- **每日报告**：
eports/report_YYYY-MM-DD.md（Markdown 格式，按分类组织）
- **待阅读清单**：
eports/reading_list.md（持续累积所有分类 3 的论文）
- **邮箱推送**：HTML 格式的论文摘要日报
- **微信推送**：Markdown 格式的论文摘要

## 安全

- config.yaml 包含敏感信息（API Key、邮箱密码），已配置 .gitignore 防止误上传
- 建议优先使用**环境变量**替代配置文件中的明文密钥：
  - ARXIV_LLM_API_KEY — LLM API Key
  - ARXIV_EMAIL_PASSWORD — 邮箱 SMTP 密码

## 依赖

- Python 3.10+
- requests
- pyyaml
- openai


## 云部署：GitHub Actions 定时运行（推荐）

无需本地电脑开机，每天自动抓取论文并推送邮件。

### 1. 配置 GitHub Secrets

在你的 GitHub 仓库 → **Settings → Secrets and variables → Actions**，添加以下 Secrets：

| Secret 名称 | 说明 |
|------------|------|
| `ARXIV_LLM_API_KEY` | DeepSeek API Key |
| `ARXIV_LLM_MODEL` | 模型名，如 `DeepSeek-V4-Flash-0731` |
| `ARXIV_LLM_BASE_URL` | API 地址，如 `https://llmapi.paratera.com` |
| `ARXIV_RESEARCH_DESCRIPTION` | 研究方向描述（全部内容） |
| `ARXIV_CATEGORIES` | 分类列表，逗号分隔，如 `astro-ph.CO,astro-ph.IM,cs.LG` |
| `ARXIV_EMAIL_ENABLED` | `true` |
| `ARXIV_EMAIL_SMTP_SERVER` | SMTP 服务器，如 `mails.tsinghua.edu.cn` |
| `ARXIV_EMAIL_SMTP_PORT` | `465` |
| `ARXIV_EMAIL_USE_SSL` | `true` |
| `ARXIV_EMAIL_SENDER` | 发件人邮箱 |
| `ARXIV_EMAIL_PASSWORD` | 邮箱密码/客户端专用密码 |
| `ARXIV_EMAIL_RECEIVER` | 收件人邮箱 |

### 2. 推送代码到 GitHub

```bash
git add .
git commit -m "Add GitHub Actions workflow"
git push
```

### 3. 验证

推送后，GitHub 仓库的 **Actions** 标签页会自动触发一次运行。之后每天北京时间 10:00 自动执行。

你也可以在 Actions 页面手动点击 **Run workflow** 立即测试。

> **注意**：GitHub 免费套餐每月 2000 分钟运行时长，本项目每天跑一次约 5 分钟，一个月仅需 150 分钟，完全够用。



## 反馈机制：让分类越来越准

每天推送的论文如果分类不准，可以通过反馈功能让 LLM 学习你的偏好。

### 反馈审核

`ash
python -m auto_arxiv.feedback review
`

交互式命令，分两步：
1. **浏览分类 2**（相关但不重要）的论文，可将其改为「与我无关」
2. **抽样分类 1**（与我无关）的论文，可将其改为「相关但不重要」

### 优化研究方向描述

积累足够反馈后（建议 5 条以上）：

`ash
python -m auto_arxiv.feedback refine
`

LLM 会分析你的改判记录，识别分类不准的模式，生成优化后的研究方向描述草案，经你确认后自动更新 config.yaml。

### 手动更新

`ash
python -m auto_arxiv.feedback apply
`

如果你想手动修改研究方向描述并保存版本历史。

### 版本历史

所有研究方向描述的变更都会记录在 prompt_history 数据库表中，可追溯。

## License

MIT
