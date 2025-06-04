# FixPilot - 自动化漏洞修复系统

## 🎯 项目简介

FixPilot 是一个基于 AI 的自动化漏洞修复系统，集成了 Vuls 漏洞扫描、LLM 智能分析和 Ansible 自动化修复功能。系统能够自动发现、分析和修复 Linux 系统中的安全漏洞，大大提高运维效率和安全防护能力。

## ✨ 核心功能

- 🔍 **自动漏洞扫描**: 基于 Vuls 的定时扫描和漏洞发现
- 🤖 **AI 智能分析**: 使用 SecGPT/OpenAI 生成修复方案
- ⚡ **自动化修复**: 通过 Ansible Playbook 执行修复任务
- 📊 **可视化监控**: Vue3 + TailwindCSS 实时监控界面
- 🔄 **回滚机制**: 支持修复失败后的自动回滚
- 📱 **消息通知**: 企业微信机器人推送修复结果

## 🏗️ 系统架构

```
FixPilot/
├─ backend/           # 后端服务 (FastAPI)
│  ├─ app.py         # 主应用入口
│  ├─ parser.py      # Vuls 结果解析
│  ├─ llm_client.py  # LLM 客户端封装
│  └─ playbook_gen.py # Ansible Playbook 生成
├─ frontend/         # 前端界面 (Vue3)
│  ├─ src/
│  │  ├─ App.vue
│  │  ├─ components/
│  │  └─ api.js
│  └─ vite.config.js
├─ deploy/           # 部署配置
│  ├─ docker-compose.yml
│  └─ vulsctl-config.toml
└─ docs/            # 项目文档
```

## 🚀 快速开始

### 环境要求

- Docker & Docker Compose
- Python 3.8+
- Node.js 16+
- SSH 密钥对（用于主机访问）

### 1. 克隆项目

```bash
git clone https://github.com/your-org/fixpilot.git
cd fixpilot
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
vim .env
```

必要的环境变量：
```bash
# OpenAI API Key (可选，用于在线 LLM)
OPENAI_API_KEY=your_openai_api_key

# 企业微信机器人 Webhook (可选)
WECHAT_WEBHOOK_URL=your_webhook_url

# SSH 密钥路径
SSH_PRIVATE_KEY_PATH=/path/to/your/ssh/key
```

### 3. 配置扫描目标

编辑 `deploy/vulsctl-config.toml`，添加要扫描的主机：

```toml
[servers.web-server]
host = "192.168.1.100"
port = "22"
user = "ubuntu"
keyPath = "/root/.ssh/id_rsa"
scanMode = ["fast", "deep"]
```

### 4. 启动服务

```bash
# 使用 Docker Compose 启动所有服务
cd deploy
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 5. 访问系统

- 前端界面: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 📖 使用指南

### 手动扫描

```bash
# 进入 Vuls 容器
docker exec -it fixpilot-vuls bash

# 执行扫描
vulsctl scan --config /opt/vuls/config.toml

# 生成报告
vulsctl report --config /opt/vuls/config.toml
```

### API 调用示例

```bash
# 获取主机列表
curl http://localhost:8000/hosts

# 获取漏洞列表
curl http://localhost:8000/issues?cvss_min=7.0

# 生成修复 Playbook
curl -X POST http://localhost:8000/playbook \
  -H "Content-Type: application/json" \
  -d '{"host_id": 1, "cvss_threshold": 7.0}'
```

### 自动化流程

系统支持完全自动化的漏洞修复流程：

1. **定时扫描**: Cron 任务定期执行 Vuls 扫描
2. **结果解析**: 自动解析扫描结果并存储到数据库
3. **AI 分析**: LLM 生成针对性的修复命令
4. **Playbook 生成**: 创建 Ansible 修复脚本
5. **自动执行**: 执行修复任务并记录结果
6. **结果通知**: 推送修复结果到企业微信

## 🔧 开发指南

### 后端开发

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 测试

```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm run test
```

## 📊 监控和告警

### 系统监控

- 主机在线状态监控
- 漏洞扫描进度跟踪
- 修复任务执行状态
- 系统资源使用情况

### 告警机制

- 高危漏洞发现告警
- 修复任务失败告警
- 系统异常状态告警
- 定期安全报告推送

## 🔒 安全考虑

### 访问控制

- SSH 密钥管理
- API 访问认证
- 角色权限控制
- 操作审计日志

### 数据安全

- 敏感信息加密存储
- 网络通信 TLS 加密
- 定期数据备份
- 访问日志记录

## 🛠️ 故障排查

### 常见问题

1. **Vuls 扫描失败**
   - 检查 SSH 连接配置
   - 验证目标主机可达性
   - 查看 Vuls 日志输出

2. **LLM 生成失败**
   - 检查 API Key 配置
   - 验证网络连接
   - 查看模型加载状态

3. **Ansible 执行失败**
   - 检查目标主机权限
   - 验证 Playbook 语法
   - 查看执行日志

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f vulsctl
```

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系我们

- 项目主页: https://github.com/your-org/fixpilot
- 问题反馈: https://github.com/your-org/fixpilot/issues
- 邮箱: security@yourcompany.com

## 🙏 致谢

感谢以下开源项目的支持：

- [Vuls](https://vuls.io/) - 漏洞扫描引擎
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Web 框架
- [Vue.js](https://vuejs.org/) - 渐进式前端框架
- [Ansible](https://www.ansible.com/) - 自动化运维工具
