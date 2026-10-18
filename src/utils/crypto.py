import hmac
import hashlib
from typing import Union

def generate_signature(data: Union[str, bytes], secret_key: Union[str, bytes]) -> str:
    """
    使用 HMAC-SHA256 算法生成签名
    
    Args:
        data: 要签名的数据，可以是字符串或字节
        secret_key: 密钥，可以是字符串或字节
        
    Returns:
        str: 十六进制编码的签名字符串
        
    Example:
        >>> signature = generate_signature("test", "secret")
        >>> print(signature)
        '0329a06b62cd16b33eb6792be8c60b158d89a2ee3a876fce9a881ebb488c0914'
    """
    # 确保输入是字节类型
    if isinstance(data, str):
        data = data.encode('utf-8')
    if isinstance(secret_key, str):
        secret_key = secret_key.encode('utf-8')
    
    # 创建 HMAC-SHA256 对象
    hmac_obj = hmac.new(
        key=secret_key,
        msg=data,
        digestmod=hashlib.sha256
    )
    
    # 生成签名并转换为十六进制字符串
    return hmac_obj.hexdigest()

# Example usage
if __name__ == "__main__":
    # 测试用例
    test_data = "test"
    test_key = "secret"
    
    # 生成签名
    signature = generate_signature(test_data, test_key)
    print(f"Data: {test_data}")
    print(f"Secret Key: {test_key}")
    print(f"Signature: {signature}")
    
    # 验证签名（通过重新生成签名并比较）
    new_signature = generate_signature(test_data, test_key)
    print(f"Signature verification: {'Success' if signature == new_signature else 'Failed'}") 