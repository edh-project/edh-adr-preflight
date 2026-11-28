import test from "node:test";
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import worker, {R10NonceGate} from "./worker.mjs";
globalThis.crypto ??= webcrypto;
const PATH="/v1/chat/completions", url="https://example.invalid"+PATH;
const key="K".repeat(40), grant="Bearer "+"g".repeat(43);
const hex = bytes=>Buffer.from(bytes).toString("hex");
async function request(body="{}", overrides={}) {
 const ts=String(Date.now()), nonce="a".repeat(32);
 const digest=hex(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(body)));
 const msg=["R10-HMAC-v2",ts,nonce,"POST",PATH,digest,hex(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(grant)))].join("\n");
 const k=await crypto.subtle.importKey("raw",new TextEncoder().encode(key),{name:"HMAC",hash:"SHA-256"},false,["sign"]);
 const signature=hex(await crypto.subtle.sign("HMAC",k,new TextEncoder().encode(msg)));
 return new Request(overrides.url||url,{method:overrides.method||"POST",
  body:overrides.method==="GET"?undefined:body,
  headers:{"Content-Type":"application/json","Authorization":grant,
   "X-R10-Timestamp":ts,"X-R10-Nonce":nonce,"X-R10-Signature":signature,...overrides.headers}});
}
function fixture() {
 const calls=[];const seen=new Set();let count=0;
 const env={R10_GATE_ID:"r10-byoi-diagnostic-v1",R10_HMAC_KEY:key,R10_NOT_AFTER:new Date(Date.now()+120000).toISOString(),
  R10_NONCES:{idFromName:()=>({}),get:()=>({fetch:async(_url,opts)=>{
    const {nonce}=JSON.parse(opts.body);
    if(seen.has(nonce))return new Response(null,{status:409});
    if(count>=9)return new Response(null,{status:429});
    seen.add(nonce);count++;return new Response(null,{status:204});
  }})},
  PRIVATE_GATEWAY:{async fetch(target,options){calls.push({target,options});return new Response('{"choices":[]}',{status:200});}}};
 return {env,calls};
}
test("closed without key, nonce binding, deadline, or gate selection",async()=>{
 for(const missing of ["R10_HMAC_KEY","R10_NONCES","R10_NOT_AFTER","R10_GATE_ID"]){
  const {env,calls}=fixture();delete env[missing];
  assert.equal((await worker.fetch(await request(),env,{})).status,503);
  assert.equal(calls.length,0);
 }
});
test("valid signature, fixed destination, and minimal forwarding",async()=>{
 const {env,calls}=fixture();
 assert.equal((await worker.fetch(await request(),env,{})).status,200);
 assert.equal(calls.length,1);
 assert.equal(calls[0].target,"http://localhost"+PATH);
 assert.deepEqual(calls[0].options.headers,{"Content-Type":"application/json","Authorization":grant});
});
test("reject forged signature, modified body, and missing headers",async()=>{
 const {env,calls}=fixture();
 for(const headers of [{"X-R10-Signature":"0".repeat(64)},{"X-R10-Timestamp":"0"},{"X-R10-Nonce":"invalid"}]){
  assert.equal((await worker.fetch(await request("{}",{headers}),env,{})).status,403);
 }
 assert.equal(calls.length,0);
});
test("replay rejected before inference",async()=>{
 const {env,calls}=fixture();const req=await request();
 assert.equal((await worker.fetch(req.clone(),env,{})).status,200);
 assert.equal((await worker.fetch(req.clone(),env,{})).status,409);
 assert.equal(calls.length,1);
});
test("route, method, and oversized body fail closed",async()=>{
 const {env,calls}=fixture();
 assert.equal((await worker.fetch(await request("{}",{url:url+"?q=1"}),env,{})).status,404);
 assert.equal((await worker.fetch(await request("{}",{method:"GET"}),env,{})).status,405);
 assert.equal((await worker.fetch(await request("x".repeat(16385)),env,{})).status,413);
 assert.equal(calls.length,0);
});
test("nonce gate serializes storage, rejects replay and enforces quota",async()=>{
 const m=new Map();let chain=Promise.resolve();
 const storage={transaction:fn=>{
  const run=chain.then(()=>fn({get:async k=>m.get(k),put:async(k,v)=>{m.set(k,v);}}));
  chain=run.catch(()=>{});return run;
 }};
 const gate=new R10NonceGate({storage});
 const deadline=Date.now()+60000;
 const admit=nonce=>gate.fetch(new Request("https://internal/admit",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({nonce,deadline})}));
 const results=await Promise.all(Array.from({length:12},(_,i)=>admit(i.toString(16).padStart(32,"0"))));
 assert.equal(results.filter(r=>r.status===204).length,9);
 assert.equal(results.filter(r=>r.status===429).length,3);
 assert.equal((await admit("0".repeat(32))).status,409);
});

test("diagnostic and benchmark ledgers are distinct and unknown IDs fail closed",async()=>{
 const ids=[];
 const {env}=fixture();
 env.R10_NONCES.idFromName=name=>{ids.push(name);return {};};
 assert.equal((await worker.fetch(await request(),env,{})).status,200);
 env.R10_GATE_ID="r10-byoi-one-shot";
 assert.equal((await worker.fetch(await request(),env,{})).status,200);
 assert.deepEqual(ids,["r10-byoi-diagnostic-v1","r10-byoi-one-shot"]);
 env.R10_GATE_ID="unexpected";
 assert.equal((await worker.fetch(await request(),env,{})).status,503);
 assert.equal(ids.length,2);
});
