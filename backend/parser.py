"""
Vuls JSON 解析器
功能：解析 Vuls 扫描结果，提取主机和漏洞信息
"""

import json
import os
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from loguru import logger
from pydantic import BaseModel, Field


class VulnerabilityInfo(BaseModel):
    """漏洞信息模型"""
    cve: str
    summary: str
    cvss: float = 0.0
    package: str = ""
    patchable: str = "unknown"
    published: str = ""
    modified: str = ""


class HostInfo(BaseModel):
    """主机信息模型"""
    ip: str
    hostname: str = ""
    os: str = ""
    kernel: str = ""
    scan_time: str = ""
    vulnerabilities: List[VulnerabilityInfo] = Field(default_factory=list)
    risk_score: float = 0.0


class VulsParser:
    """Vuls 扫描结果解析器"""
    
    def __init__(self):
        self.logger = logger
        
    def parse_results(self, results_dir: str = "./results") -> List[Dict[str, Any]]:
        """
        解析 Vuls 扫描结果目录中的所有 JSON 文件
        
        Args:
            results_dir: 扫描结果目录路径
            
        Returns:
            解析后的主机和漏洞信息列表
        """
        if not os.path.exists(results_dir):
            self.logger.warning(f"Results directory not found: {results_dir}")
            return []
        
        all_results = []
        json_files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
        
        if not json_files:
            self.logger.warning(f"No JSON files found in {results_dir}")
            return []
        
        for json_file in json_files:
            file_path = os.path.join(results_dir, json_file)
            try:
                result = self._parse_single_file(file_path)
                if result:
                    all_results.extend(result)
            except Exception as e:
                self.logger.error(f"Error parsing {json_file}: {e}")
                continue
        
        self.logger.info(f"Parsed {len(all_results)} host results from {len(json_files)} files")
        return all_results
    
    def _parse_single_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        解析单个 JSON 文件
        
        Args:
            file_path: JSON 文件路径
            
        Returns:
            解析后的主机信息列表
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = []
        
        # Vuls 输出格式可能有多种，这里处理常见的格式
        if isinstance(data, dict):
            # 单主机结果
            if 'ServerName' in data or 'Family' in data:
                host_result = self._parse_host_data(data)
                if host_result:
                    results.append(host_result)
            # 多主机结果
            else:
                for server_name, server_data in data.items():
                    if isinstance(server_data, dict):
                        host_result = self._parse_host_data(server_data, server_name)
                        if host_result:
                            results.append(host_result)
        
        return results
    
    def _parse_host_data(self, data: Dict[str, Any], server_name: str = None) -> Dict[str, Any]:
        """
        解析单个主机的数据
        
        Args:
            data: 主机数据字典
            server_name: 服务器名称
            
        Returns:
            格式化的主机信息
        """
        try:
            # 提取基本主机信息
            host_info = {
                "ip": self._extract_ip(data, server_name),
                "hostname": data.get('ServerName', server_name or ''),
                "os": self._extract_os_info(data),
                "kernel": data.get('Kernel', {}).get('Release', ''),
                "scan_time": data.get('ScannedAt', ''),
                "issues": [],
                "risk_score": 0.0
            }
            
            # 解析漏洞信息
            vulnerabilities = data.get('ScannedCves', {})
            if vulnerabilities:
                issues, risk_score = self._parse_vulnerabilities(vulnerabilities)
                host_info["issues"] = issues
                host_info["risk_score"] = risk_score
            
            return host_info
            
        except Exception as e:
            self.logger.error(f"Error parsing host data: {e}")
            return None
    
    def _extract_ip(self, data: Dict[str, Any], server_name: str = None) -> str:
        """提取主机 IP 地址"""
        # 尝试从多个字段提取 IP
        ip_fields = ['IPv4Addrs', 'ServerName', 'Host']
        
        for field in ip_fields:
            if field in data:
                value = data[field]
                if isinstance(value, list) and value:
                    return value[0]
                elif isinstance(value, str):
                    # 简单的 IP 格式检查
                    if '.' in value and len(value.split('.')) == 4:
                        return value
        
        # 如果都没找到，使用 server_name
        if server_name and '.' in server_name:
            return server_name
        
        return "unknown"
    
    def _extract_os_info(self, data: Dict[str, Any]) -> str:
        """提取操作系统信息"""
        family = data.get('Family', '')
        release = data.get('Release', '')
        
        if family and release:
            return f"{family} {release}"
        elif family:
            return family
        elif release:
            return release
        else:
            return "unknown"
    
    def _parse_vulnerabilities(self, vulnerabilities: Dict[str, Any]) -> tuple:
        """
        解析漏洞信息
        
        Args:
            vulnerabilities: 漏洞数据字典
            
        Returns:
            (漏洞列表, 风险评分)
        """
        issues = []
        total_cvss = 0.0
        high_risk_count = 0
        
        for cve_id, cve_data in vulnerabilities.items():
            try:
                # 提取 CVSS 评分
                cvss_score = self._extract_cvss_score(cve_data)
                
                # 提取包信息
                packages = self._extract_package_info(cve_data)
                
                # 判断是否可修复
                patchable = self._check_patchable(cve_data)
                
                issue = {
                    "cve": cve_id,
                    "summary": cve_data.get('Summary', ''),
                    "cvss": cvss_score,
                    "package": packages,
                    "patchable": patchable,
                    "published": cve_data.get('PublishedDate', ''),
                    "modified": cve_data.get('LastModifiedDate', '')
                }
                
                issues.append(issue)
                total_cvss += cvss_score
                
                if cvss_score >= 7.0:
                    high_risk_count += 1
                    
            except Exception as e:
                self.logger.warning(f"Error parsing CVE {cve_id}: {e}")
                continue
        
        # 计算风险评分 (加权平均 + 高风险漏洞数量)
        if issues:
            avg_cvss = total_cvss / len(issues)
            risk_score = avg_cvss + (high_risk_count * 0.5)
        else:
            risk_score = 0.0
        
        return issues, min(risk_score, 10.0)  # 最高分 10
    
    def _extract_cvss_score(self, cve_data: Dict[str, Any]) -> float:
        """提取 CVSS 评分"""
        # 尝试从多个字段提取 CVSS 评分
        cvss_fields = ['CvssScore', 'Cvss3Score', 'Cvss2Score']
        
        for field in cvss_fields:
            if field in cve_data:
                score = cve_data[field]
                if isinstance(score, (int, float)) and score > 0:
                    return float(score)
        
        # 如果没有找到评分，尝试从 CVSS 对象中提取
        cvss_info = cve_data.get('Cvss3', cve_data.get('Cvss2', {}))
        if isinstance(cvss_info, dict) and 'Score' in cvss_info:
            return float(cvss_info['Score'])
        
        return 0.0
    
    def _extract_package_info(self, cve_data: Dict[str, Any]) -> str:
        """提取受影响的包信息"""
        packages = []
        
        # 从 AffectedPackages 提取
        affected_packages = cve_data.get('AffectedPackages', {})
        for pkg_name, pkg_info in affected_packages.items():
            if isinstance(pkg_info, dict):
                version = pkg_info.get('Version', '')
                if version:
                    packages.append(f"{pkg_name}:{version}")
                else:
                    packages.append(pkg_name)
        
        # 从 Packages 提取
        if not packages:
            pkg_list = cve_data.get('Packages', [])
            if isinstance(pkg_list, list):
                packages.extend(pkg_list)
        
        return ", ".join(packages[:3])  # 最多显示 3 个包
    
    def _check_patchable(self, cve_data: Dict[str, Any]) -> str:
        """检查漏洞是否可修复"""
        # 检查是否有可用的补丁
        if cve_data.get('FixAvailable', False):
            return "yes"
        
        # 检查包是否有更新版本
        affected_packages = cve_data.get('AffectedPackages', {})
        for pkg_info in affected_packages.values():
            if isinstance(pkg_info, dict):
                if pkg_info.get('FixedIn') or pkg_info.get('NewVersion'):
                    return "yes"
        
        return "unknown"
    
    def to_dataframe(self, results: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        将解析结果转换为 DataFrame
        
        Args:
            results: 解析后的结果列表
            
        Returns:
            包含所有漏洞信息的 DataFrame
        """
        rows = []
        
        for host_result in results:
            for issue in host_result.get("issues", []):
                row = {
                    "host_ip": host_result["ip"],
                    "hostname": host_result["hostname"],
                    "os": host_result["os"],
                    "cve": issue["cve"],
                    "summary": issue["summary"],
                    "cvss": issue["cvss"],
                    "package": issue["package"],
                    "patchable": issue["patchable"],
                    "scan_time": host_result["scan_time"],
                    "risk_score": host_result["risk_score"]
                }
                rows.append(row)
        
        return pd.DataFrame(rows)


if __name__ == "__main__":
    # 测试解析器
    parser = VulsParser()
    results = parser.parse_results("./results")
    
    if results:
        df = parser.to_dataframe(results)
        print(f"Parsed {len(results)} hosts with {len(df)} total issues")
        print(df.head())
    else:
        print("No results found")
