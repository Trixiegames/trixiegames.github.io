'use strict';
let data = JSON.parse(document.getElementById('initial-data').textContent);
let category = 'all';
const $ = selector => document.querySelector(selector);
const buttons = [...document.querySelectorAll('[data-filter]')];
const dateFormat = new Intl.DateTimeFormat('cs-CZ', {timeZone:'Europe/Prague', dateStyle:'long'});
const timeFormat = new Intl.DateTimeFormat('cs-CZ', {timeZone:'Europe/Prague', timeStyle:'short'});
const fullFormat = new Intl.DateTimeFormat('cs-CZ', {timeZone:'Europe/Prague', dateStyle:'short', timeStyle:'short'});
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function render() {
  const now = Date.now();
  const articles = data.articles.filter(a => {
    const published = Date.parse(a.published_at);
    return Number.isFinite(published) && published <= now && published >= now - 86400000;
  });
  const fragment = document.createDocumentFragment();
  for (const a of articles) {
    const url = new URL(a.url);
    if (url.protocol !== 'https:' || !['ct24.ceskatelevize.cz','www.irozhlas.cz'].includes(url.hostname)) continue;
    const card = element('article');
    card.dataset.category = a.category;
    const meta = element('div', '', 'meta');
    const time = element('time', fullFormat.format(new Date(a.published_at)));
    time.dateTime = a.published_at;
    meta.append(element('span', a.category === 'domaci' ? 'Domácí politika' : 'Zahraniční politika', 'category'), time);
    const source = element('div', '', 'source');
    const link = element('a', 'Číst původní článek ↗');
    link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
    source.append(element('span', 'Výňatek z anotace · ' + a.source), link);
    card.append(meta, element('h2',a.title), element('p',a.summary), source);
    fragment.append(card);
  }
  $('#news').replaceChildren(fragment);
  const updated = new Date(data.updated_at);
  $('#editionDate').textContent = dateFormat.format(updated);
  $('#editionTime').textContent = timeFormat.format(updated) + ' · Praha';
  const stale = now - updated.getTime() > 2 * 3600000;
  const status = $('#updateStatus');
  status.classList.toggle('warning', stale || Boolean(data.unavailable_sources?.length));
  status.textContent = stale ? 'Aktualizace se opozdila. Zobrazen je čas poslední úspěšné kontroly; články starší než 24 hodin se nezobrazují.' :
    'Automatická kontrola každou hodinu · Články zveřejněné za posledních 24 hodin · Časy v pásmu Praha.';
  if (data.unavailable_sources?.length) status.textContent += ' Při poslední kontrole nebyl dostupný zdroj: ' + data.unavailable_sources.join(', ') + '.';
  filter();
}
function filter() {
  const query = $('#search').value.trim().toLocaleLowerCase('cs');
  let count = 0;
  document.querySelectorAll('#news article').forEach(card => {
    card.hidden = (category !== 'all' && card.dataset.category !== category) || !card.textContent.toLocaleLowerCase('cs').includes(query);
    if (!card.hidden) count++;
  });
  $('#count').textContent = count + ' ' + (count === 1 ? 'zpráva' : count >= 2 && count <= 4 ? 'zprávy' : 'zpráv');
  $('#empty').hidden = count !== 0;
  $('#empty').textContent = data.articles.length ? 'Pro tento filtr nejsou dostupné aktuální zprávy.' : 'Za posledních 24 hodin nebyly nalezeny články odpovídající výběru.';
}
buttons.forEach(button => button.addEventListener('click', () => {
  category = button.dataset.filter;
  buttons.forEach(b => { b.classList.toggle('active', b === button); b.setAttribute('aria-pressed', String(b === button)); });
  filter();
}));
$('#search').addEventListener('input', filter);
async function refresh() {
  try {
    const response = await fetch('data.json', {cache:'no-store'});
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const next = await response.json();
    if (!Array.isArray(next.articles) || !Number.isFinite(Date.parse(next.updated_at))) throw new Error('Invalid edition');
    data = next;
    render();
  } catch (error) {
    // Preserve the real successful update time and keep expiry checks running.
    console.warn('Aktuální vydání se nepodařilo načíst.', error);
  }
}
render(); refresh();
setInterval(refresh, 5 * 60000);
setInterval(render, 60000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
