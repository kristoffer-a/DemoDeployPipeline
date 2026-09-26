"""Build the three ALM views; keep the first revision untouched."""
from drawing import Page, C, ET, OUT


def card(p, x, y, w, h, title, body='', fill='white', accent=None, size=20):
    """A native editable shape with labels attached to it in draw.io."""
    i=p.box(x,y,w,h,fill,accent or C['line'])
    start=len(p.root)
    p.text(x+20,y+15,w-40,title,size,accent or C['ink'],True)
    if body: p.text(x+20,y+51,w-40,body,17,C['muted'])
    for cell in list(p.root)[start:]:
        cell.set('parent',i)
        g=cell.find('mxGeometry')
        g.set('x',str(float(g.get('x'))-x)); g.set('y',str(float(g.get('y'))-y))
    return i


def diamond(p,x,y,w,h,text):
    i=p.cell('',f'rhombus;whiteSpace=wrap;html=0;fillColor={C["amberbg"]};strokeColor={C["amber"]};strokeWidth=1.5;',x,y,w,h)
    p.boxes[i]=(x,y,w,h)
    p.svg.append(f'<polygon points="{x+w/2},{y} {x+w},{y+h/2} {x+w/2},{y+h} {x},{y+h/2}" fill="{C["amberbg"]}" stroke="{C["amber"]}" stroke-width="1.5"/>')
    start=len(p.root)
    lines=text.split('\n'); ty=y+(h-len(lines)*25)/2
    p.text(x+20,ty,w-40,text,19,C['amber'],True,'center')
    c=list(p.root)[start]; c.set('parent',i)
    g=c.find('mxGeometry'); g.set('x','20'); g.set('y',str(ty-y))
    return i


def heading(p,number,title,subtitle):
    p.text(60,28,1680,f'{number}  /  POWER PLATFORM ALM',15,C['teal'],True)
    p.text(60,64,1680,title,36,bold=True)
    p.text(60,117,1680,subtitle,20,C['muted'])


# 1. Definition: one clean view of application, data and identity boundaries.
p=Page('01 — Solution definition',1600,1000)
p.text(40,42,1460,'A solution: application, data and identity boundaries',30,bold=True)
p.text(40,94,1460,'One business capability. Direct app calls use the signed-in person’s SharePoint permissions; flow calls use the configured connection identity.',17,C['muted'])

# System boundaries. The dashed inner box is the actual solution package.
p.box(40,150,850,650,C['bluebg'],C['blue'],radius=18)
p.box(940,150,600,285,C['purplebg'],C['purple'],radius=18)
p.box(940,485,600,315,C['tealbg'],C['teal'],radius=18)
p.box(85,255,615,465,'white',C['blue'],dash=True,radius=18)
p.text(70,175,350,'POWER PLATFORM',20,C['blue'],True)
p.text(70,207,400,'Shared environment — Dev, Test or Prod',14,C['muted'])
p.text(110,275,310,'SOLUTION PACKAGE',17,C['blue'],True)
p.text(110,305,420,'Unmanaged in Dev • managed in Test and Prod',14,C['muted'])

app=card(p,120,365,235,110,'Canvas app','User experience and\nbusiness logic',C['bluebg'],C['blue'],size=17)
flow=card(p,420,365,235,110,'Cloud flows','Automation for this\nbusiness need',C['bluebg'],C['blue'],size=17)
env=card(p,120,555,235,105,'Environment variables','Site, list and stage-specific\nvalues',C['purplebg'],C['purple'],size=16)
ref=card(p,420,555,235,105,'Connection references','Included in the solution',C['purplebg'],C['purple'],size=16)
p.text(720,274,145,'TARGET CONNECTIONS\n(not solution components)',14,C['blue'],True,'center')
conn=card(p,725,350,140,145,'Connections','App user’s own\nSharePoint connection\nFlow service-account\nconnection','white',C['blue'],size=15)

p.text(970,175,350,'MICROSOFT ENTRA ID',20,C['purple'],True)
p.text(970,207,350,'Security groups and licensed identities',14,C['muted'])
appgroup=card(p,975,260,245,105,'Entra security group','Canvas app sharing\nMay be added to\nSharePoint groups',C['purplebg'],C['purple'],size=16)
service=card(p,1255,260,245,105,'Licensed service accounts','Used by cloud-flow connections','white',C['purple'],size=16)

p.text(970,510,350,'SHAREPOINT',20,C['teal'],True)
p.text(970,542,390,'Business data and role-based site access',14,C['muted'])
site=card(p,975,600,165,105,'SharePoint site','Stage-specific\nlocation',C['tealbg'],C['teal'],size=16)
lists=card(p,1170,600,165,105,'Lists','Business data\nand schema',C['tealbg'],C['teal'],size=16)
spgroups=card(p,1365,600,150,105,'SharePoint groups','Role-based site/list\npermissions','white',C['teal'],size=16)

