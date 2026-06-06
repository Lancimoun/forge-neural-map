#!/usr/bin/env python3
"""
Bake graph.json -> nodes.json  (VOLUMETRIC UNIVERSE)
No Man's Sky look: each planet orbits on its OWN randomly tilted plane
(spherical orbital shells, not a flat cookie), communities arranged in a
real spiral galaxy WITH THICKNESS, nebula radius per cluster.
"""
import json, math, random, colorsys, re, os

random.seed(7)
g = json.load(open("graph.json"))
nodes = g["nodes"]
links = g["links"]

# ---- degree ----
deg = {n["id"]: 0 for n in nodes}
for l in links:
    if l["source"] in deg: deg[l["source"]] += 1
    if l["target"] in deg: deg[l["target"]] += 1

# ---- group by community ----
comms = {}
for n in nodes:
    comms.setdefault(int(n["community"]), []).append(n)
comm_ids = sorted(comms.keys())
NC = len(comm_ids)

# ---- spiral galaxy layout for community centers (WITH thickness) ----
ARMS = 5
GAL_R = 1650.0
# order communities by size so big clusters sit along the arms nicely
order = sorted(comm_ids, key=lambda c: -len(comms[c]))

gal = {}   # community -> (gR, gPh, gSp, gY, nebR)
for rank, cid in enumerate(order):
    f = rank / max(1, NC - 1)              # 0..1 outward
    Rg = 150 + (f ** 0.80) * GAL_R         # radius from galactic center
    arm = rank % ARMS
    base = (arm / ARMS) * 2 * math.pi
    wind = 2.3                             # how tightly arms wrap
    jitter = random.uniform(-0.18, 0.18)
    gPh = base + (Rg / GAL_R) * wind * math.tau if hasattr(math, "tau") else base + (Rg / GAL_R) * wind * 2 * math.pi
    gPh += jitter
    gSp = 9.0 / math.sqrt(max(40.0, Rg))   # inner systems revolve faster
    # DISC THICKNESS: thicker near center, thins outward, gaussian
    thick = (90.0 * (1.0 - 0.6 * f)) * random.gauss(0, 1)
    gY = max(-260, min(260, thick))
    members = comms[cid]
    nebR = 60 + 26 * math.log(len(members) + 1.5)   # nebula glow radius
    gal[cid] = (Rg, gPh % (2 * math.pi), gSp, gY, nebR)

# ---- per-node orbital params ----
def rand_unit():
    # uniform point on sphere
    u = random.uniform(-1, 1); th = random.uniform(0, 2 * math.pi)
    r = math.sqrt(1 - u * u)
    return (math.cos(th) * r, math.sin(th) * r, u)

def basis_from_normal(n):
    # orthonormal U,V spanning plane perpendicular to n
    ax = (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0)
    # U = normalize(ax x n)
    ux = ax[1]*n[2]-ax[2]*n[1]; uy = ax[2]*n[0]-ax[0]*n[2]; uz = ax[0]*n[1]-ax[1]*n[0]
    ul = math.sqrt(ux*ux+uy*uy+uz*uz) or 1.0
    U = (ux/ul, uy/ul, uz/ul)
    # V = n x U
    V = (n[1]*U[2]-n[2]*U[1], n[2]*U[0]-n[0]*U[2], n[0]*U[1]-n[1]*U[0])
    return U, V

GR=[];GPH=[];GSP=[];GY=[];UX=[];UY=[];UZ=[];VX=[];VY=[];VZ=[];R=[];PH=[];SP=[];C=[];S=[];NEB=[]
LB=[];DG=[];CM=[]  # label, degree, community (for hover discovery)
TP=[];FI=[];SL=[];DS=[]  # type, source-file index, source location, real summary
files_list=[]; files_idx={}
bidx={}            # node id -> bake index (for intra-system adjacency)

# pull a real one-line summary (signature + docstring) from the actual source
SRC_ROOT=".."      # repo root (telegram_bot/) relative to forge-neural-map/
_dc={}
def get_desc(sf, lab):
    # search the real Python source for the def/class by NAME (robust to line drift),
    # return its signature + first docstring line. Only .py — keeps it accurate.
    if not sf or not sf.endswith(".py") or not lab: return ""
    name = lab[:-2] if lab.endswith("()") else lab
    name = name.strip()
    if not re.match(r"^[A-Za-z_]\w*$", name): return ""
    path = os.path.join(SRC_ROOT, sf)
    if path not in _dc:
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                _dc[path] = fh.read().splitlines()
        except Exception:
            _dc[path] = None
    lines = _dc[path]
    if not lines: return ""
    pat = re.compile(r"^\s*(async\s+def|def|class)\s+" + re.escape(name) + r"\b")
    for k, line in enumerate(lines):
        if pat.match(line):
            sig = line.strip().rstrip(":")
            out = sig
            for j in range(k+1, min(k+4, len(lines))):
                s = lines[j].strip()
                if s[:1] in ('"', "'"):
                    doc = s.strip('"\' ').strip()
                    if doc: out = sig + "  —  " + doc
                    break
            return out[:180]
    return ""

