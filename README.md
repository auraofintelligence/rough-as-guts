# Rough as Guts

A bold, readable illustrated-guide prototype built around **joyful responsible abundance**: light satire that invites safer, healthier and more considerate habits, with more room to enjoy life together.

Website: https://auraofintelligence.github.io/rough-as-guts/

Concept and supplied draft artwork: Darryl Gough (Daz). Wider guide development, editorial systems and website: Luke Nathan Hayes / Aura of Intelligence.

## Pages

- Home
- Men's editions
- Women's editions
- Young Crew (high-school-age life skills)
- Worksites and worker camps
- Habit ideas: 190 bad-habit/useful-response pairs across 17 areas, including gardening and emergency preparedness
- Original 45-slide library, with searchable readable transcripts
- Editorial system and browser-local image-brief builder
- Product pipeline, from an observation to an illustrated guide or workplace format
- Site map

These are the ten primary pages. Habit Ideas, Systems and Product Pipeline are available in the main navigation. The old `provenance.html` address redirects to the source comparison on `library.html`, preserving a requested slide. It has no hero and is excluded from navigation and the sitemap.

The site is static HTML, CSS and JavaScript, with no accounts, analytics, external fonts or server-side collection. It supports phones and laptops, adjustable text size, keyboard navigation, reduced motion, lazy-loaded posters, poster zoom, footer navigation and previous/next links. Each primary page has its own hero illustration.

The men's and women's editions have distinct situations and chapters. New examples show a recognisable habit, a better action the person can take and a shared benefit. The person in the joke can learn, contribute and belong. Gifts offer encouragement and a way to discuss change. Young Crew uses school-appropriate situations, practical agency and room to ask for help, without making a child's family circumstances the joke.

These are editorial drafts. The site records proposed useful actions and questions to explore with intended readers; it does not claim that an illustration or joke has been shown to change behaviour. The source review and editorial correction are documented in [the 28 October 2026 review](docs/editorial-review-2026-10-28.md).

## Source archive and new illustrations

`assets/originals/` preserves all 42 images extracted from the supplied 45-slide PowerPoint byte-for-byte, including metadata. The PowerPoint itself is retained outside this repository because it exceeds GitHub's normal single-file limit.

`assets/references/` contains full-dimension WebP web copies and `assets/thumbnails/` contains smaller gallery previews. `data/source-provenance.json` links the original files, source slide and internal PowerPoint media path, hashes, dimensions, compression settings and metadata observations. Marker detection does not validate C2PA signatures.

The original source artwork appears in three places: home uses slides 11 and 26; Worksites uses slides 24, 30 and 44; the library contains all 45 source records and the 42 embedded images. The original-versus-web-copy comparison is on the library page. The other primary pages use new illustrations. Curation illustrates communication patterns; it does not independently validate the source's technical claims.

`assets/generated/` contains new hero artwork and inline concept illustrations. The revised men's, women's and workplace heroes use `hero-*-care-v2`; the men's, women's and Young Crew concepts use `concept-*-care-v2`. These six revisions show care, a useful response or a positive result. Their earlier PNG sources remain available as historical artwork, alongside PNG sources and WebP copies of the revisions. `data/generated-art.json` records prompts and file hashes. New illustrations are distinct from Daz's protected source archive.

`data/catalogue.json` retains the complete transcribed slide content and separate visual scene briefs. `data/content-catalogue.txt` is the readable companion. Source errors and uncertain lettering are retained and flagged. The source archive is draft material, not a validated safety or medical manual.

## Systems and product pipeline

Habit Ideas preserves the original 150 pairs and adds 20 gardening and 20 emergency preparedness ideas. Search, an area filter and topic links help readers browse the list on phone or laptop. Every pair stays visible without JavaScript. `data/habit-ideas.json` is the structured source; the build also creates a readable `data/habit-ideas.txt` download. Gardening links to Queensland waterwise guidance. Preparedness links to Get Ready Queensland planning, kit and animal resources. These are candidate teaching scenes, with current local official guidance supporting practical decisions. The page has its own hero and a new garden planning comic, recorded in the artwork manifest.

Systems provides the editorial workflow, visual patterns, Loose Goose comedy prompts and a browser-local image-brief builder. The existing useful-point field is now required as "Better action & why it helps". The two optional additions remain a comic-angle choice and another version to try. The resulting brief asks for the better action and its benefit to appear in the proposed image or sequence.

Product Pipeline explores 18 formats and seven country concepts. Each has a visible improvement pathway and a possible shared benefit; the product entries also include a question for checking the idea with intended readers. These remain options to develop, change or discard, with no claimed audience response or commercial ranking. Workplace and SWMS illustrations require review against the actual task, equipment, conditions and responsible work method.

## Rebuild

Install Python and Pillow. Edit `data/site-content.json`, then run:

```text
python scripts/build_site.py
python scripts/check_site.py
python -m http.server 8765
```

The check covers the ten primary pages and legacy redirect, unique and revised heroes, local links and anchors, source-image placement, revised inline illustrations, distinct edition headings, source hashes and the unchanged interim licence. It also checks for nonempty better-action and benefit fields in new gags, all 14 edition sections, the 18 product formats and seven country concepts. The habit bank is checked for 190 complete, consecutively numbered pairs across 17 areas and matching page anchors. The form's better-action field must be required while its two comedy controls remain optional. Site text is checked for em dashes, with the exact `LICENCE.md` and binary assets excluded. These checks verify structure and source integrity; reader interpretation and task accuracy still need appropriate review.

Regenerating the source archive requires the original PowerPoint and the extraction manifest. `scripts/prepare-source-assets.py --help` describes those inputs. It is not needed to view or publish the already-built static site.

GitHub Pages publishes the root of the `main` branch. `.nojekyll` keeps it buildless. Links and assets use relative paths so the project works under `/rough-as-guts/`.

## Licence

The existing Strange But True Public Source Licence is copied unchanged as the requested interim licence. It is not an open-source licence. The separate `LICENCE-NOTICE.md` explains source credits, retained rights and the shared licence still to come. No new ownership arrangement is asserted.
