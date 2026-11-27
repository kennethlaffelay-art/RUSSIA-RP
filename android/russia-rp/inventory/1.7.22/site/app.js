'use strict';
const $=id=>document.getElementById(id);
const create=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e};
const snapshot=JSON.parse($('snapshot').textContent);
const rows=new Map();
snapshot.body.split(/\r?\n/).forEach((line,row)=>{
 const match=line.replace(/\{[0-9a-f]{6}\}/gi,'').match(/^([^:\t]+)(?:[:\t]\s*(.*))?$/);
 if(match)rows.set(match[1].trim(),{row,value:(match[2]||'').trim()});
});
const value=key=>rows.get(key)?.value;
const format=n=>Number(n).toLocaleString('ru-RU',{maximumFractionDigits:3});
const full=rows.has('Профиль')&&rows.has('Телефон');
const vip=full&&Number(value('VIP'))>0;
const weaponPictures=WEAPONASSETS;
const account=value('Профиль')||'';
let finished=false,selection=null,assign=false,priorFocus=null,messageTimer;
const pinsKey='russia.inv.v1.'+account;
let pins=[null,null,null,null];
if(vip){try{const old=JSON.parse(localStorage.getItem(pinsKey));if(Array.isArray(old)&&old.length===pins.length)pins=old.map(k=>typeof k==='string'?k:null)}catch(e){}}
function send(type,action){
 if(finished)return;finished=true;
 location.href='rrp-inv://'+type+'/'+encodeURIComponent(action);
}
function toast(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(messageTimer);messageTimer=setTimeout(()=>$('toast').hidden=true,3000)}
function control(name,fn,cls){const b=create('button',cls);b.type='button';b.setAttribute('aria-label',name);b.onclick=fn;return b}
function clearSheet(restore=true){
 $('sheet').hidden=$('backdrop').hidden=true;
 if(restore&&priorFocus?.isConnected)priorFocus.focus({preventScroll:true});
 priorFocus=null;
}
function goBag(){clearSheet(false);assign=false;selection=null;render();$('scroll').scrollTop=0;$('scroll').focus({preventScroll:true});syncThumb()}
function modal(title,note,actions){
 if($('sheet').hidden)priorFocus=document.activeElement;
 $('sheetName').textContent=title;$('note').textContent=note||'';$('actions').replaceChildren();
 for(const [name,fn,cls] of actions){const b=control(name,fn,cls);b.textContent=name;$('actions').append(b)}
 $('sheet').hidden=$('backdrop').hidden=false;$('cancel').focus({preventScroll:true});
}
$('cancel').onclick=()=>clearSheet();$('backdrop').onclick=()=>clearSheet();
window.bagBack=()=>{if(!$('sheet').hidden){clearSheet();return}if(assign){assign=false;selection=null;render();return}send('action',-1)};
document.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();window.bagBack()}if(e.key==='Tab'&&!$('sheet').hidden){let all=Array.from($('sheet').querySelectorAll('button'));if(e.shiftKey&&document.activeElement===all[0]){e.preventDefault();all[all.length-1].focus()}else if(!e.shiftKey&&document.activeElement===all[all.length-1]){e.preventDefault();all[0].focus()}}});
$('close').onclick=()=>send('action',-1);$('plus').onclick=()=>send('section','donate');
$('backpack').onclick=goBag;
$('name').textContent=account||'Мой персонаж';$('name').title=account;
$('profile').textContent=[rows.has('Уровень')?'Уровень: '+value('Уровень'):null,rows.has('ID')?'ID: '+value('ID'):null].filter(Boolean).join('    ');
const money=value('Наличные');$('cash').textContent=money!=null&&money!==''?format(money):snapshot.cash||'';
if(!$('cash').textContent)document.querySelector('.rub').hidden=true;
const weight=value('Вес'),maxWeight=value('Максимальный вес');
if(weight&&maxWeight&&Number.isFinite(Number(weight))&&Number(maxWeight)>0){$('weight').hidden=false;$('weight').textContent=format(weight)+' / '+format(maxWeight)+' кг'}
const bagButton=control('Инвентарь',goBag,'navbutton current');bagButton.style.gridRow=1;bagButton.setAttribute('aria-current','page');bagButton.append(icon('bag'));$('rail').append(bagButton);
function nav(index,label,symbol,action){const b=control(label,action,'navbutton');b.style.gridRow=index;b.title=label;if(symbol)b.append(icon(symbol));else b.textContent='BP';$('rail').append(b)}
if(rows.has('Профиль'))nav(2,'Статистика','stats',()=>send('action',rows.get('Профиль').row));
nav(3,'Финансы','finance',()=>{const fields=[['Наличные',money??snapshot.cash],['Банк',value('Банк')]].filter(([,v])=>v!=null&&v!=='');modal('Финансы',fields.map(([k,v])=>k+' · '+(Number.isFinite(Number(v))?format(v):v)+' ₽').join('    '),[['Банк',()=>send('section','bank')]])});
if(rows.has('Галерея'))nav(4,'Галерея','image',()=>send('action',rows.get('Галерея').row));
nav(5,'Боевой пропуск',null,()=>send('section','pass'));nav(6,'Достижения','award',()=>send('section','awards'));
const definitions=[
 ['Аптечки','med','Аптечка','Использовать'],['Материалы','metal','Материалы','Сведения'],['Патроны','ammo','Патроны','Сведения'],
 [full?'Вещества':'Наркотики','pouch','Вещества','Использовать 1 г'],['Закуска','snack','Закуска','Съесть']
];
function fromRow(key,label,kind,act,qty=1){const record=rows.get(key);return record?{key,label,kind,act,qty,row:record.row}:null}
const goods=[];
for(const [key,kind,label,act] of definitions){const n=Number(value(key));if(n>0)goods.push(fromRow(key,label,kind,full||!['Материалы','Патроны'].includes(key)?act:'',n))}
const arms=[];
for(const [key,r] of rows){const match=key.match(/^Оружие (\d+)$/);if(!match)continue;
 const [name,ammo]=r.value.split('|');arms.push({...fromRow(key,name,'weapon','Взять в руки'),key:key+':'+name,weaponSlot:Number(match[1]),image:weaponPictures[name],desc:Number(ammo)>0?'Боезапас · '+format(ammo):''})}