for cid in comm_ids:
    members = sorted(comms[cid], key=lambda n: -deg[n["id"]])
    Rg, gPh, gSp, gYc, nebR = gal[cid]
    # community color (golden angle)
    hue = (cid * 137.508 % 360) / 360.0
    rr, gg, bb = colorsys.hls_to_rgb(hue, 0.60, 0.95)
    hexc = "#%02x%02x%02x" % (int(rr*255), int(gg*255), int(bb*255))
    for mi, n in enumerate(members):
        d = deg[n["id"]]
        GR.append(round(Rg,1)); GPH.append(round(gPh,4)); GSP.append(round(gSp,5)); GY.append(round(gYc,1))
        C.append(hexc); NEB.append(round(nebR,1))
        LB.append(n.get("label") or n.get("id","")); DG.append(d); CM.append(cid)
        sf=n.get("source_file") or ""
        if sf not in files_idx: files_idx[sf]=len(files_list); files_list.append(sf)
        FI.append(files_idx[sf]); SL.append(n.get("source_location") or "")
        _lab=n.get("label") or ""
        TP.append("function" if _lab.endswith(")") else
                  ("file" if re.search(r"\.(py|js|ts|md|json|txt|html|css|ya?ml|sh|cfg|ini|toml)$",_lab,re.I) else
                   ("doc" if n.get("file_type")=="doc" else "symbol")))
        DS.append(get_desc(sf, _lab))
        bidx[n["id"]]=len(LB)-1
        if mi == 0:
            # SUN: sits at system center
            S.append(round(3.6 + 1.5*math.log(d+2), 2))
            R.append(0.0); PH.append(0.0); SP.append(0.0)
            UX.append(0.0);UY.append(0.0);UZ.append(0.0);VX.append(0.0);VY.append(0.0);VZ.append(0.0)
        else:
            # PLANET: own tilted orbital plane -> volumetric shell (no cookie)
            nrm = rand_unit()
            U, V = basis_from_normal(nrm)
            orb = 10 + 16 * math.log(mi + 1.4)        # spread orbital radii
            orb *= random.uniform(0.9, 1.12)
            sp = 9.0 / math.sqrt(max(6.0, orb)) * random.uniform(0.85, 1.15)
            R.append(round(orb,2)); PH.append(round(random.uniform(0,2*math.pi),4)); SP.append(round(sp,4))
            UX.append(round(U[0],4));UY.append(round(U[1],4));UZ.append(round(U[2],4))
            VX.append(round(V[0],4));VY.append(round(V[1],4));VZ.append(round(V[2],4))
            S.append(round(1.5 + 0.9*math.log(d+2), 2))

# intra-system adjacency (links whose endpoints share a community → renderable in system view)
comm_of_id = {n["id"]: int(n["community"]) for n in nodes}
NB = [[] for _ in range(len(LB))]
for l in links:
    s = l.get("source"); t = l.get("target")
    if s in bidx and t in bidx and comm_of_id.get(s) == comm_of_id.get(t):
        NB[bidx[s]].append(bidx[t]); NB[bidx[t]].append(bidx[s])
NB = [sorted(set(x)) for x in NB]

# global link list (flat bake-index pairs) for the galaxy-wide neural web
GL = []
for l in links:
    s = l.get("source"); t = l.get("target")
    if s in bidx and t in bidx:
        GL += [bidx[s], bidx[t]]

out = {
  "gR":GR,"gPh":GPH,"gSp":GSP,"gY":GY,
  "ux":UX,"uy":UY,"uz":UZ,"vx":VX,"vy":VY,"vz":VZ,
  "r":R,"ph":PH,"sp":SP,"c":C,"s":S,"neb":NEB,
  "lb":LB,"dg":DG,"cm":CM,
  "tp":TP,"fi":FI,"sl":SL,"files":files_list,"ds":DS,"nb":NB,"gl":GL,
  "meta":{"nodes":len(GR),"links":len(links),"communities":NC,
          "loc":26000,
          "hub":(LB[DG.index(max(DG))] if DG else "")}
}
json.dump(out, open("nodes.json","w"), separators=(",",":"))
import os
print("volumetric universe baked: %.1f KB | %s" % (os.path.getsize("nodes.json")/1024, out["meta"]))
