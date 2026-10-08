/* Focused DOM harness: event/state behavior only; layout is reviewed in a browser. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

class UIEvent {
  constructor(type, properties = {}) { this.type = type; Object.assign(this, properties); }
  preventDefault() { this.defaultPrevented = true; }
  stopPropagation() {}
}
class Element {
  constructor(tag, document) {
    this.tagName = tag; this.ownerDocument = document; this.children = []; this.attributes = {};
    this.listeners = {}; this.dataset = {}; this.value = ''; this.hidden = false; this.disabled = false;
    this.textContent = ''; this.className = ''; this.labels = []; this._selectedIndex = 0;
    this.classList = {toggle: (name, on) => {
      const classes = new Set(this.className.split(' ').filter(Boolean));
      on ? classes.add(name) : classes.delete(name); this.className = [...classes].join(' ');
    }};
  }
  append(...children) { children.forEach(child => this.appendChild(child)); }
  appendChild(child) { this.children.push(child); child.parentNode = this; return child; }
  insertBefore(child, reference) { this.children.splice(this.children.indexOf(reference), 0, child); child.parentNode = this; }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  get options() { return this.children; }
  get selectedIndex() { return this._selectedIndex; }
  set selectedIndex(index) { this._selectedIndex = index; }
  get selected() { return this.parentNode?.options[this.parentNode.selectedIndex] === this; }
  get label() { return this.textContent; }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  getAttribute(key) { return this.attributes[key] ?? null; }
  removeAttribute(key) { delete this.attributes[key]; }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  dispatchEvent(event) {
    event.target ||= this;
    (this.listeners[event.type] || []).forEach(handler => handler(event));
    return !event.defaultPrevented;
  }
  focus() {
    if (this.ownerDocument.activeElement === this) return;
    this.ownerDocument.activeElement = this; this.dispatchEvent(new UIEvent('focus'));
  }
  select() { this.allTextSelected = true; }
  contains(target) { return target === this || this.children.some(child => child.contains(target)); }
  scrollIntoView() {}
}
class Document extends Element {
  constructor() { super('document'); this.ownerDocument = this; this.activeElement = null; }
  createElement(tag) { return new Element(tag, this); }
}
const observers = [];
class Observer {
  constructor(callback) { this.callback = callback; observers.push(this); }
  observe() {}
}
const sandbox = {Event: UIEvent, MutationObserver: Observer, setTimeout: callback => callback()};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../static/searchable-select.js'), 'utf8'), sandbox);
const component = sandbox.SearchableSelect;
function fixture(items) {
  const document = new Document(); const holder = document.createElement('div'); document.appendChild(holder);
  const select = document.createElement('select'); select.id = 'ontSelect'; holder.appendChild(select);
  items.forEach(([value, label]) => { const option = document.createElement('option'); option.value = value; option.textContent = label; select.appendChild(option); });
  const api = component.enhance(select, {label: '온톨로지'});
  const control = api.wrapper.children[0]; const popup = api.wrapper.children[1];
  return {document, select, api, input: api.input, clear: control.children[2], list: popup.children[1], status: popup.children[2]};
}
const type = (f, value) => { f.input.value = value; f.input.dispatchEvent(new UIEvent('input')); };
const key = (f, value, extra = {}) => { const event = new UIEvent('keydown', {key: value, ...extra}); f.input.dispatchEvent(event); return event; };
const examples = [['mv', '뮤직 비디오 (mv)'], ['healthcare', '헬스케어 AI (healthcare)'], ['academic', '대학 수강 예시']];

{
  const f = fixture(examples); let changes = 0; f.select.addEventListener('change', () => changes++);
  assert.equal(f.select.hidden, true); assert.equal(f.input.value, examples[0][1]);
  f.input.focus(); type(f, 'HEALTH CARE');
  assert.equal(f.list.children.length, 1); assert.equal(f.select.selectedIndex, 0); assert.equal(changes, 0);
  key(f, 'Enter'); assert.equal(f.select.selectedIndex, 1); assert.equal(changes, 1);
  assert.equal(f.input.getAttribute('aria-expanded'), 'false'); assert.equal(f.input.value, examples[1][1]);
  key(f, 'ArrowDown'); type(f, '대 학'); assert.equal(f.list.children.length, 1);
  key(f, 'Escape'); assert.equal(f.select.selectedIndex, 1); assert.equal(changes, 1);
  assert.equal(f.input.value, examples[1][1]);
  key(f, 'ArrowDown'); type(f, '없는 결과'); assert.equal(f.list.children.length, 0);
  assert.match(f.status.textContent, /검색 결과가 없습니다/); key(f, 'Enter'); assert.equal(changes, 1);
  f.clear.dispatchEvent(new UIEvent('click')); assert.equal(f.list.children.length, 3);
  key(f, 'Tab'); assert.equal(f.input.getAttribute('aria-expanded'), 'false'); assert.equal(changes, 1);
}
{
  const f = fixture(examples); f.input.focus();
  f.input.dispatchEvent(new UIEvent('compositionstart')); type(f, '대학');
  assert.equal(key(f, 'Enter', {isComposing: true}).defaultPrevented, undefined);
  assert.equal(f.select.selectedIndex, 0);
  f.input.dispatchEvent(new UIEvent('compositionend')); assert.equal(f.list.children.length, 1);
  key(f, 'Enter', {keyCode: 229}); assert.equal(f.select.selectedIndex, 0);
  key(f, 'Enter'); assert.equal(f.select.selectedIndex, 2);
}
{
  const f = fixture(examples); f.input.focus(); key(f, 'ArrowDown'); key(f, 'Enter');
  assert.equal(f.select.selectedIndex, 1);
  f.select.selectedIndex = 2; component.refresh(f.select); assert.equal(f.input.value, examples[2][1]);
  f.select.disabled = true; component.refresh(f.select);
  assert.equal(f.input.disabled, true); assert.equal(f.input.getAttribute('aria-expanded'), 'false');
  key(f, 'ArrowDown'); assert.equal(f.input.getAttribute('aria-expanded'), 'false');
  f.select.disabled = false; component.refresh(f.select);
  const option = f.document.createElement('option'); option.value = 'new'; option.textContent = '새 프로젝트';
  f.select.appendChild(option); observers.forEach(observer => observer.callback());
  key(f, 'ArrowDown'); type(f, '새프로젝트'); assert.equal(f.list.children.length, 1);
  f.list.children[0].dispatchEvent(new UIEvent('click')); assert.equal(f.select.selectedIndex, 3);
  assert.equal(component.enhance(f.select), f.api);
}
{
  const f = fixture(Array.from({length: 1000}, (_, i) => ['domain-' + i, '분야 ' + i]));
  f.input.focus(); assert.equal(f.list.children.length, 50); assert.match(f.status.textContent, /1000개 결과 중 50개/);
  type(f, 'domain-999'); assert.equal(f.list.children.length, 1); key(f, 'Enter'); assert.equal(f.select.selectedIndex, 999);
  key(f, 'ArrowDown'); type(f, 'ＤＯＭＡＩＮ-１２'); assert.equal(f.list.children.length, 11);
  f.document.dispatchEvent(new UIEvent('pointerdown', {target: f.document}));
  assert.equal(f.input.getAttribute('aria-expanded'), 'false'); assert.equal(f.select.selectedIndex, 999);
}
{
  const f = fixture([['safe', '<img src=x onerror=alert(1)>']]); f.input.focus();
  assert.equal(f.list.children[0].children[0].textContent, '<img src=x onerror=alert(1)>');
  assert.equal(f.list.children[0].children[0].children.length, 0);
}
console.log('Searchable select: keyboard, IME, filtering, sync, large lists, pointer, and safe labels passed.');
