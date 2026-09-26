"""Generate editable draw.io diagrams and matching SVG previews (stdlib only)."""
from pathlib import Path
from xml.etree import ElementTree as ET
from html import escape

OUT = Path(__file__).resolve().parent
C = dict(ink='#172B3A', muted='#526775', line='#C7D4DC', bg='#F3F7FA',
         blue='#1766B3', bluebg='#EAF3FD', teal='#087F78', tealbg='#E6F5F1',
         purple='#7353AC', purplebg='#F1ECF8', amber='#986310', amberbg='#FFF5DD')

class Page:
    def __init__(self, name, w, h):
        self.name, self.w, self.h = name, w, h
        self.model = ET.Element('mxGraphModel', dx=str(w), dy=str(h), grid='1', gridSize='10', page='1', pageWidth=str(w), pageHeight=str(h), background=C['bg'])
        self.root = ET.SubElement(self.model, 'root')
        ET.SubElement(self.root, 'mxCell', id='0')
        ET.SubElement(self.root, 'mxCell', id='1', parent='0')
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
                    '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/></marker></defs>',
                    f'<rect width="{w}" height="{h}" fill="{C["bg"]}"/>']
        self.n = 0
        self.boxes = {}

    def cell(self, value, style, x,y,w,h):
        self.n += 1
        i = f'n{self.n}'
        c=ET.SubElement(self.root, 'mxCell', id=i, value=value, style=style, vertex='1', parent='1')
        ET.SubElement(c, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), attrib={'as':'geometry'})
        return i

    def box(self,x,y,w,h,fill='white',stroke=None,dash=False,radius=14):
        stroke=stroke or C['line']
        i=self.cell('', f'rounded=1;arcSize=10;whiteSpace=wrap;html=0;fillColor={fill};strokeColor={stroke};strokeWidth=1.5;dashed={int(dash)};',x,y,w,h)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"'+(' stroke-dasharray="7 5"' if dash else '')+'/>')
        self.boxes[i]=(x,y,w,h)
        return i

    def text(self,x,y,w,text,size=18,color=None,bold=False,align='left',line=1.35):
        color=color or C['ink']; lines=text.split('\n'); h=len(lines)*size*line+4
        self.cell(text,f'text;html=0;strokeColor=none;fillColor=none;align={align};verticalAlign=top;whiteSpace=wrap;rounded=0;fontFamily=Helvetica;fontSize={size};fontColor={color};fontStyle={int(bold)};spacing=0;',x,y,w,h)
        tx=x if align=='left' else x+w/2
        anchor='start' if align=='left' else 'middle'
        self.svg.append(f'<text x="{tx}" y="{y+size}" fill="{color}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" text-anchor="{anchor}">')
        for n,t in enumerate(lines):
            self.svg.append(f'<tspan x="{tx}" dy="{0 if n==0 else size*line}">{escape(t)}</tspan>')
        self.svg.append('</text>')

    def card(self,x,y,w,h,title,body,fill='white',accent=None):
        i=self.box(x,y,w,h,fill)
        self.text(x+20,y+14,w-40,title,20,accent or C['ink'],True)
        self.text(x+20,y+48,w-40,body,17,C['muted'])
        return i

    def edge(self,src,dst,points=None,sc=(.5,1),tc=(.5,0),color=None,dash=False):
        color=color or C['blue']
        x,y,w,h=self.boxes[src]; start=(x+w*sc[0],y+h*sc[1])
        x,y,w,h=self.boxes[dst]; end=(x+w*tc[0],y+h*tc[1])
        pts=[start]+(points or [])+[end]
        self.n+=1
        cell=ET.SubElement(self.root,'mxCell',id=f'n{self.n}',style=f'edgeStyle=none;rounded=0;html=0;endArrow=block;endFill=1;strokeWidth=2;strokeColor={color};dashed={int(dash)};exitX={sc[0]};exitY={sc[1]};exitDx=0;exitDy=0;entryX={tc[0]};entryY={tc[1]};entryDx=0;entryDy=0;',edge='1',source=src,target=dst,parent='1')
        geo=ET.SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})
        if points:
            arr=ET.SubElement(geo,'Array',attrib={'as':'points'})
            for px,py in points: ET.SubElement(arr,'mxPoint',x=str(px),y=str(py))
        self.svg.append(f'<polyline points="'+ ' '.join(f'{a},{b}' for a,b in pts)+f'" fill="none" stroke="{color}" stroke-width="2" marker-end="url(#arrow)"'+(' stroke-dasharray="7 5"' if dash else '')+'/>')

    def save(self,filename):
        (OUT/filename).write_text('\n'.join(self.svg+['</svg>']))

