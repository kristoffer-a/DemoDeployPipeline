from pathlib import Path
import xml.etree.ElementTree as ET

OUT = Path(__file__).parent
model = ET.Element('mxGraphModel', grid='0', page='0', pageWidth='1530', pageHeight='1010', background='#FFFFFF', adaptiveColors='auto')
root = ET.SubElement(model, 'root')
ET.SubElement(root, 'mxCell', id='0')
ET.SubElement(root, 'mxCell', id='1', parent='0')
ink, muted, blue, purple, teal = '#19354A', '#536B7A', '#1766B3', '#7353AC', '#087F78'

def box(id, x, y, w, h, label='', parent='1', stroke=blue, fill='#FFFFFF', size=20, bold=False, align='center', extra=''):
    style = f'rounded=1;arcSize=10;html=0;whiteSpace=wrap;fontFamily=Helvetica;fontSize={size};fontColor={ink};fontStyle={int(bold)};align={align};verticalAlign=middle;spacing=12;strokeColor={stroke};fillColor={fill};strokeWidth=2;{extra}'
    c = ET.SubElement(root, 'mxCell', id=id, parent=parent, value=label, style=style, vertex='1')
    ET.SubElement(c, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), **{'as':'geometry'})

def text(id, x, y, w, h, label, parent='1', size=18, bold=False):
    box(id,x,y,w,h,label,parent,'none','none',size,bold,'left')

def edge(id, source, target, label='', points=(), dashed=False, sc=(1,.5), tc=(0,.5), color=blue):
    c = ET.SubElement(root, 'mxCell', id=id, parent='1', source=source, target=target, value=label, edge='1', style=f'edgeStyle=orthogonalEdgeStyle;rounded=1;html=0;whiteSpace=nowrap;fontFamily=Helvetica;fontSize=17;fontColor={color};labelBackgroundColor=#FFFFFF;strokeColor={color};strokeWidth=2;endArrow=block;endFill=1;dashed={int(dashed)};exitX={sc[0]};exitY={sc[1]};entryX={tc[0]};entryY={tc[1]};')
    g=ET.SubElement(c,'mxGeometry',relative='1',**{'as':'geometry'})
    if points:
        a=ET.SubElement(g,'Array',**{'as':'points'})
        for x,y in points: ET.SubElement(a,'mxPoint',x=str(x),y=str(y))

text('title',40,25,1450,55,'Release once. Test it. Promote the same package.',size=35,bold=True)
text('subtitle',40,88,1450,42,'A simple manual ALM process · three Power Platform environments · SharePoint stores release files until Git is available',size=19)

for id,x,title,subtitle,color,fill in [
    ('dev',50,'DEV','Unmanaged · all development happens here',blue,'#F0F6FC'),
    ('test',560,'TEST','Managed · validate the release',purple,'#F6F2FA'),
    ('prod',1070,'PROD','Managed · approved releases only',teal,'#EFF8F5')]:
    box(id,x,175,410,420,stroke=color,fill=fill,extra='container=1;collapsible=0;recursiveResize=0;')
    text(id+'title',15,10,380,43,title,id,27,True)
    text(id+'sub',15,55,380,40,subtitle,id,17)

box('build',25,120,360,90,'1  Build & check\nApps, flows and configuration','dev',blue,size=21)
box('export',25,260,360,115,'2  Freeze a release version\nPublish, then export both\nunmanaged + managed ZIPs','dev',blue,size=21)
box('import-test',25,120,360,90,'3  Import managed ZIP\nApply Test configuration','test',purple,size=21)
box('uat',25,250,360,125,'4  Test & approve\nApp + flows + user permissions\nBusiness owner signs off','test',purple,size=21)
box('import-prod',25,120,360,90,'5  Import approved ZIP\nApply Prod configuration','prod',teal,size=21)
box('verify-prod',25,250,360,125,'6  Verify & record\nSmoke test, check flows\nRecord deployed version','prod',teal,size=21)
edge('dev-work','build','export',sc=(.5,1),tc=(.5,0))
edge('test-work','import-test','uat',sc=(.5,1),tc=(.5,0),color=purple)
edge('prod-work','import-prod','verify-prod',sc=(.5,1),tc=(.5,0),color=teal)

edge('deploy-test','export','import-test',points=[(510,492.5),(510,340)],color=blue)
text('test-arrow-note',468,220,84,65,'Managed\nrelease',size=15)
edge('approve-prod','uat','import-prod',points=[(1020,487.5),(1020,340)],color=teal)
text('prod-arrow-note',976,205,88,100,'Approved:\nsame\nmanaged\nZIP',size=15)
edge('rework','uat','build','Issues → fix in Dev → new version → retest',[(765,640),(25,640),(25,340)],True,(.5,1),(0,.5),purple)

box('archive',50,710,1430,180,stroke='#AB7A24',fill='#FFFAEF',extra='container=1;collapsible=0;recursiveResize=0;')
text('archive-title',15,10,1390,35,'SHAREPOINT RELEASE LIBRARY  ·  one folder per solution / release version', 'archive',21,True)
box('source-zip',25,65,395,75,'Unmanaged ZIP\nSource snapshot / recovery input','archive','#AB7A24',size=19)
box('managed-zip',455,65,420,75,'Managed ZIP\nOne package used for Test and Prod','archive','#AB7A24',size=19)
box('release-record',910,65,495,75,'Release notes + deployment record\nSettings, SharePoint changes and approval','archive','#AB7A24',size=19)
edge('save-release','export','archive','Store both exports',[(255,675),(430,675)],True,(.5,1),(.266,0),'#AB7A24')
text('footer',50,912,1430,64,'Before each target import: prepare SharePoint list changes, site/list values and connection mappings.\nKeep release ZIPs unchanged. Make fixes in Dev. SharePoint business data is not transported by the solution.',size=19)

ET.indent(model)
(OUT/'alm-deployment-process.model.xml').write_text(ET.tostring(model,encoding='unicode'))
file=ET.Element('mxfile',host='app.diagrams.net',type='device')
page=ET.SubElement(file,'diagram',id='alm-process-v3',name='ALM · Dev to Test to Prod')
page.append(model)
ET.indent(file)
(OUT/'alm-deployment-process.drawio').write_text(ET.tostring(file,encoding='unicode'))
print('Created editable ALM deployment diagram.')
