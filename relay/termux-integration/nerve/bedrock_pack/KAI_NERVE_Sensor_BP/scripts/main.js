import { world, system } from "@minecraft/server";
const PREFIX="KAINERVE|4", VERSION="0.4.1", BUILD_LABEL="kai-nerve-sensor-v0.4.1";
const SNAPSHOT_TICKS=4, HEARTBEAT_TICKS=20, ENTITY_RADIUS=32, ENTITY_LIMIT=64;
let enabled=false, sessionId=null, seq=0, sessionChallenge=null, sessionStartedWallMs=null;
const bootId=Date.now().toString(36)+"-"+Math.random().toString(36).slice(2,12);
const instanceId=bootId+"-"+Math.random().toString(36).slice(2,8);
function safe(fn,fallback=null){try{return fn();}catch(e){return fallback;}}
function n(v,d=3){return typeof v==="number"&&Number.isFinite(v)?Number(v.toFixed(d)):null;}
function vec(v){return v?[n(v.x),n(v.y),n(v.z)]:null;}
function newSession(challenge=null){sessionId=Date.now().toString(36)+"-"+Math.random().toString(36).slice(2,12);seq=0;sessionChallenge=challenge||null;sessionStartedWallMs=Date.now();}
const capabilities={
  snapshot:["position","rotation","view","velocity","health","hand","lookingAt","entities.id","entities.typeId","entities.relative","entities.velocity","entities.health","entities.tags"],
  events:["playerSpawn","entityHurt","entityDie","entitySpawn","playerBreakBlock","playerPlaceBlock","itemUse"],
  transport:"console.warn/logcat-candidate",actuation:false,protocol:4
};
function emit(kind,payload={},force=false){
  if(!enabled&&!force)return;
  const now=Date.now();
  const e={schema:"kai.nerve.sensor.v4",version:VERSION,build_label:BUILD_LABEL,boot_id:bootId,instance_id:instanceId,
    session_id:sessionId,session_started_wall_ms:sessionStartedWallMs,seq:sessionId?++seq:0,tick:system.currentTick,
    observed_wall_ms:now,emitted_wall_ms:Date.now(),enabled,challenge:sessionChallenge,...payload};
  console.warn(`${PREFIX}|${kind}|${JSON.stringify(e)}`);
}
function healthOf(e){const h=safe(()=>e.getComponent("minecraft:health"));return h?{current:n(h.currentValue),effectiveMax:n(h.effectiveMax),defaultValue:n(h.defaultValue)}:null;}
function handOf(p){return safe(()=>{const inv=p.getComponent("minecraft:inventory");const item=inv?.container?.getItem(p.selectedSlotIndex);return item?{typeId:item.typeId,amount:item.amount,nameTag:item.nameTag||null}:null;});}
function lookBlock(p){return safe(()=>{const hit=p.getBlockFromViewDirection({maxDistance:16});if(!hit?.block)return null;return{typeId:hit.block.typeId,location:vec(hit.block.location),face:hit.face??null,faceLocation:hit.faceLocation?vec(hit.faceLocation):null};});}
function entityRecord(p,e){const a=p.location,b=e.location,dx=b.x-a.x,dy=b.y-a.y,dz=b.z-a.z;return{id:safe(()=>e.id),typeId:safe(()=>e.typeId),nameTag:safe(()=>e.nameTag||null),distance:n(Math.sqrt(dx*dx+dy*dy+dz*dz),2),relative:[n(dx,2),n(dy,2),n(dz,2)],location:vec(b),velocity:safe(()=>vec(e.getVelocity())),health:healthOf(e),tags:safe(()=>e.getTags().slice(0,16),[])};}
function nearby(p){try{const list=p.dimension.getEntities({location:p.location,maxDistance:ENTITY_RADIUS,closest:ENTITY_LIMIT+2});const out=[];for(const e of list){if(safe(()=>e.id)===safe(()=>p.id))continue;out.push(entityRecord(p,e));}out.sort((a,b)=>(a.distance??9999)-(b.distance??9999));return{entities:out.slice(0,ENTITY_LIMIT),truncated:out.length>ENTITY_LIMIT,scan_error:null,total_seen:out.length};}catch(e){return{entities:[],truncated:false,scan_error:String(e)};}}
function snapshot(p){const scan=nearby(p);return{player_state:{name:p.name,id:safe(()=>p.id),dimension:safe(()=>p.dimension.id),location:vec(p.location),rotation:safe(()=>{const r=p.getRotation();return[n(r.x,2),n(r.y,2)];}),view:safe(()=>vec(p.getViewDirection())),velocity:safe(()=>vec(p.getVelocity())),health:healthOf(p),selectedSlot:safe(()=>p.selectedSlotIndex),hand:handOf(p),lookingAt:lookBlock(p),entities:scan.entities,entities_truncated:scan.truncated,entity_scan_error:scan.scan_error}};}
function sourceData(ds){if(!ds)return null;return{cause:safe(()=>String(ds.cause)),damagingEntity:ds.damagingEntity?{id:safe(()=>ds.damagingEntity.id),typeId:safe(()=>ds.damagingEntity.typeId),location:safe(()=>vec(ds.damagingEntity.location))}:null,damagingProjectile:ds.damagingProjectile?{id:safe(()=>ds.damagingProjectile.id),typeId:safe(()=>ds.damagingProjectile.typeId)}:null};}
function sub(name,fn){const sig=safe(()=>world.afterEvents[name]);if(!sig?.subscribe)return;sig.subscribe(ev=>{if(!enabled)return;try{fn(ev);}catch(e){emit("ERROR",{where:name,error:String(e)});}});}
emit("BOOT",{capabilities,api:"@minecraft/server",apiTarget:"2.0.0",note:"disabled_default"},true);
system.afterEvents.scriptEventReceive.subscribe(ev=>{
  if(ev.id==="kai:nerve_enable"){
    const challenge=String(ev.message||"").trim();
    if(challenge.length>128){emit("ENABLE_REJECTED",{reason:"challenge_too_long"},true);return;}
    if(!challenge){emit("ENABLE_REJECTED",{reason:"missing_challenge"},true);return;}
    newSession(challenge);enabled=true;emit("ENABLED",{capabilities,reason:"explicit_scriptevent"});
  }else if(ev.id==="kai:nerve_disable"){
    enabled=false;emit("DISABLED",{reason:"explicit_scriptevent"},true);sessionChallenge=null;
  }else if(ev.id==="kai:nerve_status"){
    emit("STATUS",{capabilities,current_session:sessionId},true);
  }
});
sub("playerSpawn",ev=>emit("EVENT",{type:"playerSpawn",player:ev.player.name,initialSpawn:ev.initialSpawn??null,location:vec(ev.player.location)}));
sub("entityHurt",ev=>emit("EVENT",{type:"entityHurt",target:{id:safe(()=>ev.hurtEntity.id),typeId:safe(()=>ev.hurtEntity.typeId),location:safe(()=>vec(ev.hurtEntity.location))},damage:n(ev.damage,2),source:sourceData(ev.damageSource)}));
sub("entityDie",ev=>emit("EVENT",{type:"entityDie",dead:{id:safe(()=>ev.deadEntity.id),typeId:safe(()=>ev.deadEntity.typeId),location:safe(()=>vec(ev.deadEntity.location))},source:sourceData(ev.damageSource)}));
sub("entitySpawn",ev=>emit("EVENT",{type:"entitySpawn",entity:{id:safe(()=>ev.entity.id),typeId:safe(()=>ev.entity.typeId),location:safe(()=>vec(ev.entity.location))}}));
sub("playerBreakBlock",ev=>emit("EVENT",{type:"playerBreakBlock",player:ev.player.name,location:vec(ev.block.location),brokenTypeId:safe(()=>ev.brokenBlockPermutation.type.id)}));
sub("playerPlaceBlock",ev=>emit("EVENT",{type:"playerPlaceBlock",player:ev.player.name,location:vec(ev.block.location),typeId:safe(()=>ev.block.typeId)}));
sub("itemUse",ev=>emit("EVENT",{type:"itemUse",source:safe(()=>ev.source.name),item:ev.itemStack?{typeId:ev.itemStack.typeId,amount:ev.itemStack.amount}:null}));
system.runInterval(()=>{if(!enabled)return;for(const p of safe(()=>world.getAllPlayers(),[])){const s=snapshot(p);if(s.player_state.entity_scan_error)emit("ERROR",{where:"entity_scan",error:s.player_state.entity_scan_error});emit("STATE",s);}},SNAPSHOT_TICKS);
system.runInterval(()=>{if(enabled)emit("HEARTBEAT",{players:safe(()=>world.getAllPlayers().length,0)});},HEARTBEAT_TICKS);
