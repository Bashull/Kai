'use strict';

const PROTOCOL_VERSION = 'kai-nervous-link/0.1';

const ACTIONS = Object.freeze([
  'ping',
  'heartbeat',
  'device_info',
  'list_processes',
  'list_directory',
  'read_file',
  'audit_log',
  'write_file',
  'run_command',
  'kill_process',
  'kill_switch',
]);

const CAPABILITIES = Object.freeze([
  'system.read',
  'process.list',
  'process.kill',
  'file.read',
  'file.write',
  'command.execute.safe',
  'adb.read',
  'adb.control',
  'git.read',
  'git.write',
  'emergency.kill',
]);

module.exports = { PROTOCOL_VERSION, ACTIONS, CAPABILITIES };
