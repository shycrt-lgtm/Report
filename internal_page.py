#!/usr/bin/env python3
"""HTML 문서를 비밀번호로 암호화해 자체자료용 페이지로 만든다 (비밀번호는 환경변수 INTERNAL_PW).
  INTERNAL_PW=... python3 internal_page.py 원본.html internal/출력.html "제목"
"""
import os, sys, json, gzip, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
ITER = 1000000
b64 = lambda x: base64.b64encode(x).decode()
SHELL = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>__TITLE__</title>
<style>body{margin:0;font-family:'Malgun Gothic','Noto Sans KR',sans-serif;background:#fff;color:#1a1a1a}
.bar{background:#001f3f;color:#fff;padding:16px;font-weight:700}.bar a{color:#cbd5e1;font-weight:400;margin-left:12px;font-size:13px;text-decoration:none}
form{max-width:340px;margin:60px auto;padding:0 16px}input,button{font:inherit;padding:10px;width:100%;box-sizing:border-box;margin-top:8px}
button{background:#001f3f;color:#fff;border:0;cursor:pointer}#err{color:#991b1b;font-size:13px;min-height:18px;margin-top:6px}</style></head>
<body><div class="bar">__TITLE__<a href="../">← 에너지 자료실</a></div>
<form id="f"><div>자체자료입니다. 비밀번호를 입력하세요.</div><input id="pw" type="password" autocomplete="current-password"><div id="err"></div><button>열기</button></form>
<script>
const P=__PAYLOAD__;
const d=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function open_(pw){
  const base=await crypto.subtle.importKey('raw',new TextEncoder().encode(pw),'PBKDF2',false,['deriveKey']);
  const key=await crypto.subtle.deriveKey({name:'PBKDF2',salt:d(P.salt),iterations:P.iter,hash:'SHA-256'},base,{name:'AES-GCM',length:256},false,['decrypt']);
  const pt=new Uint8Array(await crypto.subtle.decrypt({name:'AES-GCM',iv:d(P.iv)},key,d(P.ct)));
  const ds=new Blob([pt]).stream().pipeThrough(new DecompressionStream('gzip'));
  const html=new TextDecoder().decode(new Uint8Array(await new Response(ds).arrayBuffer()));
  document.open(); document.write(html); document.close();
}
document.getElementById('f').addEventListener('submit',async e=>{e.preventDefault();const err=document.getElementById('err');err.textContent='';
  try{await open_(document.getElementById('pw').value);}catch(x){err.textContent='비밀번호가 맞지 않습니다.';}});
(async()=>{let s=null;try{s=sessionStorage.getItem('energyInternal.pw');}catch(e){}
  if(s&&crypto.subtle){try{await open_(s);}catch(e){}}})();
</script></body></html>"""
pw = os.environ.get("INTERNAL_PW") or sys.exit("INTERNAL_PW 필요")
src, out, title = sys.argv[1:4]
raw = gzip.compress(open(src, "rb").read(), 9)
salt, iv = os.urandom(16), os.urandom(12)
k = PBKDF2HMAC(hashes.SHA256(), 32, salt, ITER).derive(pw.encode())
ct = AESGCM(k).encrypt(iv, raw, None)
P = {"v": 1, "iter": ITER, "salt": b64(salt), "iv": b64(iv), "ct": b64(ct)}
open(out, "w", encoding="utf-8").write(SHELL.replace("__TITLE__", title).replace("__PAYLOAD__", json.dumps(P)))
