'use strict';
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const menu = $('.menu-toggle');
menu?.addEventListener('click', () => {
  const open = menu.getAttribute('aria-expanded') !== 'true';
  menu.setAttribute('aria-expanded', String(open));
  $('#main-nav').classList.toggle('is-open', open);
});
let scale = 1;
try { scale = Math.min(1.4, Math.max(.9, Number(localStorage.getItem('rag-text-scale')) || 1)); } catch {}
function applyScale() {
  document.documentElement.style.setProperty('--scale', scale.toFixed(2));
  try { localStorage.setItem('rag-text-scale', String(scale)); } catch {}
}
applyScale();
$('#text-larger')?.addEventListener('click', () => { scale = Math.min(1.4, scale + .1); applyScale(); });
$('#text-smaller')?.addEventListener('click', () => { scale = Math.max(.9, scale - .1); applyScale(); });
$('#text-reset')?.addEventListener('click', () => { scale = 1; applyScale(); });
const topButton = $('#back-top');
const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
function updateTop() { topButton.hidden = window.scrollY < 500; }
window.addEventListener('scroll', updateTop, { passive: true });
topButton?.addEventListener('click', () => window.scrollTo({ top: 0, behavior: motionQuery.matches ? 'instant' : 'smooth' }));
updateTop();

const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
let provenancePromise;
function getProvenance() {
  return provenancePromise ??= fetch('data/source-provenance.json').then(r => { if (!r.ok) throw new Error('Source index could not be loaded.'); return r.json(); });
}

const search = $('#library-search');
const filter = $('#category-filter');
const entries = $$('.slide-entry');
if (search) {
  const searchable = entries.map(el => ({ el, text: el.textContent.toLowerCase() }));
  function updateLibrary() {
    const terms = search.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    let visible = 0;
    searchable.forEach(({el, text}) => {
      const match = (!filter.value || el.dataset.category === filter.value) && terms.every(term => text.includes(term));
      el.hidden = !match; if (match) visible++;
    });
    $('#results-count').textContent = `${visible} of 45 slides`;
    $('#empty-results').hidden = visible > 0;
  }
  search.addEventListener('input', updateLibrary);
  filter.addEventListener('change', updateLibrary);
  const query = new URLSearchParams(location.search).get('q');
  if (query) { search.value = query; updateLibrary(); }
  function openHash() {
    if (!/^#slide-\d+$/.test(location.hash)) return;
    const target = $(location.hash);
    if (!target) return;
    search.value = ''; filter.value = ''; updateLibrary();
    target.open = true; target.scrollIntoView({ block: 'start' });
  }
  window.addEventListener('hashchange', openHash); openHash();
}

const dialog = $('#poster-dialog');
const posterImage = $('#dialog-poster');
let posterZoom = 1;
let posterTrigger = null;
function setZoom(value) { posterZoom = Math.min(3, Math.max(1, value)); posterImage.style.width = `${posterZoom * 100}%`; }
$$('[data-poster]').forEach(button => button.addEventListener('click', async () => {
  try {
    const data = await getProvenance();
    const record = data.slides.find(s => s.slide === Number(button.dataset.poster));
    if (!record?.has_image) return;
    posterTrigger = button;
    posterImage.src = record.reference_path;
    posterImage.alt = `Optimised copy of original source artwork, slide ${record.slide}`;
    $('#poster-dialog-title').textContent = `Original draft · slide ${record.slide}`;
    setZoom(1); dialog.showModal(); $('#poster-close').focus();
  } catch (error) { button.textContent = 'Could not load. Try the original file.'; }
}));
$('#poster-zoom-in')?.addEventListener('click', () => setZoom(posterZoom + .25));
$('#poster-zoom-out')?.addEventListener('click', () => setZoom(posterZoom - .25));
$('#poster-close')?.addEventListener('click', () => dialog.close());
dialog?.addEventListener('close', () => posterTrigger?.focus());
dialog?.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });

const compareSelect = $('#compare-slide');
if (compareSelect) {
  const selected = new URLSearchParams(location.search).get('slide');
  if ([...compareSelect.options].some(o => o.value === selected)) compareSelect.value = selected;
  $('#load-comparison').addEventListener('click', async () => {
    const area = $('#comparison-result');
    area.textContent = 'Loading the selected source comparison…';
    try {
      const data = await getProvenance();
      const record = data.slides.find(s => s.slide === Number(compareSelect.value));
      const kb = bytes => `${(bytes / 1024 / 1024).toFixed(2)} MB`;
      area.innerHTML = `<div class="compare-grid"><figure><img src="${escapeHTML(record.original_path)}" alt="Byte-identical original source, slide ${record.slide}"><figcaption>Original embedded file · ${kb(record.original.bytes)}</figcaption><p class="hash">SHA-256: ${escapeHTML(record.original_sha256)}</p><a href="${escapeHTML(record.original_path)}" download>Download exact original</a></figure><figure><img src="${escapeHTML(record.reference_path)}" alt="Optimised WebP derivative, slide ${record.slide}"><figcaption>Optimised web copy · ${kb(record.reference.bytes)}</figcaption><p class="hash">SHA-256: ${escapeHTML(record.derivative_sha256)}</p><a href="${escapeHTML(record.reference_path)}" download>Download web copy</a></figure></div><div class="notice"><strong>Same source artwork. Different file encodings.</strong>The web derivative is a compressed copy with original dimensions. The original remains unchanged. A hash identifies a file; metadata-marker detection is not validation of a C2PA signature or proof of an image’s claims.</div><p><a href="library.html#slide-${record.slide}">Read the slide transcription and source notes →</a></p>`;
    } catch (error) { area.textContent = 'The comparison could not load. The source files remain available in the original library.'; }
  });
}

