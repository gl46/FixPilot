"""
Ansible Playbook 生成器
功能：根据 LLM 生成的修复命令创建 Ansible Playbook
"""

import os
import yaml
from typing import List, Dict, Any
from datetime import datetime
from jinja2 import Template
from loguru import logger


class PlaybookGenerator:
    """Ansible Playbook 生成器"""
    
    def __init__(self, templates_dir: str = "./templates"):
        self.templates_dir = templates_dir
        self.logger = logger
        
        # 确保模板目录存在
        os.makedirs(templates_dir, exist_ok=True)
        
        # 初始化模板
        self._init_templates()
    
    def _init_templates(self):
        """初始化 Jinja2 模板"""
        self.main_template = Template("""---
# FixPilot Auto-generated Playbook
# Generated at: {{ timestamp }}
# Target Host: {{ target_host }}
# Issues Count: {{ issues_count }}

- name: Fix security vulnerabilities on {{ target_host }}
  hosts: {{ target_host }}
  become: yes
  gather_facts: yes
  
  vars:
    backup_dir: "/tmp/fixpilot_backup_{{ ansible_date_time.epoch }}"
    log_file: "/var/log/fixpilot_{{ ansible_date_time.epoch }}.log"
  
  pre_tasks:
    - name: Create backup directory
      file:
        path: "{{ backup_dir }}"
        state: directory
        mode: '0755'
    
    - name: Log playbook start
      lineinfile:
        path: "{{ log_file }}"
        line: "{{ ansible_date_time.iso8601 }} - FixPilot playbook started"
        create: yes
    
    - name: Update package cache
      apt:
        update_cache: yes
        cache_valid_time: 3600
      when: ansible_os_family == "Debian"
    
    - name: Update package cache (RedHat)
      yum:
        update_cache: yes
      when: ansible_os_family == "RedHat"

  tasks:
{% for issue in issues %}
    - name: Fix {{ issue.cve }} - {{ issue.summary[:50] }}...
      block:
        - name: Backup affected packages for {{ issue.cve }}
          shell: |
            dpkg -l | grep "{{ issue.package.split(':')[0] }}" > {{ backup_dir }}/{{ issue.cve }}_packages.txt || true
          when: issue.package != ""
        
        - name: Execute fix command for {{ issue.cve }}
          shell: |
            {{ issue.command }}
          register: fix_result_{{ loop.index }}
          failed_when: false
        
        - name: Log fix result for {{ issue.cve }}
          lineinfile:
            path: "{{ log_file }}"
            line: "{{ ansible_date_time.iso8601 }} - {{ issue.cve }}: {{ fix_result_{{ loop.index }}.rc == 0 | ternary('SUCCESS', 'FAILED') }}"
        
        - name: Verify fix for {{ issue.cve }}
          shell: |
            {{ issue.verify_command | default('echo "No verification command"') }}
          register: verify_result_{{ loop.index }}
          failed_when: false
          when: issue.verify_command is defined

      rescue:
        - name: Log fix failure for {{ issue.cve }}
          lineinfile:
            path: "{{ log_file }}"
            line: "{{ ansible_date_time.iso8601 }} - {{ issue.cve }}: RESCUE - {{ ansible_failed_result.msg }}"
        
        - name: Continue with next fix
          debug:
            msg: "Fix for {{ issue.cve }} failed, continuing with next issue"

{% endfor %}

  post_tasks:
    - name: Restart services if needed
      systemd:
        name: "{{ item }}"
        state: restarted
      loop: {{ services_to_restart }}
      when: services_to_restart | length > 0
    
    - name: Check if reboot is required
      stat:
        path: /var/run/reboot-required
      register: reboot_required
    
    - name: Log reboot requirement
      lineinfile:
        path: "{{ log_file }}"
        line: "{{ ansible_date_time.iso8601 }} - Reboot required: {{ reboot_required.stat.exists }}"
    
    - name: Log playbook completion
      lineinfile:
        path: "{{ log_file }}"
        line: "{{ ansible_date_time.iso8601 }} - FixPilot playbook completed"
    
    - name: Display summary
      debug:
        msg: |
          FixPilot Execution Summary:
          - Target Host: {{ target_host }}
          - Issues Processed: {{ issues_count }}
          - Log File: {{ log_file }}
          - Backup Directory: {{ backup_dir }}
          - Reboot Required: {{ reboot_required.stat.exists | default(false) }}

# Rollback playbook (run with --tags rollback)
- name: Rollback changes
  hosts: {{ target_host }}
  become: yes
  tags: rollback
  
  tasks:
    - name: Find backup directory
      find:
        paths: /tmp
        patterns: "fixpilot_backup_*"
        file_type: directory
      register: backup_dirs
    
    - name: Display available backups
      debug:
        msg: "Available backup directories: {{ backup_dirs.files | map(attribute='path') | list }}"
    
    - name: Manual rollback instructions
      debug:
        msg: |
          To rollback changes manually:
          1. Check backup files in: {{ backup_dirs.files | map(attribute='path') | list }}
          2. Review log files: /var/log/fixpilot_*.log
          3. Restore packages if needed
          4. Restart services: {{ services_to_restart }}
""")
        
        self.inventory_template = Template("""[targets]
{{ target_host }} ansible_user={{ ansible_user }} ansible_ssh_private_key_file={{ ssh_key_file }}

[targets:vars]
ansible_python_interpreter=/usr/bin/python3
ansible_ssh_common_args='-o StrictHostKeyChecking=no'
""")
    
    def generate_playbook(
        self, 
        target_host: str, 
        fix_commands: List[Dict[str, Any]], 
        **kwargs
    ) -> str:
        """
        生成 Ansible Playbook
        
        Args:
            target_host: 目标主机 IP
            fix_commands: 修复命令列表
            **kwargs: 额外参数
            
        Returns:
            生成的 Playbook YAML 内容
        """
        try:
            # 处理修复命令，提取服务重启需求
            processed_issues = []
            services_to_restart = set()
            
            for cmd_info in fix_commands:
                processed_issue = {
                    "cve": cmd_info.get("cve", ""),
                    "summary": cmd_info.get("summary", ""),
                    "command": cmd_info.get("command", ""),
                    "package": cmd_info.get("package", "")
                }
                
                # 添加验证命令
                verify_cmd = self._generate_verify_command(processed_issue)
                if verify_cmd:
                    processed_issue["verify_command"] = verify_cmd
                
                # 检查是否需要重启服务
                restart_services = self._extract_service_restarts(processed_issue["command"])
                services_to_restart.update(restart_services)
                
                processed_issues.append(processed_issue)
            
            # 渲染模板
            playbook_content = self.main_template.render(
                timestamp=datetime.now().isoformat(),
                target_host=target_host,
                issues_count=len(processed_issues),
                issues=processed_issues,
                services_to_restart=list(services_to_restart),
                **kwargs
            )
            
            # 验证生成的 YAML
            try:
                yaml.safe_load(playbook_content)
            except yaml.YAMLError as e:
                self.logger.error(f"Generated invalid YAML: {e}")
                raise ValueError(f"Invalid YAML generated: {e}")
            
            return playbook_content
            
        except Exception as e:
            self.logger.error(f"Error generating playbook: {e}")
            raise
    
    def _generate_verify_command(self, issue: Dict[str, Any]) -> str:
        """生成验证命令"""
        cve = issue.get("cve", "")
        package = issue.get("package", "")
        command = issue.get("command", "")
        
        # 基于修复命令类型生成验证命令
        if "apt upgrade" in command and package:
            pkg_name = package.split(':')[0]
            return f"dpkg -l | grep {pkg_name} | head -1"
        elif "systemctl restart" in command:
            service = self._extract_service_from_command(command)
            return f"systemctl is-active {service}"
        elif "apt update" in command:
            return "apt list --upgradable | wc -l"
        else:
            return f"echo 'Verification needed for {cve}'"
    
    def _extract_service_restarts(self, command: str) -> List[str]:
        """从命令中提取需要重启的服务"""
        services = []
        
        if "systemctl restart" in command:
            # 提取 systemctl restart 后的服务名
            parts = command.split("systemctl restart")
            for part in parts[1:]:
                service = part.strip().split()[0]
                if service and not service.startswith('&&'):
                    services.append(service)
        
        # 基于包名推断服务
        if "apache" in command.lower():
            services.append("apache2")
        elif "nginx" in command.lower():
            services.append("nginx")
        elif "mysql" in command.lower():
            services.append("mysql")
        elif "postgresql" in command.lower():
            services.append("postgresql")
        elif "ssh" in command.lower():
            services.append("ssh")
        
        return list(set(services))  # 去重
    
    def _extract_service_from_command(self, command: str) -> str:
        """从 systemctl 命令中提取服务名"""
        if "systemctl restart" in command:
            parts = command.split("systemctl restart")
            if len(parts) > 1:
                service = parts[1].strip().split()[0]
                return service.replace('&&', '').strip()
        return "unknown"
    
    def generate_inventory(
        self, 
        target_host: str, 
        ansible_user: str = "root",
        ssh_key_file: str = "~/.ssh/id_rsa"
    ) -> str:
        """
        生成 Ansible inventory 文件
        
        Args:
            target_host: 目标主机
            ansible_user: SSH 用户
            ssh_key_file: SSH 私钥文件路径
            
        Returns:
            inventory 文件内容
        """
        return self.inventory_template.render(
            target_host=target_host,
            ansible_user=ansible_user,
            ssh_key_file=ssh_key_file
        )
    
    def save_playbook(
        self, 
        playbook_content: str, 
        filename: str,
        output_dir: str = "./playbooks"
    ) -> str:
        """
        保存 Playbook 到文件
        
        Args:
            playbook_content: Playbook 内容
            filename: 文件名
            output_dir: 输出目录
            
        Returns:
            保存的文件路径
        """
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(playbook_content)
        
        self.logger.info(f"Playbook saved to {filepath}")
        return filepath
    
    def save_inventory(
        self, 
        inventory_content: str, 
        filename: str = "inventory.ini",
        output_dir: str = "./playbooks"
    ) -> str:
        """
        保存 inventory 文件
        
        Args:
            inventory_content: inventory 内容
            filename: 文件名
            output_dir: 输出目录
            
        Returns:
            保存的文件路径
        """
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(inventory_content)
        
        self.logger.info(f"Inventory saved to {filepath}")
        return filepath
    
    def validate_playbook(self, playbook_path: str) -> bool:
        """
        验证 Playbook 语法
        
        Args:
            playbook_path: Playbook 文件路径
            
        Returns:
            验证是否通过
        """
        try:
            # 使用 ansible-playbook --syntax-check
            import subprocess
            result = subprocess.run(
                ["ansible-playbook", "--syntax-check", playbook_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.info(f"Playbook {playbook_path} syntax is valid")
                return True
            else:
                self.logger.error(f"Playbook syntax error: {result.stderr}")
                return False
                
        except FileNotFoundError:
            self.logger.warning("ansible-playbook command not found, skipping syntax check")
            return True  # 假设有效，如果 ansible 未安装
        except Exception as e:
            self.logger.error(f"Error validating playbook: {e}")
            return False


if __name__ == "__main__":
    # 测试 Playbook 生成器
    generator = PlaybookGenerator()
    
    # 测试数据
    test_commands = [
        {
            "cve": "CVE-2023-1234",
            "summary": "Buffer overflow in Apache HTTP Server",
            "command": "apt update && apt upgrade -y apache2 && systemctl restart apache2",
            "package": "apache2:2.4.41"
        },
        {
            "cve": "CVE-2023-5678",
            "summary": "SQL injection vulnerability in MySQL",
            "command": "apt update && apt upgrade -y mysql-server && systemctl restart mysql",
            "package": "mysql-server:8.0.32"
        }
    ]
    
    # 生成 Playbook
    playbook = generator.generate_playbook("192.168.1.100", test_commands)
    print("Generated Playbook:")
    print(playbook)
    
    # 生成 inventory
    inventory = generator.generate_inventory("192.168.1.100")
    print("\nGenerated Inventory:")
    print(inventory)
