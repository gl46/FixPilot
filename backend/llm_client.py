"""
LLM 客户端
功能：集成 SecGPT-mini 和 OpenAI，生成漏洞修复命令
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from loguru import logger

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available")

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers library not available")


class BaseLLMClient(ABC):
    """LLM 客户端基类"""
    
    @abstractmethod
    async def generate_fix_command(self, cve: str, summary: str, **kwargs) -> str:
        """生成修复命令"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT 客户端"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library is required for OpenAI client")
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
    
    async def generate_fix_command(self, cve: str, summary: str, **kwargs) -> str:
        """使用 OpenAI GPT 生成修复命令"""
        try:
            prompt = self._build_prompt(cve, summary, **kwargs)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的网络安全专家，专门负责生成Linux系统漏洞的修复命令。请提供准确、安全的Shell命令来修复指定的CVE漏洞。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            fix_command = response.choices[0].message.content.strip()
            return self._extract_command(fix_command)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"# Error generating fix command for {cve}: {e}"
    
    def _build_prompt(self, cve: str, summary: str, **kwargs) -> str:
        """构建修复命令生成的提示词"""
        os_info = kwargs.get('os', 'Linux')
        package = kwargs.get('package', '')
        
        prompt = f"""
请为以下CVE漏洞生成修复命令：

CVE编号: {cve}
漏洞描述: {summary}
操作系统: {os_info}
受影响包: {package}

要求：
1. 提供具体的Shell命令来修复此漏洞
2. 优先使用包管理器更新（如apt, yum, dnf等）
3. 如果需要重启服务，请包含相关命令
4. 确保命令的安全性和准确性
5. 只返回可执行的Shell命令，不要包含解释文字

示例格式：
apt update && apt upgrade -y package-name
systemctl restart service-name
"""
        return prompt
    
    def _extract_command(self, response: str) -> str:
        """从响应中提取Shell命令"""
        lines = response.strip().split('\n')
        commands = []
        
        for line in lines:
            line = line.strip()
            # 跳过注释和空行
            if line and not line.startswith('#') and not line.startswith('//'):
                # 移除可能的markdown代码块标记
                if line.startswith('```'):
                    continue
                if line.endswith('```'):
                    line = line[:-3]
                commands.append(line)
        
        return ' && '.join(commands) if commands else response.strip()


class SecGPTClient(BaseLLMClient):
    """SecGPT-mini 本地客户端"""
    
    def __init__(self, model_path: str = "secgpt-mini-1.5b"):
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("Transformers library is required for SecGPT client")
        
        self.model_path = model_path
        self.tokenizer = None
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self._load_model()
    
    def _load_model(self):
        """加载 SecGPT 模型"""
        try:
            logger.info(f"Loading SecGPT model from {self.model_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            logger.info("SecGPT model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load SecGPT model: {e}")
            raise
    
    async def generate_fix_command(self, cve: str, summary: str, **kwargs) -> str:
        """使用 SecGPT 生成修复命令"""
        try:
            prompt = self._build_prompt(cve, summary, **kwargs)
            
            # 在线程池中运行推理以避免阻塞
            loop = asyncio.get_event_loop()
            fix_command = await loop.run_in_executor(
                None, self._generate_sync, prompt
            )
            
            return self._extract_command(fix_command)
            
        except Exception as e:
            logger.error(f"SecGPT generation error: {e}")
            return f"# Error generating fix command for {cve}: {e}"
    
    def _generate_sync(self, prompt: str) -> str:
        """同步生成文本"""
        inputs = self.tokenizer.encode(prompt, return_tensors="pt")
        if self.device == "cuda":
            inputs = inputs.to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                max_length=inputs.shape[1] + 200,
                temperature=0.3,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                num_return_sequences=1
            )
        
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # 移除原始提示词，只保留生成的部分
        response = generated_text[len(prompt):].strip()
        return response
    
    def _build_prompt(self, cve: str, summary: str, **kwargs) -> str:
        """构建 SecGPT 的提示词"""
        os_info = kwargs.get('os', 'Linux')
        package = kwargs.get('package', '')
        
        prompt = f"""### 漏洞修复任务

CVE: {cve}
描述: {summary}
系统: {os_info}
包: {package}

请生成修复此漏洞的Shell命令：

"""
        return prompt
    
    def _extract_command(self, response: str) -> str:
        """从响应中提取Shell命令"""
        lines = response.strip().split('\n')
        commands = []
        
        for line in lines:
            line = line.strip()
            # 跳过注释和空行
            if line and not line.startswith('#') and not line.startswith('//'):
                # 检查是否是有效的Shell命令
                if any(cmd in line.lower() for cmd in ['apt', 'yum', 'dnf', 'systemctl', 'service', 'update', 'upgrade', 'install']):
                    commands.append(line)
        
        return ' && '.join(commands) if commands else response.strip()


