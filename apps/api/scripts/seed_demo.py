"""Seed a running AskFlow API with realistic demo data (knowledge base, customers, chats,
tickets, handoffs, gaps, drafts, team, launch card).

Everything goes through the public HTTP API, so the data exercises the real pipeline:
retrieval, refusals, intent routing, cost ledger, SLA and audit log.

    ASKFLOW_ENV=development ALLOW_BOOTSTRAP_ADMIN=1 uvicorn app.main:app &
    python scripts/seed_demo.py --base http://127.0.0.1:8000

The first registered account becomes the admin (development bootstrap).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import httpx

API = "/api/v1"
ADMIN = ("admin", "admin@example.com", "Admin12345!")
CUSTOMER_PASSWORD = "Demo12345!"
CUSTOMERS = [
    ("zhangwei", "张伟"),
    ("lina", "李娜"),
    ("wangfang", "王芳"),
    ("chenjie", "陈杰"),
]
TIMEOUT_SEC = 30.0

KNOWLEDGE = {
    "退换货政策.md": """# 退换货政策
签收之日起 7 天内可申请无理由退货，商品需保持未使用、包装与配件完整。
签收之日起 15 天内如出现性能故障，可申请换货。
退款在仓库验收通过后 3-5 个工作日原路返回；使用优惠券的订单按实付金额退款。
定制商品、已激活的软件与虚拟卡券不支持无理由退货。
退货运费：质量问题由商家承担，非质量问题由买家承担，会员每月享 1 次免费退货上门取件。
""",
    "配送与物流.md": """# 配送与物流
默认使用顺丰或京东物流，下单后 48 小时内发货，预售商品以详情页时间为准。
会员包邮门槛为实付满 99 元，非会员满 199 元包邮。
偏远地区（新疆、西藏、青海）预计 5-7 天送达，其余地区 1-3 天。
可在订单详情查看运单号与物流轨迹；超过 72 小时物流无更新可联系客服催件。
支持修改收货地址的时间为发货前，发货后需联系快递改派。
""",
    "发票与报销.md": """# 发票与报销
所有订单均可开具增值税电子普通发票，下单时或订单完成后 30 天内在订单详情申请。
企业客户可申请增值税专用发票，需提供税号、开户行及账号、注册地址与电话。
电子发票在申请后 1 个工作日内发送至预留邮箱，也可在订单详情下载 PDF。
发票抬头填写错误可在 30 天内申请红冲重开一次。
""",
    "会员与积分.md": """# 会员与积分
每消费 1 元累计 1 积分，积分有效期为获得当年及次年年底。
100 积分可抵扣 1 元，单笔订单最多抵扣实付金额的 20%。
会员等级分为银卡、金卡、黑金卡，按近 12 个月消费金额自动升降级。
金卡及以上会员享专属客服通道、生日月双倍积分与每月 1 次免费退货。
""",
    "账户与安全.md": """# 账户与安全
登录问题：请确认手机号或邮箱是否正确，并尝试通过短信验证码重置密码。
连续输错密码 5 次账户将临时锁定 15 分钟。
更换绑定手机号需验证原手机号；原手机号已停用可提交身份证明人工审核，1-3 个工作日完成。
注销账户前需结清订单与售后，注销后积分与优惠券将清零且不可恢复。
""",
    "售后保修.md": """# 售后保修
