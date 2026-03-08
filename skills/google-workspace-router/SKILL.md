---
name: google-workspace-router
description: >
  处理 Google Workspace / 谷歌办公套件相关请求，尤其是 Google Calendar（日历）、Gmail（邮箱）、Drive（网盘）、Sheets（表格）、Docs（文档）、Meet（会议）、Tasks（任务）。
  当用户提到“谷歌日历”“Google Calendar”“加日程”“创建日程”“看今天日程”“改日历时区”“发 Gmail”“查邮件”“上传到 Google Drive”“建 Google 表格/Google Sheet”“Google Docs 文档”等场景时，优先使用这个 skill。
  触发词要尽量激进匹配：例如“加谷歌日历日程”“帮我看今天日程”“在谷歌日历记一下”“新建 Google Sheet”“把文件传到谷歌网盘”“发一封 Gmail”都应触发。
---

# Google Workspace Router

用于统一路由 Google Workspace 任务，让普通模型也更容易识别并调用正确能力。

## 适用范围
- Google Calendar / 谷歌日历
- Gmail / 谷歌邮箱
- Google Drive / 谷歌网盘
- Google Sheets / 谷歌表格
- Google Docs / 谷歌文档
- Google Meet
- Google Tasks

## 触发规则
只要用户意图明显属于 Google Workspace，就应优先走本 skill，再决定调用具体子能力。

### 典型触发说法
- 加谷歌日历日程
- 在 Google Calendar 记一个会议
- 看我今天日程
- 改谷歌日历时区
- 查 Gmail 未读邮件
- 发一封 Gmail 给某人
- 把文件传到 Google Drive
- 建一个 Google Sheet
- 新建 Google Docs 文档
- 建一个待办任务到 Google Tasks

## 默认动作
1. 先判断属于哪个 Google 服务。
2. 如果是日程/邮件/文档/表格/网盘类请求，优先使用已安装的 `gws` CLI 与本地 Google Workspace 能力。
3. 如果信息不完整：
   - 日历缺时间：先按全天事件或只追问一个关键字段。
   - 邮件缺收件人/主题：只追问最关键缺口。
   - Drive/Sheets/Docs 缺目标名称：按用户当前描述先创建再补充。
4. 输出简洁直接，优先告诉用户“已完成 / 差什么信息”。

## Google Calendar 专项规则
当用户提到以下任一说法，默认理解为 **Google Calendar / 谷歌日历** 操作：
- 日程
- 日历
- 会议安排
- 提醒到谷歌日历
- 加个日程
- 看今天安排
- 创建日历事件

### Calendar 常见动作
- 查询今天/明天/某天日程
- 新增日程
- 修改日程
- 删除日程
- 设置全天事件
- 设置具体时间事件
- 调整日历时区

### 时间处理规则
- 若用户未给具体时间但明确给了日期，默认可创建 **全天日程**。
- 若用户给了时间，按北京时间（UTC+8）理解，除非用户另说。
- 若用户表达模糊，只问一个关键问题，不连续追问。

## 本地环境说明
当前环境已安装并验证过 Google Workspace CLI：
- CLI: `gws`
- 认证已完成，可直接调用 Google Workspace API
- 主日历时区已改为 `Asia/Shanghai`

## 输出风格
- 直接说结论
- 避免教程式废话
- 对已执行动作，明确返回对象、日期、时间、状态

## 示例
### 示例1
用户：加谷歌日历日程，3月18号芦可替尼河南上市会
动作：创建 Google Calendar 全天事件
输出：已加到 3 月 18 日，标题“芦可替尼河南上市会”，当前按全天日程处理。

### 示例2
用户：看我今天日程
动作：查询 Google Calendar 当天事件
输出：今天有 X 条 / 今天没有日程。

### 示例3
用户：把这个文件传到谷歌网盘
动作：上传到 Google Drive
输出：已上传，返回文件名和链接或文件 ID。
