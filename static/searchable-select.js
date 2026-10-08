/* Local, dependency-free enhancement. The native select remains the source of truth. */
(function (global) {
  'use strict';
  const instances = new WeakMap();
  const normalizeSearch = value => String(value || '').normalize('NFKC').toLocaleLowerCase().replace(/\s+/gu, '');
  const filterOptions = (options, query) => {
    const terms = String(query || '').normalize('NFKC').trim().toLocaleLowerCase().split(/\s+/u).filter(Boolean);
    return options.filter(option => !option.disabled && !option.hidden && terms.every(term =>
      normalizeSearch([option.label || option.textContent, option.value, option.dataset?.searchKeywords || ''].join(' ')).includes(normalizeSearch(term))));
  };

  function enhance(select, settings = {}) {
    if (!select || select.multiple) return null;
    if (instances.has(select)) return instances.get(select);
    const doc = select.ownerDocument;
    const label = settings.label || select.getAttribute('aria-label') || '항목';
    const limit = Math.max(1, settings.limit || 50);
    const make = (tag, className, text) => {
      const element = doc.createElement(tag);
      if (className) element.className = className;
      if (text) element.textContent = text;
      return element;
    };
    const wrapper = make('div', 'searchable-select');
    const control = make('div', 'searchable-select-control');
    const icon = make('i', 'bi bi-search searchable-select-icon');
    icon.setAttribute('aria-hidden', 'true');
    const input = make('input', 'searchable-select-input');
    input.id = select.id + '-search';
    input.type = 'text';
    input.autocomplete = 'off';
    input.spellcheck = false;
    input.placeholder = label + ' 이름 또는 코드 검색';
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-haspopup', 'listbox');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-label', label + ' 검색 및 선택');
    const clear = make('button', 'searchable-select-clear', '×');
    clear.type = 'button';
    clear.setAttribute('aria-label', label + ' 검색어 지우기');
    clear.hidden = true;
    const toggle = make('button', 'searchable-select-toggle', '⌄');
    toggle.type = 'button';
    toggle.tabIndex = -1;
    toggle.setAttribute('aria-label', label + ' 목록 열기');
    const popup = make('div', 'searchable-select-popup');
    popup.hidden = true;
    const hint = make('div', 'searchable-select-hint', '이름·코드 검색 · ↑↓ 이동 · Enter 선택');
    const list = make('div', 'searchable-select-list');
    list.id = select.id + '-results';
    list.setAttribute('role', 'listbox');
    list.setAttribute('aria-label', label + ' 검색 결과');
    input.setAttribute('aria-controls', list.id);
    const status = make('div', 'searchable-select-status');
    status.id = select.id + '-search-status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    status.setAttribute('aria-atomic', 'true');
    input.setAttribute('aria-describedby', status.id);
    control.append(icon, input, clear, toggle);
    popup.append(hint, list, status);
    wrapper.append(control, popup);
    select.parentNode.insertBefore(wrapper, select);
    Array.from(select.labels || []).forEach(item => { item.htmlFor = input.id; });
    select.hidden = true;
    select.tabIndex = -1;
    select.setAttribute('aria-hidden', 'true');
    let opened = false;
    let query = '';
    let composing = false;
    let active = -1;
    let matches = [];
    let rendered = [];
    const selectedLabel = () => select.options[select.selectedIndex]?.label || select.options[select.selectedIndex]?.textContent || '';

    function activate(index, scroll = false) {
      active = index;
      Array.from(list.children).forEach((item, offset) => item.classList.toggle('is-active', offset === index));
      const item = list.children[index];
      if (item && opened) {
        input.setAttribute('aria-activedescendant', item.id);
        if (scroll) item.scrollIntoView({block: 'nearest'});
      } else input.removeAttribute('aria-activedescendant');
    }

    function render(preferSelected = false) {
      matches = filterOptions(Array.from(select.options), query);
      rendered = matches.slice(0, limit);
      list.replaceChildren();
      rendered.forEach((option, index) => {
        const item = make('div', 'searchable-select-option');
        item.id = select.id + '-result-' + index;
        item.setAttribute('role', 'option');
        item.setAttribute('aria-selected', String(option.selected));
        const title = make('span', 'searchable-select-option-label', option.label || option.textContent);
        item.appendChild(title);
        if (option.value) item.appendChild(make('span', 'searchable-select-option-code', option.value));
        item.addEventListener('mousedown', event => event.preventDefault());
        item.addEventListener('click', () => choose(index));
        list.appendChild(item);
      });
      status.textContent = matches.length === 0
        ? '검색 결과가 없습니다. 다른 이름이나 코드를 입력하세요.'
        : matches.length > limit
          ? `${matches.length}개 결과 중 ${limit}개 표시 · 검색어를 더 입력해 범위를 좁히세요.`
          : `${matches.length}개 결과`;
      clear.hidden = !query;
      const selected = preferSelected ? rendered.findIndex(option => option.selected) : -1;
      activate(rendered.length ? Math.max(0, selected) : -1);
    }

    function open() {
      if (select.disabled || opened) return;
      opened = true;
      query = '';
      popup.hidden = false;
      input.setAttribute('aria-expanded', 'true');
      toggle.setAttribute('aria-label', label + ' 목록 닫기');
      render(true);
      input.select();
    }

    function close() {
      opened = false;
      composing = false;
      query = '';
      popup.hidden = true;
      input.value = selectedLabel();
      clear.hidden = true;
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
      toggle.setAttribute('aria-label', label + ' 목록 열기');
    }

    function choose(index) {
      const option = rendered[index];
      if (!option || select.disabled || composing) return;
      const previous = select.selectedIndex;
      select.selectedIndex = Array.from(select.options).indexOf(option);
      close();
      input.focus({preventScroll: true});
      // focus may open the popup again if a pointer had moved focus to a button.
      close();
      if (previous !== select.selectedIndex) select.dispatchEvent(new Event('change', {bubbles: true}));
    }

    function refresh() {
      input.disabled = select.disabled;
      clear.disabled = select.disabled;
      toggle.disabled = select.disabled;
      wrapper.classList.toggle('is-disabled', select.disabled);
      if (select.disabled) close();
      if (opened) render();
      else input.value = selectedLabel();
    }

    input.addEventListener('focus', open);
    input.addEventListener('click', open);
    input.addEventListener('input', () => {
      if (composing) return;
      if (!opened) open();
      query = input.value;
      render();
    });
    input.addEventListener('compositionstart', () => { composing = true; });
    input.addEventListener('compositionend', () => {
      composing = false;
      if (!opened) open();
      query = input.value;
      render();
    });
    input.addEventListener('keydown', event => {
      if (composing || event.isComposing || event.keyCode === 229) return;
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        const wasOpen = opened;
        open();
        if (!rendered.length) return;
        const delta = event.key === 'ArrowDown' ? 1 : -1;
        activate(wasOpen ? (active + delta + rendered.length) % rendered.length : active, true);
      } else if (event.key === 'Enter' && opened) {
        event.preventDefault();
        choose(active);
      } else if (event.key === 'Escape' && opened) {
        event.preventDefault();
        event.stopPropagation();
        close();
      } else if (event.key === 'Tab') close();
    });
    clear.addEventListener('click', () => {
      input.focus({preventScroll: true});
      open();
      input.value = '';
      query = '';
      render();
    });
    toggle.addEventListener('mousedown', event => event.preventDefault());
    toggle.addEventListener('click', () => {
      if (opened) { close(); input.focus({preventScroll: true}); close(); }
      else { input.focus({preventScroll: true}); open(); }
    });
    wrapper.addEventListener('focusout', () => {
      setTimeout(() => { if (!wrapper.contains(doc.activeElement)) close(); }, 0);
    });
    doc.addEventListener('pointerdown', event => { if (!wrapper.contains(event.target)) close(); });
    select.addEventListener('change', () => { close(); refresh(); });
    const observer = new MutationObserver(refresh);
    observer.observe(select, {childList: true, subtree: true, characterData: true, attributes: true,
      attributeFilter: ['disabled', 'hidden', 'label', 'selected', 'value', 'data-search-keywords']});
    const api = {refresh, close, input, wrapper};
    instances.set(select, api);
    refresh();
    return api;
  }

  global.SearchableSelect = {enhance, normalizeSearch, filterOptions,
    refresh: select => instances.get(select)?.refresh()};
})(typeof window === 'undefined' ? globalThis : window);
