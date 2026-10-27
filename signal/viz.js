/* =====================================================================
   VIZ — Visualisations interactives (canvas pur, sans dépendance)
   Un widget par concept clé, monté dans chaque chapitre.
   ===================================================================== */
(function(){
  const cssVar = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const REDUCE = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let ACTIVE = [];

  /* ---------- utilitaires d'échelle ---------- */
  function ticks(min,max){
    const span=max-min; if(span<=0) return [min];
    let step=Math.pow(10,Math.floor(Math.log10(span/5)));
    const err=span/5/step;
    if(err>5)step*=5; else if(err>2)step*=2;
    const out=[];
    for(let t=Math.ceil(min/step)*step; t<=max+1e-9; t+=step) out.push(+t.toFixed(6));
    return out;
  }
  const fmt = v => Math.abs(v)<1e-9 ? '0'
    : (Math.abs(v)>=1000||Math.abs(v)<0.01) ? v.toExponential(0)
    : (+v.toFixed(2)).toString();

  /* ---------- traceur ---------- */
  function makePlot(canvas){
    const ctx=canvas.getContext('2d');
    let W=300,H=200,dpr=1, xmin=-1,xmax=1,ymin=-1,ymax=1;
    const PAD={l:38,r:14,t:14,b:26};
    function resize(){
      dpr=window.devicePixelRatio||1;
      const r=canvas.getBoundingClientRect();
      W=Math.max(20,r.width); H=Math.max(20,r.height);
      canvas.width=Math.round(W*dpr); canvas.height=Math.round(H*dpr);
      ctx.setTransform(dpr,0,0,dpr,0,0);
    }
    const X=x=>PAD.l+(x-xmin)/(xmax-xmin)*(W-PAD.l-PAD.r);
    const Y=y=>H-PAD.b-(y-ymin)/(ymax-ymin)*(H-PAD.t-PAD.b);
    function begin(o){
      o=o||{};
      xmin=o.xmin??-1; xmax=o.xmax??1; ymin=o.ymin??-1; ymax=o.ymax??1;
      resize(); ctx.clearRect(0,0,W,H);
      const line=cssVar('--line'), soft=cssVar('--ink-dim'), ink=cssVar('--ink-soft');
      ctx.font='10px ui-monospace,monospace';
      ctx.strokeStyle=line; ctx.lineWidth=1; ctx.globalAlpha=.55;
      const xs=ticks(xmin,xmax), ys=ticks(ymin,ymax);
      xs.forEach(t=>{ctx.beginPath();ctx.moveTo(X(t),PAD.t);ctx.lineTo(X(t),H-PAD.b);ctx.stroke();});
      ys.forEach(t=>{ctx.beginPath();ctx.moveTo(PAD.l,Y(t));ctx.lineTo(W-PAD.r,Y(t));ctx.stroke();});
      ctx.globalAlpha=1; ctx.strokeStyle=soft; ctx.lineWidth=1.4;
      if(ymin<0&&ymax>0){ctx.beginPath();ctx.moveTo(PAD.l,Y(0));ctx.lineTo(W-PAD.r,Y(0));ctx.stroke();}
      if(xmin<0&&xmax>0){ctx.beginPath();ctx.moveTo(X(0),PAD.t);ctx.lineTo(X(0),H-PAD.b);ctx.stroke();}
      ctx.fillStyle=soft; ctx.textAlign='center'; ctx.textBaseline='top';
      xs.forEach(t=>{ if(Math.abs(t)>1e-9) ctx.fillText(fmt(t),X(t),H-PAD.b+4);});
      ctx.textAlign='right'; ctx.textBaseline='middle';
      ys.forEach(t=>{ if(Math.abs(t)>1e-9) ctx.fillText(fmt(t),PAD.l-5,Y(t));});
      if(o.xlabel){ctx.fillStyle=ink;ctx.textAlign='right';ctx.textBaseline='bottom';ctx.fillText(o.xlabel,W-PAD.r,H-PAD.b-3);}
      if(o.ylabel){ctx.fillStyle=ink;ctx.textAlign='left';ctx.textBaseline='top';ctx.fillText(o.ylabel,PAD.l+3,Math.max(2,PAD.t-2));}
    }
    function fn(f,{color,width=2,dash=null}={}){
      ctx.save();ctx.strokeStyle=color;ctx.lineWidth=width;if(dash)ctx.setLineDash(dash);
      ctx.beginPath();let started=false;const N=Math.max(2,Math.round(W));
      for(let i=0;i<=N;i++){const x=xmin+(xmax-xmin)*i/N;let y=f(x);
        if(!isFinite(y)){started=false;continue;}
        y=Math.max(ymin-2,Math.min(ymax+2,y));
        const px=X(x),py=Y(y);
        if(!started){ctx.moveTo(px,py);started=true;}else ctx.lineTo(px,py);}
      ctx.stroke();ctx.restore();
    }
    function fill(f,{color}={}){
      ctx.save();ctx.fillStyle=color;ctx.globalAlpha=.22;ctx.beginPath();
      const N=Math.max(2,Math.round(W));let started=false;const y0=Y(Math.max(ymin,Math.min(ymax,0)));
      for(let i=0;i<=N;i++){const x=xmin+(xmax-xmin)*i/N;let y=f(x);if(!isFinite(y))y=0;
        y=Math.max(ymin,Math.min(ymax,y));const px=X(x),py=Y(y);
        if(!started){ctx.moveTo(px,y0);ctx.lineTo(px,py);started=true;}else ctx.lineTo(px,py);}
      ctx.lineTo(X(xmax),y0);ctx.closePath();ctx.fill();ctx.globalAlpha=1;ctx.restore();
    }
    function stems(pts,{color,dot=true}={}){
      ctx.save();ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=2;
      pts.forEach(p=>{ctx.beginPath();ctx.moveTo(X(p.x),Y(0));ctx.lineTo(X(p.x),Y(p.y));ctx.stroke();
        if(dot){ctx.beginPath();ctx.arc(X(p.x),Y(p.y),3,0,7);ctx.fill();}});
      ctx.restore();
    }
    function arrow(x,y,{color}={}){
      ctx.save();ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=2.4;
      ctx.beginPath();ctx.moveTo(X(x),Y(0));ctx.lineTo(X(x),Y(y));ctx.stroke();
      const a=6,s=Math.sign(y)||1;
      ctx.beginPath();ctx.moveTo(X(x),Y(y));ctx.lineTo(X(x)-a,Y(y)+s*a*1.4);ctx.lineTo(X(x)+a,Y(y)+s*a*1.4);ctx.closePath();ctx.fill();
      ctx.restore();
    }
    function dot(x,y,{color,r=4}={}){ctx.save();ctx.fillStyle=color;ctx.beginPath();ctx.arc(X(x),Y(y),r,0,7);ctx.fill();ctx.restore();}
    function vline(x,{color,dash=[4,4],width=1.3}={}){ctx.save();ctx.strokeStyle=color;ctx.lineWidth=width;if(dash)ctx.setLineDash(dash);ctx.beginPath();ctx.moveTo(X(x),PAD.t);ctx.lineTo(X(x),H-PAD.b);ctx.stroke();ctx.restore();}
    function hline(y,{color,dash=[4,4]}={}){ctx.save();ctx.strokeStyle=color;ctx.lineWidth=1.3;if(dash)ctx.setLineDash(dash);ctx.beginPath();ctx.moveTo(PAD.l,Y(y));ctx.lineTo(W-PAD.r,Y(y));ctx.stroke();ctx.restore();}
    function bars(arr,{color}={}){
      ctx.save();ctx.fillStyle=color;
      const bw=Math.max(3,(W-PAD.l-PAD.r)/(arr.length*2.2));
      arr.forEach(p=>{const px=X(p.x);ctx.fillRect(px-bw/2,Y(p.y),bw,Y(0)-Y(p.y));});ctx.restore();
    }
    function label(x,y,text,{color,align='left',base='middle',font='10px ui-monospace,monospace'}={}){
      ctx.save();ctx.fillStyle=color;ctx.textAlign=align;ctx.textBaseline=base;ctx.font=font;ctx.fillText(text,X(x),Y(y));ctx.restore();}
    return {begin,fn,fill,stems,arrow,dot,vline,hline,bars,label};
  }

  /* ---------- helpers UI ---------- */
  const C = { phos:()=>cssVar('--phos'), amber:()=>cssVar('--amber'), cyan:()=>cssVar('--cyan'),
              danger:()=>cssVar('--danger'), soft:()=>cssVar('--ink-soft'), ink:()=>cssVar('--ink'), dim:()=>cssVar('--ink-dim') };
  function slider(label,id,min,max,step,val){
    return `<label class="viz-ctrl">${label}: <span class="vval" id="${id}-v"></span>
      <input type="range" id="${id}" min="${min}" max="${max}" step="${step}" value="${val}"></label>`;
  }
  function legend(items){
    return `<div class="viz-legend">${items.map(i=>`<span class="lg"><span class="sw" style="background:${i.c}"></span>${i.t}</span>`).join('')}</div>`;
  }
  function register(redraw,stop){ ACTIVE.push({redraw,stop:stop||null}); redraw(); }

  /* =====================================================================
     CH1 — Signaux singuliers
     ===================================================================== */
  function buildSingular(el){
    el.innerHTML = `
      <div class="viz-seg" id="sg-type">
        <button data-t="delta" class="active">δ(t−a)</button>
        <button data-t="heav">h(t−a)</button>
        <button data-t="porte">Π_τ(t)</button>
        <button data-t="peigne">Ш(t)</button>
        <button data-t="exp">h(t)·e^(−t/τ)</button>
      </div>
      <canvas class="viz-canvas" id="sg-c"></canvas>
      <div class="viz-row">
        ${slider('Décalage a','sg-a',-2,2,0.1,1)}
        ${slider('Largeur τ','sg-w',0.4,3,0.1,1.5)}
      </div>
      <div class="viz-readout" id="sg-r"></div>`;
    const cv=el.querySelector('#sg-c'), plot=makePlot(cv);
    let type='delta';
    const aWrap=el.querySelector('#sg-a').closest('.viz-ctrl');
    const wWrap=el.querySelector('#sg-w').closest('.viz-ctrl');
    function redraw(){
      const a=+el.querySelector('#sg-a').value, w=+el.querySelector('#sg-w').value;
      el.querySelector('#sg-a-v').textContent=a.toFixed(1);
      el.querySelector('#sg-w-v').textContent=w.toFixed(1);
      aWrap.style.display=(type==='delta'||type==='heav')?'flex':'none';
      wWrap.style.display=(type==='porte'||type==='exp')?'flex':'none';
      plot.begin({xmin:-3,xmax:3,ymin:-0.3,ymax:1.4,xlabel:'t'});
      const g=C.phos();
      let txt='';
      if(type==='delta'){ plot.arrow(a,1,{color:g}); plot.label(a,1.18,'(aire 1)',{color:C.soft(),align:'center'}); txt=`<b>δ(t−a)</b> : impulsion d'aire 1 en t=${a.toFixed(1)}. Sous intégrale : ∫φ(t)δ(t−a)dt = φ(a).`; }
      else if(type==='heav'){ plot.fn(t=> t>=a?1:0,{color:g,width:2.4}); plot.dot(a,1,{color:g}); txt=`<b>h(t−a)</b> : échelon, passe de 0 à 1 en t=${a.toFixed(1)}. C'est la primitive du Dirac.`; }
      else if(type==='porte'){ plot.fill(t=>(Math.abs(t)<=w/2)?1:0,{color:g}); plot.fn(t=>(Math.abs(t)<=w/2)?1:0,{color:g,width:2.4}); plot.vline(-w/2,{color:C.soft()});plot.vline(w/2,{color:C.soft()}); txt=`<b>Π_τ(t)</b> : porte de largeur τ=${w.toFixed(1)}, centrée en 0, sur [−τ/2, +τ/2]. Énergie = τ.`; }
      else if(type==='peigne'){ const pts=[];for(let k=-3;k<=3;k++)pts.push({x:k,y:1}); pts.forEach(p=>plot.arrow(p.x,1,{color:g})); txt=`<b>Ш(t)</b> : peigne de Dirac = impulsions régulières (échantillonnage / périodicité).`; }
      else { const tau=w; plot.fill(t=> t>=0?Math.exp(-t/tau):0,{color:g}); plot.fn(t=> t>=0?Math.exp(-t/tau):0,{color:g,width:2.4}); plot.dot(tau,Math.exp(-1),{color:C.amber()}); plot.label(tau,Math.exp(-1)+0.12,'37% à t=τ',{color:C.amber(),align:'center'}); txt=`<b>h(t)·e^(−t/τ)</b> : exponentielle causale (τ=${tau.toFixed(1)}). Vaut 37% en t=τ. Énergie = A²τ/2.`; }
      el.querySelector('#sg-r').innerHTML=txt;
    }
    el.querySelectorAll('#sg-type button').forEach(b=>b.onclick=()=>{
      el.querySelectorAll('#sg-type button').forEach(x=>x.classList.remove('active'));
      b.classList.add('active'); type=b.dataset.t; redraw();
    });
    el.querySelector('#sg-a').oninput=redraw;
    el.querySelector('#sg-w').oninput=redraw;
    register(redraw);
  }

  /* =====================================================================
     CH2 — Reconstruction série de Fourier + spectre
     ===================================================================== */
  function buildFourier(el){
    el.innerHTML=`
      <div class="viz-seg" id="fo-type">
        <button data-t="square" class="active">Signal carré</button>
        <button data-t="saw">Dent de scie</button>
      </div>
      <canvas class="viz-canvas" id="fo-c"></canvas>
      ${legend([{c:'var(--ink-dim)',t:'signal cible'},{c:'var(--phos)',t:'somme partielle φ_N'}])}
      <canvas class="viz-canvas" id="fo-s" style="height:130px;margin-top:12px"></canvas>
      <div class="viz-row">
        ${slider('Nombre d\'harmoniques N','fo-n',1,20,1,3)}
        <button class="viz-btn" id="fo-play">▶ Animer</button>
      </div>
      <div class="viz-readout" id="fo-r"></div>`;
    const plot=makePlot(el.querySelector('#fo-c')), spec=makePlot(el.querySelector('#fo-s'));
    let type='square', playing=false, raf=null;
    const frac = t => t-Math.floor(t); // 0..1
    function target(t){ const u=frac(t); return type==='square' ? (u<0.5?1:0) : u; }
    function partial(t,N){
      if(type==='square'){ let s=0.5,c=0; for(let n=1;c<N;n+=2){s+=(2/Math.PI)*Math.sin(2*Math.PI*n*t)/n;c++;} return s; }
      let s=0.5; for(let k=1;k<=N;k++) s-=(1/Math.PI)*Math.sin(2*Math.PI*k*t)/k; return s;
    }
    function coeffs(N){
      const a=[];
      if(type==='square'){ let c=0; for(let n=1;c<N;n+=2){a.push({k:n,amp:2/(Math.PI*n)});c++;} }
      else for(let k=1;k<=N;k++) a.push({k,amp:1/(Math.PI*k)});
      return a;
    }
    function redraw(){
      const N=+el.querySelector('#fo-n').value;
      el.querySelector('#fo-n-v').textContent=N;
      plot.begin({xmin:-1,xmax:1,ymin:-0.35,ymax:1.35,xlabel:'t (périodes)'});
      plot.fn(t=>target(t),{color:C.dim(),width:1.6,dash:[5,4]});
      plot.fn(t=>partial(t,N),{color:C.phos(),width:2.4});
      // spectre
      const cf=coeffs(type==='square'?Math.max(N,1):N);
      const maxK = type==='square' ? (2*N) : N+0.5;
      const maxA = cf.length?cf[0].amp*1.15:1;
      spec.begin({xmin:0,xmax:maxK+1,ymin:0,ymax:maxA,xlabel:'harmonique k',ylabel:'|amplitude|'});
      spec.bars(cf.map(c=>({x:c.k,y:c.amp})),{color:C.cyan()});
      const real = type==='square'
        ? `Carré : seules les harmoniques <b>impaires</b> (1,3,5…), amplitude en 1/k. Aux sauts, on voit les oscillations de <b>Gibbs</b>.`
        : `Dent de scie (signal impair) : <b>uniquement des sinus</b>, amplitude en 1/k.`;
      el.querySelector('#fo-r').innerHTML = `${N} harmonique${N>1?'s':''} retenue${N>1?'s':''}. ${real}`;
    }
    el.querySelectorAll('#fo-type button').forEach(b=>b.onclick=()=>{
      el.querySelectorAll('#fo-type button').forEach(x=>x.classList.remove('active'));
      b.classList.add('active'); type=b.dataset.t; redraw();
    });
    el.querySelector('#fo-n').oninput=redraw;
    const playBtn=el.querySelector('#fo-play');
    let dir=1;
    function step(){ if(!playing)return; const s=el.querySelector('#fo-n'); let v=+s.value+dir;
      if(v>=+s.max){v=+s.max;dir=-1;} if(v<=+s.min){v=+s.min;dir=1;} s.value=v; redraw(); raf=requestAnimationFrame(()=>setTimeout(step,260)); }
    playBtn.onclick=()=>{ playing=!playing; playBtn.classList.toggle('active',playing); playBtn.textContent=playing?'⏸ Pause':'▶ Animer'; if(playing)step(); };
    register(redraw, ()=>{playing=false; if(raf)cancelAnimationFrame(raf);});
  }

  /* =====================================================================
     CH3 — Convolution « retourner-glisser »
     ===================================================================== */
  function buildConv(el){
    el.innerHTML=`
      <canvas class="viz-canvas" id="cv-top"></canvas>
      ${legend([{c:'var(--cyan)',t:'x(τ) = Π fixe'},{c:'var(--amber)',t:'y(t−τ) retournée & glissée'},{c:'var(--phos)',t:'recouvrement'}])}
      <canvas class="viz-canvas" id="cv-bot" style="height:180px;margin-top:12px"></canvas>
      ${legend([{c:'var(--phos)',t:'z(t) = (x∗y)(t)'}])}
      <div class="viz-row">
        ${slider('Décalage t','cv-t',-2,3,0.05,-2)}
        <button class="viz-btn" id="cv-play">▶ Balayer</button>
      </div>
      <div class="viz-readout" id="cv-r"></div>`;
    const top=makePlot(el.querySelector('#cv-top')), bot=makePlot(el.querySelector('#cv-bot'));
    const xbox=u=>(Math.abs(u)<=1)?1:0;            // largeur 2
    const ybox=(u,t)=>(Math.abs(u-t)<=0.5)?1:0;    // largeur 1, centrée en t
    const z=t=>{ const lo=Math.max(-1,t-0.5), hi=Math.min(1,t+0.5); return Math.max(0,hi-lo); };
    let playing=false, raf=null;
    function redraw(){
      const t=+el.querySelector('#cv-t').value;
      el.querySelector('#cv-t-v').textContent=t.toFixed(2);
      top.begin({xmin:-2.5,xmax:3.5,ymin:-0.2,ymax:1.4,xlabel:'τ'});
      top.fill(u=>(xbox(u)&&ybox(u,t))?1:0,{color:C.phos()});
      top.fn(u=>xbox(u),{color:C.cyan(),width:2.2});
      top.fn(u=>ybox(u,t),{color:C.amber(),width:2.2});
      bot.begin({xmin:-2.5,xmax:3.5,ymin:-0.1,ymax:1.25,xlabel:'t',ylabel:'z(t)'});
      bot.fn(tt=> tt<=t? z(tt):NaN,{color:C.phos(),width:2.6});
      bot.fn(tt=> z(tt),{color:C.dim(),width:1.2,dash:[4,4]});
      bot.dot(t,z(t),{color:C.phos(),r:5});
      el.querySelector('#cv-r').innerHTML=`t = ${t.toFixed(2)} → z(t) = aire de recouvrement = <b>${z(t).toFixed(2)}</b>. Deux portes (largeurs 2 et 1) ⇒ le résultat est un <b>trapèze</b> de largeur 3.`;
    }
    el.querySelector('#cv-t').oninput=redraw;
    const playBtn=el.querySelector('#cv-play');
    function step(){ if(!playing)return; const s=el.querySelector('#cv-t'); let v=+s.value+0.04;
      if(v>+s.max)v=+s.min; s.value=v; redraw(); raf=requestAnimationFrame(step); }
    playBtn.onclick=()=>{ playing=!playing; playBtn.classList.toggle('active',playing); playBtn.textContent=playing?'⏸ Pause':'▶ Balayer'; if(playing)step(); };
    register(redraw, ()=>{playing=false; if(raf)cancelAnimationFrame(raf);});
  }

  /* =====================================================================
     CH4 — Échantillonnage & repliement (Shannon)
     ===================================================================== */
  function buildSampling(el){
    el.innerHTML=`
      <canvas class="viz-canvas" id="sp-c" style="height:260px"></canvas>
      ${legend([{c:'var(--cyan)',t:'signal x(t)=sin(2πf₀t)'},{c:'var(--phos)',t:'échantillons'},{c:'var(--danger)',t:'sinusoïde repliée perçue'}])}
      <div class="viz-row">
        ${slider('Fréquence f₀','sp-f0',0.5,12,0.5,3)}
        ${slider('Échantillonnage F_E','sp-fs',3,24,1,16)}
      </div>
      <div class="viz-readout" id="sp-r"></div>`;
    const plot=makePlot(el.querySelector('#sp-c'));
    function redraw(){
      const f0=+el.querySelector('#sp-f0').value, fs=+el.querySelector('#sp-fs').value;
      el.querySelector('#sp-f0-v').textContent=f0.toFixed(1)+' Hz';
      el.querySelector('#sp-fs-v').textContent=fs+' Hz';
      const fa = f0 - fs*Math.round(f0/fs);   // fréquence repliée signée (passe par les échantillons)
      const aliasing = f0 > fs/2 + 1e-9;
      plot.begin({xmin:0,xmax:1,ymin:-1.25,ymax:1.25,xlabel:'t (s)'});
      plot.fn(t=>Math.sin(2*Math.PI*f0*t),{color:C.cyan(),width:1.6});
      if(aliasing) plot.fn(t=>Math.sin(2*Math.PI*fa*t),{color:C.danger(),width:2.4,dash:[6,4]});
      const pts=[]; for(let n=0;n/fs<=1+1e-9;n++) pts.push({x:n/fs,y:Math.sin(2*Math.PI*f0*n/fs)});
      plot.stems(pts,{color:C.phos()});
      const r=el.querySelector('#sp-r');
      r.className='viz-readout'+(aliasing?' warn-on':'');
      r.innerHTML = aliasing
        ? `⚠ <b>Repliement !</b> f₀=${f0.toFixed(1)} Hz > F_E/2=${(fs/2).toFixed(1)} Hz. Le signal est perçu comme une sinusoïde de <b>${Math.abs(fa).toFixed(1)} Hz</b> (= |f₀ − F_E·round(f₀/F_E)|). La condition de Shannon F_E/2 > f₀ n'est pas respectée.`
        : `✓ Échantillonnage correct : F_E/2 = ${(fs/2).toFixed(1)} Hz > f₀ = ${f0.toFixed(1)} Hz. Les échantillons décrivent fidèlement le signal (Shannon respecté).`;
    }
    el.querySelector('#sp-f0').oninput=redraw;
    el.querySelector('#sp-fs').oninput=redraw;
    register(redraw);
  }

  /* CH4 — Dualité porte ↔ sinc */
  function buildPorteSinc(el){
    el.innerHTML=`
      <div class="viz-twin">
        <div><canvas class="viz-canvas" id="ps-t" style="height:200px"></canvas><div style="text-align:center;font-family:var(--mono);font-size:11px;color:var(--ink-dim);margin-top:4px">temps — Π_τ(t)</div></div>
        <div><canvas class="viz-canvas" id="ps-f" style="height:200px"></canvas><div style="text-align:center;font-family:var(--mono);font-size:11px;color:var(--ink-dim);margin-top:4px">fréquence — X(f)=τ·sinc(πτf)</div></div>
      </div>
      <div class="viz-row">${slider('Largeur τ','ps-w',0.3,3,0.1,1)}</div>
      <div class="viz-readout" id="ps-r"></div>`;
    const pt=makePlot(el.querySelector('#ps-t')), pf=makePlot(el.querySelector('#ps-f'));
    function redraw(){
      const w=+el.querySelector('#ps-w').value;
      el.querySelector('#ps-w-v').textContent=w.toFixed(1);
      pt.begin({xmin:-2,xmax:2,ymin:-0.3,ymax:1.4,xlabel:'t'});
      pt.fill(t=>(Math.abs(t)<=w/2)?1:0,{color:C.phos()});
      pt.fn(t=>(Math.abs(t)<=w/2)?1:0,{color:C.phos(),width:2.4});
      const sinc=f=> f===0? w : Math.sin(Math.PI*w*f)/(Math.PI*f);
      pf.begin({xmin:-6,xmax:6,ymin:-w*0.35,ymax:w*1.15,xlabel:'f'});
      pf.fn(sinc,{color:C.cyan(),width:2.2});
      pf.vline(1/w,{color:C.amber()}); pf.vline(-1/w,{color:C.amber()});
      pf.label(1/w,w*0.95,'1/τ',{color:C.amber(),align:'left'});
      el.querySelector('#ps-r').innerHTML=`τ = ${w.toFixed(1)} ⇒ 1ᵉʳ zéro du sinc en f = ±1/τ = ±${(1/w).toFixed(2)}. <b>Plus la porte est étroite, plus le sinc est large</b> : c'est le compromis temps-fréquence (principe d'incertitude).`;
    }
    el.querySelector('#ps-w').oninput=redraw;
    register(redraw);
  }

  /* =====================================================================
     CH5 — Réponse 2nd ordre amortie & charge RC
     ===================================================================== */
  function buildSecondOrder(el){
    el.innerHTML=`
      <canvas class="viz-canvas" id="so-c" style="height:240px"></canvas>
      ${legend([{c:'var(--phos)',t:'g(t)=e^(−bt)·sin(at)'},{c:'var(--ink-dim)',t:'enveloppe ±e^(−bt)'}])}
      <div class="viz-row">
        ${slider('Amortissement b','so-b',0.1,3,0.1,0.5)}
        ${slider('Pseudo-pulsation a','so-a',0.5,5,0.1,2)}
      </div>
      <div class="viz-readout" id="so-r"></div>`;
    const plot=makePlot(el.querySelector('#so-c'));
    function redraw(){
      const b=+el.querySelector('#so-b').value, a=+el.querySelector('#so-a').value;
      el.querySelector('#so-b-v').textContent=b.toFixed(1);
      el.querySelector('#so-a-v').textContent=a.toFixed(1);
      plot.begin({xmin:0,xmax:12,ymin:-1.1,ymax:1.1,xlabel:'t'});
      plot.fn(t=>Math.exp(-b*t),{color:C.dim(),width:1.3,dash:[5,4]});
      plot.fn(t=>-Math.exp(-b*t),{color:C.dim(),width:1.3,dash:[5,4]});
      plot.fn(t=>Math.exp(-b*t)*Math.sin(a*t),{color:C.phos(),width:2.4});
      el.querySelector('#so-r').innerHTML=`Réponse impulsionnelle d'un 2ᵉ ordre : pôles p = −b ± ja = −${b.toFixed(1)} ± ${a.toFixed(1)}j. Comme <b>b > 0</b> (partie réelle < 0), le système est <b>stable</b> : oscillations qui s'amortissent. Cas du cours : b=2, a=1 ⇒ e^(−2t)sin(t).`;
    }
    el.querySelector('#so-b').oninput=redraw;
    el.querySelector('#so-a').oninput=redraw;
    register(redraw);
  }
  function buildRC(el){
    el.innerHTML=`
      <canvas class="viz-canvas" id="rc-c" style="height:240px"></canvas>
      ${legend([{c:'var(--phos)',t:'v_S(t)=5(1−e^(−t/τ))'},{c:'var(--amber)',t:'63% à t=τ'},{c:'var(--ink-dim)',t:'valeur finale 5 V'}])}
      <div class="viz-row">${slider('Constante de temps τ','rc-t',0.3,3,0.1,1)}</div>
      <div class="viz-readout" id="rc-r"></div>`;
    const plot=makePlot(el.querySelector('#rc-c'));
    function redraw(){
      const tau=+el.querySelector('#rc-t').value;
      el.querySelector('#rc-t-v').textContent=tau.toFixed(1);
      plot.begin({xmin:0,xmax:10,ymin:0,ymax:6,xlabel:'t',ylabel:'V'});
      plot.hline(5,{color:C.dim()});
      plot.fn(t=>5*(1-Math.exp(-t/tau)),{color:C.phos(),width:2.6});
      plot.dot(tau,5*(1-Math.exp(-1)),{color:C.amber(),r:5});
      plot.vline(tau,{color:C.amber()});
      el.querySelector('#rc-r').innerHTML=`Réponse indicielle d'un RC (passe-bas 1ᵉʳ ordre), τ=${tau.toFixed(1)}. v_S atteint <b>63%</b> (≈3,16 V) à t=τ et tend vers la valeur finale <b>5 V</b> (vérifiée par le théorème de la valeur finale : lim p→0 de p·V_S(p)).`;
    }
    el.querySelector('#rc-t').oninput=redraw;
    register(redraw);
  }

  /* =====================================================================
     REGISTRE
     ===================================================================== */
  const VIZ = {
    ch1:[{id:'singular', title:'Explorateur de signaux singuliers', desc:"Affichez et manipulez Dirac, Heaviside, porte, peigne et exponentielle causale. Réglez décalage et largeur pour voir l'effet.", build:buildSingular}],
    ch2:[{id:'fourier', title:'Reconstruction d\'une série de Fourier', desc:"Ajoutez les harmoniques une à une et voyez le signal se former. Le spectre montre l'amplitude de chaque harmonique ; le phénomène de Gibbs apparaît aux discontinuités.", build:buildFourier}],
    ch3:[{id:'conv', title:'Convolution : retourner, glisser, intégrer', desc:"Le panneau du haut montre x(τ) fixe et y(t−τ) retournée puis glissée, avec leur recouvrement. Le panneau du bas trace z(t)=(x∗y)(t) qui se construit.", build:buildConv}],
    ch4:[
      {id:'sampling', title:'Échantillonnage et repliement (Shannon)', desc:"Réglez la fréquence du signal et celle d'échantillonnage. Quand f₀ dépasse F_E/2, le repliement apparaît : on perçoit une fausse fréquence (en rouge).", build:buildSampling},
      {id:'portesinc', title:'Dualité porte ↔ sinus cardinal', desc:"Une porte dans le temps devient un sinc en fréquence. Variez la largeur τ pour visualiser le compromis temps-fréquence.", build:buildPorteSinc}
    ],
    ch5:[
      {id:'second', title:'Réponse d\'un système du 2ᵉ ordre', desc:"Variez l'amortissement b et la pseudo-pulsation a. La partie réelle négative du pôle (b>0) garantit la stabilité : l'oscillation s'amortit.", build:buildSecondOrder},
      {id:'rc', title:'Charge d\'un circuit RC (réponse indicielle)', desc:"Réglez la constante de temps τ et observez la charge exponentielle vers la valeur finale, avec le repère des 63% à t=τ.", build:buildRC}
    ],
  };

  /* ---------- API exposée ---------- */
  window.vizListFor = ch => (VIZ[ch]||[]).map(({id,title,desc})=>({id,title,desc}));
  window.mountChapterViz = ch => {
    window.clearViz();
    (VIZ[ch]||[]).forEach(w=>{ const elx=document.getElementById('viz-'+w.id); if(elx) try{w.build(elx);}catch(e){console.warn('viz',w.id,e);} });
  };
  window.clearViz = () => { ACTIVE.forEach(a=>{try{a.stop&&a.stop();}catch(e){}}); ACTIVE=[]; };
  window.redrawViz = () => { ACTIVE.forEach(a=>{try{a.redraw&&a.redraw();}catch(e){}}); };

  let rt=null;
  window.addEventListener('resize', ()=>{ clearTimeout(rt); rt=setTimeout(()=>window.redrawViz(),120); });
})();
