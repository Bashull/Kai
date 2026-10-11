import { world, system } from "@minecraft/server";

// Sensor only. Disabled by default. No teleport, impulse, damage or block/inventory mutation.
const PREFIX="KAINERVE|1", VERSION="0.1.0", SNAPSHOT_TICKS=4, ENTITY_RADIUS=32, ENTITY_LIMIT=32;
let enabled=false,sessionId=null,seq=0;
const safe=(fn,fallback=null)=>{try{return fn();}catch{return fallback;}};
const n=(v,d=3)=>typeof v==="number"&&Number.isFinite(v)?Number(v.toFixed(d)):null;
const vec=v=>v?[n(v.x),n(v.y),n(v.z)]:null;
function newSession(){sessionId=Date.now().toString(36)+"-"+Math.random().toString(36).slice(2,10);seq=0;}
function emit(kind,payload={},force=false){
 if(!enabled&&!force)return;
 const e={schema:"kai.nerve.sensor.v1",version:VERSION,session_id:sessionId,seq:++seq,
          tick:system.currentTick,observed_wall_ms:Date.now(),enabled,...payload};
 console.warn(`${PREFIX}|${kind}|${JSON.stringify(e)}`);
}
function healthOf(e){const h=safe(()=>e.getComponent("minecraft:health"));return h?{current:n(h.currentValue),effectiveMax:n(h.effectiveMax),defaultValue:n(h.defaultValue)}:null;}
function handOf(p){return safe(()=>{const inv=p.getComponent("minecraft:inventory"),item=inv?.container?.getItem(p.selectedSlotIndex);return item?{typeId:item.typeId,amount:item.amount,nameTag:item.nameTag||null}:null;});}
function lookBlock(p){return safe(()=>{const hit=p.getBlockFromViewDirection({maxDistance:16});if(!hit?.block)return null;return{typeId:hit.block.typeId,location:vec(hit.block.location),face:hit.face??null,faceLocation:hit.faceLocation?vec(hit.faceLocation):null};});}
function entityRecord(p,e){const a=p.location,b=e.location,dx=b.x-a.x,dy=b.y-a.y,dz=b.z-a.z;return{id:safe(()=>e.id),typeId:safe(()=>e.typeId),nameTag:safe(()=>e.nameTag||null),distance:n(Math.sqrt(dx*dx+dy*dy+dz*dz),2),relative:[n(dx,2),n(dy,2),n(dz,2)],location:vec(b),velocity:safe(()=>vec(e.getVelocity())),health:healthOf(e),tags:safe(()=>e.getTags().slice(0,12),[])};}
function nearby(p){return safe(()=>{const list=p.dimension.getEntities({location:p.location,maxDistance:ENTITY_RADIUS,closest:ENTITY_LIMIT}),out=[];for(const e of list){if(safe(()=>e.id)===safe(()=>p.id))continue;out.push(entityRecord(p,e));}out.sort((a,b)=>(a.distance??9999)-(b.distance??9999));return out;},[]);}
function snapshot(p){return{player:{name:p.name,id:safe(()=>p.id),dimension:safe(()=>p.dimension.id),location:vec(p.location),rotation:safe(()=>{const r=p.getRotation();return[n(r.x,2),n(r.y,2)];}),view:safe(()=>vec(p.getViewDirection())),velocity:safe(()=>vec(p.getVelocity())),health:healthOf(p),selectedSlot:safe(()=>p.selectedSlotIndex),hand:handOf(p),lookingAt:lookBlock(p)},entities:nearby(p)};}
function sourceData(ds){if(!ds)return null;return{cause:safe(()=>String(ds.cause)),damagingEntity:ds.damagingEntity?{id:safe(()=>ds.damagingEntity.id),typeId:safe(()=>ds.damagingEntity.typeId),location:safe(()=>vec(ds.damagingEntity.location))}:null,damagingProjectile:ds.damagingProjectile?{id:safe(()=>ds.damagingProjectile.id),typeId:safe(()=>ds.damagingProjectile.typeId)}:null};}
function sub(name,fn){const sig=safe(()=>world.afterEvents[name]);if(!sig?.subscribe)return;sig.subscribe(ev=>{if(!enabled)return;try{fn(ev);}catch(e){emit("ERROR",{where:name,error:String(e)});}});}
newSession();emit("LOADED",{api:"@minecraft/server",apiTarget:"2.0.0"},true);
system.afterEvents.scriptEventReceive.subscribe(ev=>{
 if(ev.id==="kai:nerve_enable"){newSession();enabled=true;emit("ENABLED",{reason:"explicit_scriptevent"});}
 else if(ev.id==="kai:nerve_disable"){emit("DISABLED",{reason:"explicit_scriptevent"},true);enabled=false;}
 else if(ev.id==="kai:nerve_status"){emit("STATUS",{enabled},true);}
});
sub("playerSpawn",ev=>emit("EVENT",{type:"playerSpawn",player:ev.player.name,initialSpawn:ev.initialSpawn??null,location:vec(ev.player.location)}));
sub("entityHurt",ev=>emit("EVENT",{type:"entityHurt",target:{id:safe(()=>ev.hurtEntity.id),typeId:safe(()=>ev.hurtEntity.typeId),location:safe(()=>vec(ev.hurtEntity.location))},damage:n(ev.damage,2),source:sourceData(ev.damageSource)}));
sub("entityDie",ev=>emit("EVENT",{type:"entityDie",dead:{id:safe(()=>ev.deadEntity.id),typeId:safe(()=>ev.deadEntity.typeId),location:safe(()=>vec(ev.deadEntity.location))},source:sourceData(ev.damageSource)}));
sub("entitySpawn",ev=>emit("EVENT",{type:"entitySpawn",entity:{id:safe(()=>ev.entity.id),typeId:safe(()=>ev.entity.typeId),location:safe(()=>vec(ev.entity.location))}}));
sub("playerBreakBlock",ev=>emit("EVENT",{type:"playerBreakBlock",player:ev.player.name,location:vec(ev.block.location),brokenTypeId:safe(()=>ev.brokenBlockPermutation.type.id)}));
sub("playerPlaceBlock",ev=>emit("EVENT",{type:"playerPlaceBlock",player:ev.player.name,location:vec(ev.block.location),typeId:safe(()=>ev.block.typeId)}));
sub("itemUse",ev=>emit("EVENT",{type:"itemUse",source:safe(()=>ev.source.name),item:ev.itemStack?{typeId:ev.itemStack.typeId,amount:ev.itemStack.amount}:null}));
system.runInterval(()=>{if(!enabled)return;for(const p of safe(()=>world.getAllPlayers(),[]))emit("STATE",snapshot(p));},SNAPSHOT_TICKS);