p=Page('01 — Environment and release model',1580,1260)
p.text(50,32,1400,'A practical ALM model for Power Platform',34,bold=True)
p.text(50,85,1480,'Three shared environments · SharePoint business data · Dataverse metadata · Manual solution delivery',20,C['muted'])
p.text(50,122,1450,'REFERENCE DESIGN  /  Confirmed constraints, with recommended access and release controls',14,C['teal'],True)

stages=[('DEV','Build and own the source',C['blue'],C['bluebg'],
         'Makers + admins + runtime accounts','Development users, per solution','Unmanaged solutions','Developers may change components.','Dev sites + lists','Synthetic / non-sensitive test data'),
        ('TEST','Validate a release candidate',C['purple'],C['purplebg'],
         'Testers + admins + runtime accounts','UAT testers, per solution','Managed solutions','Test the package intended for Prod.','Test sites + lists','Independent from Dev and Prod'),
        ('PROD','Operate the approved release',C['teal'],C['tealbg'],
         'End users + admins + runtime accounts','Business users, per solution','Managed solutions','Restrict maker and co-owner rights.','Production sites + lists','Business data; explicit access grants')]
for idx,(name,desc,accent,tint,members,audience,kind,detail,sites,data) in enumerate(stages):
    x=50+idx*505
    p.box(x,172,470,782,'white')
    p.box(x,172,470,88,tint,tint)
    p.text(x+24,185,420,name,27,accent,True)
    p.text(x+24,222,420,desc,17,C['muted'])
    p.card(x+20,280,430,99,'01  Environment admission',members+'\nEnvironment group + required roles',accent=accent)
    p.card(x+20,398,430,118,'02  Audience groups',audience+'\nShare canvas apps with these groups.\nGrant SharePoint roles separately.',fill=tint,accent=accent)
    pp=p.box(x+20,538,430,209,'white',accent)
    p.text(x+40,551,385,'POWER PLATFORM',13,accent,True)
    p.text(x+40,580,385,kind,23,bold=True)
    for j,label in enumerate(['Solution 1','Solution …','Solution N']):
        bx=x+40+j*128
        p.box(bx,620,118,42,tint,tint, radius=8)
        p.text(bx,630,118,label,15,accent,True,'center')
    p.text(x+40,680,390,detail+'\nDataverse stores solution metadata.',16,C['muted'])
    sp=p.card(x+20,800,430,131,sites,data+'\nProvision schema and permissions\nseparately from solution imports.',C['tealbg'],C['teal'])
    p.edge(pp,sp,color=C['teal'])
    p.text(x+255,761,195,'Runtime access',15,C['teal'])

p.text(50,978,1450,'RELEASE PATH  /  Promote one versioned managed ZIP; retain its unmanaged source snapshot',17,C['ink'],True)
a=p.card(50,1020,440,105,'1  Build and archive','Export managed + unmanaged packages.\nRecord schema steps and target settings.',C['bluebg'],C['blue'])
b=p.card(570,1020,440,105,'2  Import and verify','Bind Test connections and variables.\nRun functional and negative access tests.',C['purplebg'],C['purple'])
c=p.card(1090,1020,440,105,'3  Approve and promote','Import the same managed ZIP into Prod.\nApply Prod bindings; smoke-test and monitor.',C['tealbg'],C['teal'])
p.edge(a,b,sc=(1,.5),tc=(0,.5)); p.edge(b,c,sc=(1,.5),tc=(0,.5))
p.text(50,1153,1450,'Guardrails: separate Prod identity where possible • no Dev/Test connection to Prod data • no routine edits in Test/Prod',17,C['ink'],True)
p.text(50,1190,1450,'SharePoint sites sit outside Power Platform environments. Managed solutions do not require Managed Environments.\n“Dev” is a lifecycle stage; use a suitable shared environment type. See the research note for prerequisites and limitations.',16,C['muted'])
p.save('01-environment-model.svg')

