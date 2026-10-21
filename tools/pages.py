"""Render Notion-mobile-style (dark) screenshots of the Second Brain OS pages."""
from playwright.sync_api import sync_playwright
import os, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "shots"
os.makedirs(OUT, exist_ok=True)

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#191919;color:#d4d4d4;font-family:Inter,'Noto Color Emoji',sans-serif;width:360px;-webkit-font-smoothing:antialiased}
.status{height:44px;display:flex;justify-content:space-between;align-items:center;padding:0 22px;font-weight:600;font-size:15px;color:#fff}
.status .r{display:flex;gap:6px;align-items:center;font-size:12px}
.bat{width:24px;height:11px;border:1.5px solid #fff;border-radius:3px;position:relative}
.bat:after{content:'';position:absolute;left:1.5px;top:1.5px;width:14px;height:5px;background:#fff;border-radius:1px}
.nav{height:44px;display:flex;align-items:center;justify-content:space-between;padding:0 14px;color:#9b9b9b;font-size:14px;border-bottom:1px solid #262626}
.nav .crumb{color:#d4d4d4;font-size:14px;max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.page{padding:22px 20px 40px}
.icon{font-size:52px;line-height:1;margin-bottom:12px}
h1{font-size:30px;font-weight:700;color:#e9e9e7;letter-spacing:-.5px;margin-bottom:14px}
p{font-size:15px;line-height:1.5;color:#c9c9c7;margin:8px 0}
.muted{color:#8a8a88}
.embed{height:300px;border-radius:6px;background:#07080b;margin:6px -20px 14px;position:relative}
.callout{background:#252525;border-radius:6px;padding:14px 14px;display:flex;gap:10px;font-size:14px;line-height:2}
.mention{color:#d4d4d4;text-decoration:underline;text-decoration-color:#555;text-underline-offset:3px;white-space:nowrap}
.sub{margin-top:14px;font-size:15px;display:flex;gap:8px;align-items:center;text-decoration:underline;text-decoration-color:#555;text-underline-offset:3px}
.hdr{height:130px;margin:0 -20px 16px;background:radial-gradient(circle at 30% 40%,#2a3b55,#0b0d12 70%)}
.dbtitle{font-size:17px;font-weight:600;color:#e9e9e7;margin:20px 0 8px;display:flex;gap:8px;align-items:center}
.views{display:flex;gap:14px;font-size:13px;color:#8a8a88;border-bottom:1px solid #2f2f2f;padding-bottom:8px;margin-bottom:6px}
.views b{color:#e9e9e7;font-weight:500;border-bottom:2px solid #e9e9e7;padding-bottom:7px}
.row{border-bottom:1px solid #2a2a2a;padding:12px 0}
.rt{font-size:15.5px;font-weight:600;color:#e9e9e7;margin-bottom:8px}
.props{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:12.5px}
.tag{padding:2px 7px;border-radius:4px;font-size:12.5px}
.green{background:#2b593f;color:#e0f2e7}.yellow{background:#89632a;color:#fbeed3}.red{background:#6e3630;color:#fbe4e1}
.gray{background:#373737;color:#d4d4d4}.blue{background:#28456c;color:#dbe8fa}.orange{background:#854c1d;color:#fde6d3}.purple{background:#492f64;color:#ecdff9}
.prog{display:flex;align-items:center;gap:8px;margin-top:8px;font-size:12.5px;color:#9b9b9b}
.bar{width:150px;height:6px;background:#333;border-radius:3px;overflow:hidden}
.bar i{display:block;height:100%;background:#4a9e6b}
.cb{width:16px;height:16px;border-radius:3px;border:1.5px solid #6b6b6b;display:inline-flex;align-items:center;justify-content:center;font-size:11px;color:#fff}
.cb.on{background:#2383e2;border-color:#2383e2}
.hab{display:grid;grid-template-columns:62px repeat(6,1fr) 46px;gap:4px;align-items:center;font-size:11px;color:#8a8a88;padding:10px 0;border-bottom:1px solid #2a2a2a;text-align:center}
.hab .d{color:#e9e9e7;font-size:14px;font-weight:600;text-align:left}
.hab .s{color:#e9e9e7;font-weight:700;font-size:14px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
.card{background:#202020;border:1px solid #2f2f2f;border-radius:6px;padding:12px;font-size:14px;color:#e9e9e7;font-weight:600}
.card span{display:block;font-size:24px;margin-bottom:6px}
.card em{display:block;font-style:normal;color:#8a8a88;font-weight:400;font-size:12px;margin-top:3px}
"""

STATUS = '<div class="status"><span>9:41</span><span class="r">●●●● <span class="bat"></span></span></div>'
def nav(crumb):
    return f'<div class="nav"><span style="font-size:20px">‹</span><span class="crumb">{crumb}</span><span>···</span></div>'

def page(body, crumb, extra=""):
    return f"<html><head><style>{CSS}</style></head><body>{STATUS}{nav(crumb)}<div class='page'>{body}</div>{extra}</body></html>"

CATS = [("📥","Inbox"),("🚀","Projects"),("🧭","Areas"),("📚","Resources"),("🗄️","Archive"),("📝","Notes"),
        ("✅","Tasks"),("🎯","Goals"),("📓","Journal"),("🔁","Habits"),("📖","Library"),("💡","Ideas")]
mentions = "  ·  ".join(f'<span class="mention" id="m-{n}">{e} {n}</span>' for e, n in CATS)

home = page(f"""
<div class="icon">🧠</div><h1>Second Brain OS</h1>
<div class="embed" id="brain"></div>
<div class="callout"><span>🧠</span><div>{mentions}</div></div>
<div class="sub">📄 ⚙️ Behind the scenes</div>
""", "🧠 Second Brain OS")

def prog(pct):
    return f'<div class="prog"><span class="bar"><i style="width:{pct}%"></i></span>{pct}%</div>'

projects = page(f"""
<div class="hdr"></div>
<div class="icon" style="margin-top:-46px">🚀</div><h1>Projects</h1>
<p>Anything with a finish line. If it has a deadline and more than one step, it lives here.</p>
<div class="dbtitle">🚀 Projects</div>
<div class="views"><b>Active</b><span>All</span><span>Timeline</span></div>
<div class="row"><div class="rt">🚀 Launch my Notion template</div>
 <div class="props"><span class="tag green">Active</span><span class="tag red">🔥 High</span><span class="muted">25 days left</span></div>{prog(25)}
 <div class="props" style="margin-top:6px"><span class="muted">Next: Build the Gumroad sales page</span></div></div>
<div class="row"><div class="rt">🏃 Get back in shape</div>
 <div class="props"><span class="tag green">Active</span><span class="tag yellow">Medium</span><span class="muted">71 days left</span></div>{prog(0)}
 <div class="props" style="margin-top:6px"><span class="muted">Next: Thursday run</span></div></div>
<div class="row"><div class="rt">📦 Declutter the apartment</div>
 <div class="props"><span class="tag gray">Paused</span><span class="tag blue">Low</span></div></div>
""", "🧠 Second Brain OS / Projects")

def task(name, status, scls, energy, due, alert=None):
    a = f'<span class="tag {"red" if alert=="Overdue" else "orange"}">{"⚠️" if alert=="Overdue" else "📌"} {alert}</span>' if alert else ""
    return f'<div class="row"><div class="rt">{name}</div><div class="props">{a}<span class="tag {scls}">{status}</span><span class="tag purple">{energy}</span><span class="muted">{due}</span></div></div>'

tasks = page(f"""
<div class="hdr" style="background:radial-gradient(circle at 70% 40%,#3b2a55,#0b0d12 70%)"></div>
<div class="icon" style="margin-top:-46px">✅</div><h1>Tasks</h1>
<p>Every next action, linked to a project. Pick by energy, not by guilt.</p>
<div class="dbtitle">✅ Tasks</div>
<div class="views"><b>Today</b><span>Board</span><span>By energy</span><span>Calendar</span></div>
{task("Call the bank","To do","gray","🪫 Low","Oct 19","Overdue")}
{task("Film the 3D brain for TikTok","To do","gray","🔋 Medium","Oct 21","Today")}
{task("Build the Gumroad sales page","In progress","blue","⚡ High","Oct 22")}
{task("5K run","To do","gray","⚡ High","Oct 22")}
{task("Take 5 screenshots of the template","To do","gray","🪫 Low","Oct 23")}
""", "🧠 Second Brain OS / Tasks")

def hab(day, vals):
    cells = "".join(f'<span><span class="cb {"on" if v else ""}">{"✓" if v else ""}</span></span>' for v in vals)
    return f'<div class="hab"><span class="d">{day}</span>{cells}<span class="s">{sum(vals)}/6</span></div>'

habits = page(f"""
<div class="hdr" style="background:radial-gradient(circle at 50% 40%,#1f4d3a,#0b0d12 70%)"></div>
<div class="icon" style="margin-top:-46px">🔁</div><h1>Habits</h1>
<p>One row per day. Tick what you did, the score does the rest.</p>
<div class="dbtitle">🔁 Habits</div>
<div class="hab" style="font-size:10px"><span></span><span>🏋️<br>Exercise</span><span>💧<br>Water</span><span>📖<br>Read</span><span>🎧<br>Deep</span><span>🧘<br>Medit.</span><span>😴<br>Sleep</span><span>Score</span></div>
{hab("Oct 20",[1,1,1,1,0,0])}
{hab("Oct 19",[0,1,1,1,1,1])}
{hab("Oct 18",[1,0,0,0,1,1])}
""", "🧠 Second Brain OS / Habits")

desc = {"Inbox":"Dump it, sort later","Areas":"Ongoing responsibilities","Resources":"Stuff worth keeping",
        "Archive":"Done & dusted","Notes":"Capture → Distill","Goals":"Why you do it all","Journal":"One page a day",
        "Library":"Books, films, courses","Ideas":"Half-baked is fine"}
cards = "".join(f'<div class="card"><span>{e}</span>{n}<em>{desc[n]}</em></div>' for e, n in CATS if n in desc)
more = page(f"""<div class="icon">⚙️</div><h1>Behind the scenes</h1>
<p class="muted">The rest of the system: 12 pages, 5 guides, all linked.</p>
<div class="grid">{cards}</div>""", "🧠 Second Brain OS / Behind the scenes")

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 360, "height": 640}, device_scale_factor=3)
    for name, html in [("home", home), ("projects", projects), ("tasks", tasks), ("habits", habits), ("more", more)]:
        pg.set_content(html); pg.wait_for_timeout(150)
        pg.screenshot(path=f"{OUT}/{name}.png", full_page=True)
        if name == "home":
            r = pg.eval_on_selector("#brain", "e=>{const b=e.getBoundingClientRect();return [b.x,b.y,b.width,b.height]}")
            m = pg.eval_on_selector("#m-Projects", "e=>{const b=e.getBoundingClientRect();return [b.x+b.width/2,b.y+b.height/2]}")
            open(f"{OUT}/home_geom.txt", "w").write(",".join(str(round(v * 3)) for v in r + m))
    b.close()
print("ok")
