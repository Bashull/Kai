import { world, system } from "@minecraft/server";

const SCHEMA = "kai.eyes.v2";
const RANGE = 20;
const MAX_ENTITIES = 16;
const SNAPSHOT_PERIOD = 5;
const HEARTBEAT_PERIOD = 100;
const NEAR_ALERT_RANGE = 8;

const HOSTILE_IDS = [
  "creeper","phantom","zombie","skeleton","spider","enderman","witch","drowned",
  "pillager","ravager","warden","ghast","blaze","hoglin","piglin_brute","slime",
  "magma_cube","vex","guardian","elder_guardian","shulker","silverfish","endermite"
];
const HOSTILE_FAMILIES = ["monster","hostile","enemy","undead","illager","boss"];

let enabled = true;
let sequence = 0;
let lastAlertTick = new Map();

function safe(fn, fallback = null) { try { return fn(); } catch (_) { return fallback; } }
function r1(v) { return Math.round(Number(v || 0) * 10) / 10; }
function vec(v) { return { x:r1(v.x), y:r1(v.y), z:r1(v.z) }; }
function health(entity) {
  const c=safe(()=>entity.getComponent("minecraft:health"));
  if(!c) return null;
  return {current:r1(c.currentValue), max:r1(c.effectiveMax ?? c.defaultValue ?? 0)};
}
function families(entity) {
  const c=safe(()=>entity.getComponent("minecraft:type_family"));
  const values=safe(()=>c?.getTypeFamilies(),[]);
  return Array.isArray(values) ? values.map(String).slice(0,16) : [];
}
function hostileById(typeId) {
  const id=String(typeId||"").toLowerCase();
  return HOSTILE_IDS.some(name=>id.includes(name));
}
function hostileByFamily(values) {
  const normalized=values.map(x=>String(x).toLowerCase());
  return normalized.some(f=>HOSTILE_FAMILIES.some(h=>f===h||f.includes(h)));
}
function classify(entity) {
  const fs=families(entity);
  return {families:fs, threat:hostileByFamily(fs)||hostileById(entity.typeId)};
}
function entityRecord(entity, origin) {
  const loc=safe(()=>entity.location); if(!loc) return null;
  const dx=loc.x-origin.x, dy=loc.y-origin.y, dz=loc.z-origin.z;
  const distance=Math.sqrt(dx*dx+dy*dy+dz*dz);
  const cls=classify(entity);
  return {
    id:String(entity.typeId||"unknown"),
    name:String(safe(()=>entity.nameTag,"")||"").slice(0,80),
    distance:r1(distance),
    relative:{x:r1(dx),y:r1(dy),z:r1(dz)},
    families:cls.families,
    threat:cls.threat,
    hp:health(entity)
  };
}
function output(kind,payload) {
  sequence+=1;
  console.warn("KAI_EYES:"+JSON.stringify({
    schema:SCHEMA,seq:sequence,tick:system.currentTick,kind,...payload
  }));
}
function snapshot(player) {
  if(!enabled) return;
  const origin=safe(()=>player.location), dimension=safe(()=>player.dimension);
  if(!origin||!dimension) return;
  const all=safe(()=>dimension.getEntities({location:origin,maxDistance:RANGE}),[]);
  const records=[];
  for(const entity of all) {
    if(safe(()=>entity.id)===safe(()=>player.id)) continue;
    const rec=entityRecord(entity,origin); if(rec) records.push(rec);
  }
  records.sort((a,b)=>a.distance-b.distance);
  const entities=records.slice(0,MAX_ENTITIES);
  const nearestThreat=entities.find(e=>e.threat)??null;
  output("snapshot",{player:String(player.name||""),dimension:String(dimension.id||""),
    position:vec(origin),health:health(player),entities,nearestThreat});
  const action=nearestThreat
    ? `§cKAI EYES ⚠ ${nearestThreat.id.replace("minecraft:","")} ${nearestThreat.distance}m`
    : `§aKAI EYES §7${r1(origin.x)}, ${r1(origin.y)}, ${r1(origin.z)} §8| §7${entities.length} entidades`;
  safe(()=>player.onScreenDisplay.setActionBar(action));
  if(nearestThreat&&nearestThreat.distance<=NEAR_ALERT_RANGE) {
    const last=lastAlertTick.get(player.id)??-99999;
    if(system.currentTick-last>=60) {
      lastAlertTick.set(player.id,system.currentTick);
      safe(()=>player.sendMessage(`§c[KAI EYES] Amenaza: ${nearestThreat.id} a ${nearestThreat.distance} bloques`));
    }
  }
}
system.runInterval(()=>{ if(enabled) for(const p of world.getAllPlayers()) safe(()=>snapshot(p)); },SNAPSHOT_PERIOD);
system.runInterval(()=>output("heartbeat",{enabled,players:world.getAllPlayers().map(p=>String(p.name||"")).slice(0,8)}),HEARTBEAT_PERIOD);

world.afterEvents.playerSpawn.subscribe(ev=>output("spawn",{player:String(ev.player.name||""),initial:Boolean(ev.initialSpawn),position:vec(ev.player.location)}));
world.afterEvents.entityHurt.subscribe(ev=>{
  const e=ev.hurtEntity; if(!e||e.typeId!=="minecraft:player") return;
  output("hurt",{player:String(safe(()=>e.name,"")||""),health:health(e),damage:r1(ev.damage),
    source:String(safe(()=>ev.damageSource.damagingEntity?.typeId,"unknown")||"unknown")});
});
world.afterEvents.entityDie.subscribe(ev=>{
  const e=ev.deadEntity; if(!e||e.typeId!=="minecraft:player") return;
  output("death",{player:String(safe(()=>e.name,"")||""),
    source:String(safe(()=>ev.damageSource.damagingEntity?.typeId,"unknown")||"unknown")});
});
system.afterEvents.scriptEventReceive.subscribe(ev=>{
  if(ev.id==="kai:eyes_on"){enabled=true;output("control",{enabled:true});}
  else if(ev.id==="kai:eyes_off"){output("control",{enabled:false});enabled=false;}
  else if(ev.id==="kai:eyes_ping"){output("control",{enabled,message:String(ev.message||"").slice(0,120)});}
});
output("boot",{version:"0.2.0",enabled});
