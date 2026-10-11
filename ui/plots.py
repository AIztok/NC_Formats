import plotly.graph_objects as go
from bvbs.geometry import radius_preview


def figure(record, original=None, show_radii=True):
    fig = go.Figure()
    if original is not None and original.points:
        original_points = radius_preview(original).points if show_radii else original.points
        x, y = zip(*original_points)
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name="Original", line=dict(color="gray", dash="dash")))
    preview = radius_preview(record) if show_radii else None
    display_points = preview.points if preview else record.points
    if preview and preview.bends:
        x, y = zip(*record.points)
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name="Schematisches Maßpolygon",
                                line=dict(color="#80b8bb", dash="dot", width=1), hoverinfo="skip"))
    x, y = zip(*display_points)
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name="Entwurf", line=dict(color="#007f86", width=3)))
    if preview:
        for j, bend in enumerate(preview.bends):
            x, y = zip(*bend.samples)
            info = (f"Biegung {bend.index} · {bend.angle:g}°<br>"
                    f"Innenradius: {bend.inner_radius:g} mm<br>"
                    f"Mittellinienradius: {bend.axis_radius:g} mm<br>Schematische Rundung")
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name="Biegeradien", legendgroup="radii", showlegend=j == 0,
                                    line=dict(color="#d47700", width=4), hovertemplate=info + "<extra></extra>"))
            fig.add_trace(go.Scatter(x=[bend.center[0], bend.middle[0]], y=[bend.center[1], bend.middle[1]],
                                    mode="lines", line=dict(color="#d47700", dash="dot", width=1), showlegend=False,
                                    hovertemplate=info + "<extra></extra>"))
            fig.add_annotation(x=bend.middle[0], y=bend.middle[1],
                               text=f"R innen {bend.inner_radius:g} mm", showarrow=True, arrowhead=0,
                               ax=35, ay=-35, font=dict(color="#a65c00"), bgcolor="rgba(255,255,255,.85)")
    fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", text=["Start"], textposition="bottom center", name="Stabstart"))
    for i in range(len(record.points) - 1):
        a, b = record.points[i:i+2]
        length, angle = record.elements[2*i:2*i+2]
        fig.add_annotation(x=(a[0]+b[0])/2, y=(a[1]+b[1])/2,
                           text=f"{i+1}: {length.length:g} mm · {angle.angle:g}°", showarrow=False, yshift=14)
        fig.add_annotation(x=a[0]+.65*(b[0]-a[0]), y=a[1]+.65*(b[1]-a[1]),
                           ax=a[0]+.45*(b[0]-a[0]), ay=a[1]+.45*(b[1]-a[1]),
                           axref="x", ayref="y", arrowhead=2, arrowsize=1, text="")
    fig.update_layout(height=420, margin=dict(l=20,r=20,t=30,b=20), uirevision=f"record-{record.id}",
                      xaxis_title="x [mm]", yaxis_title="y [mm]", yaxis=dict(scaleanchor="x", scaleratio=1), legend=dict(orientation="h"))
    return fig