# Runtime paths use solid lines; assignment and configuration use dashed lines.
p.edge(app,flow,sc=(1,.5),tc=(0,.5)); p.text(360,405,55,'calls',13,C['blue'],False,'center')
p.edge(env,app,sc=(.5,0),tc=(.5,1),color=C['purple'],dash=True); p.text(185,500,100,'configures',13,C['purple'],False,'center')
p.edge(flow,ref,sc=(.5,1),tc=(.5,0)); p.text(485,505,55,'uses',13,C['blue'],False,'center')
p.edge(ref,conn,sc=(1,.5),tc=(.5,1),points=[(700,607),(795,607)],color=C['blue']); p.text(660,595,60,'binds',13,C['blue'],False,'center')
p.edge(appgroup,app,sc=(0,.1),tc=(1,.5),points=[(900,270),(900,420)],color=C['purple'],dash=True)
p.edge(service,conn,sc=(.4,1),tc=(.6,0),points=[(1350,450),(810,450)],color=C['purple'],dash=True)
p.edge(app,site,sc=(.5,1),tc=(.5,1),points=[(238,755),(1058,755)],color=C['teal']); p.text(440,740,320,'app user’s own SharePoint connection and permissions',13,C['teal'],False,'center')
p.edge(conn,lists,sc=(.5,1),tc=(.5,1),points=[(795,775),(1252,775)],color=C['teal']); p.text(805,754,320,'flow uses the configured connection identity',13,C['teal'],False,'center')
p.edge(appgroup,spgroups,sc=(.85,1),tc=(.5,0),color=C['purple'],dash=True); p.text(1375,455,160,'group membership',13,C['purple'],False,'center')
p.text(40,840,1480,'Solid arrows show runtime behaviour. Dashed arrows show configuration or access assignment. Each environment has its own connections, groups, site and list mapping.',14,C['muted'])
p.save('01-solution-definition.svg')


# 2. Strategy: independent business rows across the three shared lifecycle stages.
s=Page('02 — Solution strategy',1800,1290)
heading(s,'02','Several business solutions. Three shared environments.','Each business solution follows the same lifecycle and retains its own components, audience and SharePoint mapping.')
xs=[250,790,1330]; accents=[C['blue'],C['purple'],C['teal']]; tints=[C['bluebg'],C['purplebg'],C['tealbg']]
stages=['Dev','Test','Prod']
for x,stage,accent,tint in zip(xs,stages,accents,tints):
    s.box(x,180,410,897,'white')
    s.box(x,180,410,77,tint,tint)
    s.text(x+22,192,365,stage.upper(),28,accent,True)
    s.text(x+22,229,365,'One shared Power Platform environment',16,C['muted'])
    members={'Dev':'Makers + admins + service users','Test':'Testers + admins + service users','Prod':'Business users + admins + service users'}[stage]
    card(s,x+15,275,380,99,'Environment admission',members+'\nEnvironment group + assigned roles',size=19)
s.text(60,283,170,'ACCESS',15,C['muted'],True)
s.text(60,313,170,'Stage-wide\nmembership',18,C['muted'])
for ri,letter in enumerate(['A','B','N']):
    y=417+ri*215
    s.text(60,y+18,175,f'BUSINESS NEED {letter}',15,C['ink'],True)
    s.text(60,y+53,175,'Independent owner\nand release cycle',17,C['muted'])
    sol=[]
    for ci,(x,stage,accent,tint) in enumerate(zip(xs,stages,accents,tints)):
        kind='Unmanaged source' if ci==0 else 'Managed package'
        node=card(s,x+15,y,380,79,f'Solution {letter}',kind,tint,accent,size=21)
        sol.append(node)
        s.text(x+30,y+94,345,f'App group   SG-{letter}-{stage}-Users',16,C['ink'])
        s.text(x+30,y+124,345,f'Data site     /sites/{letter}-{stage}',16,C['teal'])
        s.text(x+30,y+151,345,'Connection + variable values for this stage',14,C['muted'])
    for j in range(2):
        s.edge(sol[j],sol[j+1],sc=(1,.5),tc=(0,.5),color=accents[j+1])
        s.text(xs[j]+423,y+6,102,'deploy' if j==0 else 'promote',14,accents[j+1],False,'center')
s.text(60,1097,1680,'READ ACROSS  /  The same business solution moves from Dev to Test to Prod. Each row can release independently.',18,C['ink'],True)
s.text(60,1137,1680,'READ DOWN  /  Multiple solutions share the environment. Custom component dependencies between business solutions are prohibited.',18,C['ink'])
s.box(60,1180,1680,69,C['tealbg'],C['tealbg'])
s.text(80,1192,1640,'SharePoint remains outside Power Platform. Site names above are illustrative mappings, not a requirement for one site per solution.\nDataverse stores solution metadata. Runtime identities are assigned from the available service accounts; no account per solution is implied.',16,C['teal'])
s.save('02-solution-strategy.svg')


