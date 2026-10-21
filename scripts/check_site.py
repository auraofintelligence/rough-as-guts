from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import json,re,hashlib

ROOT=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=[];self.heroes=[];self.h1=0;self.has_viewport=False;self.images=[];self.canonical=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='h1':self.h1+=1
        if tag=='meta' and a.get('name')=='viewport':self.has_viewport=True
        if tag=='img':
            self.images.append(a)
            if a.get('class')=='hero-image':self.heroes.append(a.get('src'))
        if tag=='link' and a.get('rel')=='canonical':self.canonical.append(a.get('href'))
        for key in ['href','src']:
            if key in a:self.links.append(a[key])

errors=[];parsers={}
files=list(ROOT.glob('*.html'))
for file in files:
    parser=Page();parser.feed(file.read_text(encoding='utf-8'));parsers[file.name]=parser
    if parser.h1!=1:errors.append(f'{file.name}: expected one h1')
    if not parser.has_viewport:errors.append(f'{file.name}: no viewport')
    if len(parser.heroes)!=1:errors.append(f'{file.name}: hero missing')
    if len(parser.ids)!=len(set(parser.ids)):errors.append(f'{file.name}: duplicate IDs')
    for image in parser.images:
        if 'alt' not in image:errors.append(f'{file.name}: image missing alt')
    for url in parser.links:
        split=urlsplit(url)
        if split.scheme or url.startswith('//'):continue
        path=ROOT/unquote(split.path or file.name)
        if not path.exists():errors.append(f'{file.name}: missing {url}')
        if split.fragment and path.suffix=='.html':
            target=Page();target.feed(path.read_text(encoding='utf-8'))
            if unquote(split.fragment) not in target.ids:errors.append(f'{file.name}: missing anchor {url}')
if len(files)!=9:errors.append(f'Expected 9 pages, got {len(files)}')
heroes=[p.heroes[0] for p in parsers.values() if p.heroes]
if len(set(heroes))!=9:errors.append('Heroes must be unique for every page')
provenance=json.loads((ROOT/'data/source-provenance.json').read_text(encoding='utf-8'))
catalogue=json.loads((ROOT/'data/catalogue.json').read_text(encoding='utf-8'))
if [r['slide_number'] for r in catalogue['slides']]!=list(range(1,46)):errors.append('Catalogue coverage')
for record in provenance['slides']:
    if not record.get('has_image'):continue
    for kind in ['original','reference','thumbnail']:
        asset=record[kind];file=ROOT/asset['path']
        if hashlib.sha256(file.read_bytes()).hexdigest()!=asset['sha256']:errors.append(f'Asset hash mismatch {file.name}')
license_source=Path(r'G:\GithubLocal-PC\strange-but-true\LICENCE.md')
if license_source.exists() and license_source.read_bytes()!=(ROOT/'LICENCE.md').read_bytes():errors.append('Interim licence differs from requested original')
all_js=(ROOT/'site.js').read_text(encoding='utf-8')
if re.search(r'\bfetch\(["\']https?://',all_js):errors.append('Unexpected external data request')
report={'pages':len(files),'unique_heroes':len(set(heroes)),'source_slides':len(catalogue['slides']),'original_images':sum(bool(r.get('has_image')) for r in provenance['slides']),'checked_assets':126,'errors':errors}
print(json.dumps(report,indent=2))
raise SystemExit(1 if errors else 0)
