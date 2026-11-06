const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let clock=100, tick;
const elements=new Map();
const element=id=>{if(!elements.has(id))elements.set(id,{textContent:'',style:{},dataset:{},classList:{add(){},remove(){},toggle(){}},getContext:()=>({clearRect(){}}),addEventListener(){},replaceChildren(){},focus(){}});return elements.get(id);};
class Socket {static OPEN=1;constructor(){this.readyState=1;Socket.last=this;}send(){}}
const context={document:{getElementById:element,addEventListener(){}},window:{addEventListener(){}},performance:{now:()=>clock},location:{protocol:'http:',host:'localhost'},WebSocket:Socket,Option:function(){},setInterval:f=>(tick=f,1),clearInterval(){},fetch:async()=>{throw Error('unauthenticated')}};
vm.createContext(context);vm.runInContext(fs.readFileSync('web/app.js','utf8'),context);vm.runInContext('openPreview()',context);
const ws=Socket.last;ws.onopen();
const status=available=>ws.onmessage({data:JSON.stringify({type:'status',available,armed:false,message:'Sessão desconectada'})});
status(false);clock=10000;tick();
assert.equal(element('empty-title').textContent,'Janela indisponível','Timer must preserve authoritative unavailable status');
status(true);tick();assert.equal(element('empty-title').textContent,'Janela indisponível','Recovery gets a fresh capture deadline');
clock=19000;tick();assert.equal(element('empty-title').textContent,'O Windows não enviou imagem','Available session without frames must still time out');
console.log('PASS: unavailable message stable; recovery deadline and missing-frame timeout preserved');
