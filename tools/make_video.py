"""Render the product explainer video (Chinese narration, slide animation).

Pipeline: PIL draws every frame of each scene -> macOS `say` (Tingting,
zh_CN) renders narration per scene -> ffmpeg assembles frames+audio into
docs/wind_tunnel_explainer.mp4. Uses real experiment data from runs/evidence/demo2
where the script references actual results.

    python3 tools/make_video.py            # full render (~3-5 min)
    python3 tools/make_video.py --scenes 1 2 3   # render selected scenes only
"""
import argparse
import json
import math
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "runs" / "scratch" / "_video"
W, H = 1280, 720
FPS = 12

BLUE, BLUE_D, BLUE_L = (30, 90, 168), (15, 58, 115), (232, 240, 251)
GOLD, GOLD_L = (176, 122, 16), (253, 246, 227)
GREEN, RED = (14, 122, 78), (178, 58, 58)
INK, SUB, LINE, BG = (26, 34, 51), (91, 103, 121), (227, 231, 238), (246, 247, 249)

FONT = "/System/Library/Fonts/STHeiti Medium.ttc"


def font(sz):
    return ImageFont.truetype(FONT, sz)


def ease(x):
    return 1 - (1 - x) ** 3


def lerp(a, b, t):
    return a + (b - a) * t


def fade(hexcolor, t):
    return tuple(int(c * t + 255 * (1 - t)) for c in hexcolor)


class Scene:
    def __init__(self, idx, title, narration):
        self.idx, self.title, self.narration = idx, title, narration
        self.frames = []

    def frame(self):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img, "RGBA")
        # header band
        d.rectangle([0, 0, W, 8], fill=BLUE_D)
        d.text((48, 26), f"{self.idx:02d}", font=font(30), fill=fade(GOLD, 0.8))
        d.text((92, 26), self.title, font=font(30), fill=BLUE_D)
        # footer
        d.text((48, H - 44), "Nebula · Asterium Labs", font=font(16), fill=SUB)
        d.text((W - 260, H - 44), "model output is not evidence", font=font(14), fill=SUB)
        d.line([40, 66, W - 40, 66], fill=LINE, width=2)
        return img, d


# --------------------------------------------------------------- helpers
def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=f) > maxw and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def chip(d, x, y, text, f, fill, outline, t=1.0):
    pad = 10
    w = d.textlength(text, font=f) + 2 * pad
    h = f.size + 2 * 8
    d.rounded_rectangle([x, y, x + w, y + h], 8, fill=fade(fill, t), outline=fade(outline, t))
    d.text((x + pad, y + 8), text, font=f, fill=fade(INK, t))
    return w + 8


def price_path(ax_runs, color, t):
    """Return normalized [(x,y)] path from a run's EQ marks."""
    rows = [m for m in ax_runs if m["asset"] == "EQ" and m["price"]]
    if not rows:
        return []
    ps = [r["price"] for r in rows]
    lo, hi = min(ps), max(ps)
    n = len(ps)
    k = max(2, int(n * t))
    out = []
    for i in range(k):
        x = 90 + (W - 180) * i / (n - 1)
        y = 150 + (H - 330) * (1 - (ps[i] - lo) / max(hi - lo, 1e-9))
        out.append((x, y))
    return out


# --------------------------------------------------------------- scenes
def sc01(s, t, d, img):
    big = font(64)
    a = ease(min(1, t * 2))
    d.text((W / 2 - d.textlength("市场风洞", font=big) / 2, 200), "市场风洞",
           font=big, fill=fade(BLUE_D, a))
    a2 = ease(min(1, max(0, t * 2 - 0.6)))
    d.text((W / 2 - d.textlength("Nebula", font=font(36)) / 2, 300),
           "Market Wind Tunnel", font=font(36), fill=fade(SUB, a2))
    a3 = ease(min(1, max(0, t * 2 - 1.2)))
    d.text((W / 2 - d.textlength("新规则上线之前，先在虚拟市场里跑一遍", font=font(26)) / 2, 400),
           "新规则上线之前，先在虚拟市场里跑一遍", font=font(26), fill=fade(GOLD, a3))


