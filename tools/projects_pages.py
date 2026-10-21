"""Render Notion iOS dark-mode screens for the 'Projects progress rollup' promo.

All names, emojis, properties, views and example rows below were read from the
real Second Brain OS template through the Notion connector (2026-10-21):
- Projects page 3ff61fa5627f8183a2c9e37e4cbb0af7 (intro, How to use it, Avoid)
- Projects data source d6bfd6a0-... (3 rows, views: Default view / Gallery / Timeline)
- Tasks data source 4c6ebb7d-... (tasks linked to "Launch my Notion template")
Progress = rollup % of Done tasks (1 of 4 Done -> 25%). Days left from End date.
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

def doc(body):
    return f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div class='page'>{body}</div></body></html>"

# faint brand bars in the dark header embed (no claim about its exact animation)
import random
rnd = random.Random(3)
bars = "".join(f'<i style="left:{rnd.randint(10,300)}px;top:{18+k*11}px;width:{rnd.randint(16,70)}px;opacity:{rnd.uniform(.12,.45):.2f}"></i>' for k in range(12))

TOP = f"""
<div class="icon">🚀</div><h1>Projects</h1>
<div class="embed">{bars}</div>
<p class="gray">← <span class="mention">🧠 Second Brain OS</span></p>
<p>A project is an outcome with an end date. "Move out before September" is a project. "Housing" isn't, that's an area.</p>
<hr>
<h3>How to use it</h3>
<ul>
<li>Name it after the result: "Website live", not "Website".</li>
<li>Always write the next action. If you can't name it, that's where you're actually stuck.</li>
<li id="b3">Link every task to its project. The progress bar fills itself in.</li>
<li>Keep three to five projects active. Pause the rest, guilt-free.</li>
</ul>
<h3>Avoid</h3>
<ul>
<li>A project with no end date. It never ends.</li>
<li>Ten active projects at once. None of them move.</li>
</ul>
<hr>
<div class="dbt" id="db">🚀 Projects</div>
"""

def tabs(on):
    names = ["Default view", "🖼️ Gallery", "📈 Timeline"]
    return '<div class="tabs">' + "".join(
        f'<span id="tab{i}" class="{"on" if i == on else ""}">{n}</span>' for i, n in enumerate(names)) + "</div>"

TABLE = tabs(0) + """
<div class="tbl">
<div class="tr th"><div class="c1" style="color:#8c8c8c;font-weight:400">Aa Name</div><div class="c2">↗ Area</div><div class="c3">Σ Days left</div><div class="c4">▦ End</div></div>
<div class="tr"><div class="c1">🏃 Get back in shape</div><div class="c2"><span class="rel">💪 Health</span></div><div class="c3" style="text-align:right">71</div><div class="c4">December 31, 2026</div></div>
<div class="tr"><div class="c1">🏠 Declutter the apartment</div><div class="c2"><span class="rel">🏠 Home</span></div><div class="c3"></div><div class="c4"></div></div>
<div class="tr"><div class="c1">🚀 Launch my Notion template</div><div class="c2"><span class="rel">💼 Career</span></div><div class="c3" style="text-align:right">25</div><div class="c4">November 15, 2026</div></div>
</div>
"""

def card(cid, title, st, stc, pct, days, nxt, area):
    prog = f'<span class="bar"><i style="width:{pct}%"></i></span> <span>{pct}%</span>'
    return f"""<div class="card" id="{cid}"><div class="ct">{title}</div>
<div class="cp"><span class="st {stc}"><b></b>{st}</span></div>
<div class="cp">{prog}</div>
{f'<div class="cp">{days}</div>' if days else ''}
{f'<div class="cp">{nxt}</div>' if nxt else ''}
<div class="cp"><span class="rel">{area}</span></div></div>"""

GALLERY = tabs(1) + card("card-launch", "🚀 Launch my Notion template", "Active", "blue", 25, "25", "Build the Gumroad sales page", "💼 Career") \
    + card("card-shape", "🏃 Get back in shape", "Active", "blue", 0, "71", "Thursday run", "💪 Health") \
    + card("card-declutter", "🏠 Declutter the apartment", "Paused", "yellow", 0, "", "", "🏠 Home")

def prow(icon, key, val, rid=""):
    return f'<div class="pr"{f" id={chr(34)}{rid}{chr(34)}" if rid else ""}><div class="pk"><s>{icon}</s>{key}</div><div class="pv">{val}</div></div>'

PROJECT = f"""
<div class="icon">🚀</div><h1>Launch my Notion template</h1>
<div class="props">
{prow("↗","Area",'<span class="rel">💼 Career</span>')}
{prow("Σ","Days left","25")}
{prow("▦","End","November 15, 2026")}
{prow("↗","Goal",'<span class="rel">💰 Make $500 with my templates</span>')}
{prow("≡","Next action","Build the Gumroad sales page")}
{prow("↗","Notes",'<span class="rel">📄 What makes a Notion template sell</span>')}
{prow("⌄","Priority",'<span class="tag t-red">🔥 High</span>')}
{prow("◎","Progress",'<span id="progval" style="display:inline-block;width:170px;height:18px"></span>',"prog")}
{prow("▦","Start","October 20, 2026")}
{prow("◉","Status",'<span class="st blue"><b></b>Active</span>')}
{prow("↗","Tasks",'<div><span class="rel">📄 Build the Gumroad sales page</span></div><div id="task-film"><span class="rel">📄 Film the 3D brain for TikTok</span></div><div><span class="rel">📄 Pick the product name</span></div><div><span class="rel">📄 Take 5 screenshots of the template</span></div>',"tasks")}
</div>
<div class="cm">Add a comment...</div>
"""

def task_page(done):
    st = '<span class="st green"><b></b>Done</span>' if done else '<span class="st gray"><b></b>To do</span>'
    return f"""
