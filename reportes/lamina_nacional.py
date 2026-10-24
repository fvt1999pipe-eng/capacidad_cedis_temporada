"""Lámina ejecutiva de la red: recibo, alistamiento y ocupación (real 2025 y proyección de temporada).

Lee las tablas de outputs/ que genera el notebook y escribe reportes/lamina_nacional.html y
img/lamina_nacional.png (1600 x 900). Requiere Playwright con Chromium para la imagen.
"""
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
h = pd.read_csv(BASE / "outputs/historico_limpio.csv")
p = pd.read_csv(BASE / "outputs/proyeccion_forecast.csv")
cds = pd.read_csv(BASE / "data/centros_distribucion.csv").set_index("cd")
ppb = cds["piezas_por_bulto"]
propios = cds[cds["tipo"] == "Propio"]["posiciones"]
CAP = cds["capacidad_alistamiento_semana"].sum()

h["bultos"] = h["piezas_real"] / h["cd"].map(ppb)
p["bultos"] = p["piezas"] / p["cd"].map(ppb)

def ocup_red(df, col, escala):
    q = df[df["cd"].isin(propios.index)].copy()
    q["w"] = q[col] * escala * q["cd"].map(propios)
    return (q.groupby(["anio", "semana"])["w"].sum() / propios.sum()).values

# ---------- Real 2025 por semana (red) ----------
h25 = h[h["anio"] == 2025]
hs = h25.groupby(["anio", "semana", "mes"], as_index=False)[["cajas_real", "cajas_forecast", "piezas_real", "piezas_forecast", "bultos"]].sum()
hs["ocup"] = ocup_red(h25, "ocupacion", 100)
hs = hs[~((hs["semana"] == 1) & (hs["mes"] == 12))]           # la S1 de 2025 pertenece a diciembre de 2024

mens = hs[hs["semana"] <= 40].groupby("mes").agg(
    cajas=("cajas_real", "mean"), piezas=("piezas_real", "mean"), cf=("cajas_forecast", "sum"), cr=("cajas_real", "sum"),
    pf=("piezas_forecast", "sum"), pr=("piezas_real", "sum"), bultos=("bultos", "mean"), total=("bultos", "sum"), ocup=("ocup", "mean"))
mens["cum_c"], mens["cum_p"] = 100 * mens["cr"] / mens["cf"], 100 * mens["pr"] / mens["pf"]
real_sem = hs[hs["semana"] >= 41].reset_index(drop=True)
real_sem["cum_c"] = 100 * real_sem["cajas_real"] / real_sem["cajas_forecast"]
real_sem["cum_p"] = 100 * real_sem["piezas_real"] / real_sem["piezas_forecast"]

# ---------- Proyección (red) ----------
ps = p.groupby(["anio", "semana", "mes"], as_index=False)[["cajas", "piezas", "bultos"]].sum()
ps["ocup"] = ocup_red(p, "ocupacion", 1)

SEP_C, SEP_P = mens.loc[9, "cajas"], mens.loc[9, "piezas"]
pico = ps[(ps["anio"] == 2025) & ps["semana"].between(45, 51)]
VAR_C, VAR_P = 100 * (pico["cajas"].mean() / SEP_C - 1), 100 * (pico["piezas"].mean() / SEP_P - 1)
i_pico = ps["ocup"].idxmax(); OCUP_PICO, SEM_PICO = ps.loc[i_pico, "ocup"], int(ps.loc[i_pico, "semana"])
CUM_C_SEP, CUM_P_SEP = mens.loc[9, "cum_c"], mens.loc[9, "cum_p"]
CUM_C_OCT = 100 * real_sem["cajas_real"].sum() / real_sem["cajas_forecast"].sum()
CUM_P_OCT = 100 * real_sem["piezas_real"].sum() / real_sem["piezas_forecast"].sum()

# ---------- Puntos del eje x ----------
MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP"]
pts = []
for m, nombre in enumerate(MESES, 1):
    r = mens.loc[m]
    pts.append(dict(tipo="mes", lab=nombre, c=r.cajas, pz=r.piezas, oc=r.ocup, b=r.bultos, cc=r.cum_c, cp=r.cum_p, mes=m))
