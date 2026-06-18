/* =====================================================================
   APP — Théorie du Signal · outil de révision
   Routage par hash, rendu des vues, quiz, flashcards, examen, recherche.
   ===================================================================== */

const $ = (s,el=document)=>el.querySelector(s);
const $$ = (s,el=document)=>Array.from(el.querySelectorAll(s));
const esc = s => String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

/* -------- MathJax re-typeset -------- */
function typeset(node){
  if(window.MathJax && window.MathJax.typesetPromise){
    window.MathJax.typesetPromise(node?[node]:undefined).catch(()=>{});
  }
}

/* -------- Theme -------- */
function applyTheme(t){
  document.documentElement.setAttribute('data-theme', t);
  try{ localStorage.setItem('ts_theme', t); }catch(e){}
}
function toggleTheme(){
  const cur = document.documentElement.getAttribute('data-theme')==='light'?'dark':'light';
  applyTheme(cur);
  if(window.redrawViz) setTimeout(window.redrawViz, 30);
}
(function initTheme(){
  let t='dark';
  try{ t = localStorage.getItem('ts_theme') || 'dark'; }catch(e){}
  applyTheme(t);
})();

/* -------- Sidebar mobile -------- */
function toggleSidebar(){ $('#sidebar').classList.toggle('open'); $('#overlay').classList.toggle('show'); }
function closeSidebar(){ $('#sidebar').classList.remove('open'); $('#overlay').classList.remove('show'); }

/* =====================================================================
   NAVIGATION
   ===================================================================== */
const NAV = [
  {grp:"Parcours"},
  {id:"accueil", ic:"⌂", label:"Accueil"},
  {grp:"Chapitres"},
  ...CHAPTERS.map(c=>({id:c.id, ic:c.num, label:c.short})),
  {grp:"Outils de révision"},
  {id:"revision", ic:"≣", label:"Révision rapide"},
  {id:"quiz", ic:"?", label:"Quiz interactifs"},
  {id:"flashcards", ic:"▭", label:"Flashcards"},
  {id:"examen", ic:"⏱", label:"Mode examen"},
];

function buildNav(){
  const nav = $('#navlist');
  nav.innerHTML = NAV.map(item=>{
    if(item.grp) return `<div class="grp">${item.grp}</div>`;
    return `<a href="#${item.id}" data-route="${item.id}"><span class="ic">${item.ic}</span><span>${esc(item.label)}</span></a>`;
  }).join('');
}

function setActiveNav(route){
  $$('#navlist a').forEach(a=>{
    a.classList.toggle('active', a.dataset.route===route || (route.startsWith('ch')&&a.dataset.route===route));
  });
}

/* =====================================================================
   ROUTER
   ===================================================================== */
function route(){
  if(window.clearViz) window.clearViz();
  const hash = (location.hash||'#accueil').slice(1);
  const [base, param] = hash.split('/');
  const content = $('#content');
  let html='';
  if(base==='accueil') html = viewHome();
  else if(base.startsWith('ch') && CHAPTERS.find(c=>c.id===base)) html = viewChapter(base);
  else if(base==='revision') html = viewRevision();
  else if(base==='quiz') html = viewQuizHome();
  else if(base==='flashcards') html = viewFlashHome();
  else if(base==='examen') html = viewExamIntro();
  else html = viewHome();

  content.innerHTML = `<div class="view active">${html}</div>`;
  setActiveNav(base);
  window.scrollTo(0,0);
  closeSidebar();
  typeset(content);
  // re-bind per-view behaviours
  if(base==='quiz') bindQuizHome();
  if(base==='flashcards') initFlash();
  if(base==='examen') {/* bound via buttons */}
  if(base.startsWith('ch')) { bindChapter(); if(window.mountChapterViz) window.mountChapterViz(base); }
}
window.addEventListener('hashchange', route);

/* =====================================================================
   VIEW : ACCUEIL
   ===================================================================== */