def sc02(s, t, d, img):
    f = font(24)
    lines = ["2016 年 1 月，A 股熔断上线四个交易日就被暂停。", "",
             "规则本意是稳住市场——却在下跌时反而加速了下跌：", "指数越接近阈值，越多人抢着先走，",
             "结果更快把指数推过阈值。这叫“磁吸效应”。", "",
             "设计时预判了价格，却没有预判人的反应。"]
    y0 = 130
    for i, ln in enumerate(lines):
        a = ease(min(1, max(0, t * 3 - i * 0.45)))
        d.text((80, y0 + i * 52), ln, font=f, fill=fade(INK if ln else BG, a))
    # falling chart doodle
    a = ease(min(1, max(0, t - 1.5)))
    if a > 0:
        pts = [(880 + 60 * i, 160 + (i ** 1.8) * 9) for i in range(10)]
        for i in range(int(9 * a) + 1):
            d.line([pts[i], pts[i + 1]], fill=fade(RED, a), width=5)
        d.line([880, 150, 1180, 150], fill=fade(GOLD, a), width=3)
        d.text((1120, 120), "-7%", font=font(22), fill=fade(GOLD, a))


def sc03(s, t, d, img):
    f = font(24)
    for i, ln in enumerate(["飞机设计用风洞：把飞机放进去吹一吹，",
                            "看气流怎么反应，再决定造不造。"]):
        d.text((80, 120 + i * 46), ln, font=f, fill=INK)
    a = ease(min(1, max(0, t - 1.0)))
    if a > 0:
        d.rounded_rectangle([120, 280, 560, 480], 16, outline=fade(BLUE, a), width=4)
        d.text((190, 300), "虚拟市场", font=font(28), fill=fade(BLUE_D, a))
        for i in range(6):
            x = 150 + i * 65
            hgt = 40 + 18 * math.sin(i * 1.2)
            d.rounded_rectangle([x, 460 - hgt, x + 26, 460], 4, fill=fade(BLUE_L, a))
        d.text((620, 290), "新费率 · 新条款 · 新规则", font=f, fill=fade(GOLD, a))
        d.text((620, 340), "放进去跑一遍", font=f, fill=fade(GOLD, a))
        d.text((620, 400), "看 883 个参与者的连锁反应", font=f, fill=fade(GOLD, a))
    a2 = ease(min(1, max(0, t - 2.2)))
    if a2 > 0:
        d.text((620, 460), "→ 输出：不同方案的风险差异", font=font(22), fill=fade(GREEN, a2))


PANEL_BREAKDOWN = [
    ("500 散户 · 6 类原型", BLUE), ("60 顾问客户池", (59, 130, 196)),
    ("60 公募经理", (111, 168, 214)), ("50 对冲基金", GOLD),
    ("45 外国机构", (74, 163, 122)), ("145 程序化：指数·养老金·回购", (148, 163, 184)),
    ("15 做市商 + 8 机制角色", (178, 58, 58)),
]


def sc04(s, t, d, img):
    f = font(24)
    d.text((80, 110), "883 个手工定义的智能体 =", font=font(34), fill=BLUE_D)
    y = 190
    for i, (txt, c) in enumerate(PANEL_BREAKDOWN):
        a = ease(min(1, max(0, t * 2 - i * 0.4)))
        d.rounded_rectangle([80, y, 100, y + 34], 6, fill=fade(c, a))
        d.text((120, y + 2), txt, font=f, fill=fade(INK, a))
        y += 56
    a = ease(min(1, max(0, t * 2 - 3)))
    d.text((80, y + 6), "每个智能体带着：钱的规模（权重）+ 性格（风险·习惯·信息来源）",
           font=font(22), fill=fade(GOLD, a))
    a2 = ease(min(1, max(0, t * 2 - 3.8)))
    d.text((80, y + 46), "不是模拟 1.6 亿人——是 883 个“代表性人格” × 权重",
           font=font(22), fill=fade(SUB, a2))


