# -*- coding: utf-8 -*-
"""京东校招岗位每日扫描：拉取官方API全部在招岗位，与基线对比，输出变更简报。

数据源：京东校招官网 campus.jd.com 官方职位API（公开接口，无需登录）
用法：python scripts/scan_jd.py
输出：data/scan_report.md（当日简报，供 webhook 推送）
      data/jd_baseline.json（有变更时更新，由 Actions 提交回仓库）
"""
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import urllib.request

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
BASELINE = DATA_DIR / "jd_baseline.json"
REPORT = DATA_DIR / "scan_report.md"

API_URL = "https://campus.jd.com/api/wx/position/page"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://campus.jd.com",
    "Referer": "https://campus.jd.com/",
}
PAGE_SIZE = 50
CST = timezone(timedelta(hours=8))


def now_cst():
    return datetime.now(CST)


def api_post(type_param, page_index, retries=3):
    body = json.dumps(
        {"pageIndex": page_index, "pageSize": PAGE_SIZE}
    ).encode("utf-8")
    req = urllib.request.Request(
        API_URL + "?type=" + type_param, data=body, headers=HEADERS, method="POST"
    )
    last_err = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.load(resp)
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(3 * (i + 1))
    raise RuntimeError("API request failed after retries: {}".format(last_err))


def fetch_all(type_param):
    """分页拉取某类型（present=校招/internship=实习）的全部岗位。"""
    items = []
    page = 1
    total = None
    while True:
        payload = api_post(type_param, page)
        data = payload.get("data") or {}
        if total is None:
            total = data.get("count") or 0
        batch = data.get("items") or []
        items.extend(batch)
        if len(items) >= total or not batch:
            break
        page += 1
        if page > 30:  # 安全上限
            break
    return total, items


def slim(item):
    return {
        "name": item.get("positionName") or "",
        "direction": item.get("jobDirection") or "",
        "workPlace": item.get("workPlace") or "",
    }


def load_baseline():
    if BASELINE.exists():
        return json.loads(BASELINE.read_text(encoding="utf-8"))
    return {"fetched_at": None, "items": {}}


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ts = now_cst().strftime("%Y-%m-%d %H:%M")
    lines = ["# 京东校招每日扫描简报", "", "执行时间：{}（北京时间）".format(ts), ""]

    # ---- 校招岗位（present）----
    try:
        total, items = fetch_all("present")
    except Exception as e:  # noqa: BLE001
        total, items = None, []
        lines += ["## ❌ 校招岗位接口异常", "", "抓取失败：{}".format(e)[:200], "",
                  "> 接口可能临时故障或拦截了海外IP，等待下次任务重试。", ""]

    baseline = load_baseline()
    base_items = baseline.get("items") or {}

    if total is not None:
        current = {str(p.get("publishId")): slim(p) for p in items}
        new_ids = [i for i in current if i not in base_items]
        gone_ids = [i for i in base_items if i not in current]

        lines += ["## 校招岗位（JDS/TET 等）", "",
                  "当前在招：**{} 个**（昨日基线：{} 个）".format(total, len(base_items)), ""]

        if new_ids:
            lines += ["### 🆕 新增岗位（{} 个）".format(len(new_ids)), ""]
            for i in new_ids[:15]:
                it = current[i]
                lines.append("- **{}** ｜ {} ｜ {}".format(
                    it["name"], it["direction"], it["workPlace"]))
            if len(new_ids) > 15:
                lines.append("- ……等共 {} 个，详见仓库 data/jd_baseline.json".format(len(new_ids)))
            lines.append("")

        if gone_ids:
            lines += ["### ⬇️ 已下线岗位（{} 个）".format(len(gone_ids)), ""]
            for i in gone_ids[:10]:
                it = base_items[i]
                lines.append("- {} ｜ {}".format(it["name"], it["direction"]))
            lines.append("")

        if not new_ids and not gone_ids:
            lines += ["✅ 与昨日相比无变化。", ""]

        # 更新基线（仅在成功抓取时）
        baseline = {
            "fetched_at": ts,
            "items": current,
        }
        BASELINE.write_text(
            json.dumps(baseline, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    # ---- 实习岗位（internship，JD YOUNG）----
    try:
        itotal, iitems = fetch_all("internship")
        if itotal:
            inames = [p.get("positionName") for p in iitems[:10]]
            lines += ["## JD YOUNG 实习生岗位", "",
                      "当前在招：**{} 个**".format(itotal), ""]
            for n in inames:
                lines.append("- {}".format(n))
            lines.append("")
            DATA_DIR.joinpath("jd_intern.json").write_text(
                json.dumps(
                    {"fetched_at": ts,
                     "items": [slim(p) for p in iitems]},
                    ensure_ascii=False, indent=1,
                ),
                encoding="utf-8",
            )
        else:
            lines += ["## JD YOUNG 实习生岗位", "",
                      "当前实习岗位数为 0（JD YOUNG 计划可能未开放或接口参数变化）。", ""]
    except Exception as e:  # noqa: BLE001
        lines += ["## JD YOUNG 实习生岗位", "",
                  "接口暂不可用：{}".format(str(e)[:150]), ""]

    lines += ["---", "",
              "本简报由 GitHub Actions 云端任务自动生成，"
              "不依赖本机电脑开关机状态。"]

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

    # 始终退出 0，接口异常不阻断工作流后续推送
    sys.exit(0)


if __name__ == "__main__":
    main()
