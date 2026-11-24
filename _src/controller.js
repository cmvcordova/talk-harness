/* =========================================================================
   SLIDE CONTROLLER
   Fixed 1920x1080 stage scaled as one unit; keyboard, wheel and touch
   navigation; speaker notes; inline editing; and lifecycle management for
   the live figures so that only the visible slide is ever simulating.

   ?t=<seconds>  freeze every visual at that moment, no entrance motion
   ?check=1      measure every slide and log problems to the console
   #<n>          open on slide n
   ========================================================================= */
const DECK_ID = '__DECK_ID__';   /* filled by build.py from deck.toml's output */

class Deck {
  constructor(){
    this.slides  = [...document.querySelectorAll('.slide')];
    /* numbered slides carry their own "NN / NN" in the chrome band; the
       nav-bar counter would be a second number. It shows only on backup
       slides, which have no band. */
    const bx = this.slides.findIndex(s => s.hasAttribute('data-backup'));
    this.backupAt = bx === -1 ? this.slides.length : bx;
    this.stage   = document.getElementById('deckStage');
    this.index   = 0;
    this.figures = [];

    this.mountFigures();
    this.scaleStage();
    this.bindNav();
    this.buildChrome();
    this.show(0);

    /* one animation loop for the whole deck; parked figures cost nothing */
    const tick = ts => {
      for(const f of this.figures){
        if(!f.running) continue;
        if(f.t0 === null) f.t0 = ts;
        f.inst.frame((ts - f.t0)/1000 + TOFF);
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);

    /* printing captures every figure, not just the one that happens to be live */
    addEventListener('afterprint', () => { PRINTING = false; });
    addEventListener('beforeprint', () => {
      PRINTING = true;
      for(const f of this.figures){
        /* each figure names the instant that represents it in a still; the
           run-up matters too, since trails accumulate. */
        const at = f.inst.printAt || 4.2;
        f.inst.reset && f.inst.reset();
        for(let k = 90; k >= 0; k--) f.inst.frame(at - k * 0.016);
      }
    });
  }

  /* --- attach every <canvas data-viz> to its visual --- */
  mountFigures(){
    document.querySelectorAll('canvas[data-viz]').forEach(cv => {
      const make = VIZ[cv.dataset.viz];
      if(!make){ console.error('no visual named', cv.dataset.viz); return; }
      this.figures.push({ inst: make(cv), slide: cv.closest('.slide'), running:false, t0:null });
    });
  }

  scaleStage(){
    const fit = () => {
      const s = Math.min(innerWidth/1920, innerHeight/1080);
      this.stage.style.transform = `translate(${(innerWidth-1920*s)/2}px,${(innerHeight-1080*s)/2}px) scale(${s})`;
    };
    fit();
    addEventListener('resize', fit);
  }

  bindNav(){
    addEventListener('keydown', e => {
      if(document.body.classList.contains('editing') && e.target.isContentEditable) return;
      if(['ArrowRight','ArrowDown',' ','PageDown'].includes(e.key)){ e.preventDefault(); this.go(1); }
      if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key)){ e.preventDefault(); this.go(-1); }
      if(e.key === 'Home') this.show(0);
      if(e.key === 'End')  this.show(this.slides.length-1);
      if((e.key === 'f' || e.key === 'F') && !e.target.isContentEditable){
        document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
      }
    });
    let wheelLock = 0;
    addEventListener('wheel', e => {
      const now = Date.now();
      if(now - wheelLock < 700) return;
      if(Math.abs(e.deltaY) < 24) return;
      wheelLock = now;
      this.go(e.deltaY > 0 ? 1 : -1);
    }, {passive:true});
    let tx = 0, ty = 0;
    addEventListener('touchstart', e => { tx = e.touches[0].clientX; ty = e.touches[0].clientY; }, {passive:true});
    addEventListener('touchend', e => {
      const dx = e.changedTouches[0].clientX - tx, dy = e.changedTouches[0].clientY - ty;
      if(Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy)) this.go(dx < 0 ? 1 : -1);
    }, {passive:true});
  }

  /* nav dots + counter, kept outside the slide stage */
  buildChrome(){
    const bar = document.createElement('nav');
    bar.className = 'deck-controls';
    bar.innerHTML =
      '<button id="prev" aria-label="Previous slide">&larr;</button>' +
      '<span class="dots"></span>' +
      '<button id="next" aria-label="Next slide">&rarr;</button>' +
      '<span id="counter"></span>' +
      '<span style="opacity:.4">&middot;</span>' +
      '<button id="notesBtn" title="Speaker notes (N)">notes</button>';
    document.body.appendChild(bar);
    const dots = bar.querySelector('.dots');
    this.slides.forEach(() => dots.appendChild(Object.assign(document.createElement('i'), {className:'dot'})));
    bar.querySelector('#prev').onclick = () => this.go(-1);
    bar.querySelector('#next').onclick = () => this.go(1);
    this.dots = [...dots.children];
    this.counter = bar.querySelector('#counter');

    /* the speaker-notes panel: presenter-side only */
    this.notes = document.createElement('div');
    this.notes.id = 'notesPanel';
    document.body.appendChild(this.notes);
    bar.querySelector('#notesBtn').onclick = () => this.toggleNotes();
    addEventListener('keydown', e => {
      if((e.key === 'n' || e.key === 'N') && !e.target.isContentEditable) this.toggleNotes();
    });
  }

  go(d){ this.show(this.index + d); }

  toggleNotes(){
    this.notes.classList.toggle('on');
    this.paintNotes();
  }
  paintNotes(){
    if(!this.notes || !this.notes.classList.contains('on')) return;
    const n = this.slides[this.index].dataset.notes;
    this.notes.textContent = n || 'No notes for this slide.';
  }

  show(i){
    this.index = Math.max(0, Math.min(i, this.slides.length - 1));
    this.slides.forEach((s, n) => {
      const on = n === this.index;
      s.classList.toggle('active', on);
      s.classList.toggle('visible', on);
    });
    /* start the figures on this slide, park every other one */
    for(const f of this.figures){
      const on = f.slide === this.slides[this.index];
      if(on && !f.running){ f.running = true; f.t0 = null; f.inst.reset && f.inst.reset(); }
      else if(!on) f.running = false;
    }
    if(this.dots) this.dots.forEach((d, n) => d.classList.toggle('on', n === this.index));
    if(this.counter) this.counter.textContent = this.index >= this.backupAt
      ? String(this.index+1).padStart(2,'0') + ' / ' + String(this.slides.length).padStart(2,'0')
      : '';
    this.paintNotes();
    location.hash = '#' + (this.index + 1);
  }

  /* =======================================================================
     CHECK MODE — ?check=1
     Scale the stage to 1, show every slide in turn, and report anything
     that leaves the 1920x1080 canvas, any text box that clips its own
     content, and any image that did not load. One console line per
     problem, so headless Chrome can collect them (tools/deck.py check).
     Elements marked data-offstage are skipped: they are meant to be outside.
     ======================================================================= */
  check(){
    this.stage.style.transform = 'none';
    let problems = 0;
    const tag = el => {
      const id = el.id ? '#' + el.id : '';
      const cls = el.classList.length ? '.' + [...el.classList].slice(0,2).join('.') : '';
      return '<' + el.tagName.toLowerCase() + id + cls + '>';
    };
    this.slides.forEach((s, n) => {
      this.show(n);
      const nn = String(n+1).padStart(2,'0');
      const sr = this.stage.getBoundingClientRect();
      for(const el of s.querySelectorAll('*')){
        if(el.closest('[data-offstage]')) continue;
        const r = el.getBoundingClientRect();
        if(r.width === 0 && r.height === 0) continue;
        const L = Math.round(r.left - sr.left), T = Math.round(r.top - sr.top);
        const R = Math.round(r.right - sr.left), B = Math.round(r.bottom - sr.top);
        if(L < -1 || T < -1 || R > 1921 || B > 1081){
          problems++; console.log(`CHECK slide ${nn}: overflow ${tag(el)} left=${L} top=${T} right=${R} bottom=${B}`);
        }
        const ov = getComputedStyle(el).overflow;
        if(ov !== 'visible' && el.scrollHeight > el.clientHeight + 2 && el.clientHeight > 0 && !el.classList.contains('slide')){
          problems++; console.log(`CHECK slide ${nn}: clipped text ${tag(el)} scrollHeight=${el.scrollHeight} clientHeight=${el.clientHeight}`);
        }
        if(el.tagName === 'IMG' && el.complete && el.naturalWidth === 0){
          problems++; console.log(`CHECK slide ${nn}: broken image ${el.getAttribute('src')}`);
        }
      }
    });
    /* ?lint=<px>: the two evidence rules that depend on wrapping (tools/lint.py has the rest).
       A headline over two lines, and running text under the minimum size. Backup slides,
       slides with data-lint="off", and the bands, labels and figures are left out. */
    const minPx = parseFloat(PARAMS.get('lint'));
    if(minPx){
      const quiet = '.chrome,.footband,.label,.kicker,.status,.credit,.wordmark,.lockup,.cite,.caption,.src,.ph,figure,table,svg,canvas,[data-nolint]';
      this.slides.forEach((s, n) => {
        const skip = (s.dataset.lint || '').split(/\s+/);
        if(s.hasAttribute('data-backup') || skip.includes('off')) return;
        this.show(n);
        const nn = String(n+1).padStart(2,'0');
        const head = s.querySelector('.chrome') && s.querySelector('.claim, h2, h1');
        if(head && !skip.includes('headline-lines')){
          const lines = Math.round(head.getBoundingClientRect().height / parseFloat(getComputedStyle(head).lineHeight));
          if(lines > 2) console.log(`LINT slide ${nn}: headline-lines: the headline takes ${lines} lines (limit 2)`);
        }
        if(skip.includes('small-text')) return;
        const seen = new Set();
        const walk = document.createTreeWalker(s, NodeFilter.SHOW_TEXT);
        for(let t = walk.nextNode(); t; t = walk.nextNode()){
          /* an inline span of code inside a sentence is read at the sentence's size */
          const el = t.parentElement.closest('p,li,h3,dd,dt,blockquote') || t.parentElement;
          if(!t.textContent.trim() || t.parentElement.closest(quiet)) continue;
          const px = parseFloat(getComputedStyle(el).fontSize);
          if(px < minPx && !seen.has(px)){
            seen.add(px);
            console.log(`LINT slide ${nn}: small-text: running text at ${px}px (minimum ${minPx}): ${t.textContent.trim().slice(0, 40).replace(/"/g, "'")}`);
          }
        }
      });
    }
    console.log(`CHECK done: ${this.slides.length} slides, ${problems} problems`);
    this.show(0);
    return problems;
  }
}

