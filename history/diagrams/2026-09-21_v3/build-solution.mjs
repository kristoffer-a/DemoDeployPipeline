import { writeFileSync } from 'node:fs';

// Native draw.io shapes and an SVG preview share the same geometry.
export function buildSolution() {
  const c = { ink:'#172B3A', muted:'#526775', blue:'#1766B3', teal:'#087F78', purple:'#7353AC', amber:'#986310' };
  const nodes = [], edges = [];
  const box = (id,parent,x,y,w,h,label,stroke,fill,size=20,bold=false,dash=false) => nodes.push({id,parent,x,y,w,h,label,stroke,fill,size,bold,dash});
  const text = (id,parent,x,y,w,h,label,size=18,color=c.muted,bold=false) => box(id,parent,x,y,w,h,label,'none','none',size,bold),
        labelColor = (id,color) => { nodes.find(n=>n.id===id).color=color; };
  const line = (id,source,target,points,label,x,y,w,color=c.blue,dash=false,sc=[1,.5],tc=[0,.5]) => {
    edges.push({id,source,target,points,color,dash,sc,tc});
    if(label) { box(id+'label','1',x,y,w,30,label,'none','#F7FAFC',16,false); labelColor(id+'label',color); }
  };
  text('title','1',50,35,1450,48,'One solution. Three connected services.',36,c.ink,true); labelColor('title',c.ink);
  text('subtitle','1',50,92,1450,30,'Application components in Power Platform • business data in SharePoint • identities and groups in Entra ID',19);
  box('entra','1',50,145,1500,210,'',c.purple,'#F6F1FA',20);
  text('entra-title','entra',25,16,1400,32,'MICROSOFT ENTRA ID  /  Identity and security groups',23,c.purple,true); labelColor('entra-title',c.purple);
  box('user','entra',40,70,260,95,'User\nSigns in with own Entra account',c.purple,'#FFFFFF',20);
  box('group','entra',580,70,360,95,'Solution users security group\nMembers receive assigned access',c.purple,'#EEE5F7',20);
  box('account','entra',1150,70,300,95,'Licensed service account\nIdentity used for flow connection',c.purple,'#FFFFFF',19);
  box('pp','1',50,465,1000,580,'',c.blue,'#EEF5FD');
  text('pp-title','pp',25,18,900,35,'POWER PLATFORM  /  One environment',23,c.blue,true); labelColor('pp-title',c.blue);
  box('solution','pp',30,80,570,455,'',c.blue,'#FFFFFF',20,false,true);
  text('sol-title','solution',20,12,520,30,'Solution package',22,c.blue,true); labelColor('sol-title',c.blue);
  box('app','solution',30,65,210,110,'Canvas app\nUser interface',c.blue,'#E3EFFC',22,true);
  box('flow','solution',30,285,210,110,'Power Automate\nCloud flows',c.blue,'#E3EFFC',22,true);
  box('ref','solution',320,285,225,110,'Connection references\nUsed by the flows',c.purple,'#F3EDF9',19);
  box('vars','solution',320,145,225,95,'Environment variables\nSite / list configuration\nfor apps and flows',c.purple,'#F3EDF9',18);
  text('sol-rule','solution',20,414,530,27,'Custom components stay within this solution.',16);
  text('conn-title','pp',670,82,300,42,'Connections in this environment\nOutside the solution package',18,c.blue,true); labelColor('conn-title',c.blue);
  box('userconn','pp',685,145,270,110,'User’s SharePoint connection\nAuthenticated as the app user',c.teal,'#E5F5EF',20);
  box('svcconn','pp',685,365,270,110,'Flow’s SharePoint connection\nConfigured service account',c.amber,'#FFF5DE',20);
  box('sp','1',1160,465,390,580,'',c.teal,'#EFF9F5');
  text('sp-title','sp',25,18,345,35,'SHAREPOINT',23,c.teal,true); labelColor('sp-title',c.teal);
  box('spgroup','sp',30,70,330,95,'SharePoint permissions group\nContains the Entra security group\nRead / Contribute as required',c.purple,'#F3EDF9',18);
  box('site','sp',30,215,330,310,'',c.teal,'#FFFFFF');
  text('site-title','site',20,15,290,32,'SharePoint site',23,c.teal,true); labelColor('site-title',c.teal);
  text('site-note','site',20,52,290,45,'Users can open the site directly\nwith their own account.',17);
  box('lists','site',30,130,270,145,'Lists / libraries\nBusiness data\n\nUser or service-account\npermissions are enforced here.',c.teal,'#E5F5EF',18);
  line('membership','user','group',[],'member of',405,244,120,c.purple,true);
  line('appshare','group','app',[[560,275],[560,430],[215,430]],'app sharing',330,414,160,c.purple,true,[0,.63],[.5,0]);
  line('groupaccess','group','spgroup',[[1105,257.5],[1105,580]],'add group',1056,450,100,c.purple,true,[1,.45],[0,.47]);
  line('siteperm','spgroup','site',[],'grants access',1360,638,145,c.purple,true,[.5,1],[.5,0]);
  line('directsite','user','site',[[220,385],[1580,385],[1580,737]],'1  Open SharePoint directly — user authentication',760,369,465,c.teal,false,[.5,1],[1,.184]);
  line('appuser','app','userconn',[],'2  Direct data access as the user',380,624,290,c.teal,false);
  line('userdata','userconn','lists',[[1120,665],[1120,775],[1355,775]],'',0,0,0,c.teal,false,[1,.5],[.5,0]);
  line('invoke','app','flow',[],'3  Call flow',120,760,150,c.blue,false,[.5,1],[.5,0]);
  line('useref','flow','ref',[],'uses',337,858,60,c.blue);
  line('bind','ref','svcconn',[],'binds to',650,858,80,c.blue);
  line('flowdata','svcconn','lists',[],'as service account',1023,900,182,c.amber,false,[1,.55],[0,.55]);
  text('note','1',50,1070,1500,28,'The flow route is explicitly implemented. Its SharePoint actions use the selected connection; they can also be configured to use the invoking user.',17);
  text('legend','1',50,1110,1500,28,'Solid arrows: requests / connection use     Dashed arrows: membership / permission assignment     App sharing and SharePoint permissions are separate.',16);
  const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll('\n','&#xa;');
  let cells='<mxCell id="0"/><mxCell id="1" parent="0"/>';
  for(const n of nodes) {
    const style=`rounded=1;arcSize=10;whiteSpace=wrap;html=0;fontFamily=Helvetica;fontSize=${n.size};fontColor=${n.color||c.ink};fontStyle=${n.bold?1:0};fillColor=${n.fill};strokeColor=${n.stroke};strokeWidth=2;dashed=${n.dash?1:0};align=${n.stroke==='none'?'left':'center'};verticalAlign=middle;spacing=10;container=${['entra','pp','solution','sp','site'].includes(n.id)?1:0};collapsible=0;recursiveResize=0;`;
    cells+=`<mxCell id="${n.id}" parent="${n.parent}" value="${esc(n.label)}" style="${style}" vertex="1"><mxGeometry x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" as="geometry"/></mxCell>`;
  }
  for(const e of edges) cells+=`<mxCell id="${e.id}" parent="1" source="${e.source}" target="${e.target}" edge="1" style="edgeStyle=none;rounded=0;html=0;endArrow=block;endFill=1;strokeWidth=2;strokeColor=${e.color};dashed=${e.dash?1:0};exitX=${e.sc[0]};exitY=${e.sc[1]};entryX=${e.tc[0]};entryY=${e.tc[1]};"><mxGeometry relative="1" as="geometry">${e.points.length?'<Array as="points">'+e.points.map(p=>`<mxPoint x="${p[0]}" y="${p[1]}"/>`).join('')+'</Array>':''}</mxGeometry></mxCell>`;
  const model=`<mxGraphModel grid="0" page="0" pageWidth="1630" pageHeight="1170" background="#F7FAFC"><root>${cells}</root></mxGraphModel>`;
  const absolute=n=>{if(n.parent==='1')return [n.x,n.y];const [x,y]=absolute(nodes.find(p=>p.id===n.parent));return [x+n.x,y+n.y];};
  let svg='<svg xmlns="http://www.w3.org/2000/svg" width="1630" height="1170" viewBox="0 0 1630 1170"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/></marker></defs><rect width="1630" height="1170" fill="#F7FAFC"/>';
  for(const n of nodes) { const [x,y]=absolute(n); if(n.stroke!=='none')svg+=`<rect x="${x}" y="${y}" width="${n.w}" height="${n.h}" rx="12" fill="${n.fill}" stroke="${n.stroke}" stroke-width="2" ${n.dash?'stroke-dasharray="8 6"':''}/>`; }
  for(const e of edges) {const a=nodes.find(n=>n.id===e.source),b=nodes.find(n=>n.id===e.target),ap=absolute(a),bp=absolute(b);const pts=[[ap[0]+a.w*e.sc[0],ap[1]+a.h*e.sc[1]],...e.points,[bp[0]+b.w*e.tc[0],bp[1]+b.h*e.tc[1]]];svg+=`<polyline points="${pts.map(p=>p.join(',')).join(' ')}" fill="none" stroke="${e.color}" stroke-width="2" ${e.dash?'stroke-dasharray="7 5"':''} marker-end="url(#arrow)"/>`;}
  for(const n of nodes) {const [x,y]=absolute(n),ls=n.label.split('\n'),cx=n.stroke==='none'?x+10:x+n.w/2,cy=y+n.h/2-(ls.length-1)*n.size*.66+n.size*.35;if(n.stroke==='none'&&n.fill!=='none')svg+=`<rect x="${x}" y="${y}" width="${n.w}" height="${n.h}" fill="${n.fill}"/>`;svg+=`<text font-family="Arial,Helvetica,sans-serif" font-size="${n.size}" font-weight="${n.bold?700:400}" fill="${n.color||c.ink}" text-anchor="${n.stroke==='none'?'start':'middle'}">${ls.map((l,i)=>`<tspan x="${cx}" y="${cy+i*n.size*1.32}">${esc(l)}</tspan>`).join('')}</text>`;}
  return {model,drawio:`<mxfile host="app.diagrams.net" type="device"><diagram id="solution-access-v3" name="Solution — components and access">${model}</diagram></mxfile>`,svg:svg+'</svg>'};
}

if (process.argv[1] && import.meta.url === new URL(process.argv[1], 'file:').href) {
  const result=buildSolution();
  writeFileSync(new URL('./solution-access.drawio',import.meta.url),result.drawio);
  writeFileSync(new URL('./solution-access.svg',import.meta.url),result.svg);
  console.log('Created editable solution-access.drawio and matching SVG.');
}
