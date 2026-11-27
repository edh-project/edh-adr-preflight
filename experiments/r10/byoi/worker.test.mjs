import test from "node:test";
import assert from "node:assert/strict";
import worker from "./worker.mjs";

const url = "https://example.invalid/v1/chat/completions";
const auth = "Bearer " + "x".repeat(43);
const ctx = {access: {aud: "test-audience"}};
function fixture(status=200, reply='{"choices":[]}') {
  const calls=[];
  const env={
    POLICY_AUD:"test-audience",
    R10_NOT_AFTER:new Date(Date.now()+60000).toISOString(),
    PRIVATE_GATEWAY:{async fetch(target, options) {
      calls.push({target,options});
      return new Response(reply,{status});
    }}
  };
  return {calls,env};
}
function req({target=url,method="POST",body="{}",headers={}}={}) {
  return new Request(target,{method,body:method==="GET"?undefined:body,
    headers:{"Content-Type":"application/json",Authorization:auth,
      "CF-Access-Client-Secret":"fixture-only","Cookie":"fixture-only",...headers}});
}
test("unconfigured deployment fails closed",async()=>{
  const {calls,env}=fixture(); delete env.POLICY_AUD;
  assert.equal((await worker.fetch(req(),env,ctx)).status,503);
  assert.equal(calls.length,0);
});
test("expired deadline closes admission",async()=>{
  const {calls,env}=fixture(); env.R10_NOT_AFTER="2000-01-01T00:00:00Z";
  assert.equal((await worker.fetch(req(),env,ctx)).status,503);
  assert.equal(calls.length,0);
});
test("no authenticated platform context / wrong audience",async()=>{
  const {calls,env}=fixture();
  for(const c of [{},{access:{aud:"wrong"}}])
    assert.equal((await worker.fetch(req(),env,c)).status,403);
  assert.equal((await worker.fetch(req({headers:{"CF-Access-Jwt-Assertion":"forged"}}),env,{})).status,403);
  assert.equal(calls.length,0);
});
test("fixed path, method, no query",async()=>{
  const {calls,env}=fixture();
  assert.equal((await worker.fetch(req({target:url+"?x=1"}),env,ctx)).status,404);
  assert.equal((await worker.fetch(req({target:"https://example.invalid/admin"}),env,ctx)).status,404);
  assert.equal((await worker.fetch(req({method:"GET"}),env,ctx)).status,405);
  assert.equal(calls.length,0);
});
test("invalid grant and content type",async()=>{
  const {calls,env}=fixture();
  assert.equal((await worker.fetch(req({headers:{Authorization:"Bearer bad"}}),env,ctx)).status,401);
  assert.equal((await worker.fetch(req({headers:{"Content-Type":"text/plain"}}),env,ctx)).status,415);
  assert.equal(calls.length,0);
});
test("oversize body and advertised length",async()=>{
  const {calls,env}=fixture();
  assert.equal((await worker.fetch(req({body:"x".repeat(16385)}),env,ctx)).status,413);
  assert.equal((await worker.fetch(req({headers:{"Content-Length":"99999"}}),env,ctx)).status,413);
  assert.equal(calls.length,0);
});
test("only gateway grant and content type forwarded to fixed destination",async()=>{
  const {calls,env}=fixture();
  const res=await worker.fetch(req(),env,ctx);
  assert.equal(res.status,200);
  assert.equal(res.headers.get("Cache-Control"),"no-store");
  assert.equal(calls.length,1);
  assert.equal(calls[0].target,"http://localhost/v1/chat/completions");
  assert.deepEqual(calls[0].options.headers,{"Content-Type":"application/json","Authorization":auth});
  assert.equal(calls[0].options.redirect,"manual");
});
test("gateway denial survives; redirect and failure sanitized",async()=>{
  for(const [status,expected] of [[401,401],[403,403],[429,429],[302,502],[500,502]]){
    const {env}=fixture(status,"private details");
    const res=await worker.fetch(req(),env,ctx);
    assert.equal(res.status,expected);
    assert.ok(!(await res.text()).includes("private details"));
  }
});
test("oversize response and failed binding fail closed",async()=>{
  const {env}=fixture(200,"x".repeat(65537));
  assert.equal((await worker.fetch(req(),env,ctx)).status,502);
  env.PRIVATE_GATEWAY={async fetch(){throw Error("private details");}};
  const res=await worker.fetch(req(),env,ctx);
  assert.equal(res.status,502);
  assert.ok(!(await res.text()).includes("private details"));
});
