#!/usr/bin/env python3
"""
解密API key - 支持企业版AES加密
"""

import binascii
import sys
import os

# 尝试导入企业版加密功能
try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import algorithms
    from cryptography.hazmat.primitives.ciphers import Cipher
    from cryptography.hazmat.primitives.ciphers import modes
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("警告: cryptography库不可用，无法解密AES加密的数据")

# 获取环境变量中的加密密钥
ENCRYPTION_KEY_SECRET = os.environ.get("ENCRYPTION_KEY_SECRET", "")

def get_trimmed_key(key: str) -> bytes:
    """获取修剪后的加密密钥"""
    encoded_key = key.encode()
    key_length = len(encoded_key)
    if key_length < 16:
        raise RuntimeError("Invalid ENCRYPTION_KEY_SECRET - too short")
    elif key_length > 32:
        key = key[:32]
    elif key_length not in (16, 24, 32):
        valid_lengths = [16, 24, 32]
        key = key[: min(valid_lengths, key=lambda x: abs(x - key_length))]
    
    return encoded_key

def decrypt_aes_bytes(input_bytes: bytes, encryption_key: str) -> str:
    """使用AES解密字节数据"""
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography库不可用")
    
    key = get_trimmed_key(encryption_key)
    iv = input_bytes[:16]
    encrypted_data = input_bytes[16:]
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
    
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    decrypted_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()
    
    return decrypted_data.decode()

def decrypt_api_key(hex_string: str) -> str:
    """
    解密API key - 尝试多种方法
    """
    print(f"当前ENCRYPTION_KEY_SECRET: {ENCRYPTION_KEY_SECRET}")
    print(f"是否有加密密钥: {'是' if ENCRYPTION_KEY_SECRET else '否'}")
    print(f"加密库是否可用: {'是' if CRYPTO_AVAILABLE else '否'}")
    print()
    
    # 将hex字符串转换为bytes
    try:
        if hex_string.startswith("x"):
            hex_string = hex_string[1:]
        elif hex_string.startswith("\\x"):
            hex_string = hex_string[2:]
        
        encrypted_bytes = binascii.unhexlify(hex_string)
        print(f"原始bytes: {encrypted_bytes}")
        print(f"bytes长度: {len(encrypted_bytes)}")
        
    except Exception as e:
        return f"错误: 无效的hex字符串: {e}"
    
    # 方法1: 简单UTF-8解码（MIT版本无加密）
    try:
        decrypted_str = encrypted_bytes.decode('utf-8')
        print(f"方法1 - UTF-8解码成功: {decrypted_str}")
        return decrypted_str
    except:
        print("方法1 - UTF-8解码失败")
    
    # 方法2: AES解密（如果有加密密钥）
    if ENCRYPTION_KEY_SECRET and CRYPTO_AVAILABLE:
        try:
            decrypted_str = decrypt_aes_bytes(encrypted_bytes, ENCRYPTION_KEY_SECRET)
            print(f"方法2 - AES解密成功: {decrypted_str}")
            return decrypted_str
        except Exception as e:
            print(f"方法2 - AES解密失败: {e}")
    
    # 方法3: 尝试常见的加密密钥
    common_keys = ["default_key", "onyx_key", "test_key", "encryption_key"]
    if CRYPTO_AVAILABLE:
        for test_key in common_keys:
            try:
                decrypted_str = decrypt_aes_bytes(encrypted_bytes, test_key)
                print(f"方法3 - 使用密钥'{test_key}'解密成功: {decrypted_str}")
                return decrypted_str
            except:
                continue
    
    return "无法解密 - 所有方法都失败了"

if __name__ == "__main__":
    # 你的加密API key
    encrypted_api_key = "b6d02fa7a7045a8548437148fd64c395cf4965ff8663e3e48647f014e16974f5"
    
    print(f"加密的API Key: {encrypted_api_key}")
    print(f"API Key长度: {len(encrypted_api_key)}")
    print()
    
    decrypted_key = decrypt_api_key(encrypted_api_key)
    print()
    print(f"最终结果 - 解密后的API Key: {decrypted_key}")