def sc05(s, t, d, img):
    f = font(19)
    d.text((80, 110), "每个智能体有一张人物卡（persona card）", font=font(30), fill=BLUE_D)
    card = [
        ("budget_usd", "$85,000", "SCF 财富分布先验"),
        ("loss_aversion", "2.2（亏 1 块痛 2.2 块）", "文献先验"),
        ("attention_per_day", "2（每天真看盘 2 次）", "经纪商活跃度先验"),
        ("news_beta", "0.8（对新闻敏感）", "假设，待校准"),
        ("frictions", "只午休看盘 · 不读费率细则", "—"),
    ]
    y = 170
    d.rounded_rectangle([70, y - 14, 1210, y + 5 * 52 + 6], 14, fill=(255, 255, 255),
                        outline=LINE, width=2)
    for i, (k, v, src) in enumerate(card):
        a = ease(min(1, max(0, t * 2.2 - i * 0.5)))
        d.text((100, y + i * 52), k, font=font(19), fill=fade(BLUE, a))
        d.text((360, y + i * 52), v, font=f, fill=fade(INK, a))
        d.text((940, y + i * 52), src, font=font(16), fill=fade(SUB, a))
    a = ease(min(1, max(0, t * 2.2 - 2.8)))
    d.text((80, y + 5 * 52 + 30), "每个字段标来源和置信度；没有依据的留空，不许模型瞎编",
           font=font(22), fill=fade(GOLD, a))


def sc06(s, t, d, img):
    f = font(22)
    steps = ["事件注入", "谁被惊动？", "想一下", "下订单", "撮合定价", "价格影响下一轮"]
    x = 60
    for i, st in enumerate(steps):
        a = ease(min(1, max(0, t * 1.6 - i * 0.5)))
        if a <= 0:
            continue
        box = [x, 320, x + 165, 380]
        d.rounded_rectangle(box, 10, fill=fade((255, 255, 255), a), outline=fade(BLUE, a), width=2)
        d.text((x + 82 - d.textlength(st, font=f) / 2, 334), st, font=f, fill=fade(BLUE_D, a))
        if i < len(steps) - 1 and a > 0.6:
            d.polygon([(x + 172, 350), (x + 190, 342), (x + 190, 358)], fill=fade(BLUE, a))
        x += 200
    a = ease(min(1, max(0, t - 2.6)))
    if a > 0:
        d.text((80, 180), "一轮 = 1 模拟分钟 · 一天 = 390 轮", font=font(26), fill=INK)
        d.text((80, 230), "关键：大多数智能体在“睡觉”——只有被新闻或价格惊动的人才醒来",
               font=font(22), fill=fade(GOLD, a))
    a2 = ease(min(1, max(0, t - 3.4)))
    if a2 > 0:
        for i in range(14):
            c = GOLD if i in (3, 9) else SUB
            xx = 90 + i * 80
            d.ellipse([xx, 460, xx + 14, 474], fill=fade(c, a2))
        d.text((90, 490), "14 个智能体 · 只有 2 个被惊醒（金色）", font=font(18), fill=fade(SUB, a2))


TIERS = [
    ("规则层 · 做市商/指数流", "每轮都跑 · 0 次 AI 调用", SUB, "15+145 个"),
    ("编译策略层 · 日常反应", "习惯和触发 → 本地策略", BLUE, "~93% 的决策"),
    ("大模型层 · 新鲜事", "新闻措辞 · 没见过的局面", GOLD, "~7% 的决策"),
]


