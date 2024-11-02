from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import hashlib
import os

# 1. 密钥生成
def generate_key_pair():
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()
    return private_key, public_key

# 2. 聚合公钥
def aggregate_public_keys(public_keys):
    # 使用哈希函数聚合公钥
    hash_object = hashlib.sha256()
    for pub_key in public_keys:
        pub_bytes = pub_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        hash_object.update(pub_bytes)
    aggregated_public_key = hash_object.digest()
    return aggregated_public_key

# 3. 签名生成
def sign_message(message, private_key):
    signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
    return signature

# 4. 签名聚合
def aggregate_signatures(signatures, message, aggregated_public_key):
    # 使用哈希函数聚合签名
    hash_object = hashlib.sha256()
    for sig in signatures:
        hash_object.update(sig)
    aggregated_signature = hash_object.digest()
    return aggregated_signature

# 5. 签名验证
def verify_aggregated_signature(message, aggregated_signature, aggregated_public_key):
    # 重新生成聚合签名以验证
    hash_object = hashlib.sha256()
    for pub_key in public_keys:
        pub_bytes = pub_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        hash_object.update(pub_bytes)
    recalculated_aggregated_public_key = hash_object.digest()

    if recalculated_aggregated_public_key != aggregated_public_key:
        return False

    # 重新生成聚合签名以验证
    hash_object = hashlib.sha256()
    for sig in signatures:
        hash_object.update(sig)
    recalculated_aggregated_signature = hash_object.digest()

    return recalculated_aggregated_signature == aggregated_signature

# 示例主流程
if __name__ == "__main__":
    # 初始化节点数量
    n = 3

    # 1. 密钥生成
    private_keys = []
    public_keys = []
    for _ in range(n):
        priv_key, pub_key = generate_key_pair()
        private_keys.append(priv_key)
        public_keys.append(pub_key)

    # 2. 聚合公钥
    aggregated_public_key = aggregate_public_keys(public_keys)

    # 3. 签名生成
    message = b"This is a test message."
    signatures = [sign_message(message, priv_key) for priv_key in private_keys]

    # 4. 签名聚合
    aggregated_signature = aggregate_signatures(signatures, message, aggregated_public_key)

    # 5. 签名验证
    is_valid = verify_aggregated_signature(message, aggregated_signature, aggregated_public_key)
    print("Is the aggregated signature valid?", is_valid)