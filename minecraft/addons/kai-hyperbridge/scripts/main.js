import { world, system } from "@minecraft/server";

const PREFIX = "KAIHB";
const VERSION = "0.1.0";
const SNAPSHOT_TICKS = 4; // 5 Hz at 20 TPS
const ENTITY_RADIUS = 32;
const ENTITY_LIMIT = 16;

function n(v, d = 3) {
  return typeof v === "number" && Number.isFinite(v) ? Number(v.toFixed(d)) : null;
}
function vec(v) {
  return v ? [n(v.x), n(v.y), n(v.z)] : null;
}
function safe(fn, fallback = null) {
  try { return fn(); } catch { return fallback; }
}
function emit(kind, payload) {
  try {
    console.warn(PREFIX + "|" + kind + "|" + JSON.stringify({
      v: VERSION,
      tick: system.currentTick,
      ...payload
    }));
  } catch (e) {
    console.warn(PREFIX + "|ERROR|" + JSON.stringify({ v: VERSION, tick: system.currentTick, where: "emit", error: String(e) }));
  }
}
function healthOf(entity) {
  const h = safe(() => entity.getComponent("minecraft:health"));
  if (!h) return null;
  return {
    current: n(h.currentValue),
    effectiveMax: n(h.effectiveMax),
    defaultValue: n(h.defaultValue)
  };
}
function itemInHand(player) {
  return safe(() => {
    const inv = player.getComponent("minecraft:inventory");
    if (!inv || !inv.container) return null;
    const item = inv.container.getItem(player.selectedSlotIndex);
    if (!item) return null;
    return { typeId: item.typeId, amount: item.amount, nameTag: item.nameTag || null };
  });
}
function blockLook(player) {
  return safe(() => {
    const hit = player.getBlockFromViewDirection({ maxDistance: 16 });
    if (!hit || !hit.block) return null;
    return {
      typeId: hit.block.typeId,
      location: vec(hit.block.location),
      face: hit.face ?? null,
      faceLocation: hit.faceLocation ? vec(hit.faceLocation) : null
    };
  });
}
function entityRecord(player, entity) {
  const p = player.location;
  const q = entity.location;
  const dx = q.x - p.x, dy = q.y - p.y, dz = q.z - p.z;
  return {
    id: safe(() => entity.id),
    typeId: safe(() => entity.typeId),
    nameTag: safe(() => entity.nameTag || null),
    d: n(Math.sqrt(dx*dx + dy*dy + dz*dz), 2),
    rel: [n(dx,2), n(dy,2), n(dz,2)],
    location: vec(q),
    velocity: safe(() => vec(entity.getVelocity())),
    health: healthOf(entity),
    tags: safe(() => entity.getTags().slice(0, 8), [])
  };
}
function nearby(player) {
  return safe(() => {
    const list = player.dimension.getEntities({
      location: player.location,
      maxDistance: ENTITY_RADIUS,
      closest: ENTITY_LIMIT
    });
    const out = [];
    for (const e of list) {
      if (safe(() => e.id) === safe(() => player.id)) continue;
      out.push(entityRecord(player, e));
    }
    out.sort((a,b) => (a.d ?? 9999) - (b.d ?? 9999));
    return out;
  }, []);
}
function snapshotPlayer(player) {
  const loc = player.location;
  return {
    name: player.name,
    id: safe(() => player.id),
    dimension: safe(() => player.dimension.id),
    location: vec(loc),
    rotation: safe(() => {
      const r = player.getRotation();
      return [n(r.x,2), n(r.y,2)];
    }),
    view: safe(() => vec(player.getViewDirection())),
    velocity: safe(() => vec(player.getVelocity())),
    health: healthOf(player),
    selectedSlot: safe(() => player.selectedSlotIndex),
    hand: itemInHand(player),
    lookingAt: blockLook(player),
    entities: nearby(player)
  };
}
function stateTick() {
  const players = safe(() => world.getAllPlayers(), []);
  for (const player of players) {
    emit("STATE", snapshotPlayer(player));
  }
}
function sourceData(ds) {
  if (!ds) return null;
  return {
    cause: safe(() => String(ds.cause)),
    damagingEntity: ds.damagingEntity ? {
      id: safe(() => ds.damagingEntity.id),
      typeId: safe(() => ds.damagingEntity.typeId),
      location: safe(() => vec(ds.damagingEntity.location))
    } : null,
    damagingProjectile: ds.damagingProjectile ? {
      id: safe(() => ds.damagingProjectile.id),
      typeId: safe(() => ds.damagingProjectile.typeId)
    } : null
  };
}
function sub(signalName, handler) {
  const signal = safe(() => world.afterEvents[signalName]);
  if (!signal || typeof signal.subscribe !== "function") {
    emit("CAP", { signal: signalName, available: false });
    return;
  }
  try {
    signal.subscribe((ev) => {
      try { handler(ev); }
      catch (e) { emit("ERROR", { where: signalName, error: String(e) }); }
    });
    emit("CAP", { signal: signalName, available: true });
  } catch (e) {
    emit("CAP", { signal: signalName, available: false, error: String(e) });
  }
}

emit("BOOT", { version: VERSION, api: "@minecraft/server", apiTarget: "2.0.0" });

sub("playerSpawn", ev => emit("EVENT", {
  type: "playerSpawn",
  player: safe(() => ev.player.name),
  initialSpawn: ev.initialSpawn ?? null,
  location: safe(() => vec(ev.player.location))
}));
sub("entityHurt", ev => emit("EVENT", {
  type: "entityHurt",
  target: {
    id: safe(() => ev.hurtEntity.id),
    typeId: safe(() => ev.hurtEntity.typeId),
    location: safe(() => vec(ev.hurtEntity.location))
  },
  damage: n(ev.damage, 2),
  source: sourceData(ev.damageSource)
}));
sub("entityDie", ev => emit("EVENT", {
  type: "entityDie",
  dead: {
    id: safe(() => ev.deadEntity.id),
    typeId: safe(() => ev.deadEntity.typeId),
    location: safe(() => vec(ev.deadEntity.location))
  },
  source: sourceData(ev.damageSource)
}));
sub("entitySpawn", ev => emit("EVENT", {
  type: "entitySpawn",
  entity: {
    id: safe(() => ev.entity.id),
    typeId: safe(() => ev.entity.typeId),
    location: safe(() => vec(ev.entity.location))
  }
}));
sub("playerBreakBlock", ev => emit("EVENT", {
  type: "playerBreakBlock",
  player: safe(() => ev.player.name),
  location: safe(() => vec(ev.block.location)),
  brokenTypeId: safe(() => ev.brokenBlockPermutation.type.id)
}));
sub("playerPlaceBlock", ev => emit("EVENT", {
  type: "playerPlaceBlock",
  player: safe(() => ev.player.name),
  location: safe(() => vec(ev.block.location)),
  typeId: safe(() => ev.block.typeId)
}));
sub("itemUse", ev => emit("EVENT", {
  type: "itemUse",
  source: safe(() => ev.source.name),
  item: ev.itemStack ? { typeId: ev.itemStack.typeId, amount: ev.itemStack.amount } : null
}));

system.runInterval(stateTick, SNAPSHOT_TICKS);