function viewHome(){
  const cards = CHAPTERS.map(c=>`
    <a class="card click chap-card" href="#${c.id}" style="text-decoration:none">
      <div class="num">CHAPITRE ${c.num}</div>
      <h3>${esc(c.title)}</h3>
      <p>${esc(c.intro.slice(0,120))}…</p>
      <div class="tags">${c.tags.slice(0,4).map(t=>`<span class="tag">${esc(t)}</span>`).join('')}</div>
    </a>`).join('');

  return `
  <div class="hero">
    <svg class="scope" viewBox="0 0 1200 360" preserveAspectRatio="none">
      <defs>
        <linearGradient id="g1" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="#39ff8b" stop-opacity="0"/>
          <stop offset=".5" stop-color="#39ff8b" stop-opacity=".55"/>
          <stop offset="1" stop-color="#39ff8b" stop-opacity="0"/>
        </linearGradient>
      </defs>
      <g stroke="#22364f" stroke-width="1">
        ${Array.from({length:13},(_,i)=>`<line x1="${i*100}" y1="0" x2="${i*100}" y2="360"/>`).join('')}
        ${Array.from({length:5},(_,i)=>`<line x1="0" y1="${i*90}" x2="1200" y2="${i*90}"/>`).join('')}
      </g>
      <path id="wave" d="" stroke="url(#g1)" stroke-width="2.5" fill="none"/>
    </svg>
    <div class="htext">
      <div class="eyebrow">Théorie du signal · EFREI · 2025/2026</div>
      <h1>Réviser le signal,<br><span class="accent">sans bruit.</span></h1>
      <p>Tout le cours de Didier Achvar, condensé pour l'examen : résumés, formules expliquées, méthodes types, exercices corrigés, quiz, flashcards et examen blanc chronométré.</p>
      <div class="cta">
        <a class="btn btn-primary" href="#ch1">Commencer par les bases →</a>
        <a class="btn btn-ghost" href="#examen">Passer un examen blanc</a>
      </div>
    </div>
  </div>

  <div class="section-title"><span class="bar"></span><h2>Parcours recommandé</h2></div>
  <p class="lead">Le cours se construit en escalier : chaque chapitre s'appuie sur le précédent. Suivez l'ordre — les notions de corrélation mènent à Fourier, la convolution prépare la transformée, qui elle-même ouvre sur Laplace.</p>
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin:18px 0 8px;align-items:center">
    ${CHAPTERS.map((c,i)=>`
      <a href="#${c.id}" style="text-decoration:none" class="pill" title="${esc(c.title)}">${c.num} · ${esc(c.short)}</a>
      ${i<CHAPTERS.length-1?'<span style="color:var(--phos);font-family:var(--mono)">→</span>':''}
    `).join('')}
  </div>

  <div class="section-title"><span class="bar"></span><h2>Les chapitres</h2></div>
  <div class="grid g3">${cards}</div>

  <div class="section-title"><span class="bar"></span><h2>Conseils avant l'examen</h2></div>
  <div class="grid g2">
    <div class="card">
      <h3 style="margin-top:0">Méthode de révision</h3>
      <ul class="clean">
        <li><b>Comprenez la logique d'ensemble</b> avant de mémoriser : corrélation → projection → Fourier → convolution → Laplace forment une seule histoire.</li>
        <li><b>Les formules s'attrapent par l'intuition</b> : chaque page « Interprétation » explique le pourquoi. Une formule comprise se retrouve, une formule apprise s'oublie.</li>
        <li><b>Refaites les exercices types</b> sans regarder la correction, puis comparez. Ce sont les schémas qui retombent à l'examen.</li>
        <li><b>Exploitez la parité</b> partout : elle annule la moitié des coefficients et évite les erreurs.</li>
      </ul>
    </div>
    <div class="card">
      <h3 style="margin-top:0">À avoir en tête le jour J</h3>
      <ul class="clean">
        <li><b>Bornes d'intégration</b> : une période pour les périodiques, tout l'axe pour l'énergie, 0→∞ pour Laplace.</li>
        <li><b>Conjugués et conditions initiales</b> : ne pas les oublier (corrélation, dérivée en Laplace).</li>
        <li><b>Convolution ≠ corrélation</b> : on retourne un signal pour la convolution.</li>
        <li><b>Vérifiez vos inversions de Laplace</b> par les théorèmes valeur initiale / finale.</li>
      </ul>
    </div>
  </div>

  <div class="section-title"><span class="bar"></span><h2>S'entraîner</h2></div>
  <div class="grid g4">
    <a class="card click" href="#revision" style="text-decoration:none"><div class="num" style="font-family:var(--mono);color:var(--phos);font-size:12px">FICHES</div><h3 style="margin:8px 0 4px;font-size:17px">Révision rapide</h3><p style="color:var(--ink-soft);font-size:13px;margin:0">Formules + tableau comparatif des 4 outils.</p></a>
    <a class="card click" href="#quiz" style="text-decoration:none"><div class="num" style="font-family:var(--mono);color:var(--phos);font-size:12px">QCM</div><h3 style="margin:8px 0 4px;font-size:17px">Quiz</h3><p style="color:var(--ink-soft);font-size:13px;margin:0">Correction immédiate et explications.</p></a>
    <a class="card click" href="#flashcards" style="text-decoration:none"><div class="num" style="font-family:var(--mono);color:var(--phos);font-size:12px">CARTES</div><h3 style="margin:8px 0 4px;font-size:17px">Flashcards</h3><p style="color:var(--ink-soft);font-size:13px;margin:0">Question / réponse à retourner.</p></a>
    <a class="card click" href="#examen" style="text-decoration:none"><div class="num" style="font-family:var(--mono);color:var(--phos);font-size:12px">EXAMEN</div><h3 style="margin:8px 0 4px;font-size:17px">Examen blanc</h3><p style="color:var(--ink-soft);font-size:13px;margin:0">30 min, barème, corrigé détaillé.</p></a>
  </div>
  `;
}