q=Page('02 — Solution boundary and runtime identities',1580,1140)
q.text(50,32,1450,'One business capability, one release boundary',34,bold=True)
q.text(50,86,1450,'Package the app and its automation together; make external data, identity and permissions explicit.',20,C['muted'])
q.box(50,139,1480,58,C['amberbg'],C['amberbg'])
q.text(70,154,1440,'A solution is a deployment boundary. It does not isolate users, credentials or SharePoint data.',20,C['amber'],True)
q.box(50,222,865,539,'white',C['blue'])
q.text(75,238,780,'BUSINESS SOLUTION  /  Exported components',16,C['blue'],True)
app=q.card(100,325,290,110,'Canvas app(s)','Screens, formulas\nand app-to-flow calls',C['bluebg'],C['blue'])
ev=q.card(575,325,290,110,'Environment variables','Site + list definitions\nand other configuration',C['purplebg'],C['purple'])
flow=q.card(100,570,290,110,'Solution cloud flows','Triggers, actions\nand authorization checks',C['bluebg'],C['blue'])
ref=q.card(575,570,290,110,'Connection references','Flow connector bindings\nowned by this solution',C['purplebg'],C['purple'])
q.text(75,714,800,'Independent release • one owning team • no dependencies on other business solutions',16,C['blue'],True)

user=q.card(1050,260,430,110,'User’s SharePoint connection','Canvas app OAuth path\nActs with the signed-in user’s rights',C['tealbg'],C['teal'])
q.card(1050,402,430,122,'Outside the exported solution','Connections and credentials; Entra groups;\nSharePoint sites, schema, data and grants.\nProvision / configure these per stage.',fill='white',accent=C['muted'])
svc=q.card(1050,570,430,110,'Flow’s SharePoint connection','Service account in this design*\nActs with that account’s SharePoint rights',C['tealbg'],C['teal'])
sp=q.card(1050,810,430,133,'SharePoint site(s) + lists','Enforce actual read / write permissions.\nSeparate Dev, Test and Prod resources.\nKeep compatible list and column metadata.',C['tealbg'],C['teal'])

q.edge(ev,app,sc=(0,.5),tc=(1,.5),color=C['purple'],dash=True)
q.text(416,345,140,'configuration',14,C['purple'])
q.edge(ev,flow,points=[(475,400),(475,530),(245,530)],sc=(0,.7),tc=(.5,0),color=C['purple'],dash=True)
q.edge(app,flow,sc=(.2,1),tc=(.2,0))
q.text(180,474,230,'Optional flow call',15,C['blue'])
q.edge(flow,ref,sc=(1,.5),tc=(0,.5),color=C['blue'])
q.text(420,592,140,'uses',15,C['blue'])
q.edge(ref,svc,sc=(1,.5),tc=(0,.5),color=C['teal'])
q.text(926,592,115,'bind on import',14,C['teal'])
q.edge(app,user,points=[(245,295),(1000,295),(1000,315)],sc=(.5,0),tc=(0,.5),color=C['teal'])
q.text(465,265,470,'Direct SharePoint access uses user OAuth',15,C['teal'])
q.edge(user,sp,points=[(1510,315),(1510,875)],sc=(1,.5),tc=(1,.5),color=C['teal'])
q.edge(svc,sp,color=C['teal'])
q.text(1285,730,190,'Permission check',15,C['teal'])

q.box(50,798,865,164,C['purplebg'],C['purplebg'])
q.text(75,814,810,'ACCESS IS CONFIGURED AT THREE SEPARATE LAYERS',16,C['purple'],True)
q.text(75,851,810,'1   Environment group admits eligible users; roles control platform privileges.\n2   Business audience group receives app sharing / applicable flow run rights.\n3   SharePoint grants protect data; use role groups for finer segmentation.',18,C['ink'],line=1.6)
q.text(50,989,1470,'* For eligible instant flows, a run-only user connection is an alternative. Check each trigger and connection setting.',17,C['muted'])
q.text(50,1021,1470,'A privileged flow must authorize each operation. UI filtering and a user-supplied email address are not sufficient controls.',17,C['ink'],True)
q.text(50,1059,1470,'Solid arrows = runtime call or connection binding. Dashed arrows = configuration. Target variable values are supplied per environment.\nSharePoint OAuth canvas connections do not follow the flow connection-reference path. Sources and decisions: research note.',16,C['muted'])
q.save('02-solution-boundary.svg')

mx=ET.Element('mxfile',host='app.diagrams.net',modified='2026-09-21T00:00:00.000Z',agent='Codex',version='24.7.17',type='device')
for n,page in enumerate([p,q]):
    d=ET.SubElement(mx,'diagram',id=f'alm-{n+1}',name=page.name)
    d.append(page.model)
ET.indent(mx)
ET.ElementTree(mx).write(OUT/'power-platform-alm.drawio',encoding='utf-8',xml_declaration=True)
print('Generated two editable draw.io pages and two SVG previews.')
