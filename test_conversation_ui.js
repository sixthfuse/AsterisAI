const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function browser() {
  const element = () => ({
    handlers: {}, classList: { add() {} }, disabled: false,
    appendChild() {}, setAttribute() {}, remove() {}, focus() {},
    querySelectorAll() { return []; },
    addEventListener(name, fn) { this.handlers[name] = fn; },
  });
  const nodes = {};
  const requests = [];
  let fail = false;
  const state = { version: 1, scope: 'program_family', scope_query: 'nursing programs' };
  const context = vm.createContext({
    document: {
      querySelector(selector) { return nodes[selector] ||= element(); },
      querySelectorAll() { return []; },
      createElement: element,
      createTextNode(text) { return text; },
    },
    async fetch(url, options) {
      requests.push(JSON.parse(options.body));
      if (fail) throw new Error('Temporary failure');
      return { ok: true, async json() { return { answer: 'Family details', conversation_state: state }; } };
    },
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, 'static/app.js'), 'utf8'), context);
  return { nodes, requests, state, context, setFail() { fail = true; },
    ask(text) { return vm.runInContext(`askAdvisor(${JSON.stringify(text)})`, context); } };
}

test('structured subject persists beyond the ten-message transcript window', async () => {
  const ui = browser();
  await ui.ask('What about nursing programs?');
  for (let i = 0; i < 12; i++) await ui.ask('Tell me more');
  const request = ui.requests.at(-1);
  assert.deepEqual(request.conversation_state, ui.state);
  assert.equal(request.conversation.length, 10);
  assert.equal(request.conversation.some(turn => turn.content.includes('nursing')), false);
});

test('starting a new conversation clears both transcript and structured subject', async () => {
  const ui = browser();
  await ui.ask('What about nursing programs?');
  ui.nodes['#clear'].handlers.click();
  await ui.ask('Tell me more');
  assert.equal(ui.requests.at(-1).conversation_state, null);
  assert.deepEqual(ui.requests.at(-1).conversation, []);
});

test('a failed request keeps the last successful subject', async () => {
  const ui = browser();
  await ui.ask('What about nursing programs?');
  ui.setFail();
  await ui.ask('Tell me about 9940BSC');
  await ui.ask('Tell me more');
  assert.deepEqual(ui.requests.at(-1).conversation_state, ui.state);
  assert.equal(ui.nodes['#send'].disabled, false);
  assert.equal(ui.nodes['#clear'].disabled, false);
});

test('a pending answer cannot repopulate a conversation cleared in flight', async () => {
  const ui = browser();
  const pending = ui.ask('What about nursing programs?');
  assert.equal(ui.nodes['#clear'].disabled, true);
  await pending;
  assert.equal(ui.nodes['#clear'].disabled, false);
});

test('student rendering removes internal function protocol as a defense in depth', () => {
  const ui = browser();
  const cleaned = vm.runInContext(
    `sanitizeStudentText('functions.search_programs {"credential":"engineering"}\\n{"query":"engineering"}\\nBCIT offers Civil Engineering.')`,
    ui.context
  );
  assert.equal(cleaned, 'BCIT offers Civil Engineering.');
});


test('unique program and search scope survive transcript flow and truncation', async () => {
  const ui = browser();
  await ui.ask('What about nursing programs?');
  await ui.ask("Do you have any programs with a master's degree?");
  Object.assign(ui.state, { scope: 'global', scope_query: null, catalog_kind: 'programs',
    result_query: 'master', unique_result_program_id: 'M600MSC' });
  await ui.ask("ok, what about BCIT programs overall, does bcit have any master's degree programs?");
  for (const q of ['give me more information about this program',
    'do you have more information about this program on your asteris database?',
    'I need more information about this program from asteris.', 'ok, i give up.']) {
    await ui.ask(q);
    assert.deepEqual(ui.requests.at(-1).conversation_state, ui.state);
  }
  for (let i = 0; i < 12; i++) await ui.ask('tell me more');
  assert.equal(ui.requests.at(-1).conversation.length, 10);
  assert.equal(ui.requests.at(-1).conversation_state.unique_result_program_id, 'M600MSC');
  await ui.ask('do you have any biotechnology or biochemistry programs?');
  Object.assign(ui.state, { scope: 'program_family', catalog_kind: null,
    scope_query: 'biotechnology or biochemistry programs', result_query: null,
    unique_result_program_id: '9940BSC' });
  await ui.ask('do you have any biochemistry programs?');
  await ui.ask('more information');
  assert.equal(ui.requests.at(-1).conversation_state.unique_result_program_id, '9940BSC');
  ui.nodes['#clear'].handlers.click();
  await ui.ask('it');
  assert.equal(ui.requests.at(-1).conversation_state, null);
});
