# -*- coding: utf-8 -*-
"""把 scan_report.md 推送到微信（Server酱优先）或企业微信群机器人。

环境变量（至少配一个）：
  SCT_SENDKEY     - Server酱 SendKey（推荐，推送到个人微信）
                    https://sct.ftqq.com 微信扫码登录后获取
  WECOM_WEBHOOK   - 企业微信群机器人 Webhook（可选，同时配置则双通道都发）
用法：python scripts/notify.py
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "data" / "scan_report.md"

# 单条消息上限（utf-8 字节）。Server酱 desp 上限较大，这里保守控制避免超限
MAX_BYTES = 4000


def read_report():
    if not REPORT.exists():
        print("[notify] 未找到 data/scan_report.md，跳过推送。")
        return None
    content = REPORT.read_text(encoding="utf-8").strip()
    raw = content.encode("utf-8")
    if len(raw) > MAX_BYTES:
        content = raw[:MAX_BYTES].decode("utf-8", errors="ignore")
        # 截到最后一行完整行为止，避免切断多字节字符
        content = content.rsplit("\n", 1)[0]
        content += "\n\n……（内容过长已截断，完整报告见仓库 data/scan_report.md）"
    return content


def push_serverchan(sendkey, content):
    """Server酱微信推送。首行当标题，其余当正文（支持 Markdown）。"""
    lines = content.splitlines()
    title = lines[0].lstrip("#").strip()[:32] if lines else "校招监控日报"
    if not title:
        title = "校招监控日报"
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else content
    if not body:
        body = content
    data = urllib.parse.urlencode({"title": title, "desp": body}).encode("utf-8")
    url = "https://sctapi.ftqq.com/{}.send".format(sendkey)
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.load(resp)
    if result.get("code") == 0:
        print("[notify] Server酱 微信推送成功。")
        return True
    print("[notify] Server酱 推送失败：{}".format(result))
    return False


def push_wecom(webhook, content):
    """企业微信群机器人推送（markdown）。"""
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
        print("[notify] 企微群机器人推送成功。")
        return True
    print("[notify] 企微 推送失败：{}".format(result))
    return False


def main():
    sendkey = os.environ.get("SCT_SENDKEY", "").strip()
    webhook = os.environ.get("WECOM_WEBHOOK", "").strip()
    if not sendkey and not webhook:
        print("[notify] 未配置 SCT_SENDKEY 或 WECOM_WEBHOOK，跳过推送。")
        print("[notify] 在 GitHub 仓库 Settings > Secrets and variables > Actions 添加：")
        print("[notify]   SCT_SENDKEY    = Server酱 SendKey（推荐，推送到微信）")
        print("[notify]   WECOM_WEBHOOK  = 企微群机器人 webhook（可选）")
        return

    content = read_report()
    if content is None:
        return

    ok = True
    if sendkey:
        ok = push_serverchan(sendkey, content) and ok
    if webhook:
        ok = push_wecom(webhook, content) and ok
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
