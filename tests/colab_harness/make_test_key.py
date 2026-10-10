# TEST: jednorazowy klucz RSA w formacie klucza serwisowego CLMS (atrapa; nie daje dostępu do żadnej usługi).
# Użycie: python make_test_key.py <ścieżka clms_token.json> <ścieżka pub.pem>
import json, sys
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

key_path, pub_path = Path(sys.argv[1]), Path(sys.argv[2])
priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pem = priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                         serialization.NoEncryption()).decode()
key_path.parent.mkdir(parents=True, exist_ok=True)
key_path.write_text(json.dumps({"client_id": "TEST", "user_id": "TEST",
                                "token_uri": "https://land.copernicus.eu/@@oauth2-token", "private_key": pem}))
pub_path.write_bytes(priv.public_key().public_bytes(serialization.Encoding.PEM,
                                                    serialization.PublicFormat.SubjectPublicKeyInfo))
print("Zapisano atrapę klucza:", key_path, "i klucz publiczny:", pub_path)
