const { v4: uuid } = require('uuid');
const db = require('../database');

class AvatarController {
  static async getAvatarState() {
    const companion = await db.get('SELECT * FROM companion LIMIT 1');
    return {
      id: companion?.id || 'kai-001',
      name: companion?.name || 'Kai',
      status: 'active',
      position: { x: 0, y: 0, z: 0 },
      animation: 'idle'
    };
  }

  static async updateAvatarAnimation(animation, duration = 1000) {
    return {
      animation,
      duration,
      timestamp: Date.now()
    };
  }

  static async processInput(input) {
    const { text, intent, emotion } = input;

    // Map intents to animations and gestures
    const animations = {
      greeting: 'wave',
      thinking: 'look_up',
      excited: 'jump',
      confused: 'tilt_head',
      sad: 'head_down',
      happy: 'smile_big',
      listening: 'nod'
    };

    const gesture = animations[intent] || 'listen';

    return {
      response: `I received: "${text}"`,
      gesture,
      emotion: emotion || 'neutral',
      timestamp: Date.now()
    };
  }

  static async createGesture(gestureName, keyframes) {
    const id = uuid();
    await db.run(
      `INSERT INTO animations (id, name, frames, duration) 
       VALUES (?, ?, ?, ?)`,
      [id, gestureName, JSON.stringify(keyframes), keyframes.length * 0.1]
    );
    return { id, name: gestureName, keyframes };
  }

  static async listGestures() {
    return db.all('SELECT * FROM animations ORDER BY created_at DESC');
  }
}

module.exports = AvatarController;
