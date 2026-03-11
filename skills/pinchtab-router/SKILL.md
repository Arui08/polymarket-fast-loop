---
name: pinchtab-router
version: 1.0.0
description: "将浏览器控制统一路由到 PinchTab（pinchtab-agent）。当用户要求浏览网页、自动化、点击/输入/截图/监控变化时，优先使用 pt_* 工具族；仅在 PinchTab 不适配（Shadow DOM、复杂组件）时回退 OpenClaw browser 工具。"
metadata:
  openclaw:
    emoji: "📌"
    requires:
      anyBins: ["node", "pinchtab"]
---

# pinchtab-router

**目标**：把所有浏览器控制默认切到 PinchTab（pinchtab-agent 的 pt_* 工具）。

## 何时触发
- 打开网页、抓取文本
- 点击/输入/表单
- 监控页面变化
- 多标签并行抓取

## 核心策略
1. **默认优先**：使用 pt_* 工具完成浏览器任务。
2. **必要回退**：遇到 Shadow DOM/复杂组件、PinchTab 失败时，才用 OpenClaw `browser` 工具。
3. **安全**：不读写敏感文件，不外发数据。

## 常用工具
- `pt_navigate` / `pt_snapshot` / `pt_text`
- `pt_click` / `pt_type`
- `pt_diff` / `pt_screenshot`
- `pt_close` / `pt_cleanup`

## 简例
```
pt_navigate({ url: "https://news.ycombinator.com" })
pt_text()
```

## 兼容性说明
- PinchTab 基于可访问性树，**对 Shadow DOM/复杂前端组件不可靠**。
- 需要精确 UI 操作时回退 `browser` 工具。
