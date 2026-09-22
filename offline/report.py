"""无第三方前端依赖的离线结果回放；仅播放已计算轨迹，不冒充实时重规划。"""
import json

def write_report(results,path):
    data=json.dumps(results,ensure_ascii=False).replace("</","<\\/")
    template='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>智能车 · 离线验证结果</title><style>
body{font:16px system-ui;background:#f4f5f7;color:#172438;margin:30px auto;max-width:1100px;padding:0 18px}h1{font-size:28px}p{line-height:1.7}.warn{background:#fff1d7;padding:15px;border-radius:8px}.layout{display:grid;grid-template-columns:240px 1fr;gap:18px}button{display:block;width:100%;text-align:left;background:white;border:1px solid #ddd;border-radius:8px;padding:12px;margin:8px 0;cursor:pointer}button.active{border:2px solid #2168b0}canvas{width:100%;background:white;border-radius:12px}#detail{white-space:pre-line;line-height:1.8}input{width:100%}.small{font-size:13px;color:#657184}@media(max-width:650px){.layout{grid-template-columns:1fr}}</style>
<h1>智能车 · 离线验证结果</h1><p>Reeds–Shepp 路径规划 → 跟踪控制 → 同源 C 速度环 → 模拟电机与车辆 → 反馈。<br>这是已运行结果的回放，不连接真实小车。</p>
<p class="warn">实验模型：阿克曼后轴中心坐标。尺寸、电机响应、每圈计数均为仿真假设。通过不代表实车安全或泊车精度达标。</p>
<div class="layout"><aside id="cases"></aside><main><canvas id="view" width="820" height="540"></canvas><input id="time" type="range" min="0" value="0"><button id="play">播放 / 暂停轨迹</button><div id="detail"></div></main></div>
<p class="small">蓝线：规划路径；绿色：已执行轨迹；车身箭头：车头方向（倒车时不翻转）。每个场景 CSV 与 JSON 位于同目录。故障场景的通过表示按预期停止，不表示泊车成功。</p>
<script>const results=DATA;let selected=0,playing=false;const canvas=document.querySelector('#view'),ctx=canvas.getContext('2d'),slider=document.querySelector('#time');
const zh={PARKED:'泊车完成',FAULT:'故障停止',NO_PATH:'拒绝规划',TRACKING:'跟踪中'};
results.forEach((r,i)=>{let b=document.createElement('button');b.textContent=(r.passed?'✓ ':'✗ ')+r.name+' · '+zh[r.status];b.onclick=()=>select(i);document.querySelector('#cases').append(b)});
function select(i){selected=i;playing=false;slider.max=Math.max(0,results[i].trace.length-1);slider.value=0;document.querySelectorAll('#cases button').forEach((b,n)=>b.classList.toggle('active',n===i));draw()}
function draw(){const r=results[selected],n=Number(slider.value),row=r.trace[n];let pts=r.path.flat().concat([r.start,r.goal]);let xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);let minx=Math.min(...xs)-.7,maxx=Math.max(...xs)+.7,miny=Math.min(...ys)-.7,maxy=Math.max(...ys)+.7;let scale=Math.min(780/(maxx-minx),500/(maxy-miny));const X=x=>20+(x-minx)*scale,Y=y=>520-(y-miny)*scale;ctx.clearRect(0,0,820,540);ctx.strokeStyle='#e8edf3';ctx.lineWidth=1;for(let x=Math.ceil(minx*2)/2;x<maxx;x+=.5){ctx.beginPath();ctx.moveTo(X(x),Y(miny));ctx.lineTo(X(x),Y(maxy));ctx.stroke()}for(let y=Math.ceil(miny*2)/2;y<maxy;y+=.5){ctx.beginPath();ctx.moveTo(X(minx),Y(y));ctx.lineTo(X(maxx),Y(y));ctx.stroke()}
function line(ps,color){if(!ps.length)return;ctx.beginPath();ps.forEach((p,i)=>i?ctx.lineTo(X(p[0]),Y(p[1])):ctx.moveTo(X(p[0]),Y(p[1])));ctx.strokeStyle=color;ctx.lineWidth=3;ctx.stroke()}
r.path.forEach(p=>line(p,'#438bd3'));line(r.trace.slice(0,n+1).map(p=>[p.x,p.y]),'#24a279');r.obstacles.forEach(([x,y,rad])=>{ctx.beginPath();ctx.arc(X(x),Y(y),rad*scale,0,2*Math.PI);ctx.fillStyle='#e97765';ctx.fill()});
function car(p,color){ctx.save();ctx.translate(X(p[0]),Y(p[1]));ctx.rotate(-p[2]);ctx.strokeStyle=color;ctx.fillStyle=color+'30';ctx.lineWidth=2;ctx.fillRect(-r.config.rear_overhang_m*scale,-r.config.width_m*scale/2,r.config.length_m*scale,r.config.width_m*scale);ctx.strokeRect(-r.config.rear_overhang_m*scale,-r.config.width_m*scale/2,r.config.length_m*scale,r.config.width_m*scale);ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(.25*scale,0);ctx.lineTo(.20*scale,-.035*scale);ctx.stroke();ctx.restore()}
car(r.goal,'#8997a8');car(row?[row.x,row.y,row.yaw]:r.start,'#16446b');const num=v=>v==null?'无':v.toFixed(3);document.querySelector('#detail').textContent=`${r.name}：${zh[r.status]} / ${r.passed?'符合本场景预期':'未通过'}\n最终位置误差 ${num(r.position_error_m)} m；航向误差 ${num(r.yaw_error_rad)} rad\n原因：${r.reason||'无'}\n${row?`回放 ${row.t_s.toFixed(2)} s · 速度 ${row.speed_mps.toFixed(3)} m/s · duty ${row.duty.toFixed(3)} · ${zh[row.state]}`:''}`;}
slider.oninput=()=>{playing=false;draw()};document.querySelector('#play').onclick=()=>playing=!playing;setInterval(()=>{if(playing){slider.value=Math.min(Number(slider.max),Number(slider.value)+5);draw();if(slider.value===slider.max)playing=false}},50);select(0);</script></html>'''
    path.write_text(template.replace('DATA',data),encoding="utf-8")
