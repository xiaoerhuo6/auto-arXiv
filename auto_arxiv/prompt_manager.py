"""Prompt manager: analyze misclassifications and generate refined prompts."""
from typing import List, Dict, Any
from openai import OpenAI

from .config import Config


ANALYSIS_PROMPT = """你是一个研究论文分类质量分析师。用户的研究兴趣描述和论文分类结果如下。

请分析这些被用户"改判"的论文，识别出当前分类 prompt 的不足：

1. 用户的真正兴趣点是什么？当前描述是否遗漏了某些重要方向？
2. 哪些论文被误分类为"无关"但实际上用户认为相关？为什么？
3. 哪些论文被误分类为"相关"但实际上用户认为无关？为什么？
4. 当前描述中有没有模糊或容易引起误导的表述？

请给出具体、可操作的分析结论。"""


REFINE_PROMPT = """你是一个研究兴趣描述优化专家。基于以下分析结论，生成一份优化后的研究方向描述。

要求：
1. 用中文写，与原有描述风格一致
2. 补充当前描述遗漏的重要方向
3. 澄清容易引起歧义的表述
4. 保持简洁准确，不要过于啰嗦
5. 只输出描述文本本身，不要输出其他内容"""


def analyze_misclassifications(config: Config, misclassified: List[Dict[str, Any]],
                               current_prompt: str) -> str:
    """Analyze misclassification patterns using LLM."""
    if not misclassified:
        return "暂无改判记录可供分析。"

    client = OpenAI(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
    )

    # Build the misclassified examples
    examples = []
    for m in misclassified[:20]:  # limit to 20 examples
        cat_labels = {1: "与我无关", 2: "相关但不重要", 3: "强相关", 4: "不相关但重要"}
        orig = cat_labels.get(m["original_category"], str(m["original_category"]))
        user = cat_labels.get(m["user_category"], str(m["user_category"]))
        examples.append(
            f"论文标题: {m['title']}\n"
            f"原分类: {orig} → 用户改判: {user}\n"
            f"摘要: {m['abstract'][:300]}\n"
        )

    examples_text = "\n---\n".join(examples)

    user_msg = f"""当前研究方向描述:
{current_prompt}

被改判的论文列表:
{examples_text}

请分析这些问题。"""

    resp = client.chat.completions.create(
        model=config.llm_model,
        messages=[
            {"role": "system", "content": ANALYSIS_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=config.llm_max_tokens,
        temperature=config.llm_temperature,
    )

    return resp.choices[0].message.content


def generate_refined_prompt(config: Config, analysis: str, current_prompt: str) -> str:
    """Generate a refined research description based on analysis."""
    client = OpenAI(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
    )

    user_msg = f"""当前研究方向描述:
{current_prompt}

分析结论:
{analysis}

请生成优化后的研究方向描述。"""

    resp = client.chat.completions.create(
        model=config.llm_model,
        messages=[
            {"role": "system", "content": REFINE_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=config.llm_max_tokens,
        temperature=config.llm_temperature,
    )

    return resp.choices[0].message.content