def sc07(s, t, d, img):
    d.text((80, 110), "三层大脑：不是每次思考都花钱", font=font(32), fill=BLUE_D)
    y = 200
    for i, (name, desc, c, share) in enumerate(TIERS):
        a = ease(min(1, max(0, t * 1.8 - i * 0.7)))
        if a <= 0:
            continue
        d.rounded_rectangle([80, y, 1200, y + 96], 14, fill=fade((255, 255, 255), a),
                            outline=fade(LINE, a), width=2)
        d.rounded_rectangle([80, y, 96, y + 96], 4, fill=fade(c, a))
        d.text((120, y + 16), name, font=font(26), fill=fade(INK, a))
        d.text((120, y + 58), desc, font=font(20), fill=fade(SUB, a))
        d.text((980, y + 30), share, font=font(24), fill=fade(c, a))
        y += 118
    a = ease(min(1, max(0, t - 2.8)))
    if a > 0:
        d.text((80, y + 8), "实测：一天 ~700 次决策，只有 ~30 次真正调用了远程大模型",
               font=font(24), fill=fade(GREEN, a))


def sc08(s, t, d, img):
    d.text((80, 110), "大模型只“想”，不“报价”", font=font(32), fill=BLUE_D)
    f = font(20)
    a = ease(min(1, t * 2))
    d.rounded_rectangle([80, 190, 620, 330], 14, fill=fade((255, 255, 255), a),
                        outline=fade(GOLD, a), width=2)
    d.text((110, 210), '大模型说（Intent）:', font=f, fill=fade(GOLD, a))
    d.text((110, 250), '{"side": "sell",', font=f, fill=fade(INK, a))
    d.text((110, 280), ' "size_frac": 0.2, "urgency": 0.8}', font=f, fill=fade(INK, a))
    a2 = ease(min(1, max(0, t - 1.2)))
    if a2 > 0:
        d.rounded_rectangle([660, 190, 1200, 330], 14, fill=fade((255, 255, 255), a2),
                            outline=fade(BLUE, a2), width=2)
        d.text((690, 210), "确定性代码做（执行层）:", font=f, fill=fade(BLUE, a2))
        for i, ln in enumerate(["预算 · 杠杆 · 许可范围检查", "拆单 · 限价换算 · 反应延迟", "违规拦截并记录"]):
            d.text((690, 245 + i * 30), ln, font=f, fill=fade(INK, a2))
    a3 = ease(min(1, max(0, t - 2.2)))
    if a3 > 0:
        d.text((80, 380), "价格完全由撮合引擎产生——模型永远不报价", font=font(26), fill=fade(RED, a3))
        # mini auction
        d.text((80, 440), "撮合：所有订单同时交叉 → 均一清算价", font=f, fill=fade(INK, a3))
        for i in range(8):
            xx = 100 + i * 130
            d.rectangle([xx, 560 - (30 + (i % 3) * 25), xx + 110, 560], fill=fade(BLUE_L, a3))
            d.rectangle([xx, 560, xx + 110, 560 + (30 + ((i + 1) % 3) * 25)], fill=fade((253, 240, 240), a3),
                        outline=fade(LINE, a3))
        d.text((100, 620), "买盘 ▲          ▼ 卖盘", font=f, fill=fade(SUB, a3))


def sc09(s, t, d, img):
    d.text((80, 110), "五个市场同时开", font=font(32), fill=BLUE_D)
    books = [("EQ 股票", BLUE), ("IR 利率", (111, 168, 214)), ("FX 外汇", GREEN),
             ("CMD 商品", GOLD), ("CRYPTO 加密", RED)]
    for i, (name, c) in enumerate(books):
        a = ease(min(1, max(0, t * 1.6 - i * 0.35)))
        x = 80 + i * 232
        d.rounded_rectangle([x, 200, x + 210, 300], 14, fill=fade((255, 255, 255), a),
                            outline=fade(c, a), width=3)
        d.text((x + 24, 222), name, font=font(24), fill=fade(c, a))
        pts = [(x + 20 + j * 28, 270 - 14 * math.sin(j * 0.9 + i)) for j in range(7)]
        for j in range(6):
            if a > 0.5:
                d.line([pts[j], pts[j + 1]], fill=fade(c, a), width=3)
    a = ease(min(1, max(0, t - 2.2)))
    if a > 0:
        d.text((80, 370), "跨市场联动是“涌现”的：宏观基金同时在几本账上再平衡，",
               font=font(24), fill=INK)
        d.text((80, 415), "利率的冲击自己传导到股票和外汇——引擎里没有任何写死的相关性",
               font=font(24), fill=INK)
    a2 = ease(min(1, max(0, t - 3.2)))
    if a2 > 0:
        for (x1, y1), (x2, y2) in [((300, 250), (510, 250)), ((740, 250), (970, 250)), ((510, 250), (740, 250))]:
            d.line([(x1 + x2) / 2 - 20, 340, (x1 + x2) / 2 + 20, 340], fill=fade(GOLD, a2), width=3)


