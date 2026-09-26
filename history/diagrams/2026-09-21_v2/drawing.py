"""Shared drawing primitives for the second diagram revision."""
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
