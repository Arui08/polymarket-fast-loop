# X 自动发推（最小可用版）

## 目标
- 用本机 `xurl` 已授权身份发推
- 不把密钥写进项目仓库
- 支持测试发帖 / 正式发帖 / cron 定时
- 自动记录日志

## 1. 本机配置
先在本机创建：

```bash
mkdir -p ~/.config/x-bot
cp /root/.openclaw/workspace/config/x-bot.env.example ~/.config/x-bot/.env
chmod 600 ~/.config/x-bot/.env
```

编辑 `~/.config/x-bot/.env`：

```env
XURL_APP_NAME=default
```

如果你不确定 app 名称，先看：

```bash
xurl auth apps list
xurl auth status
```

## 2. 测试是否可发
### Dry run
```bash
bash /root/.openclaw/workspace/scripts/x_autopost.sh --dry-run "测试文案"
```

### 正式发一条
```bash
bash /root/.openclaw/workspace/scripts/x_autopost.sh "测试发帖：X 自动发推已接通。"
```

## 3. 从文件发
```bash
echo "今日日更：测试内容" > /tmp/x_post.txt
bash /root/.openclaw/workspace/scripts/x_autopost.sh --from-file /tmp/x_post.txt
```

## 4. 定时发布
编辑 cron：

```bash
crontab -e
```

示例：每天北京时间 09:00 发一条（服务器若是 UTC，自行换算）

```cron
0 1 * * * /bin/bash /root/.openclaw/workspace/scripts/x_autopost.sh --from-file /root/.openclaw/workspace/notes/x_post.txt >> /root/.local/share/x-bot/cron.log 2>&1
```

## 5. 日志位置
- 单次发帖日志：`~/.local/share/x-bot/logs/`
- 最近一次文案：`~/.local/share/x-bot/last_post.txt`
- cron 汇总日志：`~/.local/share/x-bot/cron.log`

## 6. 安全规则
- 不要把任何 X key/token 发到聊天里
- 真实密钥只放本机安全文件
- 若曾在聊天里发送过旧凭证，全部 rotate 后再用