class LLMClient:
    """LLM 客户端管理器"""
    
    def __init__(self, provider: str = "auto"):
        self.provider = provider
        self.client = None
        
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化 LLM 客户端"""
        if self.provider == "openai" or (self.provider == "auto" and os.getenv("OPENAI_API_KEY")):
            try:
                self.client = OpenAIClient()
                self.provider = "openai"
                logger.info("Using OpenAI client")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
                if self.provider == "openai":
                    raise
        
        if self.client is None and (self.provider == "secgpt" or self.provider == "auto"):
            try:
                self.client = SecGPTClient()
                self.provider = "secgpt"
                logger.info("Using SecGPT client")
            except Exception as e:
                logger.warning(f"Failed to initialize SecGPT client: {e}")
                if self.provider == "secgpt":
                    raise
        
        if self.client is None:
            # 回退到模板生成
            self.client = TemplateClient()
            self.provider = "template"
            logger.info("Using template-based client")
    
    async def generate_fix_command(self, cve: str, summary: str, **kwargs) -> str:
        """生成修复命令"""
        return await self.client.generate_fix_command(cve, summary, **kwargs)


class TemplateClient(BaseLLMClient):
    """基于模板的修复命令生成器（回退方案）"""
    
    def __init__(self):
        self.templates = {
            "package_update": "apt update && apt upgrade -y {package}",
            "service_restart": "systemctl restart {service}",
            "kernel_update": "apt update && apt upgrade -y linux-image-generic && reboot",
            "security_update": "apt update && apt upgrade -y && apt autoremove -y",
            "default": "# Manual review required for {cve}: {summary}"
        }
    
    async def generate_fix_command(self, cve: str, summary: str, **kwargs) -> str:
        """基于模板生成修复命令"""
        package = kwargs.get('package', '')
        
        # 简单的规则匹配
        summary_lower = summary.lower()
        
        if package and any(keyword in summary_lower for keyword in ['package', 'library', 'component']):
            return self.templates["package_update"].format(package=package.split(':')[0])
        elif any(keyword in summary_lower for keyword in ['kernel', 'linux kernel']):
            return self.templates["kernel_update"]
        elif any(keyword in summary_lower for keyword in ['service', 'daemon', 'server']):
            service = self._extract_service_name(summary, package)
            return self.templates["service_restart"].format(service=service)
        elif any(keyword in summary_lower for keyword in ['security', 'vulnerability']):
            return self.templates["security_update"]
        else:
            return self.templates["default"].format(cve=cve, summary=summary[:100])
    
    def _extract_service_name(self, summary: str, package: str) -> str:
        """从描述中提取服务名称"""
        if package:
            return package.split(':')[0]
        
        # 常见服务名称映射
        service_mapping = {
            'apache': 'apache2',
            'nginx': 'nginx',
            'mysql': 'mysql',
            'postgresql': 'postgresql',
            'ssh': 'ssh',
            'openssh': 'ssh'
        }
        
        summary_lower = summary.lower()
        for keyword, service in service_mapping.items():
            if keyword in summary_lower:
                return service
        
        return "unknown-service"


if __name__ == "__main__":
    # 测试 LLM 客户端
    async def test_llm():
        client = LLMClient()
        
        test_cve = "CVE-2023-1234"
        test_summary = "Buffer overflow in Apache HTTP Server"
        
        fix_command = await client.generate_fix_command(
            test_cve, 
            test_summary,
            package="apache2:2.4.41",
            os="Ubuntu 20.04"
        )
        
        print(f"Generated fix command: {fix_command}")
    
    asyncio.run(test_llm())