for _, r in real_sem.iterrows():
    pts.append(dict(tipo="real", lab=f"S{int(r.semana)}", c=r.cajas_real, pz=r.piezas_real, oc=r.ocup, b=r.bultos, cc=r.cum_c, cp=r.cum_p, mes=10))
for _, r in ps.iterrows():
    pts.append(dict(tipo="proy", lab=f"S{int(r.semana)}", c=r.cajas, pz=r.piezas, oc=r.ocup, b=r.bultos, mes=int(r.mes), anio=int(r.anio)))

# ---------- Geometría ----------
W, X0, X1 = 1560, 112, 1500
GAP = 24
n_m, n_r = 9, len(real_sem)
step = (X1 - X0 - 2 * GAP) / (len(pts) - 1)
xs = []
for i, q in enumerate(pts):
    x = X0 + i * step + (GAP if i >= n_m else 0) + (GAP if i >= n_m + n_r else 0)
    xs.append(x)
TOP, BOT = 52, 222           # panel de líneas (índice)
OTOP, OBOT = 236, 290        # franja de ocupación
YMIN, YMAX = 45, 150
y = lambda v: BOT - (v - YMIN) / (YMAX - YMIN) * (BOT - TOP)
oy = lambda v: OBOT - min(v, 110) / 110 * (OBOT - OTOP - 12)
idx_c = lambda q: 100 * q["c"] / SEP_C
idx_p = lambda q: 100 * q["pz"] / SEP_P

def k(v): return f"{v/1000:,.0f}K".replace(",", ".")
def pct(v, d=0): return f"{v:,.{d}f} %".replace(".", ",") if d else f"{v:.0f} %"
def sem(v):
    return "#1a7f37" if 95 <= v <= 105 else ("#c62828" if v > 105 else "#8d6e2b")

C_COL, P_COL, O_COL, O_FILL = "#e0602a", "#2a6fd6", "#5b47c9", "#e6e1f8"
svg = []
# grid y
for v in [50, 75, 100, 125]:
    svg.append(f'<line x1="{X0-14}" x2="{X1+10}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{"#bdbbb5" if v==100 else "#eeede9"}" stroke-width="1" {"stroke-dasharray=\'3 3\'" if v==100 else ""}/>')
    svg.append(f'<text x="{X0-22}" y="{y(v)+4:.1f}" class="ax" text-anchor="end">{v}</text>')
