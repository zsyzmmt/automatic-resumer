# 校招云端扫描（GitHub Actions + Server酱微信推送）

不依赖本机电脑开关机的校招岗位监控保底方案：
每天北京时间 8:00 由 GitHub Actions 云端定时执行，扫描京东校招官方 API，
对比昨日基线发现新增/下线岗位，并通过 Server酱推送到你的微信。

## 目录结构

```
├── scripts/
│   ├── scan_jd.py     # 扫描京东校招API + 对比基线 + 生成简报
│   └── notify.py      # 把简报通过 Server酱 (SCT_SENDKEY) 推送到微信
├── data/
│   ├── jd_baseline.json  # 岗位基线（每日扫描后自动更新并提交）
│   └── scan_report.md    # 当日简报
└── .github/workflows/
    └── daily-scan.yml    # 每日 00:00 UTC（北京 8:00）定时任务
```

## 首次部署步骤（一次性）

1. 在 GitHub 网页上新建一个**私有**仓库（Private，必须私有——包含岗位数据），
   不要勾选初始化 README。
2. 本地推送：
   ```
   git remote add origin https://github.com/<你的用户名>/<仓库名>.git
   git push -u origin main
   ```
3. 浏览器打开 [sct.ftqq.com](https://sct.ftqq.com) → 用**微信**扫码登录 →
   首页会显示一串 **SendKey**（形如 `SCTxxxxxx...`）。
4. GitHub 仓库 → Settings → Secrets and variables → Actions → New repository secret：
   - Name: `SCT_SENDKEY`
   - Secret: 完整 SendKey（`SCT` 开头那一串）
5. 同步修改工作流文件：让 GitHub Actions 把 `SCT_SENDKEY` 注入到
   `python scripts/notify.py` 这一步的环境变量里。最简单的方式是
   在 GitHub 网页上编辑 `.github/workflows/daily-scan.yml`，找到
   `python scripts/notify_wecom.py` 这一行替换为：
   ```yaml
   - name: Push report to WeChat via Server酱
     env:
       SCT_SENDKEY: ${{ secrets.SCT_SENDKEY }}
     run: python scripts/notify.py
   ```
6. 测试：仓库 Actions 页 → Daily JD Campus Scan → Run workflow 手动跑一次，
   微信应收到简报。

## 运行机制

- 定时：cron `0 0 * * *`（UTC）= 北京时间 8:00；GitHub 高峰时段任务可能
  延迟 10~30 分钟，属正常现象。
- 变更提交：只有岗位数据发生变化时才提交（github-actions[bot] 身份），
  仓库无 60 天以上不活动即可保持 cron 生效（GitHub 会自动禁用 60 天无
  commit 的仓库的定时任务，本任务的每日数据提交天然规避了这一点；若某段
  时间岗位无变化，偶发停用时到 Actions 页重新 Enable 即可）。
- 接口容错：京东 API 异常时简报会标注"接口异常待重试"，不影响工作流
  后续推送，基线保持不动。

## 已知限制

- GitHub Actions runner 在海外，京东 API 若拦截海外 IP，扫描会持续报
  "接口异常"。首次手动运行即可验证；若被拦截，改用本机 WorkBuddy 任务
  作为主扫描、云端仅做兜底提醒。
- 云端版只做确定性监控（岗位增减），不做智能匹配评估和简历生成——
  这两项能力保留在本机 WorkBuddy（每天 8:00 的"校招每日扫描与推送"
  任务），两套并行互补。
