from math import cos, sin, tau
import plotly.graph_objects as go
from dstv.geometry import view_point


def _trace(fig, face, points, name, color, *, fill=None, dash=None, width=2, hover=None):
    pts = [view_point(face.code,*p) for p in points]
    x,y = zip(*pts)
    fig.add_trace(go.Scatter(x=x,y=y,mode='lines',name=name,line=dict(color=color,width=width,dash=dash),
                            fill='toself' if fill else None,fillcolor=fill,
                            hovertemplate=hover or '%{x:g} / %{y:g} mm<extra></extra>'))


def circle(x,q,d):
    return [(x+d/2*cos(tau*j/72),q+d/2*sin(tau*j/72)) for j in range(73)]


def face_figure(face, *, selected=None, original=None, labels=True):
    fig = go.Figure()
    _trace(fig,face,face.base,'Grundkontur aus Header','#c1ccd3',dash='dot',width=1)
    for e in face.outers:
        _trace(fig,face,e.points,'Außenkontur '+e.id,'#007f86',fill='rgba(0,127,134,.15)',
               hover=f'AK · {e.id} · Zeile {e.lines[0].number}<extra></extra>')
    if not face.outers:
        _trace(fig,face,face.base,'Abgeleitete Materialfläche','#007f86',fill='rgba(0,127,134,.12)')
    for e in face.inners:
        _trace(fig,face,e.points,'Öffnung '+e.id,'#4b666d',fill='white',
               hover=f'IK · {e.id} · Zeile {e.lines[0].number}<extra></extra>')
    for e in face.holes:
        info = f'BO · {e.id} · Zeile {e.lines[0].number}<br>Fläche {e.face} · x {e.x:g} mm · q {e.q:g} mm<br>'
        info += 'Ankörnung' if e.marking else f'Ø {e.diameter:g} mm'
        px,py = view_point(face.code,e.x,e.q)
        if e.marking:
            fig.add_trace(go.Scatter(x=[px],y=[py],mode='markers',marker=dict(symbol='cross',size=11,color='#d47700'),name='Ankörnung',hovertemplate=info+'<extra></extra>'))
        else:
            _trace(fig,face,circle(e.x,e.q,e.diameter),'Bohrung '+e.id,'#264f9c',fill='white',hover=info+'<extra></extra>')
        if labels:
            fig.add_annotation(x=px,y=py,text='×' if e.marking else f'Ø{e.diameter:g}',showarrow=False,yshift=16)
    if original is not None and (original.supported or original.partial_display) and original.plausible:
        for pts in [e.points for e in original.outers] or [original.base]:
            _trace(fig,original,pts,'Original außen','#777',dash='dash',width=1)
        for e in original.inners:
            _trace(fig,original,e.points,'Original Öffnung','#777',dash='dash',width=1)
        for e in original.holes:
            if not e.marking:
                _trace(fig,original,circle(e.x,e.q,e.diameter),'Original Bohrung','#777',dash='dash',width=1)
    if selected:
        if selected.points:
            _trace(fig,face,selected.points,'Gewählte Textbearbeitung','#d47700',width=5)
        elif selected.x is not None:
            px,py = view_point(face.code,selected.x,selected.q)
            fig.add_trace(go.Scatter(x=[px],y=[py],mode='markers',marker=dict(symbol='circle-open',size=18,color='#d47700',line=dict(width=3)),name='Gewählte Textbearbeitung'))
    fig.add_trace(go.Scatter(x=[0],y=[0],mode='markers+text',text=['Ursprung'],textposition='bottom right',marker=dict(color='#222',size=6),name='Ursprung'))
    fig.add_annotation(x=face.length*.08,y=0,ax=0,ay=0,axref='x',ayref='y',text='x+',arrowhead=2)
    fig.add_annotation(x=0,y=face.extent*.25*face.q_sign,ax=0,ay=0,axref='x',ayref='y',text='q+',arrowhead=2)
    fig.update_layout(height=400,margin=dict(l=25,r=20,t=20,b=35),showlegend=False,plot_bgcolor='#fafcfc',
                      xaxis_title='Längskoordinate x [mm]',yaxis_title=f"Ansichtskoordinate {'q' if face.q_sign>0 else '−q'} [mm]",
                      yaxis=dict(scaleanchor='x',scaleratio=1),uirevision=f'dstv-face-{face.code}')
    return fig


def cross_section(part, selected_face):
    h = part.header.values
    height, width, tw, tf = h['height'],h['width'],h['web_thickness'],h['flange_thickness']
    fig=go.Figure()
    if h['profile_type']=='I':
        rects=[(0,0,tf,width),(height-tf,0,height,width),(tf,(width-tw)/2,height-tf,(width+tw)/2)]
        highlights={'v':[(tf,(width+tw)/2),(height-tf,(width+tw)/2)],
                    'h':[(tf,(width-tw)/2),(height-tf,(width-tw)/2)],
                    'o':[(height,0),(height,width)],'u':[(0,0),(0,width)]}
    else:
        rects=[(0,0,height,tw)]
        highlights={'v':[(0,tw),(height,tw)]}
    for y0,z0,y1,z1 in rects:
        fig.add_trace(go.Scatter(x=[-y0,-y1,-y1,-y0,-y0],y=[z0,z0,z1,z1,z0],mode='lines',fill='toself',fillcolor='#dce4e8',line=dict(color='#778b94'),hoverinfo='skip'))
    for code,points in highlights.items():
        x,z=zip(*[(-y,z) for y,z in points])
        fig.add_trace(go.Scatter(x=x,y=z,mode='lines',line=dict(color='#d47700' if code==selected_face else '#778b94',width=6 if code==selected_face else 2),hovertemplate=f'Fläche {code}<extra></extra>'))
        fig.add_annotation(x=sum(x)/2,y=sum(z)/2,text=code,showarrow=False,yshift=12)
    fig.update_layout(height=240,margin=dict(l=25,r=20,t=20,b=30),showlegend=False,xaxis_title='−Y [mm] · Y+ nach links',
                      yaxis_title='Z [mm]',yaxis=dict(scaleanchor='x',scaleratio=1))
    return fig
