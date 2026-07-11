'use strict';

const { createRelayServer } = require('../relay/server');

const port = Number(process.env.PORT ?? 8787);
const relay = createRelayServer({
  ownerToken: process.env.KAI_NERVOUS_LINK_OWNER_TOKEN,
});

relay.start(port).then(address => {
  console.log(`KAI Nervous Link relay listening on http://127.0.0.1:${address.port}`);
}).catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});

async function shutdown() {
  await relay.stop();
  process.exit(0);
}

process.once('SIGINT', shutdown);
process.once('SIGTERM', shutdown);
