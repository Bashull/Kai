'use strict';

const fs = require('node:fs/promises');
const path = require('node:path');

class KillSwitch {
  constructor(flagPath) {
    this.flagPath = flagPath;
  }

  async isTriggered() {
    try {
      await fs.access(this.flagPath);
      return true;
    } catch (error) {
      if (error.code === 'ENOENT') return false;
      throw error;
    }
  }

  async trigger(reason = 'manual') {
    await fs.mkdir(path.dirname(this.flagPath), { recursive: true });
    await fs.writeFile(
      this.flagPath,
      JSON.stringify({ reason, timestamp: new Date().toISOString() }),
      'utf8'
    );
  }

  async assertActive() {
    if (await this.isTriggered()) {
      throw new Error('Kai Nervous Link kill switch is triggered');
    }
  }
}

module.exports = { KillSwitch };
