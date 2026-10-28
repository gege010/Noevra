const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('src/static/providers.js', 'utf8');

function workspace(requestCatalog) {
  const elements = new Map();
  function $(id) {
    if (!elements.has(id)) {
      let html = '';
      const element = {value:'', textContent:'', disabled:false, hidden:false, handlers:{},
        addEventListener(type, handler) {this.handlers[type] = handler;}, close() {},
        get innerHTML() {return html;},
        set innerHTML(value) {html=value; if(id==='modelSelect') this.value = value.match(/value="([^"]*)"/)?.[1] || '';}};
      elements.set(id, element);
    }
    return elements.get(id);
  }
  const state = {provider:'groq', model:'', connections:{groq:{key:'test-key'}}, providers:{groq:{name:'Groq', configured_in_backend:false},openai:{name:'OpenAI', configured_in_backend:false}}};
  const window = {ScholarControls:{sync(){}},ScholarWorkspace:{openSettings(){}}};
  vm.runInNewContext(source, {window,state,$,esc:s=>String(s),shortModel:s=>s,notify(){},openDialog(){},location:{protocol:'http:',hostname:'127.0.0.1'},request:(url,options)=>url.includes('capabilities')?Promise.resolve({}):requestCatalog(url, options)});
  window.NoevraProviders.init();
  return {api:window.NoevraProviders,state,$};
}
const settle = () => new Promise(resolve => setImmediate(resolve));

test('connecting discovers live models; filtering does not change the chosen model', async () => {
  const w = workspace(async (_url, options) => {assert.equal(JSON.parse(options.body).api_key,'test-key');return {models:[{id:'model-a',name:'First'},{id:'model-b',name:'Second'}]};});
  w.api.selectProvider('groq'); await settle();
  assert.equal(w.state.model,'model-a');
  w.$('modelSearch').value='Second'; w.$('modelSearch').handlers.input();
  assert.equal(w.$('modelSelect').value,'model-b');
  w.api.selectModel();
  assert.equal(w.state.model,'model-a');
  w.api.selectModel(true);
  assert.equal(w.state.model,'model-b');
});

test('failed refresh removes a previously discovered selection', async () => {
  let fail = false;
  const w = workspace(async () => {if(fail) throw new Error('Permission revoked');return {models:[{id:'first',name:'First'}]};});
  w.api.selectProvider('groq'); await settle();
  assert.equal(w.state.model,'first');
  fail=true; w.$('refreshModelsBtn').handlers.click(); await settle();
  assert.equal(w.state.model,'');
  assert.equal(w.$('modelSelect').disabled,true);
  assert.equal(w.$('catalogStatus').textContent,'Permission revoked');
});

test('late provider responses do not replace another provider model', async () => {
  let finish;
  const w = workspace(() => new Promise(resolve=>finish=resolve));
  w.api.selectProvider('groq');
  w.api.selectProvider('openai');
  finish({models:[{id:'groq-model',name:'Groq model'}]}); await settle();
  assert.equal(w.state.provider,'openai');
  assert.equal(w.state.model,'');
});