# 3. Deployment flow: actual process and decisions, with deliberate return paths.
f=Page('03 — Deployment pipeline',1800,1360)
heading(f,'03','Deployment pipeline','Manual export and import today. The same controlled sequence can later be automated.')
for y,h,title,accent,tint in [(185,235,'DEV  /  BUILD & PACKAGE',C['blue'],C['bluebg']),(475,345,'TEST  /  VALIDATE',C['purple'],C['purplebg']),(870,415,'PROD  /  RELEASE & VERIFY',C['teal'],C['tealbg'])]:
    f.box(60,y,1680,h,tint,tint)
    f.text(80,y+15,1600,title,16,accent,True)
build=card(f,220,264,300,116,'1  Build in Dev','Update the unmanaged solution.\nComplete checks and publish.',accent=C['blue'])
export=card(f,680,264,300,116,'2  Version and export','Managed deployment ZIP\nUnmanaged source snapshot',accent=C['blue'])
archive=card(f,1140,264,480,116,'3  Archive the release bundle','Packages + manifest + SharePoint changes\nRecord version and package checksum.',accent=C['blue'])
f.edge(build,export,sc=(1,.5),tc=(0,.5)); f.edge(export,archive,sc=(1,.5),tc=(0,.5))
prep=card(f,1290,551,340,126,'4  Prepare Test','Provision / update SharePoint.\nPrepare connections and values.',accent=C['purple'])
imp=card(f,830,551,340,126,'5  Import into Test','Import the managed package.\nBind Test connections and values.',accent=C['purple'])
test=card(f,370,551,340,126,'6  Verify the release','Check target data and flow state.\nRun functional testing and UAT.',accent=C['purple'])
passed=diamond(f,90,541.5,210,145,'Tests\npassed?')
f.edge(archive,prep,points=[(1380,446),(1460,446)],color=C['purple'])
f.edge(prep,imp,sc=(0,.5),tc=(1,.5),color=C['purple']); f.edge(imp,test,sc=(0,.5),tc=(1,.5),color=C['purple']); f.edge(test,passed,sc=(0,.5),tc=(1,.5),color=C['purple'])
f.edge(passed,build,sc=(0,.5),tc=(0,.5),points=[(35,614),(35,322)],color=C['amber'])
f.text(70,426,550,'NO  /  Fix in Dev, create a new version and repeat',16,C['amber'],True)
f.text(385,721,1200,'The Test result and acceptance evidence refer to the exact archived managed package.',18,C['purple'])
approve=card(f,90,942,300,132,'7  Release approval','Approve the exact release bundle.\nIf withheld: hold at this step.',accent=C['teal'])
prodprep=card(f,490,942,300,132,'8  Prepare Prod','Apply planned SharePoint changes.\nPrepare Prod configuration.',accent=C['teal'])
prodimp=card(f,890,942,300,132,'9  Import into Prod','Use the managed ZIP from step 3.\nBind Prod connections and values.',accent=C['teal'])
smoke=diamond(f,1280,929,240,158,'10  Smoke test\npassed?')
live=card(f,1570,970,145,73,'Released',fill=C['tealbg'],accent=C['teal'],size=18)
recover=card(f,1230,1162,465,92,'Recover / correct','Follow the agreed recovery plan; retest.',fill=C['amberbg'],accent=C['amber'],size=19)
f.edge(passed,approve,tc=(5/6,0),points=[(195,853),(340,853)],color=C['teal'])
f.text(211,768,140,'YES',16,C['teal'],True)
f.edge(approve,prodprep,sc=(1,.5),tc=(0,.5),color=C['teal']); f.text(395,979,95,'approved',14,C['teal'])
f.edge(prodprep,prodimp,sc=(1,.5),tc=(0,.5),color=C['teal']); f.edge(prodimp,smoke,sc=(1,.5),tc=(0,.5),color=C['teal'])
f.edge(smoke,live,sc=(1,.5),tc=(0,.5),color=C['teal']); f.text(1525,976,45,'YES',13,C['teal'],True)
f.edge(smoke,recover,tc=(170/465,0),color=C['amber']); f.text(1423,1116,80,'NO',15,C['amber'],True)
f.edge(recover,smoke,sc=(0,.5),tc=(.25,.75),points=[(1210,1208),(1210,1107),(1340,1107)],color=C['amber'],dash=True)
f.text(92,1140,1070,'PROMOTION RULE',15,C['teal'],True)
f.text(92,1174,1060,'One managed artifact travels through Test and Prod.\nA change to the package returns to Dev and Test; it requires renewed approval.',19,C['ink'])
f.text(60,1310,1680,'Release completion: record the deployed version, configuration, approval and verification result. Monitor the solution after release.',17,C['muted'])
f.save('03-deployment-pipeline.svg')

mx=ET.Element('mxfile',host='app.diagrams.net',agent='Codex',version='24.7.17',type='device')
for n,page in enumerate([p,s,f],1):
    d=ET.SubElement(mx,'diagram',id=f'alm-v2-{n}',name=page.name); d.append(page.model)
ET.indent(mx)
ET.ElementTree(mx).write(OUT/'power-platform-alm-v2.drawio',encoding='utf-8',xml_declaration=True)
print('Generated 3 native draw.io pages and matching SVG previews.')
