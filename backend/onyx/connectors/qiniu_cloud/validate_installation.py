"""
七牛云连接器安装验证模块

验证七牛云 SDK 和连接器的正确安装和配置
"""

import os
from typing import Dict, Any

from onyx.utils.logger import setup_logger

logger = setup_logger()


def validate_qiniu_installation() -> Dict[str, Any]:
    """
    验证七牛云连接器安装
    
    Returns:
        验证结果字典
    """
    result = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "dependencies": {},
        "configuration": {}
    }
    
    # 1. 检查 qiniu SDK 安装
    try:
        import qiniu
        from qiniu import Auth, put_file, put_data, BucketManager
        result["dependencies"]["qiniu"] = {
            "installed": True,
            "version": getattr(qiniu, "__version__", "unknown")
        }
    except ImportError as e:
        result["is_valid"] = False
        result["errors"].append(f"七牛云 SDK 未安装: {e}")
        result["dependencies"]["qiniu"] = {"installed": False}
    
    # 2. 检查 requests 依赖
    try:
        import requests
        result["dependencies"]["requests"] = {
            "installed": True,
            "version": getattr(requests, "__version__", "unknown")
        }
    except ImportError as e:
        result["is_valid"] = False
        result["errors"].append(f"requests 库未安装: {e}")
        result["dependencies"]["requests"] = {"installed": False}
    
    # 3. 检查必需的环境变量
    required_env_vars = [
        "QINIU_ACCESS_KEY",
        "QINIU_SECRET_KEY",
        "QINIU_DEFAULT_BUCKET",
        "QINIU_BUCKET_DOMAIN"
    ]
    
    for var in required_env_vars:
        value = os.getenv(var)
        if value:
            result["configuration"][var] = "已设置"
        else:
            result["warnings"].append(f"环境变量 {var} 未设置")
            result["configuration"][var] = "未设置"
    
    # 4. 检查可选环境变量
    optional_env_vars = [
        "QINIU_REGION"
    ]
    
    for var in optional_env_vars:
        value = os.getenv(var)
        if value:
            result["configuration"][var] = value
        else:
            result["configuration"][var] = "未设置（使用默认值）"
    
    # 5. 基本连接测试
    if all(os.getenv(var) for var in required_env_vars):
        try:
            from qiniu import Auth, BucketManager
            
            access_key = os.getenv("QINIU_ACCESS_KEY")
            secret_key = os.getenv("QINIU_SECRET_KEY")
            bucket_name = os.getenv("QINIU_DEFAULT_BUCKET")
            
            auth = Auth(access_key, secret_key)
            bucket_manager = BucketManager(auth)
            
            # 测试列举文件权限
            ret, eof, info = bucket_manager.list(bucket_name, limit=1)
            if ret is not None:
                result["configuration"]["connection_test"] = "✅ 连接成功"
            else:
                result["warnings"].append(f"连接测试失败: {info}")
                result["configuration"]["connection_test"] = "❌ 连接失败"
                
        except Exception as e:
            result["warnings"].append(f"连接测试异常: {e}")
            result["configuration"]["connection_test"] = "❌ 连接异常"
    else:
        result["configuration"]["connection_test"] = "跳过（缺少必需配置）"
    
    # 6. 连接器导入测试
    try:
        from onyx.connectors.qiniu_cloud.connector import QiniuCloudConnector
        result["dependencies"]["qiniu_connector"] = {"installed": True}
    except ImportError as e:
        result["is_valid"] = False
        result["errors"].append(f"七牛云连接器导入失败: {e}")
        result["dependencies"]["qiniu_connector"] = {"installed": False}
    
    return result


def print_validation_result(result: Dict[str, Any]) -> None:
    """
    打印验证结果
    
    Args:
        result: 验证结果字典
    """
    print("=" * 60)
    print("七牛云连接器安装验证结果")
    print("=" * 60)
    
    # 总体状态
    status = "✅ 通过" if result["is_valid"] else "❌ 失败"
    print(f"总体状态: {status}")
    print()
    
    # 依赖检查
    print("📦 依赖检查:")
    for dep, info in result["dependencies"].items():
        status = "✅" if info["installed"] else "❌"
        version = f" (v{info['version']})" if info.get("version") else ""
        print(f"  {status} {dep}{version}")
    print()
    
    # 配置检查
    print("⚙️ 配置检查:")
    for config, status in result["configuration"].items():
        print(f"  {config}: {status}")
    print()
    
    # 错误信息
    if result["errors"]:
        print("❌ 错误:")
        for error in result["errors"]:
            print(f"  • {error}")
        print()
    
    # 警告信息
    if result["warnings"]:
        print("⚠️ 警告:")
        for warning in result["warnings"]:
            print(f"  • {warning}")
        print()
    
    # 安装建议
    if not result["is_valid"]:
        print("📋 安装建议:")
        print("  1. 安装七牛云 SDK:")
        print("     pip install qiniu")
        print("  2. 设置环境变量:")
        print("     export QINIU_ACCESS_KEY=your-access-key")
        print("     export QINIU_SECRET_KEY=your-secret-key")
        print("     export QINIU_DEFAULT_BUCKET=your-bucket")
        print("     export QINIU_BUCKET_DOMAIN=your-domain")
        print("  3. 在七牛云控制台创建存储桶并获取域名")
        print()


if __name__ == "__main__":
    result = validate_qiniu_installation()
    print_validation_result(result)