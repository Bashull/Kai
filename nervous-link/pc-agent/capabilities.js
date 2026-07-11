'use strict';

const ACTION_CAPABILITY = Object.freeze({
  ping: 'system.read',
  heartbeat: 'system.read',
  device_info: 'system.read',
  list_processes: 'process.list',
  list_directory: 'file.read',
  read_file: 'file.read',
  audit_log: 'system.read',
  write_file: 'file.write',
  run_command: 'command.execute.safe',
  kill_process: 'process.kill',
  kill_switch: 'emergency.kill',
});

module.exports = { ACTION_CAPABILITY };