/* =========================================================================
   INLINE EDITING
   Hover the top-left corner or press E. Click any text to edit; Ctrl+S saves
   a copy of the edited deck. Edits persist in localStorage and come back
   with ?restore in the URL.
   ========================================================================= */
class Editor {
  constructor(deck){
    this.deck = deck; this.isActive = false;
    const zone = document.createElement('div'); zone.className = 'edit-hotzone';
    const btn  = document.createElement('button');
    btn.className = 'edit-toggle'; btn.id = 'editToggle';
    btn.title = 'Edit mode (E)'; btn.textContent = 'Edit';
    document.body.append(zone, btn);
    this.btn = btn;

    let hide = null;
    const show = () => { clearTimeout(hide); btn.classList.add('show'); };
    const later = () => { hide = setTimeout(() => { if(!this.isActive) btn.classList.remove('show'); }, 400); };
    zone.addEventListener('mouseenter', show);
    zone.addEventListener('mouseleave', later);
    btn.addEventListener('mouseenter', show);
    btn.addEventListener('mouseleave', later);
    zone.addEventListener('click', () => this.toggle());
    btn.addEventListener('click', () => this.toggle());

    addEventListener('keydown', e => {
      if((e.key === 'e' || e.key === 'E') && !e.target.isContentEditable) this.toggle();
      if((e.metaKey || e.ctrlKey) && e.key === 's'){ e.preventDefault(); this.save(); }
    });
    this.restore();
  }
  targets(){
    return document.querySelectorAll('.slide h1,.slide h2,.slide h3,.slide p,.slide li,.slide td,.slide .kicker,.slide .label,.slide .display');
  }
  toggle(){
    this.isActive = !this.isActive;
    document.body.classList.toggle('editing', this.isActive);
    this.btn.classList.toggle('active', this.isActive);
    this.btn.classList.toggle('show', this.isActive);
    this.targets().forEach(el => {
      el.contentEditable = this.isActive;
      if(this.isActive) el.addEventListener('blur', this.persist, {once:true});
    });
  }
  persist = () => {
    try{ localStorage.setItem(DECK_ID + '-deck', document.querySelector('.deck-stage').innerHTML); }catch(e){}
  }
  restore(){
    try{
      const saved = localStorage.getItem(DECK_ID + '-deck');
      if(saved && new URLSearchParams(location.search).has('restore'))
        document.querySelector('.deck-stage').innerHTML = saved;
    }catch(e){}
  }
  save(){
    this.persist();
    const blob = new Blob(['<!DOCTYPE html>\n' + document.documentElement.outerHTML], {type:'text/html'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = DECK_ID + '-edited.html';
    a.click();
  }
}

/* --- boot --- */
/* read the deep link BEFORE constructing the deck: show() rewrites the hash */
const START = parseInt((location.hash || '').slice(1), 10);
const PARAMS = new URLSearchParams(location.search);
if(TOFF || PARAMS.has('check')) document.body.classList.add('settled');
const deck = new Deck();
new Editor(deck);
if(START >= 1) deck.show(START - 1);
if(PARAMS.has('check')){
  /* fonts change line breaks, so measure after they have arrived */
  (document.fonts ? document.fonts.ready : Promise.resolve()).then(() => setTimeout(() => deck.check(), 300));
}