自营电子产品享 1 年官方保修，部分品牌支持 2 年延保，以保修卡为准。
保修期内非人为损坏可免费维修；人为损坏、进水与私自拆机不在保修范围。
可在“我的-售后服务”提交维修申请，寄修运费由商家承担。
维修周期一般为 7-10 个工作日，维修完成后会短信通知。
""",
}

# (customer, conversation title hint, questions) — mixes answerable, out-of-scope,
# weak-evidence (becomes a knowledge gap), order lookups and a human handoff.
CONVERSATIONS = [
    ("zhangwei", ["退货政策是什么？", "退货运费谁来承担？", "退款多久能到账？"]),
    ("zhangwei", ["会员包邮门槛是多少？", "偏远地区多久能送到？"]),
    ("lina", ["怎么开增值税专用发票？", "发票抬头写错了能重开吗？"]),
    ("lina", ["积分怎么抵扣？", "金卡会员有什么权益？"]),
    ("wangfang", ["我的订单到哪了？", "ORD202410010001"]),
    ("wangfang", ["手机进水了还能保修吗？", "维修要多久？"]),
    ("chenjie", ["账号被锁了怎么办？", "原手机号停用了怎么换绑？"]),
    ("chenjie", ["你们支持分期付款吗？", "可以用数字人民币支付吗？"]),
    ("chenjie", ["帮我写一份法律意见书"]),
    ("lina", ["商品质量太差了，我要投诉"]),
    ("zhangwei", ["在吗"]),
    ("wangfang", ["退款一直没到账，我要转人工客服"]),
    ("chenjie", ["换绑一直审核不通过，帮我联系人工客服"]),
]

TICKETS = [
    ("zhangwei", "退款超过 5 个工作日未到账", "high", "refund", "processing"),
    ("lina", "电子发票未收到邮件", "medium", "invoice", "resolved"),
    ("wangfang", "快递显示签收但未收到货", "urgent", "logistics", "processing"),
    ("chenjie", "积分到账数量不对", "low", "account", "pending"),
    ("lina", "申请开具增值税专用发票", "medium", "invoice", "pending"),
    ("zhangwei", "耳机左耳无声，申请换货", "high", "after_sales", "pending"),
]

GAP_DRAFT = (
    "分期付款说明",
    (
        "支持花呗分期与信用卡分期，单笔满 600 元可选 3/6/12 期；"
        "3 期免息，6 期及以上按支付渠道费率收取手续费。"
    ),
)


@dataclass
class Session:
    http: httpx.Client
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def post(self, path: str, **kwargs: object) -> dict:
        resp = self.http.post(API + path, headers=self.headers, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def patch(self, path: str, body: dict) -> dict:
        resp = self.http.patch(API + path, headers=self.headers, json=body)
        resp.raise_for_status()
        return resp.json()

    def get(self, path: str) -> dict | list:
        resp = self.http.get(API + path, headers=self.headers)
        resp.raise_for_status()
        return resp.json()


def account(http: httpx.Client, username: str, email: str, password: str) -> Session:
    http.post(
        API + "/admin/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    resp = http.post(API + "/admin/auth/login", json={"username": username, "password": password})
    resp.raise_for_status()
    return Session(http, resp.json()["access_token"])


def seed_knowledge(admin: Session) -> None:
    for filename, body in KNOWLEDGE.items():
        files = {"file": (filename, body.encode("utf-8"), "text/markdown")}
        admin.post("/embedding/upload", files=files, data={"title": filename.removesuffix(".md")})


def seed_conversations(users: dict[str, Session]) -> list[str]:
    """Run every chat; rate the first answer of each conversation. Returns conversation ids."""
    ids = []
    for username, questions in CONVERSATIONS:
        user = users[username]
        conv = user.post("/chat/conversations", json={})
        ids.append(conv["id"])
        for i, question in enumerate(questions):
            turn = user.post(f"/chat/conversations/{conv['id']}/messages", json={"content": question})
            if i == 0:
                rating = -1 if turn["assistant_message"]["meta"].get("refused") else 1
                user.http.put(
                    f"{API}/chat/messages/{turn['assistant_message']['id']}/feedback",
                    headers=user.headers,
                    json={"rating": rating, "comment": ""},
                ).raise_for_status()
    return ids


def seed_tickets(admin: Session, users: dict[str, Session]) -> None:
    for username, title, priority, kind, status in TICKETS:
        ticket = users[username].post(
            "/tickets",
            json={"title": title, "description": title, "priority": priority, "type": kind},
        )
        if status != "pending":
            admin.patch(f"/admin/tickets/{ticket['id']}", {"status": "processing", "assignee": "admin"})
        if status == "resolved":
            admin.patch(f"/admin/tickets/{ticket['id']}", {"status": "resolved"})


def seed_operations(admin: Session) -> None:
    handoffs = admin.get("/admin/handoffs")
    items = handoffs["items"] if isinstance(handoffs, dict) else handoffs
    for handoff in items[:1]:
        admin.post(f"/admin/handoffs/{handoff['id']}/claim")
        admin.post(
            f"/admin/handoffs/{handoff['id']}/reply",
            json={"content": "您好，我是售后专员小周，已为您加急核查退款进度，预计今天内给您答复。"},
        )
    team = admin.post("/admin/teams", json={"name": "售后一组", "description": "退换货与保修", "intent_scope": "faq"})
    admin.post(f"/admin/teams/{team['id']}/members", json={"user_id": admin.get("/admin/auth/me")["id"]})
    gaps = admin.get("/admin/gaps")
    gap_items = gaps["items"] if isinstance(gaps, dict) else gaps
    gap_id = gap_items[0]["id"] if gap_items else None
    admin.post("/admin/drafts", json={"title": GAP_DRAFT[0], "content": GAP_DRAFT[1], "gap_id": gap_id})
    admin.post(
        "/admin/launch-cards",
        json={
            "title": "上线知识库 v2：补充分期与保修条款",
            "change_summary": "新增 6 篇业务文档，修复引用全角括号校验",
            "expected_metrics": {"refusal_rate": "<= 15%", "csat": ">= 4.5"},
            "notes": "灰度 20% 流量观察 3 天",
        },
    )
    admin.post("/admin/sla/scan")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    with httpx.Client(base_url=args.base, timeout=TIMEOUT_SEC, trust_env=False) as http:
        admin = account(http, *ADMIN)
        seed_knowledge(admin)
        users = {
            name: account(http, name, f"{name}@example.com", CUSTOMER_PASSWORD)
            for name, _ in CUSTOMERS
        }
        conversations = seed_conversations(users)
        seed_tickets(admin, users)
        seed_operations(admin)
    print(f"seeded {len(KNOWLEDGE)} documents, {len(users)} customers, {len(conversations)} chats")


if __name__ == "__main__":
    main()
