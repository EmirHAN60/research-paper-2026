// Optional integration smoke. Never append these requests to the study dataset.
import assert from 'node:assert/strict';
import { DohClient, udpQuery } from '../scripts/dns_client.mjs';
for(const provider of ['cloudflare','google']) {
  const udp=await udpQuery(provider,'example.com');assert.equal(udp.valid,true,udp.error);
  const c=new DohClient(provider);
  try {
    const rows=await Promise.all([c.query('example.com'),c.query('wikipedia.org')]);
    for(const r of rows){assert.equal(r.valid,true,r.error);assert.equal(r.alpn,'h2');assert.equal(r.tls_session_reused,false);assert.ok(Number.isFinite(r.connect_ms));}
    assert.equal(new Set(rows.map(r=>r.connect_ms)).size,1,'Concurrent first queries should share a connection');
    console.log(`${provider}: UDP validated; concurrent initial HTTP/2 queries validated on one unresumed connection`);
  } finally {c.close();}
}

