const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const elements=new Map(), events={};let clock=100,focused=true;
const document={hidden:false,activeElement:null,hasFocus:()=>focused,getElementById:element,addEventListener:(n,f)=>events['document:'+n]=f};
function element(id){if(!elements.has(id))elements.set(id,{tagName:'DIV',textContent:'',style:{},dataset:{},classList:{add(){},remove(){},toggle(){}},getContext:()=>({clearRect(){},drawImage(){}}),addEventListener(n,f){this[n]=f;},replaceChildren(){},setPointerCapture(){},hasPointerCapture(){return false;},focus(){document.activeElement=this;},getBoundingClientRect:()=>({left:0,top:0,width:100,height:100})});return elements.get(id);}
class Socket{static OPEN=1;constructor(){this.readyState=1;this.sent=[];Socket.last=this;}send(v){this.sent.push(JSON.parse(v));}}
const context={document,window:{addEventListener:(n,f)=>events['window:'+n]=f},performance:{now:()=>clock},location:{protocol:'http:',host:'localhost'},WebSocket:Socket,Option:function(){},setInterval:()=>1,clearInterval(){},requestAnimationFrame:f=>f(),createImageBitmap:async()=>({width:100,height:100,close(){}}),fetch:async()=>{throw Error('unauthenticated')}};
vm.createContext(context);vm.runInContext(fs.readFileSync('web/app.js','utf8'),context);
const run=s=>vm.runInContext(s,context);
(async()=>{
 run('openPreview()');const ws=Socket.last;ws.onopen();
 const count=()=>ws.sent.filter(m=>m.type==='activate').length;
 const status=armed=>ws.onmessage({data:JSON.stringify({type:'status',available:true,armed})});
 const frame=async()=>{clock+=100;await ws.onmessage({data:JSON.stringify({type:'frame',id:clock,geometry:'1:2:100:100'})});await ws.onmessage({data:{}});};
 await status(false);assert.equal(count(),0,'No activation before image');
 await frame();assert.equal(count(),1,'First image automatically activates control');
 await frame();assert.equal(count(),1,'Wait for server confirmation without repeated activation');
 await status(true);assert.equal(document.activeElement,element('screen'),'Keyboard goes to screen after activation');
 const screen=element('screen');
 screen.pointermove({clientX:25,clientY:75});
 screen.pointerdown({preventDefault(){},pointerId:1,button:0,clientX:25,clientY:75});
 screen.pointerup({preventDefault(){},pointerId:1,button:0,clientX:25,clientY:75});
 screen.keydown({preventDefault(){},code:'KeyA'});screen.keyup({preventDefault(){},code:'KeyA'});
 const inputs=ws.sent.filter(m=>m.type==='input');
 assert.deepEqual(inputs.map(m=>m.event.type),['move','button','button','key','key']);
 assert.equal(inputs[0].event.x,.25);assert.equal(inputs[0].event.y,.75);
 assert.equal(inputs[3].event.down,true);assert.equal(inputs[4].event.down,false);
 assert.ok(inputs.every(m=>m.geometry==='1:2:100:100'));
 element('release').onclick();await status(true);screen.pointermove({clientX:30,clientY:30});assert.equal(ws.sent.filter(m=>m.type==='input').length,5,'Stale armed status must not override explicit pause');await status(false);await frame();element('screen').pointerenter();assert.equal(count(),1,'Explicit pause survives new frames and pointer entry');
 element('activate').onclick();assert.equal(count(),2,'Resume remains available');await status(true);
 focused=false;events['window:blur']();await status(false);await frame();assert.equal(count(),2,'Background tab must not reacquire control');
 focused=true;element('screen').pointerenter();assert.equal(count(),3,'Returning to image resumes without a button');await status(true);
 events['window:blur']();await status(false);document.activeElement=element('remote-id');element('remote-id').tagName='INPUT';await frame();assert.equal(count(),3,'Typing destination must not steal focus');
 element('screen').pointerenter();assert.equal(count(),4,'Entering image explicitly allows control while an input was focused');await status(true);
 element('release').onclick();element('remote-id').value='604619388';element('connect-form').onsubmit({preventDefault(){}});await status(false);await frame();assert.equal(count(),5,'A new connection automatically enables control again');
 console.log('PASS: auto activation, confirmation, pause, background, pointer return, input focus, reconnect');
})().catch(e=>{console.error(e);process.exitCode=1;});
