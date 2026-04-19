"""
CIPHER Overlay — JARVIS × Ultron aesthetic. 60fps QPainter HUD.
"""
from __future__ import annotations
import math
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import psutil
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QFontDatabase,
    QLinearGradient, QRadialGradient, QPainterPath, QKeySequence,
)
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QShortcut

# ── Palette ────────────────────────────────────────────────────────────────────
CY  = QColor(0,   220, 255)
BL  = QColor(0,   100, 255)
RD  = QColor(255,  60,  60)
GR  = QColor(0,   200, 110)
YL  = QColor(255, 200,   0)

CAT_COLORS = {
    "chat":     CY,
    "system":   BL,
    "security": RD,
    "file":     GR,
    "web":      YL,
    "default":  QColor(140, 190, 220),
}


# ── Spring physics ─────────────────────────────────────────────────────────────
@dataclass
class Spring:
    value:    float = 0.0
    target:   float = 0.0
    velocity: float = 0.0
    k:        float = 14.0
    damp:     float = 9.0

    def step(self, dt: float) -> float:
        self.velocity += (self.target - self.value) * self.k * dt
        self.velocity -= self.velocity * self.damp * dt
        self.value    += self.velocity * dt
        return self.value


# ── Log entry ─────────────────────────────────────────────────────────────────
@dataclass
class LogEntry:
    text:     str
    category: str
    revealed: int   = 0
    alpha:    float = 1.0
    age:      float = 0.0


# ── Stats worker ──────────────────────────────────────────────────────────────
class StatsWorker(QThread):
    updated = pyqtSignal(float, float, float, float, float)

    def run(self):
        while True:
            try:
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                gpu = vu = vt = 0.0
                try:
                    import GPUtil
                    gs = GPUtil.getGPUs()
                    if gs:
                        gpu = gs[0].load * 100
                        vu  = gs[0].memoryUsed  / 1024
                        vt  = gs[0].memoryTotal / 1024
                except Exception:
                    pass
                self.updated.emit(cpu, ram, gpu, vu, vt)
            except Exception:
                pass
            self.msleep(1500)