svg.append(f'<text x="{X0-80}" y="{(TOP+BOT)/2:.0f}" class="ax" text-anchor="middle" transform="rotate(-90 {X0-80} {(TOP+BOT)/2:.0f})">Índice (septiembre = 100)</text>')
# zona proyección
xp = xs[n_m + n_r] - step / 2 - GAP / 2
svg.append(f'<rect x="{xp:.1f}" y="{TOP-30}" width="{X1+12-xp:.1f}" height="{OBOT-TOP+30+4}" fill="#f6f5f2"/>')
xr = xs[n_m] - step / 2 - GAP / 2
svg.append(f'<line x1="{xr:.1f}" x2="{xr:.1f}" y1="{TOP-30}" y2="{OBOT+4}" stroke="#cfcdc7" stroke-dasharray="3 3"/>')
svg.append(f'<line x1="{xp:.1f}" x2="{xp:.1f}" y1="{TOP-30}" y2="{OBOT+4}" stroke="#52514e" stroke-width="1.5"/>')
svg.append(f'<text x="{(X0+xr)/2:.0f}" y="{TOP-38}" class="zone" text-anchor="middle">REAL 2025 · PROMEDIO SEMANAL DEL MES</text>')
svg.append(f'<text x="{(xr+xp)/2:.0f}" y="{TOP-38}" class="zone" text-anchor="middle">REAL</text>')
svg.append(f'<text x="{xp+12:.0f}" y="{TOP-38}" class="zone">PROYECCIÓN · FORECAST DE OCTUBRE</text>')
# capacidad de alistamiento (índice sobre piezas de septiembre)
ycap = y(100 * CAP / SEP_P)
svg.append(f'<line x1="{xs[0]:.1f}" x2="{X1:.1f}" y1="{ycap:.1f}" y2="{ycap:.1f}" stroke="{P_COL}" stroke-width="1.4" stroke-dasharray="6 4" opacity=".75"/>')
svg.append(f'<text x="{X1-4:.0f}" y="{ycap-7:.1f}" class="lbl" fill="{P_COL}" text-anchor="end">Capacidad de alistamiento {k(CAP)} piezas/sem</text>')
# franja de ocupación
svg.append(f'<line x1="{X0-14}" x2="{X1+10}" y1="{oy(100):.1f}" y2="{oy(100):.1f}" stroke="{O_COL}" stroke-dasharray="4 3" stroke-width="1.2"/>')
svg.append(f'<text x="{X0-22}" y="{oy(100)+4:.1f}" class="ax" text-anchor="end" fill="{O_COL}">100 %</text>')
bw = step * 0.62
for x, q in zip(xs, pts):
    hgt = OBOT - oy(q["oc"])
    svg.append(f'<rect x="{x-bw/2:.1f}" y="{oy(q["oc"]):.1f}" width="{bw:.1f}" height="{hgt:.1f}" rx="3" fill="{O_FILL if q["oc"]<=100 else "#c9bff3"}"/>')
    svg.append(f'<text x="{x:.1f}" y="{OBOT-5:.1f}" class="oc" text-anchor="middle" fill="{O_COL}">{q["oc"]:.0f}%</text>')
svg.append(f'<text x="{X0-22}" y="{OBOT-5}" class="rowh" text-anchor="end" fill="{O_COL}" style="fill:{O_COL}">OCUPACIÓN</text>')

def path(idxf, sel):
    d = []
    for i in sel:
        d.append(f'{"M" if not d else "L"}{xs[i]:.1f},{y(idxf(pts[i])):.1f}')
    return " ".join(d)
real_ix = list(range(n_m + n_r)); proy_ix = list(range(n_m + n_r - 1, len(pts)))
for f_, col in [(idx_c, C_COL), (idx_p, P_COL)]:
    svg.append(f'<path d="{path(f_, real_ix)}" fill="none" stroke="{col}" stroke-width="2.6" stroke-linejoin="round"/>')
    svg.append(f'<path d="{path(f_, proy_ix)}" fill="none" stroke="{col}" stroke-width="2.6" stroke-dasharray="7 5" stroke-linejoin="round"/>')
    for i, q in enumerate(pts):
        filled = q["tipo"] != "proy"
        shape = "circle" if col == C_COL else "rect"
        cx, cy = xs[i], y(f_(q))
        if shape == "circle":
            svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.6" fill="{col if filled else "#fff"}" stroke="{col}" stroke-width="2"/>')
        else:
            svg.append(f'<rect x="{cx-4.2:.1f}" y="{cy-4.2:.1f}" width="8.4" height="8.4" fill="{col if filled else "#fff"}" stroke="{col}" stroke-width="2"/>')

# etiquetas: reales con volumen y cumplimiento; proyección solo en puntos clave
def etiqueta(i, f_, col, vol, cum=None, arriba=True):
    cx, cy = xs[i], y(f_(pts[i]))
    dy = -12 if arriba else 18
    svg.append(f'<text x="{cx:.1f}" y="{cy+dy:.1f}" class="lbl" text-anchor="middle" fill="{col}">{vol}</text>')
    if cum is not None:
        svg.append(f'<text x="{cx:.1f}" y="{cy+dy+(-12 if arriba else 12):.1f}" class="cum" text-anchor="middle" fill="{sem(cum)}">{cum:.0f}%</text>')
