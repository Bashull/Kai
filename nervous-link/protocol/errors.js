'use strict';

class ProtocolError extends Error {
  constructor(code, message, details = null) {
    super(message);
    this.name = 'ProtocolError';
    this.code = code;
    this.details = details;
  }
}

module.exports = {
  ProtocolError,
};
