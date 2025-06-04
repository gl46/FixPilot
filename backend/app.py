"""
FixPilot Backend API
主要功能：提供 REST API 接口，管理主机、漏洞和修复任务
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
import json
from loguru import logger

from parser import VulsParser
from llm_client import LLMClient
from playbook_gen import PlaybookGenerator

# 数据库配置
DATABASE_URL = "sqlite:///./fixpilot.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 数据模型
class Host(Base):
    __tablename__ = "hosts"
    
    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, unique=True, index=True)
    hostname = Column(String)
    os = Column(String)
    last_scan = Column(DateTime)
    risk_score = Column(Float, default=0.0)

class Issue(Base):
    __tablename__ = "issues"
    
    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer)
    cve = Column(String, index=True)
    summary = Column(Text)
    cvss = Column(Float)
    package = Column(String)
    patchable = Column(String)
    status = Column(String, default="open")  # open, fixing, fixed, failed
    fix_command = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Pydantic 模型
class HostResponse(BaseModel):
    id: int
    ip: str
    hostname: Optional[str]
    os: Optional[str]
    last_scan: Optional[datetime]
    risk_score: float

class IssueResponse(BaseModel):
    id: int
    host_id: int
    cve: str
    summary: str
    cvss: float
    package: Optional[str]
    patchable: Optional[str]
    status: str
    fix_command: Optional[str]
    created_at: datetime

class PlaybookRequest(BaseModel):
    host_id: int
    cvss_threshold: float = 7.0

# 创建表
Base.metadata.create_all(bind=engine)

# FastAPI 应用
app = FastAPI(
    title="FixPilot API",
    description="自动化漏洞修复系统 API",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 依赖注入
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 初始化组件
parser = VulsParser()
llm_client = LLMClient()
playbook_gen = PlaybookGenerator()

@app.get("/")
async def root():
    """根路径，返回 API 信息"""
    return {
        "name": "FixPilot API",
        "version": "1.0.0",
        "description": "自动化漏洞修复系统"
    }

@app.get("/hosts", response_model=List[HostResponse])
async def get_hosts(db: Session = Depends(get_db)):
    """获取所有主机列表"""
    hosts = db.query(Host).all()
    return hosts

@app.get("/hosts/{host_id}", response_model=HostResponse)
async def get_host(host_id: int, db: Session = Depends(get_db)):
    """获取指定主机信息"""
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host

@app.get("/issues", response_model=List[IssueResponse])
async def get_issues(
    host_id: Optional[int] = None,
    cvss_min: Optional[float] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取漏洞列表，支持筛选"""
    query = db.query(Issue)
    
    if host_id:
        query = query.filter(Issue.host_id == host_id)
    if cvss_min:
        query = query.filter(Issue.cvss >= cvss_min)
    if status:
        query = query.filter(Issue.status == status)
    
    issues = query.all()
    return issues

@app.post("/playbook")
async def generate_playbook(
    request: PlaybookRequest,
    db: Session = Depends(get_db)
):
    """生成 Ansible Playbook"""
    try:
        # 获取主机信息
        host = db.query(Host).filter(Host.id == request.host_id).first()
        if not host:
            raise HTTPException(status_code=404, detail="Host not found")
        
        # 获取高风险漏洞
        issues = db.query(Issue).filter(
            Issue.host_id == request.host_id,
            Issue.cvss >= request.cvss_threshold,
            Issue.status == "open"
        ).all()
        
        if not issues:
            return {"message": "No high-risk issues found", "playbook": None}
        
        # 生成修复命令
        fix_commands = []
        for issue in issues:
            if not issue.fix_command:
                # 使用 LLM 生成修复命令
                fix_cmd = await llm_client.generate_fix_command(issue.cve, issue.summary)
                issue.fix_command = fix_cmd
                db.commit()
            fix_commands.append({
                "cve": issue.cve,
                "command": issue.fix_command,
                "package": issue.package
            })
        
        # 生成 Playbook
        playbook_content = playbook_gen.generate_playbook(host.ip, fix_commands)
        
        # 保存 Playbook 文件
        filename = f"fix_{host.ip.replace('.', '_')}.yml"
        filepath = f"./playbooks/{filename}"
        os.makedirs("./playbooks", exist_ok=True)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(playbook_content)
        
        return {
            "message": "Playbook generated successfully",
            "filename": filename,
            "issues_count": len(issues),
            "playbook": playbook_content
        }
        
    except Exception as e:
        logger.error(f"Error generating playbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scan/parse")
async def parse_scan_results(db: Session = Depends(get_db)):
    """解析 Vuls 扫描结果"""
    try:
        # 解析扫描结果
        results = parser.parse_results("./results")
        
        # 更新数据库
        for result in results:
            # 更新或创建主机记录
            host = db.query(Host).filter(Host.ip == result["ip"]).first()
            if not host:
                host = Host(
                    ip=result["ip"],
                    hostname=result.get("hostname"),
                    os=result.get("os"),
                    last_scan=datetime.utcnow(),
                    risk_score=result.get("risk_score", 0.0)
                )
                db.add(host)
                db.flush()
            else:
                host.last_scan = datetime.utcnow()
                host.risk_score = result.get("risk_score", 0.0)
            
            # 添加漏洞记录
            for issue in result.get("issues", []):
                existing_issue = db.query(Issue).filter(
                    Issue.host_id == host.id,
                    Issue.cve == issue["cve"]
                ).first()
                
                if not existing_issue:
                    new_issue = Issue(
                        host_id=host.id,
                        cve=issue["cve"],
                        summary=issue["summary"],
                        cvss=issue["cvss"],
                        package=issue.get("package"),
                        patchable=issue.get("patchable"),
                        status="open"
                    )
                    db.add(new_issue)
        
        db.commit()
        return {"message": "Scan results parsed successfully"}
        
    except Exception as e:
        logger.error(f"Error parsing scan results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/playbooks/{filename}")
async def download_playbook(filename: str):
    """下载生成的 Playbook 文件"""
    filepath = f"./playbooks/{filename}"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    return FileResponse(
        filepath,
        media_type="application/x-yaml",
        filename=filename
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
