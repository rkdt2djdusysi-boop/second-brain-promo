"""Render Notion iOS dark-mode screens for the 'Tasks by energy' promo (2026-10-22).

Content read from the real Second Brain OS template via the Notion connector:
- Tasks page 3ff61fa5627f81b680afc059a95e69b7 (intro, How to use it, Avoid)
- Tasks data source 4c6ebb7d-... (6 rows) and its views: Default view, 📋 Board,
  ⚡ By energy (board grouped by Energy, Status is not Done, shows Context/Due), 🗓️ Calendar.
"""
from playwright.sync_api import sync_playwright
import json, os, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "shots"
os.makedirs(OUT, exist_ok=True)

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#191919}
body{color:#cfcfcf;font-family:Inter,'Noto Color Emoji',sans-serif;width:360px;-webkit-font-smoothing:antialiased;font-size:15px}
.page{padding:0 20px 60px}
.icon{font-size:46px;line-height:1;margin:18px 0 10px}
h1{font-size:28px;font-weight:700;color:#ececec;letter-spacing:-.4px;line-height:1.2;margin-bottom:14px}
p{line-height:1.5;margin:6px 0}
.gray{color:#8c8c8c}
.mention{color:#cfcfcf;border-bottom:1px solid #555}
hr{border:0;border-top:1px solid #333;margin:16px 0}
h3{font-size:18px;font-weight:600;color:#ececec;margin:18px 0 6px}
ul{padding-left:22px}
li{line-height:1.5;margin:4px 0}
.embed{height:150px;margin:6px -20px 12px;background:#07080b;position:relative;overflow:hidden}
.embed i{position:absolute;height:3px;background:#fff;border-radius:2px}
.dbt{font-size:18px;font-weight:700;color:#ececec;margin:14px 0 6px}
.tabs{display:flex;gap:16px;font-size:14px;color:#8c8c8c;border-bottom:1px solid #2f2f2f;white-space:nowrap}
.tabs span{padding:8px 0}
.tabs .on{color:#ececec;font-weight:500;border-bottom:2px solid #ececec}
.tbl{margin:0 -20px;overflow:hidden;white-space:nowrap;font-size:14px}
.tr{display:flex;border-bottom:1px solid #2f2f2f}
.tr>div{padding:9px 8px;border-right:1px solid #2f2f2f;overflow:hidden;text-overflow:ellipsis;flex:none}
.th{color:#8c8c8c;font-size:13px}
.c1{width:240px;padding-left:20px!important;color:#ececec;font-weight:500}.c2{width:110px}.c3{width:90px}.c4{width:120px}
.card{border:1px solid #2f2f2f;border-radius:8px;background:#202020;margin:10px 0;padding:12px 14px}
.ct{font-size:15.5px;font-weight:600;color:#ececec;margin-bottom:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cp{display:flex;align-items:center;gap:8px;font-size:13.5px;margin:5px 0;white-space:nowrap;overflow:hidden}
.st{display:inline-flex;align-items:center;gap:5px;padding:1px 8px;border-radius:10px;font-size:13px}
.st b{width:7px;height:7px;border-radius:50%;display:inline-block}
.st.blue{background:#1f3654;color:#cfe0f5}.st.blue b{background:#5b97d9}
.st.yellow{background:#4b3c17;color:#f2e2b8}.st.yellow b{background:#c99a3a}
.st.gray{background:#333;color:#d0d0d0}.st.gray b{background:#8c8c8c}
.st.green{background:#1f4430;color:#cde9d7}.st.green b{background:#4fa36f}
.tag{padding:1px 7px;border-radius:4px;font-size:13px}
.t-red{background:#5c2b27;color:#fbdcd8}.t-yellow{background:#5c4a1f;color:#fbecc9}.t-gray{background:#373737;color:#d4d4d4}.t-orange{background:#5e3a19;color:#fde3c9}
.rel{color:#cfcfcf;border-bottom:1px solid #555}
.bar{display:inline-block;width:110px;height:6px;background:#333;border-radius:3px;overflow:hidden;vertical-align:middle}
.bar i{display:block;height:100%;background:#4fa36f}
.props{margin:4px 0 10px}
.pr{display:flex;align-items:flex-start;min-height:36px;font-size:14px}
.pk{width:118px;flex:none;color:#8c8c8c;padding:8px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pk s{text-decoration:none;display:inline-block;width:20px;color:#7a7a7a}
.pv{flex:1;padding:7px 0;min-width:0;line-height:1.45;overflow:hidden;color:#cfcfcf}
.pv div{padding:2px 0;overflow:hidden;text-overflow:ellipsis}
.cm{color:#6f6f6f;font-size:14px;border-top:1px solid #2f2f2f;padding-top:14px;margin-top:6px}
"""
CSS += """
.tabs{overflow:hidden;gap:10px!important;font-size:12.5px!important;margin-right:-12px}
.board{display:flex;gap:10px;padding:10px 20px 20px;width:max-content;background:#191919}
.col{width:250px;flex:none}
.gh{display:flex;align-items:center;gap:8px;padding:6px 2px 10px;font-size:14px}
.gh .n{color:#8c8c8c}
.pill{padding:2px 8px;border-radius:4px;font-size:14px;font-weight:500}
.p-orange{background:#5e3a19;color:#fde3c9}.p-yellow{background:#5c4a1f;color:#fbecc9}.p-gray{background:#373737;color:#d4d4d4}
.bc{background:#252525;border-radius:8px;padding:11px 12px;margin-bottom:9px;box-shadow:0 0 0 1px #2f2f2f}
.bt{font-size:14.5px;font-weight:600;color:#ececec;margin-bottom:8px;line-height:1.35}
.bp{font-size:13px;margin:5px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#cfcfcf}
.t-blue{background:#1f3654;color:#cfe0f5}.t-purple{background:#3c2d49;color:#ead9f7}.t-green{background:#1f4430;color:#cde9d7}
.new{color:#6f6f6f;font-size:14px;padding:4px 2px}
.al{font-size:14px}
"""

def doc(body):
    return f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div class='page'>{body}</div></body></html>"

import random
rnd = random.Random(7)
bars = "".join(f'<i style="left:{rnd.randint(10,300)}px;top:{18+k*11}px;width:{rnd.randint(16,70)}px;opacity:{rnd.uniform(.12,.45):.2f}"></i>' for k in range(12))

# --- text read from Notion page 3ff61fa5627f81b680afc059a95e69b7 (Tasks) ---
TOP = f"""
<div class="icon">✅</div><h1>Tasks</h1>
<div class="embed">{bars}</div>
<p class="gray">← <span class="mention">🧠 Second Brain OS</span></p>
<p>Concrete actions, the kind you do in one go. If it takes several steps, it's a project.</p>
<hr>
<h3>How to use it</h3>
<ul>
<li>Start with a verb: call, send, buy, book.</li>
<li>Only add a date if it's real. Fake deadlines end up ignored.</li>
<li id="b3">Pick based on your energy right now. That's what the "By energy" view is for.</li>
<li id="b4">Each morning, keep three tasks that matter. Everything else is a bonus.</li>
</ul>
<h3>Avoid</h3>
<ul>
<li>Writing "Website project" as a task. You don't know where to start, so you don't.</li>
<li>Letting overdue tasks stack up. Reschedule or delete them on Sunday.</li>
</ul>
<hr>
<div class="dbt" id="db">✅ Tasks</div>
"""

def tabs(on):
    names = ["Default view", "📋 Board", "⚡ By energy", "🗓️ Calendar"]
    return '<div class="tabs">' + "".join(
        f'<span id="tab{i}" class="{"on" if i == on else ""}">{n}</span>' for i, n in enumerate(names)) + "</div>"

# rows from data source 4c6ebb7d (6 tasks). Alert = formula (Overdue / Today per PROJECT_CONTEXT), date ref 2026-10-22.
ROWS = [("5K run", "Today"), ("Call the bank", "Overdue"), ("Build the Gumroad sales page", "Today"),
        ("Film the 3D brain for TikTok", "Overdue"), ("Pick the product name", ""), ("Take 5 screenshots of the template", "")]
TABLE = tabs(0) + '<div class="tbl"><div class="tr th"><div class="c1" style="color:#8c8c8c;font-weight:400">Aa Name</div><div class="c4">Σ Alert</div></div>' + \
    "".join(f'<div class="tr"><div class="c1">{n}</div><div class="c4 al">{a}</div></div>' for n, a in ROWS) + "</div>"

CTX = {"Computer": "t-blue", "Phone": "t-purple", "Out": "t-green", "Anywhere": "t-gray"}
def bcard(cid, name, ctx, due):
    return f'<div class="bc" id="{cid}"><div class="bt">{name}</div><div class="bp"><span class="tag {CTX[ctx]}">{ctx}</span></div><div class="bp">{due}</div></div>'

# "⚡ By energy" view: board grouped by Energy, filter Status is not Done, cards show Context, Due, Name
GROUPS = [("⚡ High", "p-orange", [("5K run", "Out", "October 22, 2026"), ("Build the Gumroad sales page", "Computer", "October 22, 2026")]),
          ("🔋 Medium", "p-yellow", [("Film the 3D brain for TikTok", "Phone", "October 21, 2026")]),
          ("🪫 Low", "p-gray", [("Call the bank", "Phone", "October 19, 2026"), ("Take 5 screenshots of the template", "Computer", "October 23, 2026")])]
BOARD = "<html><head><meta charset='utf-8'><style>" + CSS + "body{width:auto}</style></head><body><div class='board' id='board'>" + "".join(
    f'<div class="col" id="col{gi}"><div class="gh"><span class="pill {pc}">{g}</span><span class="n">{len(cs)}</span></div>' +
    "".join(bcard(f"c{gi}{k}", *c) for k, c in enumerate(cs)) + '<div class="new">+ New page</div></div>'
    for gi, (g, pc, cs) in enumerate(GROUPS)) + "</div></body></html>"

ENERGY = tabs(2) + '<div id="boardslot" style="height:520px;margin:0 -20px"></div>'

HOME = """
<div class="icon">🧠</div><h1>Second Brain OS</h1>
<div id="brain" style="height:300px;margin:0 -20px;background:#07080b"></div>
"""

PAGES = {"tasks_table": doc(TOP + TABLE), "tasks_energy": doc(TOP + ENERGY), "home": doc(HOME)}
IDS = ["b3", "b4", "db", "tab2", "boardslot", "brain"]

geom = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 360, "height": 640}, device_scale_factor=3)
    for name, html in PAGES.items():
        pg.set_content(html); pg.wait_for_timeout(200)
        clipped = pg.evaluate("""()=>[...document.querySelectorAll('.pv,.pk,.ct,.cp,.tabs,li,p,h1')]
            .filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.className+': '+e.textContent.trim().slice(0,40))""")
        if clipped: print("CLIPPED in", name, clipped)
        pg.screenshot(path=f"{OUT}/{name}.png", full_page=True)
        g = {}
        for i in IDS:
            r = pg.evaluate(f"()=>{{const e=document.getElementById('{i}');if(!e)return null;const b=e.getBoundingClientRect();return [b.x,b.y,b.width,b.height]}}")
            if r: g[i] = [round(v * 3) for v in r]
        geom[name] = g
    pg.set_viewport_size({"width": 900, "height": 520})
    pg.set_content(BOARD); pg.wait_for_timeout(200)
    clipped = pg.evaluate("()=>[...document.querySelectorAll('.bt,.bp')].filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.textContent)")
    if clipped: print("CLIPPED in board", clipped)
    pg.query_selector("#board").screenshot(path=f"{OUT}/board.png")
    g = {}
    for i in ["col0", "col1", "col2", "c20", "c21", "c00", "board"]:
        r = pg.evaluate(f"()=>{{const b=document.getElementById('{i}').getBoundingClientRect();return [b.x,b.y,b.width,b.height]}}")
        g[i] = [round(v * 3) for v in r]
    geom["board"] = g
    b.close()
json.dump(geom, open(f"{OUT}/geom.json", "w"), indent=1)
print("ok")