proy = list(range(n_m + n_r, len(pts)))
ic_max = max(proy, key=lambda i: pts[i]["c"]); ic_min = min(proy, key=lambda i: pts[i]["c"])
ip_max = max(proy, key=lambda i: pts[i]["pz"])
etiqueta(ic_max, idx_c, C_COL, k(pts[ic_max]["c"]))
etiqueta(ic_min, idx_c, C_COL, k(pts[ic_min]["c"]), arriba=False)
etiqueta(ip_max, idx_p, P_COL, k(pts[ip_max]["pz"]), arriba=False)

# filas de bultos y eje x
RB = 304
FILAS = [("CAJAS/SEM", C_COL), ("% CUMPL.", None), ("PIEZAS/SEM", P_COL), ("% CUMPL.", None), ("BULTOS/SEM", "#7a5a12"), ("TOTAL MES", "#7a5a12")]
RH = 17
svg.append(f'<rect x="{X0-92}" y="{RB-12+4*RH}" width="{X1-X0+106}" height="{2*RH+4}" fill="#fbf6ea"/>')
for r_, (nom, col) in enumerate(FILAS):
    yy = RB + r_ * RH
    svg.append(f'<text x="{X0-22}" y="{yy}" class="rowh" text-anchor="end" style="fill:{col or "#52514e"}">{nom}</text>')
for x, q in zip(xs, pts):
    it = "font-style='italic'" if q["tipo"] == "proy" else ""
    svg.append(f'<text x="{x:.1f}" y="{RB}" class="row" text-anchor="middle" style="fill:{C_COL}" {it}>{k(q["c"])}</text>')
    svg.append(f'<text x="{x:.1f}" y="{RB+2*RH}" class="row" text-anchor="middle" style="fill:{P_COL}" {it}>{k(q["pz"])}</text>')
    if q["tipo"] != "proy":
        svg.append(f'<text x="{x:.1f}" y="{RB+RH}" class="row b" text-anchor="middle" style="fill:{sem(q["cc"])}">{q["cc"]:.0f}%</text>')
        svg.append(f'<text x="{x:.1f}" y="{RB+3*RH}" class="row b" text-anchor="middle" style="fill:{sem(q["cp"])}">{q["cp"]:.0f}%</text>')
    svg.append(f'<text x="{x:.1f}" y="{RB+4*RH}" class="row" text-anchor="middle" {it}>{k(q["b"])}</text>')
    svg.append(f'<text x="{x:.1f}" y="{RB+6*RH+8}" class="xl" text-anchor="middle">{q["lab"]}</text>')
for m in range(1, 10):
    svg.append(f'<text x="{xs[m-1]:.1f}" y="{RB+5*RH}" class="row b" text-anchor="middle">{k(mens.loc[m, "total"])}</text>')
grupos = {}
for i, q in enumerate(pts[n_m:], n_m):
    a_ = q.get("anio", 2025)
    key_ = (a_ - 1 if (q["mes"] == 12 and a_ == 2026) else a_, q["mes"])
    grupos.setdefault(key_, []).append(i)
