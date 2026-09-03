"""LLM-based paper classifier and summarizer."""
import json
import re
from typing import Dict, Any
from openai import OpenAI

from .config import Config


SYSTEM_PROMPT = """你是一个研究论文分析助手。给定用户的研究兴趣描述和一批论文，请逐篇判断每篇论文与用户研究的关联程度。

分类标准：
1 = 与我无关：论文内容与用户研究方向没有任何交集
2 = 相关但不重要：在宽泛领域上有相关性，但并非核心关注点，不值得深入阅读
3 = 强相关且值得研究：论文与用户的研究方向高度契合，值得仔细阅读甚至跟进
4 = 不相关但很重要：论文不在用户的研究方向上，但属于该领域的重要突破或影响广泛的成果

请严格按以下 JSON 对象格式输出，results 数组顺序与论文输入顺序一致：
{
  "results": [
    {
      "category": 3,
      "summary_zh": "用中文写一段100-200字的摘要总结",
      "relevance_reason": "简要说明原因（可选，仅用于4类时说明潜在联系）"
    }
  ]
}"""

BATCH_SIZE = 10


def classify_papers_batch(config, papers):
    """Classify multiple papers in one API call."""
    from openai import OpenAI
    client = OpenAI(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
    )
    results = []
    total = (len(papers) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(papers), BATCH_SIZE):
        batch = papers[i:i + BATCH_SIZE]
        bn = i // BATCH_SIZE + 1
        parts = []
        for j, p in enumerate(batch):
            parts.append('[论文 ' + str(j + 1) + ']\n标题：' + p['title'] + '\n摘要：' + p['abstract'])
        paper_list = '\n---\n'.join(parts)
        user_prompt = '用户的研究兴趣：\n' + config.research_description + '\n\n以下是一批论文，请逐篇判断关联程度：\n\n' + paper_list
        resp = client.chat.completions.create(
            model=config.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=config.llm_max_tokens * 3,
            temperature=config.llm_temperature,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        try:
            data = json.loads(content)
            br = data.get("results", data if isinstance(data, list) else [])
        except json.JSONDecodeError:
            m = re.search(r'\[.*?\]', content, re.DOTALL)
            if m:
                try:
                    br = json.loads(m.group())
                except:
                    br = [{"category": 1, "summary_zh": "解析失败", "relevance_reason": ""}] * len(batch)
            else:
                br = [{"category": 1, "summary_zh": "解析失败", "relevance_reason": ""}] * len(batch)
        if isinstance(br, dict):
            br = [br]
        while len(br) < len(batch):
            br.append({"category": 1, "summary_zh": "解析失败", "relevance_reason": ""})
        br = br[:len(batch)]
        for r in br:
            r["category"] = int(r.get("category", 1))
            r.setdefault("summary_zh", "")
            r.setdefault("relevance_reason", "")
        results.extend(br)
        print(f"      Batch {bn}/{total} done ({len(batch)} papers)")
    return results


def classify_paper(config, title, abstract):
    """Classify a single paper (uses batch internally)."""
    return classify_papers_batch(config, [{"title": title, "abstract": abstract}])[0]
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
