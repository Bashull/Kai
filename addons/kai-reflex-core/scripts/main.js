import { world, system } from "@minecraft/server";

const CONFIG = Object.freeze({
  tickInterval: 2,
  scanRadius: 6.0,
  creeperRadius: 4.25,
  criticalRadius: 1.75,
  damageFallbackRadius: 4.5,
  horizontalImpulse: 0.42,
  verticalImpulse: 0.08,
  cooldownTicks: 12,
  epsilon: 0.0001,
});

const state = new Map();
let tick = 0;

function distSq(a, b) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  const dz = a.z - b.z;
  return dx * dx + dy * dy + dz * dz;
}

function nearestEntity(origin, entities) {
  let best = undefined;
  let bestD2 = Number.POSITIVE_INFINITY;
  for (const entity of entities) {
    try {
      if (entity.typeId === "minecraft:player") continue;
      const d2 = distSq(origin, entity.location);
      if (d2 < bestD2) {
        bestD2 = d2;
        best = entity;
      }
    } catch {
      // Entity may have despawned between query and inspection.
    }
  }
  return best ? { entity: best, distance: Math.sqrt(bestD2) } : undefined;
}

function getHealth(player) {
  try {
    const health = player.getComponent("minecraft:health");
    return health ? Number(health.currentValue) : undefined;
  } catch {
    return undefined;
  }
}

function getMonsterThreat(player) {
  try {
    const entities = player.dimension.getEntities({
      location: player.location,
      maxDistance: CONFIG.scanRadius,
      closest: 16,
      families: ["monster"],
    });
    return nearestEntity(player.location, entities);
  } catch {
    return undefined;
  }
}

function getFallbackThreat(player) {
  try {
    const entities = player.dimension.getEntities({
      location: player.location,
      maxDistance: CONFIG.damageFallbackRadius,
      closest: 12,
      excludeTypes: [
        "minecraft:player",
        "minecraft:item",
        "minecraft:xp_orb",
        "minecraft:area_effect_cloud",
      ],
    });
    return nearestEntity(player.location, entities);
  } catch {
    return undefined;
  }
}

function evade(player, threat, reason) {
  const p = player.location;
  const q = threat.entity.location;
  let dx = p.x - q.x;
  let dz = p.z - q.z;
  let mag = Math.sqrt(dx * dx + dz * dz);

  if (mag < CONFIG.epsilon) {
    try {
      const view = player.getViewDirection();
      dx = -view.x;
      dz = -view.z;
      mag = Math.sqrt(dx * dx + dz * dz);
    } catch {
      return false;
    }
  }
  if (mag < CONFIG.epsilon) return false;

  const impulse = {
    x: (dx / mag) * CONFIG.horizontalImpulse,
    y: CONFIG.verticalImpulse,
    z: (dz / mag) * CONFIG.horizontalImpulse,
  };

  try {
    player.applyImpulse(impulse);
    console.warn(
      `KAI_REFLEX|${reason}|player=${player.name}|threat=${threat.entity.typeId}|distance=${threat.distance.toFixed(2)}|impulse=${impulse.x.toFixed(3)},${impulse.y.toFixed(3)},${impulse.z.toFixed(3)}`
    );
    return true;
  } catch (e) {
    console.warn(`KAI_REFLEX_ERROR|${String(e)}`);
    return false;
  }
}

system.runInterval(() => {
  tick += CONFIG.tickInterval;

  for (const player of world.getAllPlayers()) {
    const key = player.name;
    const health = getHealth(player);
    const previous = state.get(key) ?? {
      health,
      lastReflexTick: -100000,
    };

    const damaged =
      health !== undefined &&
      previous.health !== undefined &&
      health < previous.health - 0.01;

    const monster = getMonsterThreat(player);
    let threat = monster;
    let reason = undefined;

    if (monster) {
      const type = monster.entity.typeId;
      if (type === "minecraft:creeper" && monster.distance <= CONFIG.creeperRadius) {
        reason = "creeper_proximity";
      } else if (monster.distance <= CONFIG.criticalRadius) {
        reason = "monster_critical";
      } else if (damaged && monster.distance <= CONFIG.scanRadius) {
        reason = "damage_monster";
      }
    }

    if (damaged && !reason) {
      const fallback = getFallbackThreat(player);
      if (fallback) {
        threat = fallback;
        reason = "damage_unknown";
      }
    }

    if (
      reason &&
      threat &&
      tick - previous.lastReflexTick >= CONFIG.cooldownTicks
    ) {
      if (evade(player, threat, reason)) {
        previous.lastReflexTick = tick;
      }
    }

    previous.health = health;
    state.set(key, previous);
  }
}, CONFIG.tickInterval);

world.afterEvents.playerSpawn.subscribe((event) => {
  const player = event.player;
  state.set(player.name, {
    health: getHealth(player),
    lastReflexTick: -100000,
  });
  console.warn(`KAI_REFLEX_READY|player=${player.name}|initial=${event.initialSpawn}`);
});

console.warn("KAI_REFLEX_CORE|loaded|version=0.1.0");