const briefForm = $('#brief-form');
if (briefForm) {
  const output = $('#brief-output');
  const status = $('#brief-status');
  const angle = $('#brief-angle');
  const anglePrompts = {
    observation: 'What familiar excuse can we laugh at, and what different response could the person try?',
    self: 'Could the teller recognise their part, put it right and share what helped? Keep real personal details grounded in what was supplied.',
    exchange: 'Could an exchange open a useful choice, with someone listening or offering help? What happens after the laugh?',
    status: 'Could the person who asks, listens or learns turn out to be the capable one? Give the change a benefit rather than a humiliating loser.',
    visual: 'Could a reveal expose the old excuse, then show the person doing something better and enjoying the result?'
  };
  angle?.addEventListener('change', () => {
    $('#brief-angle-hint').textContent = anglePrompts[angle?.value] || 'Leave this open, or try an angle from Loose Goose.';
  });
  briefForm.addEventListener('submit', event => {
    event.preventDefault();
    const v = id => $(id)?.value.trim() || '';
    if (!v('#brief-point')) { status.textContent = 'Add a proposed better action and why it helps, so the joke has a way forward.'; $('#brief-point')?.focus(); return; }
    output.value = `ROUGH AS GUTS: DRAFT IMAGE BRIEF\n\nUSE\n${v('#brief-audience')}\n\nEDITION / CAST\n${v('#brief-edition')}\n\nSITUATION OR HABIT\n${v('#brief-habit')}\n\nBETTER ACTION AND WHY IT HELPS\n${v('#brief-point') || '[Describe the proposed better action and who it helps]'}\n\nVISUAL FORMAT\n${v('#brief-format')}\n\nSCENE\n${v('#brief-scene') || '[Show the person recognising the habit, trying the better action and reaching a worthwhile result]'}\n\nCOMIC ANGLE TO EXPLORE\n${angle?.selectedOptions[0]?.textContent || 'Still exploring'}\n${anglePrompts[angle?.value] || "No angle chosen. Keep the possible approaches open."}\n\nANOTHER VERSION TO TRY\n${v('#brief-alternative') || "No alternative recorded yet."}\n\nEXACT CAPTION\n${v('#brief-caption') || '[Lettering to be decided separately]'}\n\nSHARED VISUAL STYLE\nBold Australian comic illustration, heavy black ink outlines, safety yellow and warm cream, dusty ochre, selective red accents, expressive faces and recognisable everyday props. Keep the Australian warmth and readable composition. Aim the joke at the excuse or habit, and keep the person capable of learning. Leave clear areas for exact lettering.\n\nGENERATION INSTRUCTIONS\nGenerate the illustration with no invented text, logos or procedural numbers. Make the proposed better action and benefit visible. In a sequence, show the person participating in the change and end with care, repair or shared enjoyment. In one panel, make the better action the main event. Do not leave the unsafe or inconsiderate act as the most attractive outcome. Include support or changed work conditions where needed. A standalone page does not require a continuing protagonist. Match the cast to the intended readers. Young people can learn a different way and ask for help; their family circumstances are not the joke.\n\nREAL STORIES\nWhen using a real story, keep supplied facts and memories separate from guesses and comic exaggeration. Leave unknown motives and personal details open. Keep proposed angles and alternate endings exploratory. For skits or sequences, try the timing and pauses; no audience response is established by this brief.\n\nFACTS / SITE DETAILS TO CHECK\n${v('#brief-check') || '[Record any safety, health, equipment or site-specific claims before treating this as final copy]'}\n\nREVIEW\nCan a reader identify what the person can do differently and why it helps? Does the picture show that action, not just a bystander disapproving? Could someone admire the harmful behaviour and miss the change? Does the ending retain dignity and make a healthier, safer or more considerate choice appealing? Are task details and captions accurate? Ask intended readers; this brief does not establish their response.`;
    status.textContent = 'Draft brief ready. Read it through before generating artwork.';
  });
  $('#copy-brief').addEventListener('click', async () => {
    if (!output.value) { status.textContent = 'Build a brief first.'; return; }
    try { await navigator.clipboard.writeText(output.value); status.textContent = 'Brief copied.'; }
    catch { output.focus(); output.select(); status.textContent = 'Brief selected. Use your device’s Copy command.'; }
  });
  $('#download-brief').addEventListener('click', () => {
    if (!output.value) { status.textContent = 'Build a brief first.'; return; }
    const url = URL.createObjectURL(new Blob([output.value], {type:'text/plain;charset=utf-8'}));
    const a = document.createElement('a'); a.href = url; a.download = 'rough-as-guts-image-brief.txt'; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000); status.textContent = 'Brief downloaded.';
  });
}