const phone=Number(value('Телефон'))>0?fromRow('Телефон','Телефон','phone','Показать номер'):null;
if(phone)phone.desc='Номер · '+value('Телефон');
const kit=[phone,phone?{...phone,key:'SIM',label:'SIM-карта',kind:'sim'}:null,fromRow('Одежда','Гардероб','coat','Гардероб'),fromRow('Аксессуары','Аксессуары','glasses','Коллекция аксессуаров')];
const carried=goods.concat(arms);
const known=new Map([...kit,...carried].filter(Boolean).map(x=>[x.key,x]));
$('eat').onclick=()=>{if(full&&rows.has('Закуска'))send('action',rows.get('Закуска').row);else send('section','eat')};
function empty(cue){const e=create('div','cell empty');e.setAttribute('aria-hidden','true');if(cue){const svg=icon(cue);svg.classList.add('slotcue');e.append(svg)}return e}
function picture(x){
 if(x.image){const img=create('img');img.alt='';img.src=x.image;return img}
 if(x.key==='Аксессуары'){const cue=icon('glasses');cue.classList.add('slotcue','empty-action');return cue}
 if(x.key==='Одежда'&&window.currentLook){const img=create('img');img.alt='';img.src=window.currentLook;return img}
 return art(x.kind);
}
function savePins(){try{localStorage.setItem(pinsKey,JSON.stringify(pins))}catch(e){}}
function startAssign(x){clearSheet(false);assign=true;selection=x;render();$('scroll').scrollTop=$('scroll').scrollHeight;toast('Выберите ячейку для быстрого доступа')}
function choose(x){
 assign=false;selection=x;const actions=[];
 if(x.act)actions.push([x.act,()=>send('action',x.row)]);
 if(vip){const i=pins.indexOf(x.key);if(i>=0)actions.push(['Открепить',()=>{pins[i]=null;savePins();clearSheet(false);selection=null;render()},'secondary']);else actions.push(['В быстрый доступ',()=>startAssign(x),'secondary'])}
 const details=x.desc||(goods.includes(x)?format(x.qty)+(x.kind==='pouch'?' г':' шт.'):'');
 render();modal(x.label,details,actions);
}
function tile(x,count=false){
 const b=control(x.label+(count?' · '+x.qty:''),()=>choose(x),'cell'+(selection?.key===x.key?' selected':''));b.append(picture(x));
 if(count)b.append(create('span','qty',format(x.qty)+(x.kind==='pouch'?' г':' шт.')));
 return b;
}
function quickCell(key,index){
 const x=known.get(key);if(!vip){const e=create('div','cell locked');e.append(icon('lock'),create('small','','Доступно с VIP'));return e}
 const b=control(x?x.label:'Свободная VIP-ячейка '+(index+1),()=>{if(assign&&selection){const k=selection.key;pins=pins.map(v=>v===k?null:v);pins[index]=k;savePins();selection=null;assign=false;render();toast('Предмет закреплён')}else if(x)choose(x);else toast('Выберите предмет и нажмите «В быстрый доступ»')},'cell'+(!x?' pinopen':''));if(x)b.append(picture(x));return b;
}
function render(){
 const g=$('gear'),a=$('weapons'),r=$('grid');g.replaceChildren();a.replaceChildren();r.replaceChildren();
 for(let i=0;i<9;i++)g.append(kit[i]?tile(kit[i]):empty());
 const groups=[[3,4,5,6,7],[2],[1]];const cues=['longarm','sidearm','blade'];
 groups.forEach((slots,i)=>{const x=arms.find(w=>slots.includes(w.weaponSlot));a.append(x?tile(x):empty(cues[i]))});
 carried.forEach(x=>r.append(tile(x,true)));
 const ordinary=Math.max(12,Math.ceil(carried.length/4)*4);
 for(let i=carried.length;i<ordinary;i++)r.append(empty());
 if(full)pins.forEach((k,i)=>r.append(quickCell(k,i)));
 requestAnimationFrame(syncThumb);
}
window.applyInventoryModel=(key,src)=>{if(key==="player"){setInventoryModel(src);return}for(const arm of arms){if(arm.label===key)arm.image=src}render()};
window.setInventoryModel=src=>{const model=$('character');model.onload=()=>{model.hidden=false;document.body.classList.add('modelReady');window.currentLook=src;render()};model.src=src};
const sc=$('scroll'),track=$('track'),thumb=track.firstElementChild;
function syncThumb(){const max=sc.scrollHeight-sc.clientHeight;track.hidden=max<=1;if(max<=1)return;const h=Math.max(12,track.clientHeight*sc.clientHeight/sc.scrollHeight);thumb.style.height=h+'px';thumb.style.transform='translateY('+((track.clientHeight-h)*sc.scrollTop/max)+'px)'}
let grip=0;
function scrub(e){const rect=track.getBoundingClientRect();const travel=rect.height-thumb.offsetHeight;if(travel>0)sc.scrollTop=(sc.scrollHeight-sc.clientHeight)*Math.max(0,Math.min(1,(e.clientY-rect.top-grip)/travel))}
track.onpointerdown=e=>{e.preventDefault();const rect=thumb.getBoundingClientRect();grip=e.clientY>=rect.top&&e.clientY<=rect.bottom?e.clientY-rect.top:rect.height/2;track.setPointerCapture(e.pointerId);scrub(e)};
track.onpointermove=e=>{if(track.hasPointerCapture(e.pointerId))scrub(e)};
sc.addEventListener('scroll',syncThumb,{passive:true});window.addEventListener('resize',syncThumb);
render();
