#!/usr/bin/env python3
"""자체자료 목록(internal.json) 암호화 도구. 비밀번호는 환경변수 INTERNAL_PW로만 전달한다.
  INTERNAL_PW=... python3 internal_tool.py show              # 현재 목록 복호화해 출력
  INTERNAL_PW=... python3 internal_tool.py set 목록.json     # 목록.json({categories,items})을 암호화해 저장
"""
import os, sys, json, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "internal.json")
ITER = 600000
b64 = lambda x: base64.b64encode(x).decode()

def key(pw, salt, it):
    return PBKDF2HMAC(hashes.SHA256(), 32, salt, it).derive(pw.encode())

def show(pw):
    e = json.load(open(PATH, encoding="utf-8"))["index"]
    pt = AESGCM(key(pw, base64.b64decode(e["salt"]), e["iter"])).decrypt(base64.b64decode(e["iv"]), base64.b64decode(e["ct"]), None)
    return json.loads(pt)

def setidx(pw, data):
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(key(pw, salt, ITER)).encrypt(iv, json.dumps(data, ensure_ascii=False).encode(), None)
    json.dump({"index": {"iter": ITER, "salt": b64(salt), "iv": b64(iv), "ct": b64(ct)}}, open(PATH, "w", encoding="utf-8"), indent=2)

if __name__ == "__main__":
    pw = os.environ.get("INTERNAL_PW")
    if not pw: sys.exit("INTERNAL_PW 환경변수가 필요합니다.")
    if sys.argv[1] == "show": print(json.dumps(show(pw), ensure_ascii=False, indent=2))
    elif sys.argv[1] == "set": setidx(pw, json.load(open(sys.argv[2], encoding="utf-8")))
