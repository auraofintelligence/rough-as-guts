from pathlib import Path
from html import escape as esc
import json, re, shutil, argparse, hashlib
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
BASE='https://auraofintelligence.github.io/rough-as-guts/'
PAGES=[('home','index.html','Home'),('men','men.html','Men'),('women','women.html','Women'),('youth','youth.html','Young Crew'),('workplace','workplace.html','Worksites'),('library','library.html','Original library'),('systems','systems.html','Systems'),('pipeline','pipeline.html','Product pipeline'),('sitemap','sitemap.html','Site map')]
HERO_TITLES={'home':'Rough as guts','men':'For the blokes','women':'For the women','youth':'Young crew','workplace':'Work. Camp. Common sense.','library':'The original rough stuff','systems':'Make the hint stick','pipeline':'Out of the shed','sitemap':'Find your way round'}
SELECTED={'home':[6,28,39], 'workplace':[11,16,30]}

def p(t,cls=''):return f'<p{(" class="+chr(34)+cls+chr(34)) if cls else ""}>{esc(str(t))}</p>'
def ul(xs):return '<ul>'+''.join('<li>'+esc(str(x))+'</li>' for x in xs)+'</ul>' if xs else ''
def link(h,t,cls=''):return f'<a href="{esc(h)}" class="{cls}">{esc(t)}</a>'
def load():
    content=json.loads((ROOT/'data/site-content.json').read_text(encoding='utf-8'))
    cat=json.loads((ROOT/'data/catalogue.json').read_text(encoding='utf-8'))
    prov=json.loads((ROOT/'data/source-provenance.json').read_text(encoding='utf-8'))
    return content,cat,prov

