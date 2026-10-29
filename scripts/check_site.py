from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import json,re,hashlib

ROOT=Path(__file__).resolve().parents[1]
PRIMARY_PAGES={
    'index.html','men.html','women.html','youth.html','workplace.html',
    'library.html','systems.html','pipeline.html','sitemap.html'
}
LEGACY_PAGE='provenance.html'
MAIN_NAV={'men.html','women.html','youth.html','workplace.html','library.html','systems.html','pipeline.html'}
class Page(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=[];self.heroes=[];self.h1=0;self.has_viewport=False;self.images=[];self.canonical=[];self.main_nav=[];self.in_main_nav=False;self.controls={}
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='nav' and a.get('id')=='main-nav':self.in_main_nav=True
        if tag=='a' and self.in_main_nav:self.main_nav.append(a.get('href',''))
        if 'id' in a:self.ids.append(a['id'])
        if tag=='h1':self.h1+=1
        if tag=='meta' and a.get('name')=='viewport':self.has_viewport=True
        if tag=='img':
            self.images.append(a)
            if a.get('class')=='hero-image':self.heroes.append(a.get('src'))
        if tag in ['input','select','textarea'] and a.get('id'):self.controls[a['id']]=a
        if tag=='link' and a.get('rel')=='canonical':self.canonical.append(a.get('href'))
        for key in ['href','src']:
            if key in a:self.links.append(a[key])
    def handle_endtag(self,tag):
        if tag=='nav':self.in_main_nav=False

errors=[];parsers={}
files=list(ROOT.glob('*.html'))
expected_pages=PRIMARY_PAGES|{LEGACY_PAGE}
actual_pages={file.name for file in files}
if actual_pages!=expected_pages:
    errors.append(f'Page set mismatch: missing {sorted(expected_pages-actual_pages)}, unexpected {sorted(actual_pages-expected_pages)}')
for file in files:
    parser=Page();parser.feed(file.read_text(encoding='utf-8'));parsers[file.name]=parser
    if file.name in PRIMARY_PAGES:
        if parser.h1!=1:errors.append(f'{file.name}: expected one h1')
        if len(parser.heroes)!=1:errors.append(f'{file.name}: hero missing')
        if not MAIN_NAV.issubset(set(parser.main_nav)):errors.append(f'{file.name}: main navigation missing {sorted(MAIN_NAV-set(parser.main_nav))}')
        if LEGACY_PAGE in parser.main_nav:errors.append(f'{file.name}: legacy redirect appears in main navigation')
    if not parser.has_viewport:errors.append(f'{file.name}: no viewport')
    if len(parser.ids)!=len(set(parser.ids)):errors.append(f'{file.name}: duplicate IDs')
    for image in parser.images:
        if 'alt' not in image:errors.append(f'{file.name}: image missing alt')
    for url in parser.links:
        split=urlsplit(url)
        if split.scheme or url.startswith('//'):continue
        path=ROOT/unquote(split.path or file.name)
        if not path.exists():errors.append(f'{file.name}: missing {url}')
        if split.fragment and path.suffix=='.html' and path.exists():
            target=Page();target.feed(path.read_text(encoding='utf-8'))
            if unquote(split.fragment) not in target.ids:errors.append(f'{file.name}: missing anchor {url}')
heroes=[parsers[name].heroes[0] for name in PRIMARY_PAGES if name in parsers and parsers[name].heroes]
if len(set(heroes))!=len(PRIMARY_PAGES):errors.append('Heroes must be unique for all nine primary pages')
legacy=parsers.get(LEGACY_PAGE)
if legacy:
    legacy_text=(ROOT/LEGACY_PAGE).read_text(encoding='utf-8')
    if legacy.heroes or legacy.main_nav:errors.append('Legacy provenance page must have no hero or main navigation')
    if not all(token in legacy_text for token in ['library.html','compare']):errors.append('Legacy provenance page must redirect to library comparison')
    if not any(token in legacy_text for token in ['location.search','URLSearchParams']):errors.append('Legacy redirect must preserve the requested source slide')
library_page=parsers.get('library.html')
if library_page and 'compare' not in library_page.ids:errors.append('Source comparison must be on the library page')
site_map=parsers.get('sitemap.html')
if site_map and any(urlsplit(link).path==LEGACY_PAGE for link in site_map.links):errors.append('Legacy provenance page must not appear in site map')
sitemap_xml=(ROOT/'sitemap.xml').read_text(encoding='utf-8')
if LEGACY_PAGE in sitemap_xml:errors.append('Legacy provenance page must not appear in XML sitemap')
provenance=json.loads((ROOT/'data/source-provenance.json').read_text(encoding='utf-8'))
catalogue=json.loads((ROOT/'data/catalogue.json').read_text(encoding='utf-8'))
if [r['slide_number'] for r in catalogue['slides']]!=list(range(1,46)):errors.append('Catalogue coverage')
source_paths={asset['path']:record['slide'] for record in provenance['slides'] if record.get('has_image') for asset in [record['original'],record['reference'],record['thumbnail']]}
expected_sources={'index.html':{11,26},'workplace.html':{24,30,44},'library.html':{record['slide'] for record in provenance['slides'] if record.get('has_image')}}
for name,parser in parsers.items():
    shown_sources={source_paths[urlsplit(image.get('src','')).path] for image in parser.images if urlsplit(image.get('src','')).path in source_paths}
    if shown_sources!=expected_sources.get(name,set()):errors.append(f'{name}: unexpected original-source image placement {sorted(shown_sources)}')
for edition in ['men','women','youth']:
    page=parsers.get(edition+'.html')
    concept=f'assets/generated/concept-{edition}-care-v2.webp'
    if page and not any(image.get('src')==concept for image in page.images):errors.append(f'{edition}.html: new inline concept illustration missing')
for edition in ['men','women','workplace']:
    page=parsers.get(edition+'.html')
    hero=f'assets/generated/hero-{edition}-care-v2.webp'
    if page and page.heroes!=[hero]:errors.append(f'{edition}.html: revised care-focused hero missing')
content=json.loads((ROOT/'data/site-content.json').read_text(encoding='utf-8'))
headings={edition:{section['heading'].strip().casefold() for section in content[edition]['sections']} for edition in ['men','women']}
if headings['men']&headings['women']:errors.append('Men and women must have distinct chapter headings')
def require_text_fields(item,fields,location):
    for field in fields:
        if not isinstance(item.get(field),str) or not item[field].strip():errors.append(f'{location}: missing or empty {field}')
gag_count=0
for key,page_content in content.items():
    for index,gag in enumerate(page_content.get('sample_gags',[]),1):
        require_text_fields(gag,['try_this','benefit'],f'{key} sample gag {index}')
        gag_count+=1
for key in ['home','workplace']:
    if not content[key].get('sample_gags'):errors.append(f'{key}: improvement examples missing')
edition_section_count=0
for key in ['men','women','youth']:
    for index,section in enumerate(content[key].get('sections',[]),1):
        require_text_fields(section,['try_this','benefit'],f'{key} section {index}')
        edition_section_count+=1
if edition_section_count!=14:errors.append(f'Expected 14 edition sections, got {edition_section_count}')
products=content['pipeline'].get('products',[])
wildcards=content['pipeline'].get('wildcards',[])
if len(products)!=18:errors.append(f'Expected 18 product formats, got {len(products)}')
if len(wildcards)!=7:errors.append(f'Expected 7 country concepts, got {len(wildcards)}')
for index,product in enumerate(products,1):require_text_fields(product,['try_this','benefit','check_question'],f'Product {index}')
for index,wildcard in enumerate(wildcards,1):require_text_fields(wildcard,['try_this','benefit'],f'Country concept {index}')
systems_page=parsers.get('systems.html')
if systems_page:
    if 'required' not in systems_page.controls.get('brief-point',{}):errors.append('The brief must require a better action and its purpose')
    for control in ['brief-angle','brief-alternative']:
        if control not in systems_page.controls:errors.append(f'Systems form is missing {control}')
        elif 'required' in systems_page.controls[control]:errors.append(f'{control} must remain optional')
historical_art=[f'assets/generated/hero-{key}.png' for key in ['men','women','workplace']]+[f'assets/generated/concept-{key}.png' for key in ['men','women','youth']]
for asset in historical_art:
    if not (ROOT/asset).exists():errors.append(f'Historical illustration source missing: {asset}')
checked_assets=0
for record in provenance['slides']:
    if not record.get('has_image'):continue
    for kind in ['original','reference','thumbnail']:
        asset=record[kind];file=ROOT/asset['path']
        checked_assets+=1
        if not file.exists():errors.append(f'Source asset missing {asset["path"]}')
        elif hashlib.sha256(file.read_bytes()).hexdigest()!=asset['sha256']:errors.append(f'Asset hash mismatch {file.name}')
license_source=Path(r'G:\GithubLocal-PC\strange-but-true\LICENCE.md')
if license_source.exists() and license_source.read_bytes()!=(ROOT/'LICENCE.md').read_bytes():errors.append('Interim licence differs from requested original')
all_js=(ROOT/'site.js').read_text(encoding='utf-8')
if re.search(r'\bfetch\(["\']https?://',all_js):errors.append('Unexpected external data request')
binary_suffixes={'.png','.jpg','.jpeg','.webp','.gif','.ico','.pptx','.pdf','.zip','.woff','.woff2'}
for file in ROOT.rglob('*'):
    if not file.is_file() or '.git' in file.relative_to(ROOT).parts or file==ROOT/'LICENCE.md' or file.suffix.lower() in binary_suffixes:continue
    try:text=file.read_text(encoding='utf-8')
    except UnicodeDecodeError:continue
    if chr(0x2014) in text:errors.append(f'Em dash in site text: {file.relative_to(ROOT).as_posix()}')
report={'pages':len(files),'primary_pages':len(actual_pages&PRIMARY_PAGES),'legacy_redirects':int(LEGACY_PAGE in actual_pages),'unique_heroes':len(set(heroes)),'source_slides':len(catalogue['slides']),'original_images':sum(bool(r.get('has_image')) for r in provenance['slides']),'checked_assets':checked_assets,'gags_with_improvement':gag_count,'edition_sections_with_improvement':edition_section_count,'product_formats':len(products),'country_concepts':len(wildcards),'errors':errors}
print(json.dumps(report,indent=2))
raise SystemExit(1 if errors else 0)
