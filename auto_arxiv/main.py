"""auto-arXiv: Daily arXiv paper fetcher, classifier, and notifier."""
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auto_arxiv.config import Config
from auto_arxiv.arxiv_fetcher import fetch_latest_papers
from auto_arxiv.classifier import classify_paper
from auto_arxiv.storage import Storage
from auto_arxiv.notifiers.email_notifier import send_email, build_paper_summary_html
from auto_arxiv.notifiers.wechat_notifier import send_wechat, build_wechat_message


CATEGORY_LABELS = {
    1: "与我无关",
    2: "相关但不重要",
    3: "强相关且值得研究",
    4: "不相关但很重要",
}


def run_pipeline(config_path: str = "config.yaml"):
    """Run the full pipeline: fetch -> classify -> store -> notify -> report."""
    config = Config(config_path)
    errors = config.validate()
    if errors:
        for e in errors:
            print(f"[Config Error] {e}")
        print("请先完善 config.yaml 中的配置后再运行。")
        return

    # Ensure output dirs exist
    os.makedirs(config.report_dir, exist_ok=True)
    os.makedirs(os.path.dirname(config.db_path), exist_ok=True)

    storage = Storage(config.db_path)

    # ---- Step 1: Fetch ----
    print(f"[1/4] 正在从 arXiv 获取论文 (分类: {', '.join(config.arxiv_categories)})...")
    papers = fetch_latest_papers(
        categories=config.arxiv_categories,
        max_results=config.max_papers_per_day,
        lookback_days=1,
    )
    print(f"      获取到 {len(papers)} 篇论文")

    # ---- Step 2: Classify ----
    print(f"[2/4] 正在对论文进行分类和摘要...")
    results = []  # (paper, classification)
    for i, paper in enumerate(papers):
        # Skip already processed papers
        if storage.paper_exists(paper["arxiv_id"]):
            continue

        classification = classify_paper(config, paper["title"], paper["abstract"])
        storage.save_paper(paper, classification)
        results.append((paper, classification))

        cat_label = CATEGORY_LABELS.get(classification.get("category", 1), "未知")
        print(f"      [{i+1}/{len(papers)}] {paper['arxiv_id']} -> {cat_label}")

    # ---- Step 3: Notify ----
    print(f"[3/4] 正在推送通知...")
    _send_notifications(config, storage)

    # ---- Step 4: Generate report ----
    print(f"[4/4] 正在生成报告...")
    report_path = _generate_report(config, storage)
    print(f"      报告已保存: {report_path}")

    print(f"\n=== 完成！共处理 {len(results)} 篇新论文 ===")


def _send_notifications(config: Config, storage: Storage):
    """Send email and/or WeChat notifications for new papers in categories 2, 3, 4."""
    for cat in [2, 3, 4]:
        papers = storage.get_unnotified(cat)
        if not papers:
            continue

        cat_label = CATEGORY_LABELS.get(cat, "未知")

        # Email
        if config.email_enabled:
            html = build_paper_summary_html(papers)
            ok = send_email(
                config,
                subject=f"[auto-arXiv] {cat_label} - {len(papers)} 篇新论文",
                html_body=html,
            )
            if ok:
                print(f"      邮件推送 [{cat_label}] 成功 ({len(papers)} 篇)")
                for p in papers:
                    storage.mark_notified(p["arxiv_id"])

        # WeChat
        if config.wechat_enabled:
            msg = build_wechat_message(papers, cat_label)
            ok = send_wechat(
                config,
                title=f"[auto-arXiv] {cat_label} - {len(papers)} 篇",
                content=msg,
            )
            if ok:
                print(f"      微信推送 [{cat_label}] 成功 ({len(papers)} 篇)")
                for p in papers:
                    storage.mark_notified(p["arxiv_id"])

    # Mark category-3 papers for reading list
    cat3_papers = storage.get_unnotified(3)
    for p in cat3_papers:
        storage.mark_to_read(p["arxiv_id"])


def _generate_report(config: Config, storage: Storage) -> str:
    """Generate today's Markdown report and update reading list."""
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(config.report_dir, f"report_{today}.md")

    lines = [f"# arXiv 论文日报 - {today}", ""]

    for cat in [2, 3, 4]:
        papers = storage.get_papers_by_category(cat)
        if not papers:
            continue

        cat_label = CATEGORY_LABELS.get(cat, "未知")
        lines.append(f"## {cat_label} ({len(papers)} 篇)")
        lines.append("")

        for p in papers:
            lines.append(f"### [{p['title']}]({p['link']})")
            lines.append(f"- **ID**: {p['arxiv_id']} | **分类**: {', '.join(p['categories'])}")
            lines.append(f"- **作者**: {p['authors']}")
            lines.append(f"- **摘要**: {p['summary_zh']}")
            if p.get("relevance_reason"):
                lines.append(f"- **关联说明**: {p['relevance_reason']}")
            lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Update reading list (category 3 only)
    _update_reading_list(config, storage)

    return filepath


def _update_reading_list(config: Config, storage: Storage):
    """Append category-3 papers to the persistent reading list."""
    reading_list = Path(config.reading_list)
    if not reading_list.exists():
        reading_list.write_text("# 待阅读论文清单\n\n", encoding="utf-8")

    cat3_papers = storage.get_papers_by_category(3)
    if not cat3_papers:
        return

    existing = reading_list.read_text(encoding="utf-8")
    with open(reading_list, "a", encoding="utf-8") as f:
        for p in cat3_papers:
            entry = f"- [ ] [{p['title']}]({p['link']}) - {p['published'][:10]}\n"
            if entry not in existing:
                f.write(entry)


if __name__ == "__main__":
    run_pipeline()
