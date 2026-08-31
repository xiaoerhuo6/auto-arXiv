"""Configuration loader for auto-arXiv."""
import os
from pathlib import Path
from typing import List

import yaml


class Config:
    """Flat config object loaded from config.yaml."""

    def __init__(self, path: str = "config.yaml"):
        root = Path(__file__).resolve().parent.parent
        with open(root / path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        rp = raw.get("research_profile", {})
        self.research_description: str = rp.get("description", "")
        self.research_keywords: List[str] = rp.get("keywords", [])

        self.arxiv_categories: List[str] = raw.get("arxiv_categories", [])

        llm = raw.get("llm", {})
        self.llm_provider: str = llm.get("provider", "deepseek")
        self.llm_api_key: str = os.environ.get("ARXIV_LLM_API_KEY") or llm.get("api_key", "")
        self.llm_model: str = llm.get("model", "deepseek-chat")
        self.llm_base_url: str = llm.get("base_url", "https://api.deepseek.com")
        self.llm_max_tokens: int = llm.get("max_tokens", 1024)
        self.llm_temperature: float = llm.get("temperature", 0.1)

        notif = raw.get("notifications", {})
        email = notif.get("email", {})
        self.email_enabled: bool = email.get("enabled", False)
        self.email_smtp_server: str = email.get("smtp_server", "smtp.qq.com")
        self.email_smtp_port: int = email.get("smtp_port", 465)
        self.email_use_ssl: bool = email.get("use_ssl", True)
        self.email_sender: str = email.get("sender", "")
        self.email_password: str = os.environ.get("ARXIV_EMAIL_PASSWORD") or email.get("password", "")
        self.email_receiver: str = email.get("receiver", "")

        wechat = notif.get("wechat", {})
        self.wechat_enabled: bool = wechat.get("enabled", False)
        self.wechat_provider: str = wechat.get("provider", "serverchan")
        self.wechat_send_key: str = os.environ.get("ARXIV_WECHAT_SENDKEY") or wechat.get("send_key", "")

        s = raw.get("settings", {})
        self.max_papers_per_day: int = s.get("max_papers_per_day", 200)
        self.db_path: str = str(root / s.get("db_path", "data/arxiv.db"))
        self.report_dir: str = str(root / s.get("report_dir", "reports"))
        self.log_irrelevant: bool = s.get("log_irrelevant", False)
        self.reading_list: str = str(root / s.get("reading_list", "reports/reading_list.md"))

    def validate(self):
        errors = []
        if not self.research_description or self.research_description.startswith("在这里填写"):
            errors.append("research_profile.description: 请填写你的研究方向描述")
        if not self.arxiv_categories:
            errors.append("arxiv_categories: 至少需要一个 arXiv 分类")
        if not self.llm_api_key:
            errors.append("llm.api_key: 请填写 API Key，或设置环境变量 ARXIV_LLM_API_KEY")
        if self.email_enabled and not self.email_password:
            errors.append("email.password: 邮箱已启用但未填写密码/授权码")
        return errors
