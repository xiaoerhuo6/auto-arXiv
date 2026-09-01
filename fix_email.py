import os
path = "F:/code/auto-arXiv/auto_arxiv/notifiers/email_notifier.py"
with open(path, encoding="utf-8") as f:
    c = f.read()
old = '<p style="font-size:13px;color:#333;margin:4px 0;">{p[' + "'summary_zh'" + ']}</p>\n                {("<p style=\\"font-size:12px;color:#888;margin:4px 0;\\">- " + p[' + "'relevance_reason'" + '] + "</p>") if p.get(' + "'relevance_reason'" + ') else ""}'
new = '<p style="font-size:13px;color:#333;margin:4px 0;">{p[' + "'summary_zh'" + ']}</p>\n                {reason_html}'
c = c.replace(old, new)
before = "for p in papers:\n        rows += f"
after = "for p in papers:\n        reason_html = \"\"\n        if p.get('relevance_reason'):\n            reason_html = \"<p style=\\\"font-size:12px;color:#888;margin:4px 0;\\\">- \" + p['relevance_reason'] + \"</p>\"\n        rows += f"
c = c.replace(before, after)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("done")
