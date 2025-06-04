#!/bin/bash

# FixPilot 自动化安装脚本
# 用于快速部署 FixPilot 系统

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 命令未找到，请先安装 $1"
        exit 1
    fi
}

# 检查系统要求
check_requirements() {
    log_info "检查系统要求..."
    
    # 检查 Docker
    check_command docker
    
    # 检查 Docker Compose
    check_command docker-compose
    
    # 检查 Git
    check_command git
    
    # 检查 Python (可选)
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        log_info "Python 版本: $PYTHON_VERSION"
    fi
    
    # 检查 Node.js (可选)
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        log_info "Node.js 版本: $NODE_VERSION"
    fi
    
    log_success "系统要求检查完成"
}

# 创建目录结构
create_directories() {
    log_info "创建目录结构..."
    
    mkdir -p data
    mkdir -p logs
    mkdir -p results
    mkdir -p playbooks
    mkdir -p backups
    mkdir -p ssl
    
    log_success "目录结构创建完成"
}

# 配置环境变量
setup_environment() {
    log_info "配置环境变量..."
    
    if [ ! -f .env ]; then
        cp .env.example .env
        log_warning "已创建 .env 文件，请根据需要修改配置"
        
        # 生成随机密钥
        SECRET_KEY=$(openssl rand -hex 32)
        JWT_SECRET_KEY=$(openssl rand -hex 32)
        
        # 更新 .env 文件
        sed -i "s/your-secret-key-here/$SECRET_KEY/" .env
        sed -i "s/your-jwt-secret-key/$JWT_SECRET_KEY/" .env
        
        log_info "已生成随机密钥"
    else
        log_info ".env 文件已存在，跳过创建"
    fi
    
    log_success "环境变量配置完成"
}

# 生成 SSH 密钥对
setup_ssh_keys() {
    log_info "设置 SSH 密钥..."
    
    SSH_KEY_PATH="$HOME/.ssh/fixpilot_rsa"
    
    if [ ! -f "$SSH_KEY_PATH" ]; then
        log_info "生成 SSH 密钥对..."
        ssh-keygen -t rsa -b 4096 -f "$SSH_KEY_PATH" -N "" -C "fixpilot@$(hostname)"
        
        log_success "SSH 密钥对已生成: $SSH_KEY_PATH"
        log_warning "请将公钥添加到目标主机的 authorized_keys 文件中:"
        echo "公钥内容:"
        cat "${SSH_KEY_PATH}.pub"
    else
        log_info "SSH 密钥已存在: $SSH_KEY_PATH"
    fi
}

# 配置 Vuls
setup_vuls_config() {
    log_info "配置 Vuls 扫描器..."
    
    if [ ! -f deploy/vulsctl-config.toml ]; then
        log_error "Vuls 配置文件不存在，请检查项目完整性"
        exit 1
    fi
    
    # 提示用户配置扫描目标
    log_warning "请编辑 deploy/vulsctl-config.toml 文件，添加要扫描的主机"
    log_info "配置示例:"
    echo "[servers.example-host]"
    echo "host = \"192.168.1.100\""
    echo "port = \"22\""
    echo "user = \"ubuntu\""
    echo "keyPath = \"/root/.ssh/fixpilot_rsa\""
    echo "scanMode = [\"fast\", \"deep\"]"
    
    read -p "是否现在编辑配置文件? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} deploy/vulsctl-config.toml
    fi
    
    log_success "Vuls 配置完成"
}

# 构建 Docker 镜像
build_images() {
    log_info "构建 Docker 镜像..."
    
    cd deploy
    
    # 构建后端镜像
    log_info "构建后端镜像..."
    docker-compose build backend
    
    # 构建前端镜像
    log_info "构建前端镜像..."
    docker-compose build frontend
    
    cd ..
    
    log_success "Docker 镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动 FixPilot 服务..."
    
    cd deploy
    
    # 启动所有服务
    docker-compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    docker-compose ps
    
    cd ..
    
    log_success "FixPilot 服务启动完成"
}

# 验证安装
verify_installation() {
    log_info "验证安装..."
    
    # 检查后端服务
    if curl -f http://localhost:8000/ > /dev/null 2>&1; then
        log_success "后端服务运行正常"
    else
        log_error "后端服务启动失败"
        return 1
    fi
    
    # 检查前端服务
    if curl -f http://localhost:3000/ > /dev/null 2>&1; then
        log_success "前端服务运行正常"
    else
        log_error "前端服务启动失败"
        return 1
    fi
    
    log_success "安装验证完成"
}

# 显示访问信息
show_access_info() {
    log_success "FixPilot 安装完成！"
    echo
    echo "访问信息:"
    echo "  前端界面: http://localhost:3000"
    echo "  后端 API: http://localhost:8000"
    echo "  API 文档: http://localhost:8000/docs"
    echo
    echo "管理命令:"
    echo "  启动服务: cd deploy && docker-compose up -d"
    echo "  停止服务: cd deploy && docker-compose down"
    echo "  查看日志: cd deploy && docker-compose logs -f"
    echo "  重启服务: cd deploy && docker-compose restart"
    echo
    echo "下一步:"
    echo "  1. 编辑 deploy/vulsctl-config.toml 配置扫描目标"
    echo "  2. 配置 .env 文件中的 API 密钥和通知设置"
    echo "  3. 在目标主机上部署 SSH 公钥"
    echo "  4. 访问前端界面开始使用"
}

# 主函数
main() {
    echo "======================================"
    echo "    FixPilot 自动化安装脚本"
    echo "======================================"
    echo
    
    # 检查是否在项目根目录
    if [ ! -f "README.md" ] || [ ! -d "backend" ] || [ ! -d "frontend" ]; then
        log_error "请在 FixPilot 项目根目录下运行此脚本"
        exit 1
    fi
    
    # 执行安装步骤
    check_requirements
    create_directories
    setup_environment
    setup_ssh_keys
    setup_vuls_config
    build_images
    start_services
    
    # 验证安装
    if verify_installation; then
        show_access_info
    else
        log_error "安装验证失败，请检查日志"
        exit 1
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
