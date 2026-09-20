import fs from 'fs';
import path from 'path';

const ROOT = 'E:\\AI-Content';

/* ------------------------------------------------------------------ */
/*  Arabic normalization helpers                                       */
/* ------------------------------------------------------------------ */
const AR_DIACRITICS = /[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u06DF\u06E1\u06E5\u06E6]/g;
const AR_TATWEEL = /[\u0640]/g;
const AR_BACK = {
  'أ':'ا','إ':'ا','آ':'ا','ٱ':'ا','ؤ':'و','ئ':'ي','ى':'ي','ة':'ه','ي':'ي','ك':'ك'
};
function normAr(s){
  return (s||'')
    .replace(AR_DIACRITICS,'')
    .replace(AR_TATWEEL,'')
    .split('').map(ch=> (AR_BACK[ch]||ch)).join('')
    .replace(/[\u0648]و/g,'و');
}
function normForMatch(s){
  // strip everything non arabic-letter, unify forms
  return normAr(s).replace(/[^\u0621-\u063A\u0641-\u064A]/g,' ').replace(/\s+/g,' ').trim();
}
function stripPunct(s){
  return s.replace(/[^\u0600-\u06FF\u0660-\u0669A-Za-z0-9]/g,' ').replace(/\s+/g,' ').trim();
}
const AR2EN = {'٠':'0','١':'1','٢':'2','٣':'3','٤':'4','٥':'5','٦':'6','٧':'7','٨':'8','٩':'9'};
function toENInt(s){
  return String(s).replace(/[٠-٩]/g, d=>AR2EN[d]).replace(/[^\d]/g,'');
}
const NUM_RANGE_RE = /[٠-٩0-9]+/g;

/* ------------------------------------------------------------------ */
/*  Book config                                                        */
/* ------------------------------------------------------------------ */
const BOOKS = {
  'كيف تتقن النحو': {
    id:'kayf-tataqan-nahw', branch:'نحو', parts:14, total:553,
    index: [ {file:'part-14.md', from:531, to:545} ],
    preferMd: true,
  },
  'كيف تتقن البلاغة': {
    id:'kayf-tataqan-balagha', branch:'بلاغة', parts:14, total:528,
    index: [ {file:'part-13.md', from:511, to:520}, {file:'part-14.md', from:521, to:521} ],
  },
  'كيف تتقن الصرف': {
    id:'kayf-tataqan-sarf', branch:'صرف', parts:16, total:617,
    index: [ {file:'part-16.md', from:604, to:617} ],
  },
};

const BOOK_TITLE_KEYS = {
  'كيف تتقن النحو': ['نـحو','النحو','تتقن'],
  'كيف تتقن البلاغة': ['البلاغة','بلاغة'],
  'كيف تتقن الصرف': ['الصرف','صرف'],
};