def _load_eq(run):
    p = ROOT / "runs" / "evidence" / "demo2" / "news_demo" / run / "marks.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def sc10(s, t, d, img):
    d.text((80, 100), "真实实验：同一条新闻，两种措辞", font=font(30), fill=BLUE_D)
    d.text((80, 140), "「Fed 声明：政策保持数据依赖，风险大致平衡」 vs 「Fed 警告通胀风险加剧」",
           font=font(20), fill=SUB)
    a_runs, b_runs = _load_eq("news_a_s0"), _load_eq("news_b_s0")
    for runs, c, label, xx in ((a_runs, GREEN, "中性措辞", 90), (b_runs, RED, "警示措辞", 700)):
        path = price_path(runs, c, min(1, ease(min(1, t * 1.4))))
        if len(path) > 1:
            d.line(path, fill=c, width=4)
        d.text((xx, 118), label, font=font(22), fill=c)
    lo = min((m["price"] for m in a_runs + b_runs if m["asset"] == "EQ"), default=0)
    hi = max((m["price"] for m in a_runs + b_runs if m["asset"] == "EQ"), default=1)
    d.text((90, 560), f"{hi:.0f}", font=font(16), fill=SUB)
    d.text((90, 480), f"{lo:.0f}", font=font(16), fill=SUB)
    a = ease(min(1, max(0, t - 1.6)))
    if a > 0:
        d.text((350, 600), "中性：全天 +1.4%      警示：全天 −6.3%", font=font(30), fill=INK)
    a2 = ease(min(1, max(0, t - 2.6)))
    if a2 > 0:
        d.text((350, 650), "措辞本身就是市场变量——这就是“政策沟通风洞”要测的东西",
               font=font(20), fill=fade(GOLD, a2))


def sc11(s, t, d, img):
    d.text((80, 110), "每个实验 = 五样东西，缺一不可", font=font(32), fill=BLUE_D)
    items = ["人群（谁在市场里）", "干预（测什么变化）", "机制（什么规则）",
             "模型（哪个大脑）", "随机种子"]
    x, y = 80, 210
    for i, it in enumerate(items):
        a = ease(min(1, max(0, t * 2 - i * 0.4)))
        d.rounded_rectangle([x, y, x + 330, y + 64], 12, fill=fade((255, 255, 255), a),
                            outline=fade(BLUE, a), width=2)
        d.text((x + 24, y + 18), it, font=font(22), fill=fade(INK, a))
        y += 78
        if i == 1:
            x = 680
            y = 210
    a = ease(min(1, max(0, t - 2.4)))
    if a > 0:
        d.text((680, 420), "同一种子跑两遍 → 结果逐位一致", font=font(26), fill=fade(GREEN, a))
        d.text((680, 470), "每笔订单都能溯源到：哪个人格 · 哪层大脑 ·", font=font(20), fill=fade(SUB, a))
        d.text((680, 505), "哪个模型 · 哪版提示词", font=font(20), fill=fade(SUB, a))
    a2 = ease(min(1, max(0, t - 3.4)))
    if a2 > 0:
        d.text((80, 600), "A/B 场景对比才有效：差异只能来自干预本身", font=font(24), fill=fade(GOLD, a2))


