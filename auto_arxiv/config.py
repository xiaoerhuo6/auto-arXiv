"""Configuration loader for auto-arXiv.

Priority: environment variables > config.yaml > defaults.
When running in CI (GitHub Actions), config.yaml is absent;
all config must come from env vars.
"""
import os
from pathlib import Path
from typing import List

import yaml


class Config:
    """Flat config object. Prefers env vars, falls back to config.yaml + defaults."""

    DEFAULTS = {
        "llm_provider": "deepseek",
        "llm_model": "deepseek-chat",
        "llm_base_url": "https://api.deepseek.com",
        "llm_max_tokens": 4096,
        "llm_temperature": 0.1,
        "email_smtp_server": "smtp.qq.com",
        "email_smtp_port": 465,
        "email_use_ssl": True,
        "wechat_provider": "serverchan",
        "max_papers_per_day": 200,
        "db_path": "data/arxiv.db",
        "report_dir": "reports",
        "log_irrelevant": False,
        "reading_list": "reports/reading_list.md",
    }

    def __init__(self, path: str = "config.yaml"):
        root = Path(__file__).resolve().parent.parent
        yaml_data = self._load_yaml(root / path)
        rp = yaml_data.get("research_profile", {}) if yaml_data else {}
        self.research_description: str = os.environ.get("ARXIV_RESEARCH_DESCRIPTION") or rp.get("description", "")
        self.research_keywords: List[str] = rp.get("keywords", []) if rp else []
        self.arxiv_categories: List[str] = self._resolve_categories(yaml_data.get("arxiv_categories", []) if yaml_data else [])
        llm = yaml_data.get("llm", {}) if yaml_data else {}
        self.llm_provider: str = os.environ.get("ARXIV_LLM_PROVIDER") or llm.get("provider", self.DEFAULTS["llm_provider"])
        self.llm_api_key: str = os.environ.get("ARXIV_LLM_API_KEY") or llm.get("api_key", "")
        self.llm_model: str = os.environ.get("ARXIV_LLM_MODEL") or llm.get("model", self.DEFAULTS["llm_model"])
        self.llm_base_url: str = os.environ.get("ARXIV_LLM_BASE_URL") or llm.get("base_url", self.DEFAULTS["llm_base_url"])
        self.llm_max_tokens: int = int(os.environ.get("ARXIV_LLM_MAX_TOKENS") or llm.get("max_tokens", self.DEFAULTS["llm_max_tokens"]))
        self.llm_temperature: float = float(os.environ.get("ARXIV_LLM_TEMPERATURE") or llm.get("temperature", self.DEFAULTS["llm_temperature"]))
        notif = yaml_data.get("notifications", {}) if yaml_data else {}
        email = notif.get("email", {}) if notif else {}
        self.email_enabled: bool = self._env_bool("ARXIV_EMAIL_ENABLED", email.get("enabled", False))
        self.email_smtp_server: str = os.environ.get("ARXIV_EMAIL_SMTP_SERVER") or email.get("smtp_server", self.DEFAULTS["email_smtp_server"])
        self.email_smtp_port: int = int(os.environ.get("ARXIV_EMAIL_SMTP_PORT") or email.get("smtp_port", self.DEFAULTS["email_smtp_port"]))
        self.email_use_ssl: bool = self._env_bool("ARXIV_EMAIL_USE_SSL", email.get("use_ssl", self.DEFAULTS["email_use_ssl"]))
        self.email_sender: str = os.environ.get("ARXIV_EMAIL_SENDER") or email.get("sender", "")
        self.email_password: str = os.environ.get("ARXIV_EMAIL_PASSWORD") or email.get("password", "")
        self.email_receiver: str = os.environ.get("ARXIV_EMAIL_RECEIVER") or email.get("receiver", "")
        wechat = notif.get("wechat", {}) if notif else {}
        self.wechat_enabled: bool = self._env_bool("ARXIV_WECHAT_ENABLED", wechat.get("enabled", False))
        self.wechat_provider: str = os.environ.get("ARXIV_WECHAT_PROVIDER") or wechat.get("provider", self.DEFAULTS["wechat_provider"])
        self.wechat_send_key: str = os.environ.get("ARXIV_WECHAT_SENDKEY") or wechat.get("send_key", "")
        s = yaml_data.get("settings", {}) if yaml_data else {}
        self.max_papers_per_day: int = int(os.environ.get("ARXIV_MAX_PAPERS") or s.get("max_papers_per_day", self.DEFAULTS["max_papers_per_day"]))
        self.db_path: str = str(root / (os.environ.get("ARXIV_DB_PATH") or s.get("db_path", self.DEFAULTS["db_path"])))
        self.report_dir: str = str(root / (os.environ.get("ARXIV_REPORT_DIR") or s.get("report_dir", self.DEFAULTS["report_dir"])))
        self.log_irrelevant: bool = self._env_bool("ARXIV_LOG_IRRELEVANT", s.get("log_irrelevant", self.DEFAULTS["log_irrelevant"]))
        self.reading_list: str = str(root / (os.environ.get("ARXIV_READING_LIST") or s.get("reading_list", self.DEFAULTS["reading_list"])))

    @staticmethod
    def _env_bool(name: str, default: bool = False) -> bool:
        val = os.environ.get(name)
        if val is None:
            return default
        return val.strip().lower() in ("1", "true", "yes", "on")

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            print(f"[Warning] Failed to load config.yaml: {e}. Falling back to env vars.")
            return {}

    @classmethod
    def _resolve_categories(cls, yaml_categories: List[str]) -> List[str]:
        env_cats = os.environ.get("ARXIV_CATEGORIES")
        if env_cats:
            cats = [c.strip() for c in env_cats.split(",") if c.strip()]
            if cats:
                return cats
        return [c for c in yaml_categories if c]

    def validate(self):
        errors = []
        if not self.research_description:
            errors.append("研究方向描述未设置（请填写 config.yaml 或设 ARXIV_RESEARCH_DESCRIPTION）")
        if not self.arxiv_categories:
            errors.append("arxiv_categories: 至少需要一个 arXiv 分类")
        if not self.llm_api_key:
            errors.append("llm.api_key: 请填写 API Key，或设置环境变量 ARXIV_LLM_API_KEY")
        if self.email_enabled and not self.email_password:
            errors.append("email.password: 邮箱已启用但未填写密码，或设置 ARXIV_EMAIL_PASSWORD")
        if self.email_enabled and not self.email_sender:
            errors.append("email.sender: 邮箱已启用但未填写发件人")
        if self.email_enabled and not self.email_receiver:
            errors.append("email.receiver: 邮箱已启用但未填写收件人")
        return errors
