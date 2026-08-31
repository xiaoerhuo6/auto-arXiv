"""LLM-based paper classifier and summarizer."""
import json
import re
from typing import Dict, Any
from openai import OpenAI

from .config import Config


SYSTEM_PROMPT = """你是一个研究论文分析助手。给定用户的研究兴趣描述和一篇论文的标题+摘要，
请按以下4类判断论文与用户研究的关联程度：

1 = 与我无关：论文内容与用户研究方向没有任何交集
2 = 相关但不重要：在宽泛领域上有相关性，但并非核心关注点，不值得深入阅读
3 = 强相关且值得研究：论文与用户的研究方向高度契合，值得仔细阅读甚至跟进
4 = 不相关但很重要：论文不在用户的研究方向上，但属于该领域的重要突破或影响广泛的成果

请严格按以下 JSON 格式输出（不要包含其他文字）：
{
  "category": 3,
  "summary_zh": "用中文写一段100-200字的摘要总结",
  "relevance_reason": "简要说明为什么归为此类（可选，仅用于4类时说明潜在联系）"
}"""


def classify_paper(config: Config, title: str, abstract: str) -> Dict[str, Any]:
    """Classify a single paper using LLM. Returns dict with category, summary, etc."""
    client = OpenAI(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
    )

    user_prompt = f"""用户的研究兴趣：
{config.research_description}

论文标题：{title}
论文摘要：{abstract}

请判断这篇论文与用户研究兴趣的关联程度。"""

    resp = client.chat.completions.create(
        model=config.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=config.llm_max_tokens,
        temperature=config.llm_temperature,
        response_format={"type": "json_object"},
    )

    content = resp.choices[0].message.content
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            result = {"category": 1, "summary_zh": "解析失败", "relevance_reason": ""}

    result["category"] = int(result.get("category", 1))
    return result