<div class="icon" style="font-size:40px;color:#8c8c8c">📄</div><h1>Film the 3D brain for TikTok</h1>
<div class="props">
{prow("⌄","Context",'<span class="tag" style="background:#3c2d49;color:#ead9f7">Phone</span>')}
{prow("▦","Due","October 21, 2026")}
{prow("⌄","Energy",'<span class="tag t-yellow">🔋 Medium</span>')}
{prow("⌄","Priority",'<span class="tag t-red">🔥 High</span>')}
{prow("↗","Project",'<span class="rel">🚀 Launch my Notion template</span>')}
{prow("◉","Status",st,"status")}
</div>
<div class="cm">Add a comment...</div>
"""

SHEET = """<html><head><meta charset='utf-8'><style>""" + CSS + """
body{background:transparent}
.sh{background:#252525;border-radius:14px 14px 0 0;padding:10px 18px 34px;width:360px}
.gr{width:36px;height:5px;border-radius:3px;background:#555;margin:0 auto 12px}
.sh h4{font-size:15px;color:#ececec;font-weight:600;margin-bottom:10px;text-align:center}
.g{color:#8c8c8c;font-size:12.5px;margin:10px 0 4px}
.o{padding:8px 0}
</style></head><body><div class="sh"><div class="gr"></div><h4>Status</h4>
<div class="g">To-do</div><div class="o"><span class="st gray"><b></b>To do</span> <span style="float:right;color:#5b97d9">✓</span></div>
<div class="g">In progress</div><div class="o"><span class="st blue"><b></b>In progress</span></div>
<div class="g">Complete</div><div class="o" id="opt-done"><span class="st green"><b></b>Done</span></div>
</div></body></html>"""

HOME = """
<div class="icon">🧠</div><h1>Second Brain OS</h1>
<div id="brain" style="height:300px;margin:0 -20px;background:#07080b"></div>
"""

PAGES = {
    "projects_table": doc(TOP + TABLE),
    "projects_gallery": doc(TOP + GALLERY),
    "project": doc(PROJECT),
    "task_todo": doc(task_page(False)),
    "task_done": doc(task_page(True)),
    "home": doc(HOME),
}
IDS = ["b3", "db", "tab1", "card-launch", "prog", "progval", "task-film", "status", "brain", "tasks"]

geom = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 360, "height": 640}, device_scale_factor=3)
    for name, html in PAGES.items():
        pg.set_content(html); pg.wait_for_timeout(200)
        # overflow check: any element whose text is clipped
        clipped = pg.evaluate("""()=>[...document.querySelectorAll('.pv,.pk,.ct,.cp,.tr>div,.tabs')]
            .filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.className+': '+e.textContent.trim().slice(0,40))""")
        clipped = [c for c in clipped if not c.startswith(("tr", "c2", "c3", "c4"))]  # table columns are meant to scroll horizontally
        if clipped:
            print("CLIPPED in", name, clipped)
        pg.screenshot(path=f"{OUT}/{name}.png", full_page=True)
        g = {}
        for i in IDS:
            r = pg.evaluate(f"()=>{{const e=document.getElementById('{i}');if(!e)return null;const b=e.getBoundingClientRect();return [b.x,b.y,b.width,b.height]}}")
            if r: g[i] = [round(v * 3) for v in r]
        geom[name] = g
    pg.set_viewport_size({"width": 360, "height": 300})
    pg.set_content(SHEET); pg.wait_for_timeout(150)
    el = pg.query_selector(".sh"); el.screenshot(path=f"{OUT}/sheet.png", omit_background=True)
    r = pg.evaluate("()=>{const b=document.getElementById('opt-done').getBoundingClientRect();return [b.x,b.y,b.width,b.height]}")
    geom["sheet"] = {"opt-done": [round(v * 3) for v in r]}
    b.close()
json.dump(geom, open(f"{OUT}/geom.json", "w"), indent=1)
print("ok")