/* ------------------------------------------------------------------ */
/*  Load content: per page lines                                       */
/* ------------------------------------------------------------------ */
function loadBook(bookName, partsCount, total){
  const pages = []; // index 0 = page1 ... store per-page: {page, text, lines[]}
  const allLines = []; // flat with page
  for(let p=1;p<=partsCount;p++){
    const f = path.join(ROOT, bookName, `part-${String(p).padStart(2,'0')}.md`);
    const txt = fs.readFileSync(f, 'utf8');
    const lines = txt.split(/\r?\n/);
    let cur=null;
    for(const raw of lines){
      const m = raw.match(/^## صفحة (\d+)/);
      if(m){ cur=parseInt(m[1]); if(!pages[cur]) pages[cur]={page:cur,lines:[]}; continue; }
      const t = raw.replace(/^\s+|\s+$/g,'');
      if(cur){
        if(!pages[cur]) pages[cur]={page:cur,lines:[]};
        pages[cur].lines.push(t);
        allLines.push({page:cur, text:t, norm:normForMatch(t)});
      }
    }
  }
  return {pages, allLines};
}

/* ------------------------------------------------------------------ */
/*  Parse index → entries                                              */
/* ------------------------------------------------------------------ */
function parseIndex(bookName, cfg, total){
  const entries = [];
  for(const seg of cfg.index){
    const f = path.join(ROOT, bookName, seg.file);
    const lines = fs.readFileSync(f,'utf8').split(/\r?\n/);
    let cur=null;
    for(const raw of lines){
      const m = raw.match(/^## صفحة (\d+)/);
      if(m){ cur=parseInt(m[1]); continue; }
      if(cur==null || cur<seg.from || cur>seg.to) continue;
      const t = raw.replace(/[\u200B]/g,'').replace(/^\s+|\s+$/g,'');
      if(!t) continue;
      const parsed = parseIndexLine(t, total);
      if(parsed) entries.push(parsed);
    }
  }
  return entries;
}

function parseIndexLine(line, total){
  // returns {title, hint, isHeader}
  if(/^#/.test(line)) { // '# الفهرس'
    const t = line.replace(/^#+/,'').trim();
    return null; // index page-title line, skip
  }
  const bare = line;
  // header separators
  if(/^\|?\s*:?-+:?\s*\|??$/.test(bare) ) return null;
  // '| الموضوع | رقم |' style header row
  const cleaned = bare.replace(/^\|*/,'').replace(/\|*$/,'').trim();
  if(/^(الموضوع|رَقْمُ الصفحة|رقم الصفحة|الكلمة|تعريفها|مثال|المَوْضُوع)/.test(cleaned)) return null;

  // extract numbers
  const nums = [];
  let mm; const numRe = new RegExp(NUM_RANGE_RE.source,'g');
  while((mm = numRe.exec(bare))){ nums.push({v:parseInt(toENInt(mm[0]),10), idx:mm.index}); numRe.lastIndex = mm.index+mm[0].length; }

  // candidate page = number at extreme left (after separators) or extreme right, within 1..total
  const inRange = nums.filter(n=>n.v>=1 && n.v<=total);
  let page = null, pageIdx = -1;
  if(inRange.length===1){ page = inRange[0].v; pageIdx = inRange[0].idx; }
  else if(inRange.length>1){
    // prefer the leftmost among first 2 tokens OR rightmost
    const first = inRange[0], last = inRange[inRange.length-1];
    // if first number occurs before char index 4 → likely page-first
    if(first.idx < 5){ page=first.v; pageIdx=first.idx; }
    else { page=last.v; pageIdx=last.idx; }
  }
  // strip the page number token from title
  let titleRaw = bare;
  if(page!=null){
    const re = new RegExp(NUM_RANGE_RE.source);
    // remove the specific number string
    // find original substring numerically equal to page using AR or EN
    const tokenStr = bare.slice(pageIdx);
    const m2 = tokenStr.match(/^[٠-٩0-9]+/);
    if(m2) titleRaw = bare.slice(0,pageIdx) + ' ' + bare.slice(pageIdx+m2[0].length);
    else titleRaw = bare.replace(re,' ');
  }
  titleRaw = titleRaw.replace(/[|\[\])]/g,' ')
                      .replace(/^\s*-+\s*/,'')
                      .replace(/\s*-\s*$/,'')
                      .replace(/\s+/g,' ').trim();
  const title = titleRaw.replace(/\s+/g,' ').trim();
  if(!page) return {title, hint:null, skip:false};
  // running page header like "531 | كيف تتقن النحو" → title ≈ book title → skip
  if(bookTitleNear(title)) return null;
  return {title, hint:page, skip:false};
}

let ACTIVE_TITLE_KEYS = [];
function bookTitleNear(title){
  const t = normAr(title).replace(/[\d\u061f?؟!]/g,'').trim();
  if(!t) return true;
  let rest = t;
  for(const k of ACTIVE_TITLE_KEYS){ rest = rest.split(normAr(k)).join(' '); }
  const residue = rest.replace(/[^\u0621-\u063A\u0641-\u064A]/g,'').trim();
  return residue.length===0;
}

/* ------------------------------------------------------------------ */
/*  Heading detection                                                  */
/* ------------------------------------------------------------------ */
function looksLikeHeader(line, titleKeys){
  // running page header like "كيف تتقن النحو | 530" or "531 | كيف تتقن النحو"
  const t = normAr(line);
  let matchesKeys=0;
  for(const k of titleKeys){ if(t.includes(normAr(k))) matchesKeys++; }
  const hasSubstantive = /[مبكف].*[ةا].*/.test(t);
  // header if the line is basically just book title + optionally a number, short
  if(matchesKeys>=1){
    const content = t.replace(/[\d|]/g,'').trim();
    // remove book title keywords
    let rest = content;
    for(const k of titleKeys){ rest = rest.split(normAr(k)).join(''); }
    rest = rest.replace(/[\s\u0600-\u06FF٠-٩0-9]/g,'').trim(); // keep only non-arabic residue
    if(rest.length===0) return true;
  }
  return false;
}

function isHeadingLine(line, cfg){
  const isMd = /^#{1,3}\s/.test(line);
  const mdLevel = isMd ? (/^#+/.exec(line)[0].length) : 0;
  const t = line.replace(/^#+\s*/, '').trim();
  if(!t) return false;
  // markdown heading
  if(isMd) return {title:t, md:true, mdLevel};
  if(/^#/.test(line)) return false; // # without space unlikely
  if(t.startsWith('|')) return false; // table row
  if(/^\d/.test(t)) return false; // starts with number (page/footer)
  if(/www\.|lisanarb\.com|مكتبة لسان|.\uFEFF/.test(t)) return false;
  if(/---/.test(t)) return false;
  // footer line like "البلاغة؟ | 521"
  if(cfg.titleKeys && looksLikeHeader(t, cfg.titleKeys)) return false;
  // meaningful arabic letters count
  const letters = t.replace(/[^\u0621-\u063A\u0641-\u064A]/g,'').length;
  if(letters < 8 || letters > 52) return false;
  // exclude line endings typical of prose/labels (only for non-markdown headings)
  if(/[\u002e\u060c\u061b\u061f:؛،.]$/.test(t)) return false;
  if(letters===0) return false;
  return {title:t, md:false, mdLevel:0};
}

/* ------------------------------------------------------------------ */
/*  matching                                                           */
/* ------------------------------------------------------------------ */
function bestMatch(title, hint, headings, indexPages, preferMd){
  const nTitle = normForMatch(title);
  if(!nTitle) return null;
  const expected = hint ? hint+1 : null;
  const tw = nTitle.split(' ').filter(w=>w.length>=3);
  const tset = new Set(tw);
  const cands = [];
  for(const h of headings){
    if(indexPages && indexPages.has(h.page)) continue;
    const hn = h.norm;
    const hset = new Set(hn.split(' ').filter(w=>w.length>=2));
    let spec = 0;
    if(hn===nTitle) spec = 4;
    else if(hn.includes(nTitle)) spec = 3;
    else if(nTitle.includes(hn) && hn.length>=10) spec = 2;
    else if(tw.length){
      const matched = tw.filter(w=>hset.has(w)).length;
      const all = tw.length===matched && matched>=2;
      if(all) spec = 1.5;
      else if(matched/tw.length >= 0.75 && matched>=3) spec = 1.0;
      else continue;
    } else continue;
    if(preferMd && h.mdLevel>=2) spec += 2.0;
    cands.push({page:h.page, spec, pos: expected==null ? 0 : Math.abs(h.page-expected), hn});
  }
  if(!cands.length) return (expected? {page:expected, fallback:true, hTitle:title} : null);

  const sortCands = (arr)=> arr.sort((a,b)=> (b.spec-a.spec) || (a.pos-b.pos));
  if(expected!=null){
    const inWindow = cands.filter(c=> c.pos<=8);
    if(inWindow.length){
      const best = sortCands(inWindow)[0];
      return {page:best.page, hTitle:title};
    }
    // nothing near → strong unique global match only, else fallback to hint+1
    const strong = cands.filter(c=> c.spec>=3);
    if(strong.length) return {page: sortCands(strong)[0].page, hTitle:title};
    return {page:expected, fallback:true, hTitle:title};
  }
  const best = sortCands(cands)[0];
  return {page:best.page, hTitle:title};
}

/* ------------------------------------------------------------------ */
/*  concepts                                                           */
/* ------------------------------------------------------------------ */
const STOP = new Set(['ال','في','من','على','عن','الى','إلى','ما','كيف','ل','لـ','ثم','عنه','عليها','به','ماهو','هو','قد','و','أو','تم','كل','أن','مع','فيما','بعد','قبل']);
function genConcepts(title){
  const w = normForMatch(title).split(' ').filter(x=>x.length>=2 && !STOP.has(x));
  const out=[];
  for(const x of w){ if(!out.includes(x)) out.push(x); if(out.length>=5) break; }
  return out;
}

/* ------------------------------------------------------------------ */
/*  MAIN                                                               */
/* ------------------------------------------------------------------ */
function main(){
  const args = process.argv.slice(2);
  const booksToRun = args.length? args : Object.keys(BOOKS);
  for(const bookName of booksToRun){
    const cfg = BOOKS[bookName];
    ACTIVE_TITLE_KEYS = BOOK_TITLE_KEYS[bookName] || [];
    const {pages, allLines} = loadBook(bookName, cfg.parts, cfg.total);
    console.log('\n######## '+bookName+' ########');

    // build heading candidates (non-prose only)
    const headings=[];
    for(const pg of pages){
      if(!pg) continue;
      for(const ln of pg.lines){
        const h = isHeadingLine(ln, cfg);
        if(h){ headings.push({page:pg.page, title:h.title, norm:normForMatch(h.title), md:h.md, isProse:false}); }
      }
    }
    console.log('heading candidates:', headings.length);

    const entries = parseIndex(bookName, cfg, cfg.total).filter(e=>!e.skip);
    console.log('index entries:', entries.length);

    // index pages to forbid (the فهرس backs matter itself)
    const indexPages = new Set();
    for(const seg of cfg.index){
      for(let pg=seg.from; pg<=seg.to; pg++) indexPages.add(pg);
    }

    // match
    const preferMd = cfg.preferMd === true;
    const sections=[];
    for(const e of entries){
      const bm = bestMatch(e.title, e.hint, headings, indexPages, preferMd);
      sections.push({title:e.title, hint:e.hint, page: bm?bm.page : (e.hint?e.hint+1:null), fallback: !bm || !!bm.fallback});
    }
    const resolved = sections.filter(s=>s.page);
    console.log('sections with page:', resolved.length);

    // report part-01 for nahw
    if(bookName==='كيف تتقن النحو'){
      const p1 = resolved.filter(s=>s.page>=1&&s.page<=40).sort((a,b)=>a.page-b.page);
      console.log('--- nahw part-01 sections ---');
      for(const s of p1) console.log('  p'+String(s.page).padStart(3)+' '+(s.fallback?'[F]':'')+ s.title.slice(0,45));
    }

    // write a debug file
    fs.writeFileSync(path.join('C:\\Users\\blals\\AppData\\Local\\Temp\\opencode', 'dbg_'+cfg.id+'.json'),
      JSON.stringify({sections}, null, 1), 'utf8');
  }
}

const argv1 = process.argv[1];
if ((argv1 && argv1.endsWith('make-meta.mjs'))) {
  main();
}

export { loadBook, parseIndex, bestMatch, normForMatch, isHeadingLine, buildHeadings, BOOKS, BOOK_TITLE_KEYS };

function buildHeadings(pages, cfg){
  const headings=[];
  for(const pg of pages){
    if(!pg) continue;
    for(const ln of pg.lines){
      const h = isHeadingLine(ln, cfg);
      if(h){ headings.push({page:pg.page, title:h.title, norm:normForMatch(h.title), md:h.md, isProse:false}); }
    }
  }
  return headings;
}