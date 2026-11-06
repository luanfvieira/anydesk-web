'use strict';
const $ = id => document.getElementById(id);
const canvas = $('screen'), ctx = canvas.getContext('2d');
let available = null;
let ws, metadata, geometry, openedAt = 0, lastFrame = 0, armed = false, timer, moving = false, pendingMove;
function message(text, error = false) { $('message').textContent = text; $('message').classList.toggle('error', error); }
function setArmed(value) { armed = value; canvas.classList.toggle('control', value); $('control-tag').classList.toggle('active', value); $('control-tag').textContent = value ? 'Controle ativo' : 'Somente visualização'; $('release').disabled = !value; }
function send(value) { if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(value)); }
function release() { send({type:'release'}); setArmed(false); }
function blank(title, text) { ctx.clearRect(0,0,canvas.width,canvas.height); canvas.classList.remove('ready'); $('empty').hidden=false; $('empty-title').textContent=title; $('empty-text').textContent=text; geometry=null; lastFrame=0; setArmed(false); }
async function api(path, body) {
 const response=await fetch(path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
 if(!response.ok) throw new Error(await response.text()); return response.json();
}
function showWorkspace() { $('login-panel').hidden=true; $('workspace').hidden=false; openPreview(); }
function openPreview() {
 if(ws && ws.readyState<2) return;
 available = null; lastFrame = 0;
 $('preview').hidden=true; $('transport-label').textContent='Abrindo ponte…';
 const current=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`); ws=current; current.binaryType='blob';
 current.onopen=()=>{openedAt=performance.now(); $('transport-label').textContent='Ponte ativa'; $('transport-dot').style.background='var(--green)'; $('disconnect').disabled=false; timer=setInterval(()=>{send({type:'ping'});if(available !== false && !lastFrame && performance.now()-openedAt>8000){blank('O Windows não enviou imagem','Verifique se a sessão gráfica está ativa e o AnyDesk está visível. O controle fica suspenso até recebermos uma imagem.');$('activate').disabled=true;}if(lastFrame && performance.now()-lastFrame>2500){release();blank('Imagem interrompida','Confira se a sessão Windows está ativa e o AnyDesk está visível.');}},500); };
 current.onmessage=async event=>{
  if(current!==ws) return;
  if(typeof event.data==='string') {
   const data=JSON.parse(event.data);
   if(data.type==='frame'){metadata=data;return;}
   if(data.type==='status') {
    if(available === false && data.available) openedAt=performance.now();
    available=Boolean(data.available);
    if(data.windows){const select=$('window-choice');const items=data.windows;const signature=JSON.stringify(items);if(select.dataset.signature!==signature){select.replaceChildren(new Option('Selecione uma janela…',''),...items.map(w=>new Option(w.title||'AnyDesk',w.id)));select.dataset.signature=signature;}select.value=data.selected_window||'';}

    $('activate').disabled=!data.available || !lastFrame || performance.now()-lastFrame>2000; setArmed(Boolean(data.armed));
    if(!data.available) blank('Janela indisponível',data.message);
   }
   if(data.type==='notice'||data.type==='error') {message(data.message,data.type==='error');if(data.type==='error')setArmed(false);}
   return;
  }
  const meta=metadata;if(!meta)return;
  try {const bitmap=await createImageBitmap(event.data);if(current!==ws||current.readyState!==WebSocket.OPEN){bitmap.close();return;}
   canvas.width=bitmap.width;canvas.height=bitmap.height;ctx.drawImage(bitmap,0,0);bitmap.close();geometry=meta.geometry;lastFrame=performance.now();canvas.classList.add('ready');$('empty').hidden=true;$('frame-info').textContent=`${meta.width} × ${meta.height} · transmissão local`;$('live-dot').style.background='var(--green)';send({type:'ack',id:meta.id});
  }catch{message('Não foi possível decodificar a imagem.',true);current.close();}
 };
 current.onerror=()=>message('Não foi possível abrir a prévia. Verifique o túnel, sua sessão e se outro navegador está usando a ponte.',true);
 current.onclose=()=>{if(current!==ws)return;clearInterval(timer);$('transport-label').textContent='Prévia desconectada';$('transport-dot').style.background='#63736a';$('live-dot').style.background='#63736a';$('activate').disabled=true;$('disconnect').disabled=true;$('preview').hidden=false;blank('Prévia desconectada','Reabra a prévia para continuar. O controle foi liberado.');};
}
$('login-form').onsubmit=async event=>{event.preventDefault();$('login-error').textContent='';try{await api('/api/login',{password:$('password').value});$('password').value='';showWorkspace();}catch(error){$('login-error').textContent=error.message;}};
$('connect-form').onsubmit=event=>{event.preventDefault();if(ws?.readyState!==WebSocket.OPEN){message('Abra a prévia antes de conectar.',true);return;}release();send({type:'connect',id:$('remote-id').value});};
$('window-choice').onchange=()=>{release();blank('Abrindo janela','Aguarde a imagem da janela selecionada.');openedAt=performance.now();send({type:'select',window:$('window-choice').value});};
$('activate').onclick=()=>{send({type:'activate'});canvas.focus({preventScroll:true});};
$('release').onclick=release;
$('disconnect').onclick=()=>{release();send({type:'disconnect'});};
$('preview').onclick=openPreview;
$('logout').onclick=async()=>{release();ws?.close();try{await api('/api/logout',{});}finally{$('workspace').hidden=true;$('login-panel').hidden=false;$('password').focus();}};
$('fullscreen').onclick=()=>{if(document.fullscreenElement)document.exitFullscreen();else $('stage').requestFullscreen().catch(()=>message('Tela cheia indisponível.',true));};
function point(event){const r=canvas.getBoundingClientRect();return{x:Math.max(0,Math.min(1,(event.clientX-r.left)/r.width)),y:Math.max(0,Math.min(1,(event.clientY-r.top)/r.height))};}
function input(event){if(armed&&geometry&&performance.now()-lastFrame<2000)send({type:'input',geometry,event});}
canvas.addEventListener('pointermove',event=>{pendingMove=point(event);if(!moving){moving=true;requestAnimationFrame(()=>{moving=false;input({type:'move',...pendingMove});});}});
canvas.addEventListener('pointerdown',event=>{if(!armed)return;event.preventDefault();canvas.focus({preventScroll:true});canvas.setPointerCapture(event.pointerId);input({type:'button',button:event.button,down:true,...point(event)});});
canvas.addEventListener('pointerup',event=>{event.preventDefault();input({type:'button',button:event.button,down:false,...point(event)});if(canvas.hasPointerCapture(event.pointerId))canvas.releasePointerCapture(event.pointerId);});
canvas.addEventListener('pointercancel',release);
canvas.addEventListener('contextmenu',event=>event.preventDefault());
canvas.addEventListener('wheel',event=>{if(!armed)return;event.preventDefault();input({type:'wheel',delta:Math.max(-1200,Math.min(1200,event.deltaY)),...point(event)});},{passive:false});
for(const type of ['keydown','keyup'])canvas.addEventListener(type,event=>{if(!armed)return;event.preventDefault();if(event.metaKey||event.code.startsWith('Meta')){release();message('Atalhos do sistema local não são enviados.',true);return;}input({type:'key',code:event.code,down:type==='keydown'});});
canvas.addEventListener('blur',release);window.addEventListener('blur',release);window.addEventListener('pagehide',()=>{release();ws?.close();});document.addEventListener('visibilitychange',()=>{if(document.hidden)release();});
api('/api/status').then(showWorkspace).catch(()=>{});
