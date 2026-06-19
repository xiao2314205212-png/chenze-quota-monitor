"""
陈泽网注册名额监控 v3.0
- GitHub Actions 每60秒调用一次
- state.json 持久化
- 飞书卡片通知
"""
import urllib.request, json, os, time
from datetime import datetime, timedelta, timezone

SURL = "https://ukmhzxpmxknorqqzcwrb.supabase.co"
SKEY = "sb_publishable_xCrZLEe_85OqDESzFdGzTw_zI2ZVXTU"

FA = os.environ["FEISHU_APP_ID"]
FS = os.environ["FEISHU_APP_SECRET"]
FC = os.environ["FEISHU_CHAT_ID"]

SF = "state.json"
HB = 3 * 3600

def now():
    return (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%m-%d %H:%M:%S")

def fq():
    u = f"{SURL}/rest/v1/system_config?select=key,value"
    r = urllib.request.Request(u, headers={"apikey": SKEY, "Authorization": f"Bearer {SKEY}"})
    with urllib.request.urlopen(r, timeout=15) as resp:
        items = json.loads(resp.read())
    c = {}
    for i in items:
        c[i["key"]] = i["value"]
    return c

def pq(c):
    e = c.get("registration_enabled", "false")
    q = int(c.get("registration_quota", "0"))
    u = int(c.get("registration_used", "0"))
    a = max(0, q - u) if q > 0 else 999999
    return {"enabled": e, "quota": q, "used": u, "avail": a}

def ft():
    u = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    b = json.dumps({"app_id": FA, "app_secret": FS}).encode()
    r = urllib.request.Request(u, data=b, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(r, timeout=10) as resp:
        return json.loads(resp.read())["tenant_access_token"]

def sf(tk, title, content):
    card = {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": title}, "template": "orange"},
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": content}},
            {"tag": "hr"},
            {"tag": "note", "elements": [{"tag": "plain_text", "content": f"陈泽网监控 | 北京时间 {now()}"}]}
        ]
    }
    u = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    b = json.dumps({"receive_id": FC, "msg_type": "interactive", "content": json.dumps(card)}).encode()
    r = urllib.request.Request(u, data=b, headers={"Authorization": f"Bearer {tk}", "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(r, timeout=10) as resp:
        return json.loads(resp.read())

def ls():
    try:
        with open(SF) as f:
            return json.load(f)
    except:
        return None

def ss(s):
    with open(SF, "w") as f:
        json.dump(s, f, ensure_ascii=False)

def main():
    cf = fq()
    cur = pq(cf)
    prev = ls()

    print(f"[{now()}] 开关={'开' if cur['enabled']=='true' else '关'} 名额={cur['used']}/{cur['quota']} 可用={cur['avail']}")

    ch = []
    if prev:
        if cur["enabled"] != prev["enabled"]:
            ch.append(f"注册已{'开启' if cur['enabled']=='true' else '关闭'}")
        if cur["quota"] != prev["quota"]:
            ch.append(f"名额上限 {prev['quota']} -> {cur['quota']}")
        if cur["used"] != prev["used"]:
            ch.append(f"已用名额 {prev['used']} -> {cur['used']}")
        if cur["avail"] > 0 and prev["avail"] == 0:
            ch.append(f"名额开放！可用 {cur['avail']} 个")

    ts = int(time.time())
    lh = prev.get("last_heartbeat", 0) if prev else 0
    sh = (ts - lh) >= HB
    cur["last_heartbeat"] = ts if sh else lh

    ss(cur)

    tk = ft()
    try:
        if ch:
            m = "\n".join(["• " + c for c in ch] + ["", f"名额 {cur['used']}/{cur['quota']}（可用 {cur['avail']}）"])
            sf(tk, "陈泽网名额开放！快抢！", m)
            print("名额通知已发送")
        elif prev is None:
            m = f"注册开关: {'开启' if cur['enabled']=='true' else '关闭'}\n名额上限: {cur['quota']}\n已用名额: {cur['used']}\n可用名额: {cur['avail']}"
            sf(tk, "陈泽网监控已启动", m)
            print("启动通知已发送")
        elif sh:
            m = f"名额 {cur['used']}/{cur['quota']}（可用 {cur['avail']}）"
            sf(tk, "心跳检测", m)
            print("心跳已发送")
        else:
            print(f"无变化（距上次心跳 {ts-lh} 秒）")
    except Exception as e:
        print(f"飞书异常: {e}")

if __name__ == "__main__":
    main()