/* animate hero wave after render */
function animateWave(){
  const path = document.getElementById('wave');
  if(!path) return;
  let t=0;
  function frame(){
    const p2 = document.getElementById('wave');
    if(!p2) return; // view changed
    let d='M 0 180';
    for(let x=0;x<=1200;x+=8){
      const y = 180
        + 55*Math.sin((x/120) + t)
        + 22*Math.sin((x/45) + t*1.7)
        + 12*Math.sin((x/22) + t*2.3);
      d += ` L ${x} ${y.toFixed(1)}`;
    }
    p2.setAttribute('d', d);
    t += 0.03;
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

/* =====================================================================
   VIEW : CHAPITRE
   ===================================================================== */
function vizBlock(chId){
  const list = (window.vizListFor ? window.vizListFor(chId) : []);
  if(!list.length) return '';
  return `
  <div class="section-title"><span class="bar"></span><h2>Visualisations interactives</h2><span class="src">canvas live</span></div>
  ${list.map(w=>`<div class="vizcard"><h4>${esc(w.title)}</h4><p class="vdesc">${esc(w.desc)}</p><div id="viz-${w.id}"></div></div>`).join('')}`;
}
function viewChapter(id){
  const c = CHAPTERS.find(x=>x.id===id);
  const idx = CHAPTERS.findIndex(x=>x.id===id);
  const prev = CHAPTERS[idx-1], next = CHAPTERS[idx+1];

  const defs = c.defs.map(d=>`
    <div class="def"><b>${d.t}</b> — ${d.d} <span class="pill" style="margin-left:6px">${d.src}</span></div>`).join('');

  const formulas = c.formulas.map(f=>`
    <div class="formula"><div class="lbl">${esc(f.n)} · ${f.src}</div>${f.eq}</div>`).join('');

  const intuitions = c.intuitions.map(i=>`
    <div class="intu"><div class="h">◎ ${esc(i.h)}</div><div>${i.t}</div></div>`).join('');

  const methods = `<ol class="method">${c.methods.map(m=>`<li>${m}</li>`).join('')}</ol>`;

  const errors = c.errors.map(e=>`<li>${e}</li>`).join('');

  const fiche = `<ul>${c.fiche.map(f=>`<li>${f}</li>`).join('')}</ul>`;

  const exos = c.exercises.map((ex,i)=>`
    <div class="exo" data-exo="${i}">
      <div class="q" onclick="toggleExo(this)">
        <span class="n">${ex.n}</span>
        <div class="qt">
          <div class="title">${esc(ex.title)} <span class="pill">${ex.src}</span></div>
          <div class="stmt">${ex.stmt}</div>
        </div>
        <span class="chev">▸</span>
      </div>
      <div class="body">
        ${ex.hints && ex.hints.length ? `<div class="hint"><div class="hh">INDICES ÉTAPE PAR ÉTAPE</div><ul class="clean" style="margin-bottom:0">${ex.hints.map(h=>`<li>${h}</li>`).join('')}</ul></div>`:''}
        <div class="sol">
          <button class="sol-toggle" onclick="toggleSol(this)">▸ Afficher la correction complète</button>
          <div class="sol-body">
            <div>${ex.sol}</div>
            ${ex.take?`<div class="takeaway"><b>À retenir pour l'examen :</b> ${ex.take}</div>`:''}
          </div>
        </div>
      </div>
    </div>`).join('');

  return `
  <div class="chap-head">
    <div class="num">CHAPITRE ${c.num}</div>
    <h1>${esc(c.title)}</h1>
    <p>${esc(c.intro)}</p>
  </div>

  <div class="block">
    <h3><span class="dot">§</span> Résumé</h3>
    <p style="color:var(--ink-soft);margin:0">${c.summary}</p>
  </div>

  <div class="block">
    <h3><span class="dot">≝</span> Définitions importantes</h3>
    ${defs}
  </div>

  <div class="block">
    <h3><span class="dot">∑</span> Formules essentielles</h3>
    ${formulas}
  </div>

  <div class="block">
    <h3><span class="dot">◎</span> Interprétation intuitive</h3>
    ${intuitions}
  </div>

  ${vizBlock(c.id)}

  <div class="block">
    <h3><span class="dot">⟶</span> Méthodes types à connaître</h3>
    ${methods}
  </div>

  <div class="block">
    <h3><span class="dot">⚠</span> Erreurs fréquentes</h3>
    <div class="warn"><div class="h">À ÉVITER ABSOLUMENT</div><ul class="clean" style="margin-bottom:0">${errors}</ul></div>
  </div>

  <div class="section-title"><span class="bar"></span><h2>Mini-fiche de révision</h2></div>
  <div class="fiche"><h4>L'ESSENTIEL — ${c.short.toUpperCase()}</h4>${fiche}</div>

  <div class="section-title"><span class="bar"></span><h2>Exercices types corrigés</h2><span class="src">${c.exercises.length} exercices</span></div>
  ${exos}

  <div class="chapnav">
    ${prev?`<a href="#${prev.id}"><span class="dir">← CHAPITRE PRÉCÉDENT</span><span class="ttl">${esc(prev.short)}</span></a>`:`<a class="disabled"><span class="dir">←</span><span class="ttl">Début du cours</span></a>`}
    ${next?`<a class="next" href="#${next.id}"><span class="dir">CHAPITRE SUIVANT →</span><span class="ttl">${esc(next.short)}</span></a>`:`<a class="next" href="#revision"><span class="dir">SUITE →</span><span class="ttl">Révision rapide</span></a>`}
  </div>
  `;
}
function bindChapter(){ /* accordions use inline onclick */ }
function toggleExo(el){ el.closest('.exo').classList.toggle('open'); }
function toggleSol(btn){
  const body = btn.nextElementSibling;
  const open = body.classList.toggle('show');
  btn.textContent = open ? '▾ Masquer la correction' : '▸ Afficher la correction complète';
  if(open) typeset(body);
}

/* =====================================================================
   VIEW : RÉVISION RAPIDE
   ===================================================================== */
function viewRevision(){
  // formula sheet grouped by chapter
  const sheet = CHAPTERS.map(c=>`
    <div class="fcat">
      <div class="ch">${c.num} · ${esc(c.short)}</div>
      ${c.formulas.map(f=>`<div class="frow"><div class="name">${esc(f.n)}</div><div class="eq">${f.eq}</div></div>`).join('')}
    </div>`).join('');

  const head = `<thead><tr><th></th>${COMPARE.cols.map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead>`;
  const body = `<tbody>${COMPARE.rows.map(r=>`<tr><th>${esc(r.k)}</th>${r.v.map(v=>`<td>${v}</td>`).join('')}</tr>`).join('')}</tbody>`;

  return `
  <div class="chap-head">
    <div class="num">RÉVISION RAPIDE</div>
    <h1>Tout, d'un coup d'œil</h1>
    <p>Le formulaire complet et le tableau comparatif des quatre outils du cours. La page à relire la veille de l'examen.</p>
  </div>

  <div class="section-title"><span class="bar"></span><h2>Tableau comparatif des outils</h2></div>
  <p class="lead">Série de Fourier, transformée de Fourier, transformée de Laplace et convolution répondent à des besoins différents mais forment un tout cohérent. Cette grille montre quand utiliser quoi.</p>
  <div class="tablewrap"><table class="cmp">${head}${body}</table></div>

  <div class="section-title"><span class="bar"></span><h2>Propriétés transverses à retenir</h2></div>
  <div class="grid g2">
    <div class="card">
      <h3 style="margin-top:0">Le fil rouge énergétique</h3>
      <ul class="clean">
        <li><b>Parseval (séries)</b> : $P=\\sum_k|\\lambda_k|^2$ — la puissance se répartit sur les harmoniques.</li>
        <li><b>Parseval (TF)</b> : $E=\\int|X(f)|^2df$ — l'énergie se conserve temps↔fréquence.</li>
        <li><b>Autocorrélation</b> : $\\Gamma_x(0)$ = énergie/puissance, et $\\mathrm{TF}[\\Gamma_x]=S_x(f)$ (densité spectrale).</li>
      </ul>
    </div>
    <div class="card">
      <h3 style="margin-top:0">Convolution ↔ produit</h3>
      <ul class="clean">
        <li>Dans le temps, un système fait une <b>convolution</b> $s=r*e$.</li>
        <li>En <b>Fourier</b> : $\\mathrm{TF}[x*y]=X\\cdot Y$ ⇒ fonction de transfert $R(f)$.</li>
        <li>En <b>Laplace</b> : $\\mathrm{TL}[x*y]=X(p)Y(p)$ ⇒ $R(p)=S(p)/E(p)$.</li>
        <li>Les <b>exponentielles</b> sont les fonctions propres communes : $e^{j\\omega t}$ (Fourier), $e^{pt}$ (Laplace).</li>
      </ul>
    </div>
  </div>

  <div class="section-title"><span class="bar"></span><h2>Formulaire complet</h2><span class="src">par chapitre</span></div>
  ${sheet}

  <div class="section-title"><span class="bar"></span><h2>Fiches synthétiques (mini-fiches)</h2></div>
  <div class="grid g2">
    ${CHAPTERS.map(c=>`<div class="fiche"><h4>${c.num} · ${c.short.toUpperCase()}</h4><ul>${c.fiche.map(f=>`<li>${f}</li>`).join('')}</ul></div>`).join('')}
  </div>
  `;
}

/* =====================================================================
   VIEW : QUIZ
   ===================================================================== */
function viewQuizHome(){
  const cards = CHAPTERS.map(c=>{
    const n = (QUIZ[c.id]||[]).length;
    return `<div class="qpick-card" onclick="startQuiz('${c.id}')">
      <div class="num">CHAPITRE ${c.num}</div>
      <h4>${esc(c.short)}</h4>
      <div class="cnt">${n} questions · QCM + V/F</div>
    </div>`;
  }).join('');
  return `
  <div class="chap-head">
    <div class="num">QUIZ INTERACTIFS</div>
    <h1>Tester sa compréhension</h1>
    <p>Choisissez un chapitre. Correction immédiate après chaque réponse, explication détaillée, score final et recommandations de révision selon vos erreurs.</p>
  </div>
  <div class="section-title"><span class="bar"></span><h2>Choisir un chapitre</h2></div>
  <div class="quiz-pick">
    ${cards}
    <div class="qpick-card" onclick="startQuiz('all')" style="border-color:var(--phos-dim)">
      <div class="num">RÉVISION GLOBALE</div>
      <h4>Tous les chapitres</h4>
      <div class="cnt">mélange aléatoire</div>
    </div>
  </div>
  <div id="quizArea" style="margin-top:26px"></div>
  `;
}
function bindQuizHome(){ /* cards use inline onclick */ }

let QState=null;
function startQuiz(chId){
  let pool=[];
  if(chId==='all'){
    CHAPTERS.forEach(c=> (QUIZ[c.id]||[]).forEach(q=>pool.push({...q, ch:c.id})));
    pool = shuffle(pool).slice(0,12);
  } else {
    pool = (QUIZ[chId]||[]).map(q=>({...q, ch:chId}));
  }
  QState = {chId, pool, i:0, score:0, wrongCh:{}};
  renderQuizQ();
  const area=$('#quizArea'); if(area) area.scrollIntoView({behavior:'smooth',block:'start'});
}
function renderQuizQ(){
  const area=$('#quizArea'); if(!area) return;
  const {pool,i,score}=QState;
  if(i>=pool.length){ return renderQuizResult(); }
  const q=pool[i];
  const pct = Math.round((i)/pool.length*100);
  let opts='';
  if(q.type==='VF'){
    opts = ['Vrai','Faux'].map((txt,k)=>`<button class="qopt" data-k="${k}" onclick="answerQuiz(${k})"><span class="mk"></span>${txt}</button>`).join('');
  } else {
    opts = q.o.map((txt,k)=>`<button class="qopt" data-k="${k}" onclick="answerQuiz(${k})"><span class="mk">${String.fromCharCode(65+k)}</span><span>${txt}</span></button>`).join('');
  }
  area.innerHTML = `
    <div class="quiz-stage">
      <div class="qprog"><div class="track"><div class="fill" style="width:${pct}%"></div></div><div class="cnt">${i+1}/${pool.length}</div></div>
      <div class="qcard">
        <div class="qtype">${q.type==='VF'?'Vrai / Faux':'QCM'} · ${CHAPTERS.find(c=>c.id===q.ch).short}</div>
        <div class="qtext">${q.q}</div>
        <div class="qopts">${opts}</div>
        <div class="qexp" id="qexp"></div>
        <div class="qfoot" id="qfoot"></div>
      </div>
    </div>`;
  typeset(area);
}
function answerQuiz(k){
  const q=QState.pool[QState.i];
  const correct = (q.type==='VF') ? (k===0)===q.a : k===q.a;
  const correctIdx = (q.type==='VF') ? (q.a?0:1) : q.a;
  $$('#quizArea .qopt').forEach(btn=>{
    btn.disabled=true;
    const bk=+btn.dataset.k;
    if(bk===correctIdx) btn.classList.add('correct');
    if(bk===k && !correct) btn.classList.add('wrong');
  });
  if(correct) QState.score++;
  else QState.wrongCh[q.ch]=(QState.wrongCh[q.ch]||0)+1;
  const exp=$('#qexp');
  exp.className='qexp show '+(correct?'ok':'no');
  exp.innerHTML=`<div class="h">${correct?'✓ Correct':'✗ Incorrect'}</div><div>${q.e}</div>`;
  typeset(exp);
  const last = QState.i===QState.pool.length-1;
  $('#qfoot').innerHTML=`<button class="btn btn-primary" onclick="nextQuiz()">${last?'Voir le score':'Question suivante'} →</button>`;
}
function nextQuiz(){ QState.i++; renderQuizQ(); }
function renderQuizResult(){
  const {pool,score,wrongCh}=QState;
  const pct=Math.round(score/pool.length*100);
  let msg, color;
  if(pct>=80){msg="Solide. Vous maîtrisez l'essentiel.";color="var(--good)";}
  else if(pct>=55){msg="Correct, mais quelques notions à consolider.";color="var(--amber)";}
  else {msg="À retravailler : reprenez les chapitres concernés.";color="var(--danger)";}
  const recos = Object.keys(wrongCh).length
    ? `<div class="recos"><h4>Notions à revoir en priorité</h4><ul class="clean" style="margin-bottom:0">${
        Object.entries(wrongCh).sort((a,b)=>b[1]-a[1]).map(([ch,n])=>{
          const c=CHAPTERS.find(x=>x.id===ch);
          return `<li><a href="#${ch}">${esc(c.title)}</a> — ${n} erreur${n>1?'s':''}</li>`;
        }).join('')}</ul></div>`
    : `<div class="recos"><h4>Aucune erreur ciblée 🎯</h4><div style="color:var(--ink-soft)">Sans faute ou presque — passez à l'examen blanc pour confirmer.</div></div>`;
  $('#quizArea').innerHTML=`
    <div class="qresult">
      <div class="score" style="color:${color}">${score}<span class="o">/${pool.length}</span></div>
      <div class="msg">${msg} (${pct}%)</div>
      ${recos}
      <div style="margin-top:18px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap">
        <button class="btn btn-primary" onclick="startQuiz('${QState.chId}')">Recommencer</button>
        <a class="btn btn-ghost" href="#quiz">Autre chapitre</a>
        <a class="btn btn-ghost" href="#examen">Examen blanc</a>
      </div>
    </div>`;
  typeset($('#quizArea'));
}

/* =====================================================================
   VIEW : FLASHCARDS
   ===================================================================== */
function viewFlashHome(){
  const cats = [...new Set(FLASHCARDS.map(f=>f.cat))];
  return `
  <div class="chap-head">
    <div class="num">FLASHCARDS</div>
    <h1>Mémoriser activement</h1>
    <p>Une question d'un côté, la réponse de l'autre. Cliquez sur la carte pour la retourner. Filtrez par chapitre ou par type (définition, formule, propriété, méthode, piège).</p>
  </div>
  <div class="fc-controls">
    <label style="color:var(--ink-soft);font-size:13px;font-family:var(--mono)">Chapitre
      <select class="select" id="fcCh" onchange="rebuildFlash()">
        <option value="all">Tous</option>
        ${CHAPTERS.map(c=>`<option value="${c.id}">${c.num} · ${esc(c.short)}</option>`).join('')}
      </select>
    </label>
    <label style="color:var(--ink-soft);font-size:13px;font-family:var(--mono)">Type
      <select class="select" id="fcCat" onchange="rebuildFlash()">
        <option value="all">Tous</option>
        ${cats.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('')}
      </select>
    </label>
    <button class="tbtn" onclick="shuffleFlash()">⤮ Mélanger</button>
  </div>
  <div class="flashwrap">
    <div class="flashcard" id="flashcard" onclick="flipFlash()">
      <div class="flashinner">
        <div class="flashface flashfront">
          <span class="side">QUESTION</span><span class="cat" id="fcCatLabel"></span>
          <div class="txt" id="fcQ"></div>
          <span class="hintflip">cliquer pour retourner ↻</span>
        </div>
        <div class="flashface flashback">
          <span class="side">RÉPONSE</span><span class="cat" id="fcCatLabel2"></span>
          <div class="txt" id="fcA"></div>
          <span class="hintflip">cliquer pour retourner ↻</span>
        </div>
      </div>
    </div>
    <div class="fc-nav">
      <button class="btn btn-ghost" onclick="prevFlash()">← Précédente</button>
      <span class="fc-count" id="fcCount"></span>
      <button class="btn btn-ghost" onclick="nextFlash()">Suivante →</button>
    </div>
  </div>
  `;
}
let FState=null;
function initFlash(){ FState={list:[], i:0}; rebuildFlash(); }
function currentFlashList(){
  const ch=$('#fcCh')?.value||'all';
  const cat=$('#fcCat')?.value||'all';
  return FLASHCARDS.filter(f=>(ch==='all'||f.ch===ch)&&(cat==='all'||f.cat===cat));
}
function rebuildFlash(){
  FState.list=currentFlashList(); FState.i=0; showFlash();
}
function shuffleFlash(){ FState.list=shuffle(FState.list.slice()); FState.i=0; showFlash(); }
function showFlash(){
  const card=$('#flashcard'); if(!card) return;
  card.classList.remove('flip');
  const list=FState.list;
  if(!list.length){
    $('#fcQ').textContent='Aucune carte pour ce filtre.'; $('#fcA').textContent='';
    $('#fcCount').textContent='0 / 0'; return;
  }
  const f=list[FState.i];
  const c=CHAPTERS.find(x=>x.id===f.ch);
  $('#fcQ').innerHTML=f.q; $('#fcA').innerHTML=f.a;
  $('#fcCatLabel').textContent=`${c.num} · ${f.cat}`;
  $('#fcCatLabel2').textContent=`${c.num} · ${f.cat}`;
  $('#fcCount').textContent=`${FState.i+1} / ${list.length}`;
  typeset(card);
}
function flipFlash(){ $('#flashcard')?.classList.toggle('flip'); }
function nextFlash(){ if(!FState.list.length)return; FState.i=(FState.i+1)%FState.list.length; showFlash(); }
function prevFlash(){ if(!FState.list.length)return; FState.i=(FState.i-1+FState.list.length)%FState.list.length; showFlash(); }

/* =====================================================================
   VIEW : EXAMEN BLANC
   ===================================================================== */
function viewExamIntro(){
  return `
  <div class="chap-head">
    <div class="num">MODE EXAMEN</div>
    <h1>Examen blanc</h1>
    <p>Un examen représentatif généré à partir du cours, dans les conditions de l'épreuve : durée limitée, barème, puis correction détaillée et liste des notions à revoir.</p>
  </div>
  <div class="exam-intro">
    <div class="exam-meta">
      <div class="m"><div class="k">Durée</div><div class="v">30 min</div></div>
      <div class="m"><div class="k">Questions</div><div class="v">${EXAM.questions.length}</div></div>
      <div class="m"><div class="k">Barème</div><div class="v">/${EXAM.total}</div></div>
      <div class="m"><div class="k">Chapitres</div><div class="v">1→5</div></div>
    </div>
    <div class="card">
      <h3 style="margin-top:0">Avant de commencer</h3>
      <ul class="clean">
        <li>Le chronomètre démarre dès que vous lancez l'examen. À la fin du temps, la copie se corrige automatiquement.</li>
        <li>Chaque question vaut le nombre de points indiqué. Pas de point négatif.</li>
        <li>La correction donne le détail de chaque réponse et les chapitres à retravailler.</li>
      </ul>
      <button class="btn btn-primary" style="margin-top:8px" onclick="startExam()">▶ Lancer l'examen blanc</button>
    </div>
  </div>
  <div id="examArea"></div>
  `;
}
let EState=null;
function startExam(){
  EState={answers:{}, remaining:EXAM.duration, timer:null, done:false};
  renderExam();
  EState.timer=setInterval(()=>{
    EState.remaining--;
    updateClock();
    if(EState.remaining<=0){ gradeExam(true); }
  },1000);
}
function updateClock(){
  const cl=$('#examClock'); if(!cl)return;
  const m=Math.floor(EState.remaining/60), s=EState.remaining%60;
  cl.textContent=`${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  cl.classList.toggle('low', EState.remaining<=120);
}
function renderExam(){
  const qs=EXAM.questions.map((q,i)=>{
    const opts=q.o.map((txt,k)=>`
      <label class="opt"><input type="radio" name="eq${i}" value="${k}" onchange="EState.answers[${i}]=${k}"> <span>${txt}</span></label>`).join('');
    return `<div class="exam-q" id="eq${i}">
      <div class="head"><span class="n">Question ${i+1} · ${CHAPTERS.find(c=>c.id===q.ch).short}</span><span class="pts">${q.pts} pt${q.pts>1?'s':''}</span></div>
      <div class="stmt">${q.q}</div>
      <div class="opts">${opts}</div>
      <div class="corr"><div class="h">CORRECTION</div><div>${q.e}</div></div>
    </div>`;
  }).join('');
  $('#examArea').innerHTML=`
    <div class="exam-timer"><span style="font-family:var(--mono);font-size:12px;color:var(--ink-dim)">TEMPS RESTANT</span><span class="clock" id="examClock">30:00</span><div class="spacer" style="flex:1"></div><button class="btn btn-primary" onclick="gradeExam(false)">Terminer et corriger</button></div>
    ${qs}
    <div style="margin-top:20px;text-align:center"><button class="btn btn-primary" onclick="gradeExam(false)">Terminer et corriger l'examen</button></div>
    <div id="examResult"></div>`;
  typeset($('#examArea'));
  updateClock();
  $('#examArea').scrollIntoView({behavior:'smooth',block:'start'});
}
function gradeExam(auto){
  if(EState.done) return;
  EState.done=true;
  clearInterval(EState.timer);
  let score=0; const wrongCh={};
  EXAM.questions.forEach((q,i)=>{
    const el=$('#eq'+i); el.classList.add('graded');
    const chosen=EState.answers[i];
    $$('#eq'+i+' .opt').forEach((lab,k)=>{
      if(k===q.a) lab.classList.add('correct');
      if(k===chosen && chosen!==q.a) lab.classList.add('chosen-wrong');
    });
    if(chosen===q.a) score+=q.pts;
    else wrongCh[q.ch]=(wrongCh[q.ch]||0)+1;
  });
  const pct=Math.round(score/EXAM.total*100);
  let verdict,color;
  if(pct>=70){verdict="Vous êtes prêt·e pour l'examen.";color="var(--good)";}
  else if(pct>=50){verdict="Passable — consolidez les chapitres en rouge.";color="var(--amber)";}
  else {verdict="Reprenez le cours avant de retenter.";color="var(--danger)";}
  const recos = Object.keys(wrongCh).length
    ? `<div class="recos"><h4>Notions à revoir après correction</h4><ul class="clean" style="margin-bottom:0">${
        Object.entries(wrongCh).sort((a,b)=>b[1]-a[1]).map(([ch,n])=>{
          const c=CHAPTERS.find(x=>x.id===ch);
          return `<li><a href="#${ch}">${esc(c.title)}</a> — ${n} question${n>1?'s':''} manquée${n>1?'s':''}</li>`;
        }).join('')}</ul></div>`
    : `<div class="recos"><h4>Sans faute 🎯</h4><div style="color:var(--ink-soft)">Excellent — vous maîtrisez l'ensemble du programme.</div></div>`;
  $('#examResult').innerHTML=`
    <div class="qresult" style="margin-top:26px">
      <div class="score" style="color:${color}">${score}<span class="o">/${EXAM.total}</span></div>
      <div class="msg">${verdict} ${auto?'<br><span style="font-size:13px;color:var(--danger)">(temps écoulé)</span>':''}</div>
      ${recos}
      <div style="margin-top:18px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap">
        <button class="btn btn-primary" onclick="startExam()">Refaire un examen</button>
        <a class="btn btn-ghost" href="#revision">Réviser les formules</a>
      </div>
    </div>`;
  typeset($('#examArea'));
  $('#examResult').scrollIntoView({behavior:'smooth'});
}

/* =====================================================================
   RECHERCHE
   ===================================================================== */
let SEARCH_INDEX=[];
function buildSearchIndex(){
  SEARCH_INDEX=[];
  CHAPTERS.forEach(c=>{
    SEARCH_INDEX.push({ch:c.short, route:c.id, title:c.title, kind:'Chapitre', text:c.intro+' '+c.summary+' '+c.tags.join(' ')});
    c.defs.forEach(d=>SEARCH_INDEX.push({ch:c.short, route:c.id, title:d.t, kind:'Définition '+d.src, text:d.d}));
    c.formulas.forEach(f=>SEARCH_INDEX.push({ch:c.short, route:c.id, title:f.n, kind:'Formule '+f.src, text:f.n}));
    c.intuitions.forEach(i=>SEARCH_INDEX.push({ch:c.short, route:c.id, title:i.h, kind:'Intuition', text:i.t}));
    c.exercises.forEach(e=>SEARCH_INDEX.push({ch:c.short, route:c.id, title:e.n+' · '+e.title, kind:'Exercice '+e.src, text:e.stmt+' '+e.take}));
  });
}
function norm(s){return (s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');}
function runSearch(qraw){
  const box=$('#searchResults');
  const q=norm(qraw).trim();
  if(q.length<2){ box.classList.remove('open'); box.innerHTML=''; return; }
  const terms=q.split(/\s+/);
  const hits=SEARCH_INDEX.map(item=>{
    const hay=norm(item.title+' '+item.text+' '+item.ch);
    let score=0;
    terms.forEach(t=>{ if(hay.includes(t)) score+= norm(item.title).includes(t)?3:1; });
    return {item,score};
  }).filter(h=>h.score>0).sort((a,b)=>b.score-a.score).slice(0,8);
  if(!hits.length){ box.innerHTML=`<div class="search-empty">Aucun résultat pour « ${esc(qraw)} »</div>`; box.classList.add('open'); return; }
  box.innerHTML=hits.map(h=>`
    <a href="#${h.item.route}" onclick="setTimeout(()=>{document.getElementById('searchResults').classList.remove('open');document.getElementById('searchInput').value='';},10)">
      <div class="rc">${esc(h.item.ch)} · ${esc(h.item.kind)}</div>
      <div class="rt">${esc(h.item.title)}</div>
      <div class="rs">${esc(h.item.text.slice(0,90))}…</div>
    </a>`).join('');
  box.classList.add('open');
}

/* =====================================================================
   UTILS
   ===================================================================== */
function shuffle(a){ for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];} return a; }

/* =====================================================================
   INIT
   ===================================================================== */
document.addEventListener('DOMContentLoaded', ()=>{
  buildNav();
  buildSearchIndex();
  const si=$('#searchInput');
  si.addEventListener('input', e=>runSearch(e.target.value));
  si.addEventListener('keydown', e=>{ if(e.key==='Escape'){ $('#searchResults').classList.remove('open'); si.blur(); } });
  document.addEventListener('click', e=>{
    if(!e.target.closest('.search')) $('#searchResults').classList.remove('open');
  });
  // keyboard for flashcards
  document.addEventListener('keydown', e=>{
    if((location.hash||'').slice(1)!=='flashcards') return;
    if(e.key==='ArrowRight') nextFlash();
    else if(e.key==='ArrowLeft') prevFlash();
    else if(e.key===' '){ e.preventDefault(); flipFlash(); }
  });
  route();
  // hero wave needs to start after first render
  setTimeout(animateWave, 60);
});

// re-launch wave when returning to home
window.addEventListener('hashchange', ()=>{
  if((location.hash||'#accueil').slice(1)==='accueil') setTimeout(animateWave,60);
});