def sc12(s, t, d, img):
    a = ease(min(1, t * 2))
    d.text((80, 130), "三条红线", font=font(36), fill=fade(RED, a))
    lines = [("模型输出不是证据", "演示验证的是管线，不是市场规律"),
             ("只给方向和排序", "不预测涨跌 · 不给效应量 · 不做投资建议"),
             ("敏感性即交付物", "换模型/提示词结论会不会翻？——这本身就是要报告的风险")]
    y = 210
    for i, (h, sub) in enumerate(lines):
        aa = ease(min(1, max(0, t * 2 - 0.5 - i * 0.6)))
        d.text((80, y), f"{i + 1}. {h}", font=font(26), fill=fade(INK, aa))
        d.text((110, y + 42), sub, font=font(20), fill=fade(SUB, aa))
        y += 110
    a2 = ease(min(1, max(0, t - 2.6)))
    d.text((W / 2 - d.textlength("市场风洞 —— 规则上线前，先来跑一遍", font=font(34)) / 2, 580),
           "市场风洞 —— 规则上线前，先来跑一遍", font=font(34), fill=fade(BLUE_D, a2))
    d.text((W / 2 - d.textlength("make demo · make demo2", font=font(22)) / 2, 640),
           "make demo · make demo2", font=font(22), fill=fade(GOLD, a2))


SCENES = [
    ("市场风洞", sc01,
     "市场风洞。一句话：新规则上线之前，先在虚拟市场里跑一遍。这是一个用大模型智能体模拟金融市场的演示系统，接下来五分钟，我带你看看它到底是怎么工作的。"),
    ("为什么要做", sc02,
     "先说为什么。二零一六年一月，A股熔断上线，四个交易日就被暂停了。规则的本意是稳住市场，结果下跌的时候反而加速了下跌——指数越接近阈值，越多的人抢着先走，更快把指数推过阈值，这叫磁吸效应。问题出在哪？设计的时候预判了价格，却没有预判人的反应。"),
    ("核心思想", sc03,
     "我们的核心思想借自工程界。飞机设计用风洞：把飞机放进去吹一吹，看气流怎么反应，再决定造不造。市场规则也可以这样：造一个虚拟市场，把新的费率、新的条款、新的交易规则放进去跑一遍，看八百多个参与者的连锁反应，输出不同方案的风险差异。"),
    ("虚拟人群", sc04,
     "谁在这个虚拟市场里？八百八十三个手工定义的智能体：五百个散户，分成六类原型；六十个顾问客户池；六十个公募基金经理；五十个对冲基金；四十五个外国机构；加上一百四十五个程序化的指数、养老金和回购流，十五个做市商，八个机制角色。注意，我们不是模拟一亿六千万真人——是八百八十三个代表性人格，每人带着钱的规模和性格。"),
    ("人物卡", sc05,
     "每个智能体有一张人物卡。多少钱、亏一块钱有多痛、每天真看几次盘、对新闻多敏感、有什么坏习惯——比如只在午休看盘、从不读费率细则。关键是右边这一列：每个字段都标着数据来源和置信度，没有依据的留空，不许模型自己瞎编。"),
    ("一轮怎么跑", sc06,
     "市场按分钟推进，一天三百九十轮。每一轮：事件进来，看看谁被惊动，被惊动的想一想，下单，撮合定价，价格再影响下一轮。最关键的一点：大多数智能体在睡觉。只有被新闻惊到、或者价格动了它的持仓的人，才会醒来。注意力本身就是行为建模，不是单纯的省算力。"),
    ("三层大脑", sc07,
     "不是每次思考都花钱。三层大脑：最底下是规则层，做市商报价、指数流，每轮都跑，零次AI调用；中间是编译策略层，日常反应走本地策略；只有新鲜事——比如没见过的新闻措辞——才调用远程的大模型，也就是GLM大脑。实测下来，一天七百次决策，只有三十次真正花钱。"),
    ("想 vs 报价", sc08,
     "大模型只负责想，不负责报价。它说的是：我想卖两成仓，比较急。换成合法订单的是确定性代码：检查预算、杠杆、许可范围，拆单，算限价，加反应延迟，违规的直接拦截记录。然后所有订单同时进撮合引擎，交叉出清一价格。价格完全由撮合产生——模型永远不报价。"),
    ("五个市场", sc09,
     "五个市场同时开：股票、利率、外汇、商品、加密货币。跨市场的联动是涌现出来的，不是写死的——宏观基金同时在几本账上再平衡，利率的冲击自己传导到股票和外汇。引擎里没有任何硬编码的相关性。"),
    ("真实结果", sc10,
     "一个真实实验。同一条美联储消息，两种措辞：一种说政策保持数据依赖、风险大致平衡；另一种说通胀风险加剧、不排除进一步收紧。结果：中性措辞当天上涨百分之一点四，警示措辞下跌百分之六点三。措辞本身就是市场变量——这就是政策沟通风洞要测的东西。"),
    ("可复现", sc11,
     "科学上的关键：每个实验由五样东西唯一定义——人群、干预、机制、模型、随机种子。同一种子跑两遍，结果逐位一致。每笔订单都能溯源到哪个人格、哪层大脑、哪个模型、哪一版提示词。只有这样，A、B场景的对比才有效：差异只能来自干预本身。"),
    ("红线", sc12,
     "最后是三条红线。第一，模型输出不是证据，这个演示验证的是管线，不是市场规律。第二，只给方向和排序：不预测涨跌、不给效应量、不做投资建议。第三，敏感性本身就是交付物：换一个模型结论会不会翻？这本身就是需要报告的风险信息。市场风洞——规则上线前，先来跑一遍。"),
]