# ── Main overlay widget ───────────────────────────────────────────────────────
class CipherOverlay(QWidget):
    _log_sig   = pyqtSignal(str, str)
    _wave_sig  = pyqtSignal(object)
    _agent_sig = pyqtSignal(str, str)

    def __init__(self, W: int, H: int):
        super().__init__()
        self.W, self.H = W, H

        self.setGeometry(0, 0, W, H)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Ctrl+Shift+Q → quit CIPHER
        QShortcut(QKeySequence("Ctrl+Shift+Q"), self, activated=QApplication.quit)

        self._state = "idle"
        self._t     = 0.0
        self._last  = time.monotonic()

        # Springs
        self._exp = Spring()
        self._lp  = Spring()
        self._rp  = Spring()
        self._orb = Spring()

        # Orb
        self._ocx   = W // 2
        self._ocy   = H // 2 - 25
        self._rang  = [0.0, 120.0, 240.0]
        self._rspd  = [52.0, -37.0, 26.0]
        self._pulse = 0.0
        self._proc  = False
        self._glow  = 110.0
        self._cracks = self._gen_cracks()

        # FX
        self._shocks:    list[dict] = []
        self._arcs:      list[dict] = []
        self._next_arc   = random.uniform(12, 18)
        self._edge_flash = 0.0
        self._scan_y     = -1.0
        self._scan_spd   = H / 0.35

        # Matrix streams
        self._streams:     list[dict] = []
        self._next_stream  = random.uniform(6, 14)

        # Corner brackets
        self._brk_t = 0.0

        # Glitch
        self._idle_glitch  = False
        self._next_idle_g  = random.uniform(9, 18)
        self._holo         = False
        self._next_holo    = random.uniform(44, 58)

        # Stats
        self._cpu = self._ram = self._gpu = 0.0
        self._vu  = self._vt  = 0.0

        # Bar particles
        self._bparts: list[dict] = []

        # Log
        self._log: list[LogEntry] = []

        # Waveform + mic
        self._wave = [0.0] * 280
        self._mic  = [0.0] * 20

        # Bottom bar
        self._agent    = ""
        self._a_active = False
        self._resp_ms  = 0
        self._model    = "gemma-4-31b"
        self._start    = time.monotonic()

        # Fonts
        self._fh = QFont("Consolas", 10, QFont.Weight.Bold)
        self._fd = QFont("Consolas", 9)
        self._fs = QFont("Consolas", 8)
        self._load_fonts()

        # Workers
        sw = StatsWorker(self)
        sw.updated.connect(self._on_stats)
        sw.start()

        self._log_sig.connect(self._recv_log)
        self._wave_sig.connect(self._recv_wave)
        self._agent_sig.connect(self._recv_agent)

        tmr = QTimer(self)
        tmr.timeout.connect(self._tick)
        tmr.start(16)

    # ── helpers ───────────────────────────────────────────────────────────────
    def _load_fonts(self):
        fdir = Path(__file__).parent / "assets" / "fonts"
        if fdir.exists():
            for f in fdir.glob("*.ttf"):
                QFontDatabase.addApplicationFont(str(f))
        fams = QFontDatabase.families()
        if "Orbitron" in fams:
            self._fh = QFont("Orbitron", 9, QFont.Weight.Bold)
        if "Share Tech Mono" in fams:
            self._fd = QFont("Share Tech Mono", 9)
            self._fs = QFont("Share Tech Mono", 8)

    def _gen_cracks(self) -> list:
        out = []
        for _ in range(7):
            ang, segs = random.uniform(0, 360), []
            for i in range(6):
                ang += random.uniform(-25, 25)
                r    = 16 + i * 9
                segs.append((math.cos(math.radians(ang))*r,
                             math.sin(math.radians(ang))*r))
            out.append(segs)
        return out

    def _lightning(self, p1, p2, depth=4) -> list:
        if depth == 0:
            return [p1, p2]
        dx, dy = p2[0]-p1[0], p2[1]-p1[1]
        ln = math.hypot(dx, dy) or 1
        mx, my = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
        off = random.gauss(0, 1) * ln * 0.28
        px, py = -dy/ln, dx/ln
        mid = (mx+px*off, my+py*off)
        return self._lightning(p1, mid, depth-1)[:-1] + self._lightning(mid, p2, depth-1)

    def _lpx(self) -> int:
        return int(-244 + self._lp.value * 264)

    def _rpx(self) -> int:
        return int(self.W - 18 - self._rp.value * 264)

    # ── 60fps tick ────────────────────────────────────────────────────────────
    def _tick(self):
        now = time.monotonic()
        dt  = min(now - self._last, 0.05)
        self._last = now
        self._t   += dt

        on = self._state in ("active", "deactivating")
        for sp, tgt in [(self._exp, on), (self._lp, on), (self._rp, on), (self._orb, on)]:
            sp.target = 1.0 if tgt else 0.0
            sp.step(dt)
        if self._state == "deactivating" and self._exp.value < 0.04:
            self._state = "idle"

        for i in range(3):
            self._rang[i] += self._rspd[i] * dt * (1.5 if self._proc else 1.0)

        self._pulse = max(0.0, self._pulse - 4.0 * dt)
        tg = 140 if self._proc else 105
        self._glow += (tg - self._glow) * 4.0 * dt

        for sw in self._shocks[:]:
            sw["r"]    += 370 * dt
            sw["alpha"] = max(0.0, sw["alpha"] - dt / 0.7)
            if sw["alpha"] <= 0: self._shocks.remove(sw)

        if self._t > self._next_arc and self._state == "active":
            self._spawn_arc()
            self._next_arc = self._t + random.uniform(10, 16)
        for arc in self._arcs[:]:
            arc["life"] -= dt / 0.14
            if arc["life"] <= 0: self._arcs.remove(arc)

        if self._t > self._next_stream:
            self._spawn_stream()
            self._next_stream = self._t + random.uniform(22, 38)
        for ms in self._streams[:]:
            ms["y"] += ms["spd"] * dt
            if random.random() < 0.08:
                ms["chars"][random.randint(0, len(ms["chars"])-1)] = \
                    random.choice("0123456789ABCDEF")
            if ms["y"] > self.H + 260: self._streams.remove(ms)

        if self._scan_y >= 0:
            self._scan_y += self._scan_spd * dt
            if self._scan_y > self.H: self._scan_y = -1.0

        self._edge_flash = max(0.0, self._edge_flash - dt * 6)
        self._brk_t = (self._brk_t + dt) % 8.0

        for p in self._bparts[:]:
            p["x"] += p["vx"]*dt*60; p["y"] += p["vy"]*dt*60
            p["l"]  = max(0.0, p["l"] - dt*2.2)
            if p["l"] <= 0: self._bparts.remove(p)
        if self._exp.value > 0.5 and random.random() < 0.35:
            self._spawn_bpart()

        self._idle_glitch = False
        if self._state == "idle" and self._t > self._next_idle_g:
            self._idle_glitch = True
            self._next_idle_g = self._t + random.uniform(9, 18) + 0.07

        self._holo = False
        if self._state == "active" and self._t > self._next_holo:
            self._holo = True
            self._next_holo = self._t + random.uniform(44, 58) + 0.12

        for e in self._log:
            if e.revealed < len(e.text):
                e.revealed = min(len(e.text), e.revealed + 4)
            e.age += dt
            if e.age > 9.0:
                e.alpha = max(0.0, e.alpha - dt * 0.25)

        for i in range(20):
            tgt = max(0.0, math.sin(self._t*3 + i*0.4)*0.07 + 0.02)
            self._mic[i] = self._mic[i]*0.85 + tgt*0.15

        self.update()

    # ── spawners ──────────────────────────────────────────────────────────────
    def _spawn_arc(self):
        ang = random.uniform(0, 360)
        r   = 108 + random.uniform(15, 55)
        end = (self._ocx + math.cos(math.radians(ang))*r,
               self._ocy + math.sin(math.radians(ang))*r)
        self._arcs.append({"pts": self._lightning((self._ocx, self._ocy), end), "life": 1.0})

    def _spawn_stream(self):
        x = random.choice(list(range(8, 55, 11)) + list(range(self.W-55, self.W-8, 11)))
        self._streams.append({
            "x": x, "y": -220, "spd": random.uniform(38, 90),
            "chars": [random.choice("0123456789ABCDEF") for _ in range(22)],
            "alpha": random.uniform(0.035, 0.09), "gap": 13,
        })

    def _spawn_bpart(self):
        rows = [("cpu", self._cpu, 40), ("ram", self._ram, 65), ("gpu", self._gpu, 90)]
        _, lvl, dy = random.choice(rows)
        if lvl < 3: return
        lx = self._lpx() + 54
        by = self.H//2 - 90 + dy + 5
        c  = (255,55,55) if lvl>80 else (0,210,255)
        self._bparts.append({
            "x": lx + random.uniform(0, 162*lvl/100),
            "y": by + random.uniform(-2, 2),
            "vx": random.uniform(0.6,2.0), "vy": random.uniform(-0.4,0.4),
            "l": 1.0, "c": c,
        })

    # ── signal receivers ──────────────────────────────────────────────────────
    def _on_stats(self, cpu, ram, gpu, vu, vt):
        self._cpu, self._ram, self._gpu = cpu, ram, gpu
        self._vu, self._vt = vu, vt

    def _recv_log(self, msg: str, cat: str):
        key = "default"
        for k in CAT_COLORS:
            if k in msg.lower() or k in cat.lower(): key = k; break
        self._log.append(LogEntry(text=msg[:90], category=key))
        if len(self._log) > 22: self._log.pop(0)

    def _recv_wave(self, data):
        if data is not None:
            self._wave = list(data)[:280]
            n = len(self._wave); chunk = max(1, n//20)
            for i in range(20):
                seg = self._wave[i*chunk:(i+1)*chunk]
                self._mic[i] = min(1.0, abs(sum(seg)/len(seg))*18) if seg else 0.0
        else:
            self._wave = [0.0]*280

    def _recv_agent(self, name: str, status: str):
        self._agent    = name
        self._a_active = bool(name and status)
        self._proc     = self._a_active

    # ── paintEvent ────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        if self._holo and random.random() < 0.6:
            self._draw_holo(p); p.end(); return

        exp = self._exp.value
        if exp > 0.02:
            p.fillRect(0, 0, self.W, self.H, QColor(2, 8, 20, int(exp*130)))

        self._draw_streams(p)
        self._draw_vignette(p, exp)
        self._draw_idle_line(p, exp)
        self._draw_corners(p, exp)

        if exp > 0.02:
            self._draw_edge_flash(p)
            self._draw_scanline(p)
            self._draw_shocks(p)
            self._draw_left_panel(p, exp)
            self._draw_right_panel(p, exp)
            self._draw_orb(p, exp)
            self._draw_waveform(p, exp)
            self._draw_bottom(p, exp)
        p.end()

    # ── draw methods ──────────────────────────────────────────────────────────
    def _draw_vignette(self, p: QPainter, exp: float):
        a = 65 + int(exp*60)
        for x0,y0,w,h,vert,inv in [
            (0,0,self.W,100,True,False),(0,self.H-100,self.W,100,True,True),
            (0,0,80,self.H,False,False),(self.W-80,0,80,self.H,False,True),
        ]:
            g = QLinearGradient(0,y0,0,y0+h) if vert else QLinearGradient(x0,0,x0+w,0)
            c0,c1 = (QColor(0,0,0,a),QColor(0,0,0,0)) if not inv else (QColor(0,0,0,0),QColor(0,0,0,a))
            g.setColorAt(0,c0); g.setColorAt(1,c1)
            p.fillRect(x0,y0,w,h,g)

    def _draw_idle_line(self, p: QPainter, exp: float):
        a = int((1-exp)*255)
        if a < 5: return
        if self._idle_glitch:
            p.setPen(QPen(QColor(0,230,200,a),1))
            for _ in range(random.randint(3,7)):
                x1=random.randint(0,self.W); x2=x1+random.randint(15,140)
                p.drawLine(x1,self.H-1+random.randint(-2,2),x2,self.H-1+random.randint(-2,2))
            return
        bth = (math.sin(self._t*0.7)+1)/2
        r=0; g=int(150+70*bth); b=255
        p.setPen(QPen(QColor(r,g,b,a),1))
        p.drawLine(0,self.H-1,self.W,self.H-1)
        gr = QLinearGradient(0,self.H-7,0,self.H-1)
        gr.setColorAt(0,QColor(r,g,b,0)); gr.setColorAt(1,QColor(r,g,b,a//4))
        p.fillRect(0,self.H-7,self.W,6,gr)

    def _draw_corners(self, p: QPainter, exp: float):
        sz=22; pulse=max(0,math.sin(self._brk_t*math.pi*2/0.6)) if self._brk_t<0.6 else 0
        a=int(min(1.0,0.08+exp*0.28+pulse*0.35)*255)
        if a<4: return
        p.setPen(QPen(QColor(0,200,255,a),1.5))
        for cx,cy,sx,sy in [(8,8,1,1),(self.W-8,8,-1,1),(8,self.H-8,1,-1),(self.W-8,self.H-8,-1,-1)]:
            p.drawLine(cx,cy,cx+sx*sz,cy); p.drawLine(cx,cy,cx,cy+sy*sz)

    def _draw_streams(self, p: QPainter):
        if not self._streams: return
        p.setFont(self._fs)
        for ms in self._streams:
            for i,ch in enumerate(ms["chars"]):
                y=int(ms["y"])-i*ms["gap"]
                if y<0 or y>self.H: continue
                a=int(ms["alpha"]*max(0,1-i/len(ms["chars"]))*255)
                if a<3: continue
                p.setPen(QColor(0,190,255,a)); p.drawText(ms["x"],y,ch)

    def _draw_shocks(self, p: QPainter):
        p.setBrush(Qt.BrushStyle.NoBrush)
        for sw in self._shocks:
            a=int(sw["alpha"]*220); r=int(sw["r"])
            if a<4: continue
            p.setPen(QPen(QColor(0,220,255,a),2))
            p.drawEllipse(self._ocx-r,self._ocy-r,r*2,r*2)
            p.setPen(QPen(QColor(0,220,255,a//4),8))
            p.drawEllipse(self._ocx-r,self._ocy-r,r*2,r*2)

    def _draw_edge_flash(self, p: QPainter):
        a=int(self._edge_flash*255)
        if a<4: return
        c=QColor(0,220,255,a); t=3
        p.fillRect(0,0,self.W,t,c); p.fillRect(0,self.H-t,self.W,t,c)
        p.fillRect(0,0,t,self.H,c); p.fillRect(self.W-t,0,t,self.H,c)

    def _draw_scanline(self, p: QPainter):
        if self._scan_y<0: return
        y=int(self._scan_y)
        g=QLinearGradient(0,y-12,0,y+16)
        g.setColorAt(0,QColor(0,220,255,0)); g.setColorAt(0.45,QColor(0,220,255,55))
        g.setColorAt(0.5,QColor(0,220,255,115)); g.setColorAt(0.55,QColor(0,220,255,55))
        g.setColorAt(1,QColor(0,220,255,0))
        p.fillRect(0,y-12,self.W,28,g)

    def _draw_left_panel(self, p: QPainter, exp: float):
        lv=self._lp.value
        if lv<0.02: return
        pw,ph=244,190; x=self._lpx(); y=self.H//2-ph//2; a=int(lv*230)
        p.setBrush(QColor(0,14,32,int(lv*205))); p.setPen(QPen(QColor(0,170,255,a//2),1))
        p.drawRoundedRect(x,y,pw,ph,4,4)
        p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(QColor(0,200,255,a//3),2))
        p.drawRoundedRect(x-1,y-1,pw+2,ph+2,5,5)
        p.setFont(self._fh); p.setPen(QColor(0,215,255,a)); p.drawText(x+12,y+21,"SYSTEM")
        p.setPen(QPen(QColor(0,140,200,a//2),1)); p.drawLine(x+10,y+27,x+pw-10,y+27)
        bw=pw-70
        bars=[("CPU",self._cpu,42),("RAM",self._ram,67),("GPU",self._gpu,92),
              ("VRAM",(self._vu/max(1,self._vt))*100,117)]
        for label,val,dy in bars:
            bx=x+54; by=y+dy
            p.setFont(self._fs); p.setPen(QColor(100,175,215,a)); p.drawText(x+9,by+8,label)
            p.setBrush(QColor(0,25,55,int(lv*180))); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(bx,by,bw,8,2,2)
            fw=int(bw*min(val,100)/100)
            if fw>0:
                hot=val>80
                if hot: p.setBrush(QColor(255,55,55,int(lv*220)))
                else:
                    g=QLinearGradient(bx,0,bx+fw,0)
                    g.setColorAt(0,QColor(0,110,200,int(lv*180))); g.setColorAt(1,QColor(0,215,255,int(lv*220)))
                    p.setBrush(g)
                p.drawRoundedRect(bx,by,fw,8,2,2)
            p.setFont(self._fs); p.setPen(QColor(170,225,255,a))
            p.drawText(bx+bw+5,by+8,f"{val:.0f}%" if label!="VRAM" else f"{self._vu:.1f}G")
        p.setPen(Qt.PenStyle.NoPen)
        for bp in self._bparts:
            ba=int(bp["l"]*lv*200); c=bp["c"]
            p.setBrush(QColor(c[0],c[1],c[2],ba))
            p.drawEllipse(int(bp["x"]-1),int(bp["y"]-1),3,3)
        if self._resp_ms>0:
            p.setFont(self._fs); p.setPen(QColor(0,155,135,a//2))
            p.drawText(x+10,y+ph-10,f"last: {self._resp_ms}ms")

    def _draw_right_panel(self, p: QPainter, exp: float):
        rv=self._rp.value
        if rv<0.02: return
        pw,ph=244,228; x=self._rpx(); y=self.H//2-ph//2; a=int(rv*230)
        p.setBrush(QColor(0,14,32,int(rv*205))); p.setPen(QPen(QColor(0,170,255,a//2),1))
        p.drawRoundedRect(x,y,pw,ph,4,4)
        p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(QColor(0,200,255,a//3),2))
        p.drawRoundedRect(x-1,y-1,pw+2,ph+2,5,5)
        p.setFont(self._fh); p.setPen(QColor(0,215,255,a)); p.drawText(x+12,y+21,"ACTIVITY")
        p.setPen(QPen(QColor(0,140,200,a//2),1)); p.drawLine(x+10,y+27,x+pw-10,y+27)
        visible=[e for e in self._log if e.alpha>0.02][-9:]
        for i,e in enumerate(visible):
            ey=y+36+i*22
            if ey>y+ph-8: break
            ea=int(e.alpha*rv*a)
            col=CAT_COLORS.get(e.category,CAT_COLORS["default"])
            p.setBrush(QColor(col.red(),col.green(),col.blue(),ea)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(x+10,ey-6,5,5)
            text=e.text[:e.revealed]
            p.setFont(self._fs)
            p.setPen(QColor(min(255,col.red()//2+110),min(255,col.green()//2+110),min(255,col.blue()//2+110),ea))
            text=p.fontMetrics().elidedText(text,Qt.TextElideMode.ElideRight,pw-28)
            p.drawText(x+20,ey,text)

    def _draw_orb(self, p: QPainter, exp: float):
        ov=self._orb.value
        if ov<0.02: return
        cx,cy=self._ocx,self._ocy; r=int(100*ov); gl=int(self._glow*ov)
        for rm,ga in [(3.8,7),(2.6,14),(1.9,24),(1.4,38)]:
            gr=int(gl*rm); g=QRadialGradient(cx,cy,gr)
            g.setColorAt(0,QColor(0,170,255,int((ga+self._pulse*18)*ov))); g.setColorAt(1,QColor(0,0,0,0))
            p.setBrush(g); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(cx-gr,cy-gr,gr*2,gr*2)
        cg=QRadialGradient(cx-r//3,cy-r//3,r*1.6)
        br_=int(35+self._pulse*90)
        cg.setColorAt(0,QColor(25+br_//3,55+br_//2,75+br_,int(238*ov)))
        cg.setColorAt(0.5,QColor(5,14,28,int(228*ov))); cg.setColorAt(1,QColor(2,7,18,int(215*ov)))
        p.setBrush(cg); p.setPen(QPen(QColor(0,145,215,int(110*ov)),1))
        p.drawEllipse(cx-r,cy-r,r*2,r*2)
        p.setPen(QPen(QColor(0,200,255,int((55+self._pulse*75)*ov)),1))
        for crack in self._cracks:
            if not crack: continue
            path=QPainterPath(); path.moveTo(cx,cy)
            for nx,ny in crack: path.lineTo(cx+nx*r/75,cy+ny*r/75)
            p.drawPath(path)
        sg=QRadialGradient(cx-r//3,cy-r//2,r//2)
        sg.setColorAt(0,QColor(210,245,255,int(55*ov))); sg.setColorAt(1,QColor(0,0,0,0))
        p.setBrush(sg); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(cx-r,cy-r,r*2,r*2)
        ring_cfg=[(self._rang[0],0.28,118,2.0),(self._rang[1],0.52,128,1.5),(self._rang[2],0.18,138,1.0)]
        p.setBrush(Qt.BrushStyle.NoBrush)
        for angle,tilt,ring_r,lw in ring_cfg:
            rr=int(ring_r*ov); ry=max(2,int(rr*tilt))
            for gex,ga in [(5,12),(2,28),(0,75)]:
                p.save(); p.translate(cx,cy); p.rotate(angle)
                p.setPen(QPen(QColor(0,200,255,int(ga*ov)),lw+gex))
                p.drawEllipse(-rr,-ry,rr*2,ry*2); p.restore()
        for arc in self._arcs:
            a_=int(arc["life"]*190*ov); pts=arc["pts"]
            p.setPen(QPen(QColor(0,215,255,a_),1))
            for i in range(len(pts)-1):
                p1_,p2_=pts[i],pts[i+1]
                p.drawLine(int(p1_[0]),int(p1_[1]),int(p2_[0]),int(p2_[1]))
            p.setPen(QPen(QColor(210,245,255,int(arc["life"]*140*ov)),1))
            for i in range(0,len(pts)-1,2):
                p1_,p2_=pts[i],pts[i+1]
                p.drawLine(int(p1_[0]),int(p1_[1]),int(p2_[0]),int(p2_[1]))
        if self._pulse>0.08:
            ir=int(r*0.45*self._pulse); ig=QRadialGradient(cx,cy,ir*2)
            ig.setColorAt(0,QColor(160,240,255,int(195*self._pulse*ov))); ig.setColorAt(1,QColor(0,130,255,0))
            p.setBrush(ig); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(cx-ir*2,cy-ir*2,ir*4,ir*4)

    def _draw_waveform(self, p: QPainter, exp: float):
        if exp<0.08: return
        wy=self.H-52; wh=30; n=len(self._wave); a=int(exp*185); stp=self.W/n
        p.setPen(QPen(QColor(0,55,90,a//3),1)); p.drawLine(0,wy,self.W,wy)
        data=self._wave; maxv=max((abs(d) for d in data),default=0) or 1
        avg=sum(abs(d) for d in data)/n
        if avg<0.005:
            path=QPainterPath()
            for i in range(n):
                x=i*stp; y=wy+math.sin(self._t*2.5+i*0.25)*1.5+random.gauss(0,0.4)
                if i==0: path.moveTo(x,y)
                else:    path.lineTo(x,y)
            p.setPen(QPen(QColor(0,75,115,a//3),1)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawPath(path); return
        path=QPainterPath()
        for i in range(n):
            x=i*stp; y=wy-(data[i]/maxv)*wh
            if i==0: path.moveTo(x,y)
            else:    path.lineTo(x,y)
        wc=QColor(210,245,255,a) if avg>0.65 else (QColor(0,220,255,a) if avg>0.3 else QColor(0,110,195,a))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(wc.red(),wc.green(),wc.blue(),a//4),6)); p.drawPath(path)
        p.setPen(QPen(wc,1.5)); p.drawPath(path)

    def _draw_bottom(self, p: QPainter, exp: float):
        if exp<0.08: return
        bh=42; by=self.H-bh-56; a=int(exp*225)
        p.setBrush(QColor(0,9,22,int(exp*185))); p.setPen(QPen(QColor(0,145,195,a//2),1))
        p.drawRect(0,by,self.W,bh)
        g=QLinearGradient(0,by,self.W,by)
        g.setColorAt(0,QColor(0,0,0,0)); g.setColorAt(0.1,QColor(0,200,255,a//2))
        g.setColorAt(0.5,QColor(0,215,255,a)); g.setColorAt(0.9,QColor(0,200,255,a//2)); g.setColorAt(1,QColor(0,0,0,0))
        p.fillRect(0,by,self.W,1,g)
        p.setFont(self._fh)
        if self._a_active and self._agent:
            pulse=(math.sin(self._t*4)+1)/2
            p.setPen(QColor(0,215,255,int((0.5+pulse*0.5)*a))); p.drawText(18,by+27,f"[ {self._agent.upper()} ]")
        else:
            p.setPen(QColor(0,90,140,a//2)); p.drawText(18,by+27,"[ CIPHER ]")
        p.setFont(self._fs)
        p.setPen(QColor(55,115,155,a//2)); p.drawText(200,by+27,self._model)
        if self._resp_ms>0:
            p.setPen(QColor(0,175,145,a//2)); p.drawText(360,by+27,f"{self._resp_ms}ms")
        ut=int(time.monotonic()-self._start); h=ut//3600; m=(ut%3600)//60; s=ut%60
        p.setPen(QColor(55,115,155,a//2)); p.drawText(450,by+27,f"{h:02d}:{m:02d}:{s:02d}")
        bcount=20; bsp=4; bmaxh=26; total_w=bcount*(bsp+2); sx=self.W-total_w-18
        p.setPen(Qt.PenStyle.NoPen)
        for i,lv in enumerate(self._mic):
            bh_=max(2,int(lv*bmaxh)); bx=sx+i*(bsp+2); by_=by+(bh-bh_)//2
            p.setBrush(QColor(0,int(lv*255),255,int(a*0.72))); p.drawRect(bx,by_,2,bh_)

    def _draw_holo(self, p: QPainter):
        p.fillRect(0,0,self.W,self.H,QColor(0,215,255,12))
        for _ in range(random.randint(4,9)):
            y=random.randint(0,self.H); h=random.randint(2,18)
            p.fillRect(0,y,self.W,h,QColor(0,215,255,random.randint(18,45)))

    # ── public API ────────────────────────────────────────────────────────────
    def do_activate(self, text: str = ""):
        self._state="active"; self._edge_flash=1.0; self._scan_y=0.0
        self._shocks.append({"r":0.0,"alpha":1.0})
        self._lp.target=self._rp.target=self._orb.target=1.0
        if text: self._recv_log(text,"system")

    def do_idle(self):
        self._state="deactivating"; self._a_active=False; self._proc=False

    def do_log(self,msg:str,cat:str=""): self._log_sig.emit(msg,cat)
    def do_response(self,text:str): self._pulse=min(1.0,self._pulse+0.6)
    def do_agent(self,name:str,status:str): self._agent_sig.emit(name,status)
    def do_agent_idle(self): self._agent_sig.emit("","")
    def do_push_wave(self,data):
        self._wave_sig.emit(data)
        if data is not None:
            rms=math.sqrt(sum(d*d for d in data)/max(len(data),1))
            self._pulse=min(1.0,self._pulse+rms*3.0)
    def do_set_response_time(self,ms:int): self._resp_ms=ms
    def do_set_model(self,model:str): self._model=model


# ── Controller facade ─────────────────────────────────────────────────────────
class OverlayController:
    def __init__(self):
        self._w: Optional[CipherOverlay] = None

    def start(self, app: QApplication, sw: int, sh: int):
        self._w = CipherOverlay(sw, sh)
        self._w.show()

    def activate(self, text: str = ""):
        if self._w: self._w.do_activate(text)

    def idle(self):
        if self._w: self._w.do_idle()

    def log(self, message: str, category: str = ""):
        if self._w: self._w.do_log(message, category)

    def response(self, text: str):
        if self._w: self._w.do_response(text)

    def agent(self, name: str, status: str):
        if self._w: self._w.do_agent(name, status)

    def agent_idle(self):
        if self._w: self._w.do_agent_idle()

    def push_wave(self, data):
        if self._w: self._w.do_push_wave(data)

    def set_response_time(self, ms: int):
        if self._w: self._w.do_set_response_time(ms)

    def set_model(self, model: str):
        if self._w: self._w.do_set_model(model)

    def speaking(self): pass
    def done_speaking(self): pass


overlay = OverlayController()
