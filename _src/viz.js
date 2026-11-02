/* =========================================================================
   LIVE VISUALS
   -------------------------------------------------------------------------
   Each visual is registered by name in VIZ and mounted on any
   <canvas data-viz="name"> in the deck. It returns:

     { printAt: seconds,        the instant that represents it in a still
       reset(),                 called every time its slide is entered
       frame(t) }               called each animation frame; t in seconds

   Only the active slide's visuals run. Nothing here loads a library, an
   image or the network. Numbers drawn by a visual come from a file the
   build read, or the visual is a schematic and its slide's footer says so.

   Helpers below: mkRnd (seeded random, so the picture is identical on
   every load), gauss, smoothstep, rgba, ground, arrowHead, FONT.
   ========================================================================= */
const VIZ = {};
const REDUCE = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
/* ?t=<seconds> freezes every visual at a settled moment (stills, PDF, checks) */
const TOFF = parseFloat(new URLSearchParams(location.search).get('t') || '0') || 0;
/* Chrome prints transparent canvas pixels as white. While printing, a
   visual that relies on the slide showing through paints its own ground. */
let PRINTING = false;

function mkRnd(seed){
  return function(){ seed = (seed*1664525 + 1013904223) % 4294967296; return seed/4294967296; };
}
function gauss(rnd){ let u = 0, v = 0; while(!u) u = rnd(); while(!v) v = rnd();
  return Math.sqrt(-2*Math.log(u)) * Math.cos(2*Math.PI*v); }
const clamp01 = x => Math.max(0, Math.min(1, x));
const smoothstep = (a,b,x) => { const t = clamp01((x-a)/(b-a)); return t*t*(3-2*t); };
const rgba = (t,a) => 'rgba(' + t + ',' + clamp01(a).toFixed(3) + ')';

/* the theme's colours, read from the CSS tokens so a re-skin carries over */
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const hexToTriplet = h => { h = h.replace('#',''); if(h.length === 3) h = [...h].map(c => c+c).join('');
  return [0,2,4].map(i => parseInt(h.slice(i,i+2),16)).join(','); };
const C = {
  ground: css('--bg-dark')  || '#232E26',
  void:   '#0A0F0C',
  paper:  hexToTriplet(css('--ink-cream') || '#F0E8D2'),
  ink:    hexToTriplet(css('--ink-dark')  || '#1E2820'),
  accent: hexToTriplet(css('--accent')    || '#D4843E')
};
const FONT = {
  body:  s => s + 'px ' + (css('--f-body') || 'sans-serif'),
  bold:  s => '700 ' + s + 'px ' + (css('--f-display') || 'sans-serif'),
  mono:  s => s + 'px ' + (css('--f-mono') || 'monospace')
};

function ground(ctx, W, H, col){
  if(PRINTING){ ctx.fillStyle = col; ctx.fillRect(0,0,W,H); }
  else ctx.clearRect(0,0,W,H);
}
function arrowHead(ctx, x, y, ang, s){
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x - s*Math.cos(ang - .45), y - s*Math.sin(ang - .45));
  ctx.lineTo(x - s*Math.cos(ang + .45), y - s*Math.sin(ang + .45));
  ctx.closePath(); ctx.fill();
}

/* =========================================================================
   DRIFT — an ambient field for covers and closes. Points ride a slow,
   smooth flow made of three sine fields; they leave short trails.
   With data-opt='{"quiver":true}' a lattice of arrows sweeps in from the
   left at 1.6 s and shows the flow the points are riding.
   ========================================================================= */
