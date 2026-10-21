# Rough as Guts

A bold, readable illustrated-guide prototype for gifts, everyday competence, worker camps and site communication.

Website: https://auraofintelligence.github.io/rough-as-guts/

Concept and supplied draft artwork: Darryl Gough (Daz). Wider guide development, editorial systems and website: Luke Nathan Hayes / Aura of Intelligence.

## Pages

- Home
- Men's editions
- Women's editions
- Young Crew (high-school-age life skills)
- Worksites and worker camps
- Original 45-slide library, with searchable readable transcripts
- Editorial system and browser-local image-brief builder
- Origins, source comparison and interim licence
- Site map

The site is static HTML, CSS and JavaScript, with no accounts, analytics, external fonts or server-side collection. It supports phones and laptops, adjustable text size, keyboard navigation, reduced motion, lazy-loaded posters, poster zoom, footer navigation and previous/next links.

## Source archive and new illustrations

`assets/originals/` preserves all 42 images extracted from the supplied 45-slide PowerPoint byte-for-byte, including metadata. The PowerPoint itself is retained outside this repository because it exceeds GitHub's normal single-file limit.

`assets/references/` contains full-dimension WebP web copies and `assets/thumbnails/` contains smaller gallery previews. `data/source-provenance.json` links the original files, source slide and internal PowerPoint media path, hashes, dimensions, compression settings and metadata observations. Marker detection does not validate C2PA signatures.

`assets/generated/` contains new hero artwork. `data/generated-art.json` records the prompts and source file hashes. New illustrations are distinct from Daz's source archive.

`data/catalogue.json` retains the complete transcribed slide content and separate visual scene briefs. `data/content-catalogue.txt` is the readable companion. Source errors and uncertain lettering are retained and flagged. The source archive is draft material, not a validated safety or medical manual.

## Rebuild

Install Python and Pillow. Edit `data/site-content.json`, then run:

```text
python scripts/build_site.py
python scripts/check_site.py
python -m http.server 8765
```

Regenerating the source archive requires the original PowerPoint and the extraction manifest. `scripts/prepare-source-assets.py --help` describes those inputs. It is not needed to view or publish the already-built static site.

GitHub Pages publishes the root of the `main` branch. `.nojekyll` keeps it buildless. Links and assets use relative paths so the project works under `/rough-as-guts/`.

## Licence

The existing Strange But True Public Source Licence is copied unchanged as the requested interim licence. It is not an open-source licence. The separate `LICENCE-NOTICE.md` explains source credits, retained rights and the shared licence still to come. No new ownership arrangement is asserted.
