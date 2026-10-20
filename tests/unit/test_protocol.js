// Protocol, geometry and simulator tests (run: node tests/unit/test_protocol.js)
const fs = require('fs'), os = require('os'), path = require('path');
const SRC = path.join(__dirname, '..', '..', 'src');
global.S={limits:{minR:100,maxR:320,thMin:-90,thMax:90,zMin:-30,zMax:150},speed:{live:100,accel:100},gen:0};
global.DEBUG={frames:false}; global.log=()=>{}; global.setConnected=()=>{};
const src=['part1_protocol.js','part2_geometry.js','part31_kinematics.js','part36_place.js'].map(f=>fs.readFileSync(path.join(SRC,f),'utf8')).join('\n')+
`\nmodule.exports={CMD,encodeFrame,parseFrames,hexOf,rdp,maxReachRect,orderStrokes,buildOps,opsStats,mapToRobot,learnTakes,clampTarget,SimIO,Dobot,stopAll};`;
const bundle=path.join(os.tmpdir(),'magician-protocol-test-bundle.js');
fs.writeFileSync(bundle,src);
const M=require(bundle);
let ok=true; const t=(n,c)=>{console.log((c?'PASS ':'FAIL ')+n); if(!c) ok=false;};
// 1. GET_POSE request must match known bytes AA AA 02 0A 00 F6
t('GET_POSE frame', M.hexOf(M.encodeFrame(10,0,[]))==='AA AA 02 0A 00 F6');
// 2. Queue index request
t('Q_INDEX frame', M.hexOf(M.encodeFrame(246,0,[]))==='AA AA 02 F6 00 0A');
// 3. round trip with checksum validation
const f=M.encodeFrame(84,3,[2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]);
const p=M.parseFrames(f); t('parse roundtrip ok', p.frames.length===1 && p.frames[0].ok && p.frames[0].id===84 && p.rest.length===0);
// 4. split frames across chunks
const a=M.parseFrames(f.slice(0,7)); t('partial frame kept', a.frames.length===0 && a.rest.length===7);
// 5. max reach rect
const r=M.maxReachRect(100,320,5); console.log('  maxRect',r);
t('rect corners inside annulus', Math.hypot(r.x1,r.h)<=315+1e-6 && r.x0>=105-1e-6 && r.area>0);
// 6. clamp
const c=M.clampTarget(500,0,0); t('clamp outer', Math.abs(Math.hypot(c.x,c.y)-320)<1e-6);
const c2=M.clampTarget(10,0,500); t('clamp z', c2.z===150 && Math.abs(Math.hypot(c2.x,c2.y)-100)<1e-6);
// 7. ordering + ops
const strokes=[[{x:0,y:0},{x:10,y:0}],[{x:10.2,y:0},{x:10,y:10}],[{x:200,y:200},{x:210,y:200}],[{x:100,y:100},{x:100,y:110}]];
const seq=M.orderStrokes(strokes,{x:0,y:0},2000);
const ops=M.buildOps(seq,{x:0,y:0},0.5); const st=M.opsStats(ops,{x:0,y:0});
console.log('  ops',ops.length,st);
t('all strokes present', seq.length===4);
t('joined stroke has fewer lifts', st.lifts<=3);
// 8. learning
const takes=[[{x:0,y:0,z:0},{x:10,y:0,z:0}],[{x:0,y:1,z:0},{x:10,y:1,z:0}]];
const L=M.learnTakes(takes,11); t('learn consistency 0.5mm', Math.abs(L.consistency-0.5)<0.01);
// 9. mapToRobot fits
const mapped=M.mapToRobot([[{x:0,y:0},{x:100,y:50}]],{cx:200,cy:0,w:100,h:100});
t('mapped inside rect', mapped[0].every(p=>Math.abs(p.y)<=50.001 && Math.abs(p.x-200)<=50.001));
// 10. simulator round trip via Dobot
(async()=>{ const d=new M.Dobot(new M.SimIO()); await d.init(); await d.ptp(200,50,20); const pz=await d.pose(); console.log('  sim pose',pz);
 t('sim pose after move', Math.abs(pz.y-50)<1e-4 && Math.abs(pz.z-20)<1e-4);
 await d.runQueue([{x:210,y:0,z:20},{pause:10},{x:200,y:0,z:20}]);
 // setSpeed: 83 = ratios (100 %), 81 = mm/s for MOVL, 80 = deg/s for MOVJ
 const sent=[]; const cap={exchange:async f=>{sent.push(M.parseFrames(f).frames[0]); return M.parseFrames(M.encodeFrame(f[3],f[4],[])).frames[0];}};
 const d2=new M.Dobot(cap); await d2.setSpeed(220,264);
 const fl=fr=>{const dv=new DataView(fr.params.buffer,fr.params.byteOffset,fr.params.byteLength); return Array.from({length:fr.params.length/4},(_,i)=>+dv.getFloat32(i*4,true).toFixed(1));};
 t('setSpeed sends ratios 100/100 (cmd 83)', sent[0].id===83 && JSON.stringify(fl(sent[0]))==='[100,100]');
 t('setSpeed sends mm/s for straight moves (cmd 81)', sent[1].id===81 && JSON.stringify(fl(sent[1]))==='[220,220,264,264]');
 t('setSpeed sends deg/s for joint moves (cmd 80)', sent[2].id===80 && fl(sent[2]).length===8 && fl(sent[2])[0]===132);
 console.log(ok?'ALL PASS':'SOME FAILED');
 process.exitCode=ok?0:1;
})();