NOMBRES = {10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE", 1: "ENERO 2026", 2: "FEBRERO", 3: "MARZO"}
for (a, m), ii in grupos.items():
    tot = sum(pts[i]["b"] for i in ii)
    xm = (xs[ii[0]] + xs[ii[-1]]) / 2
    svg.append(f'<text x="{xm:.1f}" y="{RB+5*RH}" class="row b" text-anchor="middle">{k(tot)}{" *" if m == 10 else ""}</text>')
    svg.append(f'<text x="{xm:.1f}" y="{RB+6*RH+26}" class="xm" text-anchor="middle">{NOMBRES[m]}</text>')
    if ii[0] != n_m:
        xl = xs[ii[0]] - step / 2
        svg.append(f'<line x1="{xl:.1f}" x2="{xl:.1f}" y1="{RB-12+4*RH}" y2="{RB+6*RH-8}" stroke="#e8dcc0"/>')
svg.append(f'<text x="{(xs[0]+xs[8])/2:.1f}" y="{RB+6*RH+26}" class="xm" text-anchor="middle">2025</text>')
SVG = f'<svg width="{W}" height="{RB+6*RH+34}" viewBox="0 0 {W} {RB+6*RH+34}">{"".join(svg)}</svg>'

# ---------- Tabla mensual ----------
filas = [("Septiembre real", SEP_C, SEP_P, mens.loc[9, "bultos"], mens.loc[9, "total"])]
oct_ix = grupos[(2025, 10)]
filas.append(("Octubre*", sum(pts[i]["c"] for i in oct_ix) / len(oct_ix), sum(pts[i]["pz"] for i in oct_ix) / len(oct_ix),
              sum(pts[i]["b"] for i in oct_ix) / len(oct_ix), sum(pts[i]["b"] for i in oct_ix)))
for (a, m), nombre in [((2025, 11), "Noviembre"), ((2025, 12), "Diciembre"), ((2026, 1), "Enero 2026"), ((2026, 2), "Febrero 2026"), ((2026, 3), "Marzo 2026")]:
    ii = grupos[(a, m)]
    filas.append((nombre, sum(pts[i]["c"] for i in ii) / len(ii), sum(pts[i]["pz"] for i in ii) / len(ii),
                  sum(pts[i]["b"] for i in ii) / len(ii), sum(pts[i]["b"] for i in ii)))
def n(v): return f"{v:,.0f}".replace(",", ".")
def var(v): return (f"{v:+.1f} %").replace(".", ",")
tr = []
for j, (nom, c, pz, b, tot) in enumerate(filas):
    if j == 0:
        tr.append(f"<tr class='sep'><td>{nom}</td><td>{n(c)}</td><td></td><td>{n(pz)}</td><td></td><td></td><td class='bu'>{n(b)}</td><td class='bu'></td><td class='bu b'>{n(tot)}</td></tr>")
        continue
    _, c0, p0, b0, _ = filas[j - 1]
    vc, vp, vb = 100 * (c / c0 - 1), 100 * (pz / p0 - 1), 100 * (b / b0 - 1)
    br = vc - vp
    cls = "pos" if br > 2 else ("neg" if br < -2 else "")
    tr.append(f"<tr><td>{nom}</td><td>{n(c)}</td><td>{var(vc)}</td><td>{n(pz)}</td><td>{var(vp)}</td><td class='{cls}'>{(f'{br:+.1f}').replace('.', ',')}</td>"
              f"<td class='bu'>{n(b)}</td><td class='bu'>{var(vb)}</td><td class='bu b'>{n(tot)}</td></tr>")
TABLA = "".join(tr)

# ---------- Proyección con +10 % de recibo (para la conclusión) ----------
sem_tabla = pd.read_csv(BASE / "outputs/semaforo.csv").set_index("cd")
NORTE_PICO, NORTE_FALT = sem_tabla.loc["CD-Norte", "pico_%"], sem_tabla.loc["CD-Norte", "posiciones_faltantes"]

f = lambda v, d=1: f"{v:.{d}f}".replace(".", ",")
HTML = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Lámina nacional · RetailCo</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1600px;height:900px;background:#fff;font-family:Inter,Arial,sans-serif;color:#1d1d1b;position:relative;overflow:hidden}}
h1{{position:absolute;left:30px;top:24px;font-size:38px;font-weight:800;letter-spacing:-.5px;color:#2b2b2a}}
.sub{{position:absolute;left:31px;top:78px;font-size:15px;color:#5b5a56}}
.kpis{{position:absolute;left:30px;top:108px;display:flex;gap:14px;align-items:stretch}}
.kpi{{display:flex;border-radius:7px;overflow:hidden;height:46px}}
.kpi .main{{color:#fff;font-weight:800;font-size:19px;padding:0 14px;display:flex;align-items:center;letter-spacing:.2px}}
.kpi .side{{padding:6px 12px;font-size:11px;line-height:1.45;color:#5b5a56;display:flex;flex-direction:column;justify-content:center}}
.kpi .side b{{font-size:14px;font-weight:800}}
.cap{{text-transform:uppercase;letter-spacing:.6px;font-size:10px;font-weight:700}}
.nota{{font-size:12px;color:#5b5a56;line-height:1.5;align-self:center;margin-left:6px}}
.legend{{position:absolute;right:40px;top:200px;z-index:2;padding:2px 0 2px 10px;display:flex;gap:16px;font-size:12px;color:#3d3c39;align-items:center}}
.legend i{{display:inline-block;vertical-align:middle;margin-right:5px}}
.chart{{position:absolute;left:4px;top:166px}}
.ax{{font-size:11px;fill:#7a7975}} .zone{{font-size:11.5px;font-weight:700;letter-spacing:.6px;fill:#3d3c39}}
.lbl{{font-size:10.5px;font-weight:700}} .cum{{font-size:10px;font-weight:700}} .oc{{font-size:10px;font-weight:600}}
.row{{font-size:10px;fill:#5b4a1f}} .row.b{{font-weight:800;fill:#3d2f0c}} .rowh{{font-size:10px;font-weight:800;fill:#7a5a12;letter-spacing:.4px}}
.xl{{font-size:11px;fill:#3d3c39;font-weight:600}} .xm{{font-size:11.5px;font-weight:800;fill:#2b2b2a;letter-spacing:.4px}}
.tbl{{position:absolute;left:30px;top:614px;width:1080px;border-radius:8px;overflow:hidden;border:1px solid #e4e2dc}}
.tbl .tt{{background:#2b2b2a;color:#fff;font-weight:800;font-size:12.5px;text-align:center;padding:6px;letter-spacing:.5px}}
table{{width:100%;border-collapse:collapse;font-size:12.5px}}
th{{font-size:11px;font-weight:700;color:#fff;padding:4px 8px}}
.g1 th{{padding:3px}} th.c{{background:{C_COL}}} th.p{{background:{P_COL}}} th.bh{{background:#8a6a1e}} th.per{{background:#3d3c39}}
td{{padding:3px 10px;text-align:right;border-top:1px solid #efeee9}} td:first-child{{text-align:left;font-weight:700}}
tr.sep td{{background:#f4f3ef;font-weight:700}} .bu{{background:#fbf6ea}} .b{{font-weight:800}}
.pos{{color:#c62828;font-weight:800}} .neg{{color:#2a6fd6;font-weight:800}}
.concl{{position:absolute;left:1128px;top:614px;width:442px;height:222px;border:1px solid #f0d9c6;background:#fff8f2;border-radius:8px;padding:14px 16px}}
.concl h3{{font-size:12.5px;letter-spacing:.8px;color:#b4471c;margin-bottom:6px}}
.concl p{{font-size:14px;line-height:1.5;color:#2b2b2a}}
.concl small{{display:block;margin-top:8px;font-size:10.5px;color:#7a7975;line-height:1.45}}
.foot{{position:absolute;left:30px;top:846px;width:1260px;font-size:10.5px;color:#7a7975;line-height:1.45}}
.brand{{position:absolute;right:30px;top:846px;text-align:right;font-size:11px;color:#7a7975}}
.brand b{{display:block;font-size:20px;color:#2b2b2a;letter-spacing:-.3px}}
.bar{{position:absolute;left:0;bottom:0;width:100%;height:14px;background:linear-gradient(90deg,#2b2b2a 0 76%,{C_COL} 76% 88%,{P_COL} 88%)}}
</style></head><body>
<h1>Red · recibo, alistamiento y ocupación</h1>
<div class="sub">Real 2025 (promedio semanal por mes y semanas S41–S42) y proyección semanal con el forecast de octubre · índice septiembre = 100 · etiquetas: volumen y % de cumplimiento del forecast</div>
<div class="kpis">
 <div class="kpi"><div class="main" style="background:{C_COL}">CAJAS ▲ +{f(VAR_C,0)} %</div><div class="side" style="background:#fdeee6"><span class="cap">Cumpl. forecast recibo</span><span>sep <b style="color:{sem(CUM_C_SEP)}">{CUM_C_SEP:.0f} %</b> &nbsp;oct <b style="color:{sem(CUM_C_OCT)}">{CUM_C_OCT:.0f} %</b></span></div></div>
 <div class="kpi"><div class="main" style="background:{P_COL}">PIEZAS ▲ +{f(VAR_P,0)} %</div><div class="side" style="background:#e7effb"><span class="cap">Cumpl. forecast alistamiento</span><span>sep <b style="color:{sem(CUM_P_SEP)}">{CUM_P_SEP:.0f} %</b> &nbsp;oct <b style="color:{sem(CUM_P_OCT)}">{CUM_P_OCT:.0f} %</b></span></div></div>
 <div class="kpi"><div class="main" style="background:{O_COL}">OCUPACIÓN PICO {OCUP_PICO:.0f} % · S{SEM_PICO}</div></div>
 <div class="nota">▲ Promedio semanal S45–S51 frente a septiembre real<br>Cumplimiento = real ÷ forecast · oct = S41–S42</div>
</div>
<div class="legend">
 <span><i style="width:18px;height:3px;background:{C_COL}"></i>Cajas (recibo)</span>
 <span><i style="width:18px;height:3px;background:{P_COL}"></i>Piezas (alistamiento)</span>
 <span><i style="width:18px;height:0;border-top:2px dashed #52514e"></i>Proyección</span>
 <span><i style="width:12px;height:12px;background:{O_FILL};border-radius:2px"></i>Ocupación red propia</span>
 <span><i style="width:10px;height:10px;background:#1a7f37"></i>95–105 %</span>
 <span><i style="width:10px;height:10px;background:#c62828"></i>&gt;105 %</span>
 <span><i style="width:10px;height:10px;background:#8d6e2b"></i>&lt;95 %</span>
</div>
<div class="chart">{SVG}</div>
<div class="tbl"><div class="tt">RED · FORECAST POR MES · VARIACIÓN FRENTE AL MES ANTERIOR</div>
<table><tr class="g1"><th class="per" rowspan="2">Periodo</th><th class="c" colspan="2">RECIBO</th><th class="p" colspan="3">ALISTAMIENTO</th><th class="bh" colspan="3">BULTOS</th></tr>
<tr><th class="c">Cajas por semana</th><th class="c">Var. mes ant.</th><th class="p">Piezas por semana</th><th class="p">Var. mes ant.</th><th class="p">Brecha (pp)</th><th class="bh">Bultos por semana</th><th class="bh">Var. mes ant.</th><th class="bh">Bultos total mes</th></tr>
{TABLA}</table></div>
<div class="concl"><h3>CONCLUSIÓN</h3>
<p><b>La red propia queda justa:</b> llega a {OCUP_PICO:.0f} % en la S{SEM_PICO} sin pasar de 100 %. El faltante se concentra en <b>CD-Norte</b> ({f(NORTE_PICO)} %, {NORTE_FALT:.0f} posiciones). El recibo crece <b>+{f(VAR_C,0)} %</b> y el alistamiento <b>+{f(VAR_P,0)} %</b>, y el recibo real viene <b>{CUM_C_OCT-100:.0f} %</b> sobre el forecast en octubre.</p>
<small>*Octubre = S41–S42 reales + S43–S44 de forecast. Bultos = piezas de cada centro ÷ sus piezas por bulto. Total mes = suma de las semanas del mes (4 o 5).</small></div>
<div class="foot">Red = suma de CD-Norte, CD-Centro, CD-Oriente, CD-Bebidas y OPL-Frio. Ocupación = promedio ponderado por posiciones de los 4 centros propios (el OPL no entra). Proyección: forecast de octubre sin margen y modelo de flujo calibrado por centro. Capacidad (punteada) = suma de la capacidad semanal de alistamiento de los 5 centros.</div>
<div class="brand"><b>RetailCo</b>Datos ficticios · caso de estudio</div>
<div class="bar"></div>
</body></html>"""

out_html = BASE / "reportes/lamina_nacional.html"
out_html.write_text(HTML, encoding="utf-8")
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=1.5)
        pg.goto(out_html.as_uri()); pg.wait_for_timeout(300)
        pg.screenshot(path=str(BASE / "img/lamina_nacional.png")); b.close()
    print("ok")
except ImportError:
    print("Playwright no está instalado: se generó solo el HTML")
