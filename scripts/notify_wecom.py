# -*- coding: utf-8 -*-
"""把 scan_report.md 推送到企业微信群机器人 Webhook。

环境变量：
  WECOM_WEBHOOK - 完整 webhook URL
  （https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx）
用法：python scripts/notify_wecom.py
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "data" / "scan_report.md"

# 企微 markdown 消息上限 4096 字节（utf-8）
MAX_BYTES = 4000


def main():
    webhook = os.environ.get("WECOM_WEBHOOK", "").strip()
    if not webhook:
        print("[notify] 未配置 WECOM_WEBHOOK，跳过推送。")
        print("[notify] 请在 GitHub 仓库 Settings > Secrets and variables > Actions")
        print("[notify] 添加 Secret：WECOM_WEBHOOK = 企微群机器人完整webhook地址")
        return

    if not REPORT.exists():
        print("[notify] 未找到 data/scan_report.md，跳过推送。")
        return

    content = REPORT.read_text(encoding="utf-8").strip()
    raw = content.encode("utf-8")
    if len(raw) > MAX_BYTES:
        # 从后往前找安全截断点，避免截断在多字节字符中间
        content = raw[:MAX_BYTES].decode("utf-8", errors="ignore")
        # 截到最后一行完整行为止
        content = content.rsplit("\n", 1)[0]
        content += "\n\n……（内容过长已截断，完整报告见仓库 data/scan_report.md）"

    payload = json.dumps(
        {"msgtype": "markdown", "markdown": {"content": content}}
    ).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.load(resp)
    if result.get("errcode") == 0:
        print("[notify] 推送成功。")
    else:
        print("[notify] 推送失败：{}".format(result))
        sys.exit(1)


if __name__ == "__main__":
    main()
