"""WeChat notification via ServerChan or PushPlus."""
import requests
from typing import List, Dict

from ..config import Config


def send_wechat(config: Config, title: str, content: str) -> bool:
    """Send a WeChat notification. Returns True on success."""
    if not config.wechat_enabled:
        return False

    if config.wechat_provider == "serverchan":
        url = f"https://sctapi.ftqq.com/{config.wechat_send_key}.send"
        payload = {"title": title, "desp": content}
        try:
            resp = requests.post(url, data=payload, timeout=15)
            data = resp.json()
            if data.get("code") == 0:
                return True
            else:
                print(f"[WeChat] ServerChan error: {data}")
                return False
        except Exception as e:
            print(f"[WeChat] ServerChan request failed: {e}")
            return False

    elif config.wechat_provider == "pushplus":
        url = "https://www.pushplus.plus/send"
        payload = {
            "token": config.wechat_send_key,
            "title": title,
            "content": content,
            "template": "markdown",
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            data = resp.json()
            if data.get("code") == 200:
                return True
            else:
                print(f"[WeChat] PushPlus error: {data}")
                return False
        except Exception as e:
            print(f"[WeChat] PushPlus request failed: {e}")
            return False

    else:
        print(f"[WeChat] Unknown provider: {config.wechat_provider}")
        return False


def build_wechat_message(papers: List[Dict], category_label: str) -> str:
    """Build a Markdown message for WeChat push."""
    lines = [f"## arXiv 论文推送 - {category_label}", ""]
    for p in papers:
        lines.append(f"### [{p['title']}]({p['link']})")
        lines.append(f"_{p['authors']}_")
        lines.append("")
        lines.append(p["summary_zh"])
        lines.append("")
    return "\n".join(lines)
