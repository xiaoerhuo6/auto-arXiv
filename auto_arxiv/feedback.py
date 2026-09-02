"""Feedback module: review, refine, and apply prompt improvements."""
import sys
import os
import random
from datetime import datetime
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auto_arxiv.config import Config
from auto_arxiv.storage import Storage
from auto_arxiv.prompt_manager import analyze_misclassifications, generate_refined_prompt


CATEGORY_LABELS = {
    1: "与我无关",
    2: "相关但不重要",
    3: "强相关且值得研究",
    4: "不相关但很重要",
}


def cmd_review(config_path: str = "config.yaml"):
    """Interactive review: browse category-2 papers, then sample category-1."""
    config = Config(config_path)
    storage = Storage(config.db_path)

    print("=" * 60)
    print("反馈审核：第 1 步 - 浏览分类 2 论文")
    print("=" * 60)
    print("以下为今天分类为「相关但不重要」的论文。")
    print("请判断：如果也觉得不相关，输入 n 改为「与我无关」；否则直接回车跳过。")
    print()

    cat2_papers = [p for p in storage.get_papers_by_category(2) if p['processed_at'][:10]==__import__('datetime').datetime.now().strftime('%Y-%m-%d')]
    reviewed = 0
    for p in cat2_papers:
        print(f"--- {p['arxiv_id']} ---")
        print(f"标题: {p['title']}")
        print(f"摘要: {p['summary_zh'][:200]}")
        choice = input("> 保留(回车) / 改为无关(n): ").strip().lower()
        if choice == "n":
            storage.save_feedback(p["arxiv_id"], 2, 1)
            reviewed += 1
            print("  → 已记录：改为「与我无关」")
        print()

    print(f"第 1 步完成，共处理 {reviewed} 条反馈")

    print()
    print("=" * 60)
    print("反馈审核：第 2 步 - 抽样分类 1 论文")
    print("=" * 60)
    print("以下为今天分类为「与我无关」的论文中随机抽取的 5 篇。")
    print("请判断：如果觉得其实相关，输入 y 改为「相关但不重要」。")
    print()

    cat1_papers = [p for p in storage.get_papers_by_category(1) if p['processed_at'][:10]==__import__('datetime').datetime.now().strftime('%Y-%m-%d')]
    sampled = random.sample(cat1_papers, min(5, len(cat1_papers)))
    reviewed2 = 0
    for p in sampled:
        print(f"--- {p['arxiv_id']} ---")
        print(f"标题: {p['title']}")
        print(f"摘要: {p['summary_zh'][:200] if p.get('summary_zh') else p['abstract'][:200]}")
        choice = input("> 跳过(回车) / 改为相关(y): ").strip().lower()
        if choice == "y":
            storage.save_feedback(p["arxiv_id"], 1, 2)
            reviewed2 += 1
            print("  → 已记录：改为「相关但不重要」")
        print()

    print(f"第 2 步完成，共处理 {reviewed2} 条反馈")
    total = storage.get_feedback_count()
    print(f"当前总反馈数: {total}")
    if total >= 5:
        print("提示：反馈数已达到 5 条，建议运行 refine 命令优化 prompt！")
        print("  python -m auto_arxiv.feedback refine")


def cmd_refine(config_path: str = "config.yaml"):
    """Analyze feedback and generate improved research description."""
    config = Config(config_path)
    storage = Storage(config.db_path)

    errors = config.validate()
    if errors:
        print("配置验证失败，请先完善 config.yaml")
        for e in errors:
            print(f"  {e}")
        return

    print("=" * 60)
    print("分析反馈并优化研究方向描述")
    print("=" * 60)

    misclassified = storage.get_misclassified_patterns()
    if not misclassified:
        print("暂未发现改判记录，请先运行 review 命令收集反馈。")
        return

    print(f"发现 {len(misclassified)} 条改判记录，正在分析...")

    # Step 1: Analyze what went wrong
    analysis = analyze_misclassifications(config, misclassified, config.research_description)
    print()
    print("分析结果:")
    print(analysis)

    # Step 2: Generate new prompt
    print("正在生成新的研究方向描述...")
    new_prompt = generate_refined_prompt(config, analysis, config.research_description)
    print()
    print("新描述草案:")
    print(new_prompt)

    # Step 3: Ask user to confirm
    choice = input("是否应用此新描述？(y/n): ").strip().lower()
    if choice == "y":
        _apply_new_prompt(config, new_prompt, storage)
        print("新描述已应用！")
    else:
        print("已取消。你可以手动编辑 config.yaml 中的 description。")


def cmd_apply(config_path: str = "config.yaml"):
    """Manually set a new research description."""
    config = Config(config_path)
    storage = Storage(config.db_path)

    print("当前研究方向描述:")
    print(config.research_description)
    print()
    print("请输入新的描述（输入完成后输入 EOF 或 Ctrl+Z 结束）:")
    lines = []
    try:
        while True:
            line = input()
            if line == "EOF":
                break
            lines.append(line)
    except EOFError:
        pass

    new_prompt = chr(10).join(lines).strip()
    if not new_prompt:
        print("描述为空，取消操作。")
        return

    print()
    print("新描述:")
    print(new_prompt)
    choice = input("确认应用？(y/n): ").strip().lower()
    if choice == "y":
        _apply_new_prompt(config, new_prompt, storage)
        print("新描述已应用！")


def _apply_new_prompt(config: Config, new_prompt: str, storage: Storage):
    """Save new prompt to database and update config.yaml."""
    # Save to history
    storage.save_prompt(new_prompt, source="user_approved")

    # Update config.yaml in-place
    import re
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        yaml_content = f.read()

    # Replace description block
    pattern = r'(description:\s*\|)[^a-z]*?(?=\n\w)'
    indented = new_prompt.replace(chr(10), chr(10) + "    ")
    replacement = f'description: |\n    {indented}'
    new_yaml = re.sub(pattern, replacement, yaml_content, count=1, flags=re.DOTALL)

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(new_yaml)

    config.research_description = new_prompt
    print(f"config.yaml \u5df2\u66f4\u65b0\uff0c\u65b0\u63cf\u8ff0\u5df2\u4fdd\u5b58\u5230 prompt_history\u3002")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Feedback tools for auto-arXiv")
    parser.add_argument("command", choices=["review", "refine", "apply"],
                        help="review: \u6d4f\u89c8\u5206\u7c7b2+\u62bd\u6837\u5206\u7c7b1 | refine: \u5206\u6790+\u4f18\u5316 | apply: \u624b\u52a8\u66f4\u65b0")
    args = parser.parse_args()

    if args.command == "review":
        cmd_review()
    elif args.command == "refine":
        cmd_refine()
    elif args.command == "apply":
        cmd_apply()