VIZ['drift'] = function(cv){
  const W = cv.width, H = cv.height, ctx = cv.getContext('2d');
  const opt = JSON.parse(cv.dataset.opt || '{}');
  const rnd = mkRnd(20261102);
  const N = 600, P = new Float32Array(N*2);
  for(let i=0;i<N;i++){ P[i*2] = rnd(); P[i*2+1] = rnd(); }
  const flow = (x, y, t, out) => {
    const a = Math.sin(3.1*y + .21*t) + .5*Math.sin(5.3*x - .17*t);
    const b = Math.cos(2.7*x + .13*t) + .5*Math.cos(4.1*y + .19*t);
    out[0] = a*.0011 + .0004; out[1] = b*.0011;
  };
  const OUT = [0,0];
  const wipe = () => { ctx.fillStyle = C.void; ctx.fillRect(0,0,W,H); };
  wipe();
  return {
    printAt: 6,
    reset: wipe,
    frame(el){
      const t = REDUCE ? 6 : el;
      ctx.globalCompositeOperation = 'source-over';
      ctx.fillStyle = 'rgba(10,15,12,0.06)'; ctx.fillRect(0,0,W,H);
      ctx.globalCompositeOperation = 'lighter';
      for(let i=0;i<N;i++){
        let x = P[i*2], y = P[i*2+1];
        flow(x, y, t, OUT);
        const sp = Math.hypot(OUT[0], OUT[1]) / .0016;
        x += OUT[0]; y += OUT[1];
        if(x<0) x+=1; else if(x>1) x-=1;
        if(y<0) y+=1; else if(y>1) y-=1;
        P[i*2]=x; P[i*2+1]=y;
        ctx.fillStyle = rgba(C.paper, .16 + .30*sp);
        ctx.fillRect(x*W - 1.3, y*H - 1.3, 2.6, 2.6);
      }
      ctx.globalCompositeOperation = 'source-over';
      if(opt.quiver){
        const QX = 17, QY = 10, L = 46;
        ctx.lineWidth = 2.2;
        for(let qx=0; qx<QX; qx++){
          const nx = (qx+.5)/QX;
          const sweep = REDUCE ? 1 : clamp01((el - 1.6 - nx*.85)/.55);
          if(sweep <= 0) continue;
          for(let qy=0; qy<QY; qy++){
            const ny = (qy+.5)/QY;
            flow(nx, ny, t, OUT);
            const mag = Math.hypot(OUT[0], OUT[1]) / .0016;
            const ang = Math.atan2(OUT[1], OUT[0]);
            const a = sweep * (.30 + .45*clamp01(mag)) * .9;
            ctx.strokeStyle = ctx.fillStyle = rgba(C.paper, a);
            const x0 = nx*W - Math.cos(ang)*L*.5, y0 = ny*H - Math.sin(ang)*L*.5;
            const x1 = nx*W + Math.cos(ang)*L*.5, y1 = ny*H + Math.sin(ang)*L*.5;
            ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
            arrowHead(ctx, x1, y1, ang, 12);
          }
        }
      }
    }
  };
};

/* =========================================================================
   SCATTER-LABELS — a schematic. Points fly in and settle into three groups
   joined by a bridge; four readings then appear one at a time with leader
   lines. Draws no data: a slide that uses it says so in its footer.
   ========================================================================= */
VIZ['scatter-labels'] = function(cv){
  const W = cv.width, H = cv.height, ctx = cv.getContext('2d');
  const rnd = mkRnd(7);
  const pts = [];
  const blob = (cx, cy, sd, n) => { for(let i=0;i<n;i++) pts.push([cx + gauss(rnd)*sd, cy + gauss(rnd)*sd*1.15]); };
  blob(.20, .36, .055, 130);
  for(let i=0;i<95;i++){ const u = rnd(); pts.push([.27 + u*.26 + gauss(rnd)*.012, .45 + u*.24 + gauss(rnd)*.018]); }
  blob(.57, .74, .055, 130);
  blob(.86, .34, .05, 110);
  const P = pts.map(p => ({tx:p[0], ty:p[1], sx:rnd(), sy:rnd(), d:rnd()*.8, ph:rnd()*6.28}));
  const pick = P[12];
  const notes = [
    {at:2.2, text:['each point:', 'one measurement'],     col:C.accent, tx:.08, ty:.08, px:pick.tx, py:pick.ty},
    {at:3.8, text:['close together:', 'similar'],         col:C.paper,  tx:.04, ty:.80, px:.18,  py:.47},
    {at:5.4, text:['a bridge: one group', 'changing gradually'], col:C.paper, tx:.40, ty:.20, px:.40, py:.565},
    {at:7.0, text:['a gap: two groups', 'that never mix'], col:C.accent, tx:.70, ty:.80, px:.72,  py:.50}
  ];
  return {
    printAt: 9,
    frame(t){
      ground(ctx, W, H, C.ground);
      for(const p of P){
        const k = smoothstep(p.d, p.d + 1.2, t);
        const x = (p.sx + (p.tx - p.sx)*k + Math.sin(t*.8 + p.ph)*.0015) * W;
        const y = (p.sy + (p.ty - p.sy)*k + Math.cos(t*.7 + p.ph)*.0015) * H;
        ctx.fillStyle = rgba(C.paper, .30 + .55*k);
        ctx.beginPath(); ctx.arc(x, y, 5, 0, 6.283); ctx.fill();
      }
      for(const n of notes){
        const a = smoothstep(n.at, n.at + .6, t);
        if(a <= 0) continue;
        ctx.globalAlpha = a;
        ctx.fillStyle = rgba(n.col, 1); ctx.strokeStyle = rgba(n.col, 1); ctx.lineWidth = 3;
        ctx.font = FONT.body(30); ctx.textAlign = 'center';
        const tx = n.tx*W + 150, ty = n.ty*H;
        n.text.forEach((s, i) => ctx.fillText(s, tx, ty + i*38));
        const px = n.px*W, py = n.py*H;
        const sx = tx, sy = ty + (py > ty ? 60 : -40);
        const ex = sx + (px - sx)*a, ey = sy + (py - sy)*a;
        ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(ex, ey); ctx.stroke();
        if(a > .95) arrowHead(ctx, px, py, Math.atan2(py - sy, px - sx), 18);
        if(n === notes[0] && a > .95){ ctx.beginPath(); ctx.arc(px, py, 14, 0, 6.283); ctx.stroke(); }
        ctx.globalAlpha = 1;
      }
    }
  };
};