def portable_catalogue(source):
    data=json.loads(source.read_text(encoding='utf-8'))
    def clean(x):
        if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
        if isinstance(x,list):return [clean(v) for v in x]
        if isinstance(x,str):
            if re.match(r'^[A-Za-z]:[\\/]',x):
                if 'slide-' in x:return 'assets/originals/'+x.replace('\\','/').split('/')[-1]
                if x.endswith('.pptx'):return 'Rough-as-guts.pptx (retained source file; SHA-256 supplied)'
                return x.replace('\\','/').split('/')[-1]
        return x
    data=clean(data)
    (ROOT/'data/catalogue.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def hero_files():
    result={}
    for key,_,_ in PAGES:
        raw=ROOT/f'assets/generated/hero-{key}.png'
        web=ROOT/f'assets/generated/hero-{key}.webp'
        if raw.exists() and (not web.exists() or raw.stat().st_mtime>web.stat().st_mtime):
            with Image.open(raw) as im:
                im=im.convert('RGB'); im.thumbnail((1920,1200));im.save(web,'WEBP',quality=88,method=6)
        if not web.exists():raise FileNotFoundError(f'Unique hero artwork missing for {key}')
        result[key]=web.relative_to(ROOT).as_posix()
    return result

def concept_files():
    for key in ['men','women','youth']:
        raw=ROOT/f'assets/generated/concept-{key}.png'
        web=raw.with_suffix('.webp')
        if not raw.exists():raise FileNotFoundError(f'Concept artwork missing for {key}')
        if not web.exists() or raw.stat().st_mtime>web.stat().st_mtime:
            with Image.open(raw) as im:
                im=im.convert('RGB');im.thumbnail((1600,1100));im.save(web,'WEBP',quality=88,method=6)

def render_panel(obj,depth=3):
    if isinstance(obj,str):return p(obj)
    title=' '.join(str(obj[k]) for k in ['source_number','heading'] if obj.get(k)) or obj.get('label','')
    out=f'<h{min(depth,5)}>{esc(title)}</h{min(depth,5)}>' if title else ''
    texts=obj.get('text',[]);texts=texts if isinstance(texts,list) else [texts]
    out+=''.join(p(t,'text-source') for t in texts if t)
    for s in obj.get('speech',[]) or []:out+=f'<blockquote>{esc(s)}</blockquote>'
    labels=obj.get('scene_labels',[])+obj.get('image_labels',[])
    if labels:out+=p('In-image labels: '+' / '.join(labels),'caption')
    if obj.get('observed_scene'):out+=p('Scene: '+obj['observed_scene'],'scene-note')
    for sub in obj.get('subpanels',[]):out+=render_panel(sub,depth+1)
    return out

def render_misc(x):
    if not x:return ''
    if isinstance(x,str):return p(x)
    if isinstance(x,list):return ''.join(render_misc(v) for v in x)
    if isinstance(x,dict):return ''.join('<h4>'+esc(k.replace('_',' ').title())+'</h4>'+render_misc(v) for k,v in x.items())
    return p(x)

def library(cat,prov):
    cats=sorted(cat['topic_index'])
    out='<section class="section container" id="browse"><h2>Rummage through the originals</h2><div class="notice"><strong>Source archive. Original draft wording.</strong>These are Daz’s supplied drafts, with the readable wording transcribed for comparison and punctuation normalised for display. Medical, emergency and safety instructions have not been independently verified. Source errors are retained and flagged.</div>'
    out+='<div class="filters"><div class="field"><label for="library-search">Find a topic, tool or phrase</label><input id="library-search" type="search" placeholder="Try grinders, camp, parenting…"></div><div class="field"><label for="category-filter">Choose a collection</label><select id="category-filter"><option value="">All collections</option>'+''.join(f'<option>{esc(c)}</option>' for c in cats)+'</select></div></div><p class="results-count" id="results-count" aria-live="polite">45 slides</p><div class="library-list">'
    asset_map={r['slide']:r for r in prov['slides']}
    for rec in cat['slides']:
        n=rec['slide_number'];s=rec['source_record'];a=asset_map[n]
        out+=f'<details class="slide-entry" id="slide-{n}" data-category="{esc(rec["category"])}"><summary><span class="slide-number">{n:02}</span><span><h2>{esc(rec["topic"])}</h2><span class="summary-category">{esc(rec["category"])}</span></span><span class="expand-mark" aria-hidden="true">+</span></summary><div class="slide-content"><span class="tag">Original draft · slide {n}</span><div class="slide-layout">'
        if a.get('has_image'):
            out+=f'<div><img class="source-poster" src="{esc(a["reference_path"])}" width="{a["reference"]["width"]}" height="{a["reference"]["height"]}" alt="Daz’s original draft artwork for {esc(rec["topic"])}" loading="lazy"><div class="poster-actions"><button class="button" data-poster="{n}">Zoom poster</button><a class="button secondary" href="{esc(a["original_path"])}" download>Original file</a><a class="button secondary" href="library.html?slide={n}#compare">Compare copies</a></div><p class="caption">Optimised web copy shown. Exact original retained for provenance.</p></div>'
        else:out+='<div class="notice">Text-only slide. This is one of three alternative introductions.</div>'
        out+='<div class="transcript"><h3>'+esc(s['title'])+'</h3>'
        banner=s.get('subtitle_banner',s.get('subtitle'))
        out+=render_misc(banner)
        for pp in s.get('panels',[]):out+=render_panel(pp)
        if s.get('editable_text'):out+='<h3>Separate editable slide captions</h3>'+render_misc(s['editable_text'])
        ch=s.get('checklist')
        if isinstance(ch,dict):
            out+='<h3>'+esc(ch.get('heading','Checklist'))+'</h3>'
            for item in ch.get('items',[]):out+=render_panel(item,4)
        elif ch:out+=render_misc(ch)
        if s.get('footer'):out+='<h4>Source footer</h4>'+render_misc(s['footer'])
        if s.get('visible_issues'):out+='<details><summary>Source defects and unclear lettering</summary>'+ul(s['visible_issues'])+'</details>'
        out+='<details><summary>Image brief ingredients</summary>'+p('Layout: '+rec['pattern_id'])+ul(s.get('generation_notes',[]))+p('The JSON download contains the full source record and a separate draft image prompt for each scene.')+'</details>'
        out+='</div></div></div></details>'
    out+='</div><p id="empty-results" class="empty-state" hidden>No matching slides. Try a broader word or choose all collections.</p><div class="hero-actions">'+link('data/catalogue.json','Download the full catalogue','button')+link('data/content-catalogue.txt','Download the readable list','button secondary')+'</div></section>'
    return out

def posters(key,cat,prov):
    nums=SELECTED.get(key,[])
    if not nums:return ''
    am={r['slide']:r for r in prov['slides']};cm={r['slide_number']:r for r in cat['slides']}
    out='<section class="section container"><h2>From Daz’s original pile</h2>'+p('Original draft examples. Open the source record for readable text and source notes.')+'<div class="poster-row">'
    for n in nums:
        a=am[n];out+=f'<figure><a href="library.html#slide-{n}"><img src="{a["thumbnail_path"]}" loading="lazy" alt="Original draft: {esc(cm[n]["topic"])}" width="{a["thumbnail"]["width"]}" height="{a["thumbnail"]["height"]}"><figcaption>Slide {n:02} · {esc(cm[n]["topic"])}</figcaption></a><span class="tag">Original draft · unverified</span></figure>'
    return out+'</div>'+link('library.html','See all 45 slides','button')+'</section>'

def brief_form():
    return '''<section class="section container" id="brief-builder"><h2>Knock an idea into shape</h2><p>Start with the habit that gets on someone’s nerves. Fill this in and take the resulting brief to your image generator. Your entries stay in this browser until you copy or download them.</p><form id="brief-form" class="system-form"><div class="field"><label for="brief-audience">Who is this for?</label><select id="brief-audience"><option>Gift for a family member, friend or co-worker</option><option>Worker camp</option><option>Workshop or site communication</option><option>Young Crew / high school</option></select></div><div class="field"><label for="brief-edition">Edition / cast</label><select id="brief-edition"><option>Mixed cast</option><option>Men’s edition</option><option>Women’s edition</option><option>Young Crew</option></select></div><div class="field full"><label for="brief-habit">The habit or situation</label><textarea id="brief-habit" required placeholder="What keeps happening, and who has had enough?"></textarea></div><div class="field"><label for="brief-point">The useful hint</label><input id="brief-point" placeholder="One thing the reader should understand"></div><div class="field"><label for="brief-format">Format</label><select id="brief-format"><option>One picture + one sharp caption</option><option>Before and after</option><option>Four-scene comic</option><option>Workshop poster</option><option>Camp guide page</option><option>Picture-book spread</option><option>Sticker, magnet or small label</option><option>Newsletter or magazine illustration</option><option>Newspaper cartoon or comic strip</option><option>Animation storyboard</option><option>Comic storyboard for a comedy skit</option><option>Club mascot character sheet</option><option>Merchandise artwork</option><option>Task illustration beside a reviewed SWMS</option><option>Public-issue cartoon</option><option>Custom format: describe in the scene</option></select></div><div class="field full"><label for="brief-scene">The visual joke</label><textarea id="brief-scene" placeholder="People, action, props, setting and the moment that makes it funny"></textarea></div><div class="field"><label for="brief-angle">Comic angle (optional)</label><select id="brief-angle" aria-describedby="brief-angle-hint"><option value="">Still exploring</option><option value="observation">Everyday absurdity</option><option value="self">Tell the joke on yourself</option><option value="exchange">Short exchange or act-out</option><option value="status">Status reversal</option><option value="visual">Visual reveal</option></select><p id="brief-angle-hint" class="caption" aria-live="polite">Leave this open, or try an angle from Loose Goose.</p></div><div class="field"><label for="brief-alternative">Another version to try (optional)</label><textarea id="brief-alternative" placeholder="A different angle, ending or caption we could compare."></textarea></div><div class="field"><label for="brief-caption">Exact caption, if decided</label><input id="brief-caption"></div><div class="field"><label for="brief-check">Facts or site details to check</label><input id="brief-check" aria-describedby="brief-check-hint" placeholder="Source / reviewer / unresolved detail"><p id="brief-check-hint" class="caption">For a real story, distinguish what happened, what you remember and what you are guessing or exaggerating.</p></div><div class="full"><button class="button" type="submit">Build my image brief</button></div></form><div class="field" style="margin-top:1.5rem"><label for="brief-output">Your draft brief</label><textarea id="brief-output" class="brief-output" readonly placeholder="Your formatted brief will appear here."></textarea></div><div class="hero-actions"><button class="button" id="copy-brief">Copy brief</button><button class="button secondary" id="download-brief">Download brief</button></div><p id="brief-status" class="form-status" role="status"></p></section>'''

def comparison(prov):
    opts=''.join(f'<option value="{a["slide"]}">Slide {a["slide"]:02}</option>' for a in prov['slides'] if a.get('has_image'))
    summary=prov.get('summary',{})
    return '<section class="section container" id="compare"><h2>Original. Optimised. Traceable.</h2>'+p('Compare the original embedded JPEG with its web derivative. The originals retain their exact supplied bytes, including embedded metadata. Web copies are compressed for browsing; they have not been retouched or presented as new source art.')+'<div class="compare-controls"><div class="field"><label for="compare-slide">Choose a source slide</label><select id="compare-slide">'+opts+'</select></div><button id="load-comparison" class="button">Load comparison</button></div><p class="caption">Original files can be several megabytes. They load here only when you choose to compare.</p><div id="comparison-result" aria-live="polite"></div><div class="hero-actions">'+link('data/source-provenance.json','Download source provenance','button')+link('data/generated-art.json','New illustration prompts & provenance','button secondary')+link('LICENCE.md','Read the interim licence','button secondary')+'</div></section>'

def sample_gags(page,key):
    if not page.get('sample_gags'):return ''
    out='<section class="section container" id="sample-gags"><h2>A taste of the rough stuff</h2>'+p('New picture concepts in development. A familiar habit, a visual joke and a useful little nudge.')
    art={'men':('The Gym Opening Ceremony','A man launches a single exercise mat with an elaborate ribbon-cutting ceremony.'),'women':('The Chair Has Joined the Wardrobe','A woman and her mate survey a chair buried in clothes with its own tiny mailbox.'),'youth':('The Bag That Was Ready Yesterday','A teenager proudly heads out with a packed school bag while the lunchbox waits on the kitchen bench.')}
    if key in art:
        title,alt=art[key]
        with Image.open(ROOT/f'assets/generated/concept-{key}.webp') as im:width,height=im.size
        out+=f'<figure class="concept-figure"><img src="assets/generated/concept-{key}.webp" alt="{esc(alt)}" loading="lazy" width="{width}" height="{height}"><figcaption>{esc(title)} · New AI illustration concept</figcaption></figure>'
    for i,g in enumerate(page['sample_gags'],1):
        out+=f'<article class="gag"><span class="number">{i:02}</span><div><h3>{esc(g["title"])}</h3>{p(g["setup"])}{p(g["punchline"],"punchline")}{p("Picture idea: "+g["visual"],"caption")}<span class="tag">{esc(g["status"])}</span></div></article>'
    return out+'</section>'

def page_sections(page,key,heroes):
    out=sample_gags(page,key) if key in ['men','women','youth'] else ''
    for i,s in enumerate(page.get('sections',[])):
        if key=='home' and i==1:
            out+='<section class="section container" id="editions"><h2>A guide with someone’s name on it</h2><div class="edition-links">'
            for edition,label,desc in [('men','The blokes','Mates, partners, dads and the household wild card.'),('women','The women','Funny, capable, chaotic. Plenty of rough edges to go round.'),('youth','Young Crew','School-age life skills, without talking down.')]:
                out+=f'<a class="edition-link" href="{edition}.html"><img src="{heroes[edition]}" alt="" loading="lazy" width="640" height="480"><div><h3>{label}</h3><p>{desc}</p></div></a>'
            out+='</div></section>'
        anchor=' id="chapters"' if i==0 and key in ['men','women','youth'] else ''
        if s.get('id'):anchor=' id="'+esc(s['id'])+'"'
        out+='<section class="section container"'+anchor+'><div class="reading"><h2>'+esc(s['heading'])+'</h2>'+p(s.get('body',''))+ul(s.get('bullets',[]))
        if s.get('picture_idea'):out+='<details class="chapter-brief"><summary>Picture brief for this chapter</summary>'+p(s['picture_idea'],'scene-note')+'</details>'
        if s.get('links'):out+='<div class="hero-actions">'+''.join(link(item['url'],item['label'],'button secondary') for item in s['links'])+'</div>'
        out+='</div></section>'
    if key not in ['men','women','youth']:out+=sample_gags(page,key)
    return out

def pipeline(page):
    out='<section class="section container" id="product-routes"><h2>Possible formats</h2>'+p('Ideas for discussion: examples to develop, change or bin.')+'<nav class="jump-nav" aria-label="Product pipeline sections">'
    for anchor,label in [('formats','Formats & examples'),('wildcards','Country oddities'),('starter-routes','One idea, different versions')]:out+=link('#'+anchor,label)
    out+='</nav></section>'
    out+='<section class="section container" id="formats"><h2>Books, cartoons & other possibilities</h2>'+p('Open a format for a possible setting and an example of what we could make.')+'<div class="product-grid">'
    for i,item in enumerate(page['products'],1):
        out+=f'<article class="product-lane" id="product-{esc(item["id"])}"><span class="lane-number">{i:02}</span>'+p(item['format'],'format-label')+'<h3>'+esc(item['name'])+'</h3>'+p(item['example'])+'<details><summary>Premise, setting & sample</summary><dl><dt>The premise</dt><dd>'+esc(item['seed'])+'</dd><dt>Possible setting</dt><dd>'+esc(item['buyer_or_place'])+'</dd><dt>Sample version</dt><dd>'+esc(item['next_step'])+'</dd></dl>'
        if item.get('source_url'):out+=link(item['source_url'],'Safe Work Australia: SWMS guidance')+p(item['review_note'],'caption')
        out+='</details></article>'
    out+='</div></section>'
    out+='<section class="section container" id="wildcards"><span class="eyebrow">COUNTRY, OUTBACK & A BIT SIDEWAYS</span><h2>Open the other shed.</h2>'+p('A few stranger concepts for ag shows, country halls, roadhouses, camps and clubs.')+'<div class="wildcard-grid">'
    for item in page['wildcards']:
        out+='<article><h3>'+esc(item['title'])+'</h3>'+p(item['idea'])+p(item['visual'],'scene-note')+'<details><summary>Setting & sample</summary>'+p(item['setting'])+p(item['pilot'])+'</details></article>'
    out+='</div></section><section class="section container" id="starter-routes"><h2>One idea, different versions</h2><div class="route-list">'
    for i,item in enumerate(page['routes'],1):
        out+=f'<article><span class="lane-number">{i:02}</span><div><h3>{esc(item["title"])}</h3>'+ul(item['steps'])+p(item['note'],'scene-note')+'</div></article>'
    out+='</div><div id="production">'+link('systems.html#brief-builder','Image brief builder','button')+'</div></section>'
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--catalogue-source');args=ap.parse_args()
    if args.catalogue_source:portable_catalogue(Path(args.catalogue_source))
    content,cat,prov=load();heroes=hero_files();concept_files()
    art_path=ROOT/'data/generated-art.json'
    if art_path.exists():
        art=json.loads(art_path.read_text(encoding='utf-8'))
        for asset in art['assets']:
            web=ROOT/Path(asset['path']).with_suffix('.webp')
            if web.exists():
                asset['web_derivative']={'path':web.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(web.read_bytes()).hexdigest(),'bytes':web.stat().st_size,'encoding':'WebP quality 88, same composition, no retouching','derived_from':asset['path']}
        art_path.write_text(json.dumps(art,ensure_ascii=False,indent=2),encoding='utf-8')
    readable=ROOT/'data/content-catalogue.txt'
    if args.catalogue_source:
        source=Path(args.catalogue_source).with_name('Rough-as-Guts-complete-content-catalogue.txt')
        text=source.read_text(encoding='utf-8-sig')
        text=re.sub(r'G:\\GithubLocal-PC\\rough-as-guts-meeting\\review\\(slide-\d+\.[a-z]+)',r'assets/originals/\1',text)
        text=text.replace(str(Path(r'L:\Downloads after 20_09_22\Rough-as-guts.pptx')),'Rough-as-guts.pptx (retained source file)')
        readable.write_text(text,encoding='utf-8')
    script_version=hashlib.sha256((ROOT/'site.js').read_bytes()).hexdigest()[:12]
    for idx,(key,filename,label) in enumerate(PAGES):
        page=content[key];nav=''.join(f'<a href="{f}"'+(' aria-current="page"' if k==key else '')+f'>{esc(l)}</a>' for k,f,l in PAGES if k in ['men','women','youth','workplace','library','systems','pipeline'])
        footer_nav=''.join(link(f,l) for k,f,l in PAGES)
        prev=PAGES[(idx-1)%len(PAGES)];nxt=PAGES[(idx+1)%len(PAGES)]
        head=f'''<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(label)} · Rough as Guts</title><meta name="description" content="{esc(page['lead'])}"><meta name="theme-color" content="#ffd52a"><link rel="canonical" href="{BASE+filename}"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="styles.css"><meta property="og:title" content="{esc(label)} · Rough as Guts"><meta property="og:description" content="{esc(page['lead'])}"><meta property="og:type" content="website"><meta property="og:url" content="{BASE+filename}"><meta property="og:image" content="{BASE+heroes[key]}"><meta name="twitter:card" content="summary_large_image"><script src="site.js?v={script_version}" defer></script></head><body data-page="{key}"><a class="skip-link" href="#main">Skip to content</a><header class="site-header"><a class="brand" href="index.html">ROUGH AS GUTS<small>GOOD LAUGHS. USEFUL HINTS.</small></a><button class="menu-toggle" aria-controls="main-nav" aria-expanded="false">Menu</button><nav id="main-nav" class="main-nav" aria-label="Main navigation">{nav}</nav><div class="read-tools" role="group" aria-label="Text size"><button id="text-smaller" aria-label="Smaller text">A−</button><button id="text-reset" aria-label="Reset text size">A</button><button id="text-larger" aria-label="Larger text">A+</button></div></header><main id="main"><section class="hero"><img class="hero-image" src="{heroes[key]}" alt="{esc(page['heroAlt'])}" fetchpriority="high" width="1536" height="1024"><div class="hero-copy"><span class="eyebrow">{esc(page['eyebrow'])}</span><h1>{HERO_TITLES[key]}</h1><p class="lead">{esc(page['lead'])}</p><div class="hero-actions">'''
        if key=='home':head+=link('#editions','Find their edition','button')+link('library.html','Rummage through the originals','button secondary')
        elif key=='library':head+=link('#browse','Browse all 45 slides','button')+link('#compare','Compare source copies','button secondary')
        elif key=='systems':head+=link('#brief-builder','Build an image brief','button')+link('#loose-goose','Loose Goose comedy prompts','button secondary')
        elif key=='pipeline':head+=link('#formats','Explore the product range','button')+link('#wildcards','Try the weird stuff','button secondary')
        elif key in ['men','women','youth']:head+=link('#sample-gags','Get a taste','button')+link('#chapters','Inside the edition','button secondary')
        else:head+=link('#inside','Have a look','button')+link('systems.html','Make a new page','button secondary')
        head+='</div></div></section><div class="shout-strip">'+('Small moves. More independence. A decent laugh.' if key=='youth' else 'Big pictures. Plain talk. A useful bloody hint.')+'</div>'
        body=f'<div class="container intro reading" id="inside">{p(page["title"],"big-quote")}{p(page["intro"])}</div>'
        if key=='pipeline':body+=pipeline(page)
        else:body+=page_sections(page,key,heroes)
        if key=='home':body+='<section class="section container"><h2>What else could it become?</h2>'+p('Picture books, posters, cartoons, skits, stickers, animation, club mascots and a few ideas best discussed near a shed.')+link('pipeline.html','Explore the product pipeline','button')+'</section>'
        if key=='library':
            body+=library(cat,prov)+comparison(prov)+'<section class="section container"><h2>Source records & rights</h2>'+p('Darryl Gough supplied the concept and original draft artwork. Luke Nathan Hayes is developing the wider guides, editorial system and website. Original files, readable transcripts and new illustration prompts remain available together here.')+link('LICENCE-NOTICE.md','Source rights and interim licence notice','button secondary')+'</section>'
        if key=='workplace':body+='<section class="section container"><h2>SWMS, in plain English</h2>'+p('SWMS stands for Safe Work Method Statement. Safe Work Australia describes its role in high-risk construction work: identifying the activities, hazards and risk controls. Humorous illustration can support clear communication, while the actual task and site details belong in the reviewed document.')+link('https://www.safeworkaustralia.gov.au/duties-tool/construction/hazards-information/high-risk-construction-work-requiring-swms','Read Safe Work Australia’s SWMS guidance')+'</section>'
        if key=='systems':
            body+=brief_form()+'<section class="section container pattern-list"><h2>Borrow a visual pattern</h2>'
            for pat in cat['layout_patterns'].values():body+='<details><summary>'+esc(pat['name'])+'</summary>'+p(pat['observed_structure'])+p(pat['generator_template'],'scene-note')+'</details>'
            body+='</section>'
        if key=='sitemap':
            body+='<section class="section container"><h2>Every page</h2><ul class="sitemap-list">'+''.join('<li>'+link(f,l)+p(content[k]['lead'])+'</li>' for k,f,l in PAGES)+'</ul><h3>Downloads</h3>'+ul([])+link('data/catalogue.json','Complete structured catalogue')+'<br>'+link('data/content-catalogue.txt','Readable catalogue')+'<br>'+link('data/source-provenance.json','Original-image provenance')+'<br>'+link('data/generated-art.json','New-image prompts and provenance')+'</section>'
        if key in SELECTED:body+=posters(key,cat,prov)
        foot=f'''</main><footer class="site-footer"><div class="container page-turner"><a href="{prev[1]}"><span>Previous page</span>← {esc(prev[2])}</a><a href="{nxt[1]}"><span>Next page</span>{esc(nxt[2])} →</a></div><div class="container footer-main"><p class="footer-brand">Rough as guts.</p><nav class="footer-nav" aria-label="Footer navigation">{footer_nav}</nav><p class="footer-note">Concept and original drafts: Darryl Gough. Site and wider development: Luke Nathan Hayes / Aura of Intelligence. Guides and sample editions in development. Original archive safety wording is unverified source material. <a href="LICENCE.md">Interim Strange But True Public Source Licence</a> · <a href="LICENCE-NOTICE.md">Source rights and licence notice</a> · <a href="https://github.com/auraofintelligence/rough-as-guts">GitHub source</a></p></div></footer><button class="back-top" id="back-top" aria-label="Back to top" hidden>↑ Top</button><dialog class="poster-dialog" id="poster-dialog" aria-labelledby="poster-dialog-title"><div class="dialog-bar"><span class="dialog-title" id="poster-dialog-title">Source poster</span><button id="poster-zoom-out" aria-label="Zoom out">−</button><button id="poster-zoom-in" aria-label="Zoom in">+</button><button id="poster-close">Close</button></div><div class="dialog-body"><img id="dialog-poster" alt=""></div></dialog></body></html>'''
        (ROOT/filename).write_text(head+body+foot,encoding='utf-8')
    legacy='''<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Source comparison moved · Rough as Guts</title><link rel="canonical" href="'''+BASE+'''library.html#compare"><script>const target=new URL('library.html',location.href);target.search=location.search;target.hash='compare';location.replace(target.href);</script></head><body><h1>Source comparison is in the original library</h1><p><a href="library.html#compare">Open source comparison and licence records</a></p></body></html>'''
    (ROOT/'provenance.html').write_text(legacy,encoding='utf-8')
    urls=''.join(f'<url><loc>{BASE+f}</loc></url>' for _,f,_ in PAGES)
    (ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+urls+'</urlset>',encoding='utf-8')
    (ROOT/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+BASE+'sitemap.xml\n',encoding='utf-8')
    print('Built',len(PAGES),'pages; unique hero files:',len(set(heroes.values())))

if __name__=='__main__':main()
