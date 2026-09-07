# 校招云端扫描（GitHub Actions + 企微 Webhook）

不依赖本机电脑开关机的校招岗位监控保底方案：
每天北京时间 8:00 由 GitHub Actions 云端定时执行，扫描京东校招官方 API，
对比昨日基线发现新增/下线岗位，并推送到企业微信群机器人。

## 目录结构

```
├── scripts/
│   ├── scan_jd.py        # 扫描京东校招API + 对比基线 + 生成简报
│   └── notify_wecom.py   # 把简报推送到企微群机器人 Webhook
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
3. 企业微信里新建一个群（拉一个同事/家人凑数即可）→ 群设置 → 添加群机器人 →
   复制机器人的 Webhook 地址（形如
   `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx`）。
4. GitHub 仓库 → Settings → Secrets and variables → Actions → New repository secret：
   - Name: `WECOM_WEBHOOK`
   - Secret: 完整 webhook 地址
5. 测试：仓库 Actions 页 → Daily JD Campus Scan → Run workflow 手动跑一次，
   企微群里应收到简报。

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