def narration_audio(text, path):
    # explicit PCM WAVE: newer macOS `say` writes MPEG-4 unless forced
    subprocess.run(["say", "-v", "Tingting", "--data-format=LEI16@22050",
                    "-o", str(path), text], check=True)


def audio_seconds(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def render(only=None):
    WORK.mkdir(parents=True, exist_ok=True)
    for idx, (title, painter, narration) in enumerate(SCENES, 1):
        if only and idx not in only:
            continue
        wav = WORK / f"s{idx:02d}.wav"
        if not wav.exists():
            narration_audio(narration, wav)
        dur = audio_seconds(wav) + 0.8
        n = int(dur * FPS)
        s = Scene(idx, title, narration)
        for f in range(n):
            img, d = s.frame()
            painter(s, f / n, d, img)
            img.save(WORK / f"s{idx:02d}_{f:04d}.png")
        print(f"scene {idx:02d} '{title}': {dur:.1f}s, {n} frames")
    # assemble
    parts = []
    for idx, (title, _, _) in enumerate(SCENES, 1):
        if only and idx not in only:
            continue
        parts += ["-i", str(WORK / f"s{idx:02d}_%04d.png")]
    cmd = ["ffmpeg", "-y"]
    for idx, (title, _, _) in enumerate(SCENES, 1):
        if only and idx not in only:
            continue
        cmd += ["-framerate", str(FPS), "-i", str(WORK / f"s{idx:02d}_%04d.png")]
    for idx, (title, _, _) in enumerate(SCENES, 1):
        if only and idx not in only:
            continue
        cmd += ["-i", str(WORK / f"s{idx:02d}.wav")]
    n = len(only) if only else len(SCENES)
    filt = "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v];" + \
           "".join(f"[{n + i}:a]" for i in range(n)) + \
           f"concat=n={n}:v=0:a=1,apad=pad_dur=0.8[a]"
    out = ROOT / "docs" / "wind_tunnel_explainer.mp4"
    out.parent.mkdir(exist_ok=True)
    cmd += ["-filter_complex", filt, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-shortest", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"video -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", nargs="*", type=int, default=None)
    a = ap.parse_args()
    render(a.scenes)
