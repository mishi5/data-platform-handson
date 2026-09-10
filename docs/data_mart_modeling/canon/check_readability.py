#!/usr/bin/env python3
"""読みやすさ規約 §4 の機械検査。<pre>・<svg>・引用枠(.aside.kimball/.modern 内の <q>/blockquote) を除いた地の文で禁止語を数える。"""
import re, sys, html
BAN = ['壊れ','罠','効く','効か','効い','落ち','焼','畳','潰','寄せ','刺さ','踏む','解像度','回で','回）','この回','true to the grain','fan-out','正典','次元モデ']
for f in sys.argv[1:]:
    s = open(f).read()
    body = re.sub(r'<pre.*?</pre>', ' ', s, flags=re.S)
    body = re.sub(r'<svg.*?</svg>', ' ', body, flags=re.S)
    body = re.sub(r'<style.*?</style>', ' ', body, flags=re.S)
    text = html.unescape(re.sub(r'<[^>]+>', ' ', body))
    hits = {w: text.count(w) for w in BAN if text.count(w)}
    ids = set(re.findall(r'\b([CMRSJPK]\d{3}|AG?\d{2})\b', text))
    m = re.search(r'この資料で使う題材.*?</div>', body, re.S)
    box = html.unescape(re.sub(r'<[^>]+>', ' ', m.group(0))) if m else ''
    # DM00 keeps definitions in §3 サンプルデータ
    if 'サンプルデータ（シリーズ全体で使う ID）' in text: box = text
    missing = sorted(i for i in ids if i not in box)
    print(f"{f}: 禁止語={hits or 'なし'} ID未説明={missing or 'なし'} 題材枠={'あり' if (m or box==text) else 'なし'}")
