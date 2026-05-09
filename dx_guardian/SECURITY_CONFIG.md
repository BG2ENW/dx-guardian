# DX Guardian 安全配置说明

本项目的密钥、口令和第三方凭据必须通过环境变量注入，不应写入代码仓库。

## 必要环境变量

- `SECRET_KEY`
- `WAVELOG_URL`
- `WAVELOG_API_KEY`
- `CLUBLOG_APP_PASSWORD`
- `QRZ_USERNAME`
- `QRZ_PASSWORD`
- `HAMQTH_USERNAME`
- `HAMQTH_PASSWORD`
- `VAPID_PUBLIC_KEY`
- `VAPID_PRIVATE_KEY_PEM`
- `VAPID_EMAIL`

## 运行模式

- 开发环境：`FLASK_ENV=development`（允许部分默认值，便于本地调试）
- 生产环境：`FLASK_ENV=production` 或 `APP_ENV=production`

在生产环境中，缺失关键变量会触发启动失败，避免带空配置上线。

## CORS 设置

- 变量：`SOCKETIO_CORS_ALLOWED_ORIGINS`
- 默认值：`*`（仅建议开发环境）

生产环境建议设置为明确域名列表，例如：

```bash
SOCKETIO_CORS_ALLOWED_ORIGINS=https://example.com
```

## VAPID 兼容回退

Web Push 优先读取环境变量。当环境变量未设置时，代码会回退读取 `backend/settings/vapid.json`。

建议逐步停用文件方式，仅保留环境变量注入。
