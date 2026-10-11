from pathlib import Path
from hashlib import sha256
from collections import Counter
import streamlit as st
from dstv.state import Document
from dstv.validation import export_reasons, checked_bytes
from ui.dstv_plots import face_figure, cross_section

ROOT = Path(__file__).resolve().parents[1]


def add_document(data,name,encoding='Automatisch'):
    doc = Document.load(data,name,encoding)
    st.session_state.dstv_documents[doc.id] = doc
    st.session_state.dstv_active_id = doc.id
    st.session_state.dstv_file = doc.id
    return doc


def commit(doc_id,widget_key):
    st.session_state.dstv_documents[doc_id].apply(st.session_state[widget_key])
    st.session_state.dstv_editor_context = (doc_id, st.session_state.dstv_documents[doc_id].revision)


st.title('Stahlbau · DSTV / NC / NC1')
st.caption('Einzelteile und Bearbeitungsflächen · keine Baugruppen- oder Volumenrekonstruktion')
st.markdown('<style>textarea {font-family:Consolas,monospace !important;}</style>',unsafe_allow_html=True)
if 'dstv_documents' not in st.session_state:
    st.session_state.dstv_documents={}
if 'dstv_upload_seen' not in st.session_state:
    st.session_state.dstv_upload_seen=set()
with st.sidebar:
    encoding=st.selectbox('Import-Encoding',['Automatisch','utf-8','cp1252'],key='dstv_encoding')
    uploads=st.file_uploader('NC-/NC1-Dateien öffnen',type=['nc','nc1'],accept_multiple_files=True,key='dstv_upload')
    occurrences=Counter()
    for upload in uploads or []:
        data=upload.getvalue()
        base_identity=(upload.name,sha256(data).hexdigest(),encoding)
        occurrence=occurrences[base_identity]
        occurrences[base_identity]+=1
        identity=base_identity+(occurrence,)
        if identity not in st.session_state.dstv_upload_seen:
            try:
                add_document(data,upload.name,encoding)
                st.session_state.dstv_upload_seen.add(identity)
            except (UnicodeError,ValueError) as exc:
                st.error(f'{upload.name}: Importfehler: {exc}')
    if st.button('Beide Projektbeispiele laden',key='dstv_load_real'):
        for name in ['B001_HEA300.nc1','S001_Stiffener.nc1']:
            path=ROOT/'examples/dstv'/name
            add_document(path.read_bytes(),name)
        st.rerun()
    example=st.selectbox('Weitere Lehrbeispiele',['Blech mit Bohrungen und Öffnung','Träger mit allen Flächen','Nicht unterstützte Bearbeitung'],key='dstv_example_choice')
    if st.button('Lehrbeispiel hinzufügen',key='dstv_load_teaching'):
        name={'Blech mit Bohrungen und Öffnung':'plate_holes.nc1','Träger mit allen Flächen':'beam_faces.nc1','Nicht unterstützte Bearbeitung':'unsupported.nc1'}[example]
        path=ROOT/'examples/dstv'/name
        add_document(path.read_bytes(),name)
        st.rerun()

documents=st.session_state.dstv_documents
if not documents:
    st.info('Eine oder mehrere Dateien hochladen oder ein Beispiel aus der Seitenleiste laden.')
    st.stop()
st.dataframe([{'ID':doc.id[:8],'Dateiname':doc.name,'Position':doc.part.header.values.get('position'),
               'Profil':doc.part.header.values.get('profile'),'Typ':doc.part.header.values.get('profile_type'),
               'Material':doc.part.header.values.get('material'),'Stückzahl':doc.part.header.values.get('quantity'),
               'Länge [mm]':doc.part.header.values.get('length'),'Status':'Abhängige Angaben ungeklärt' if doc.dependency_reasons() else doc.part.status} for doc in documents.values()],hide_index=True,width='stretch',height=200)
ids=list(documents)
active=st.session_state.get('dstv_active_id')
if active not in ids:
    active=ids[0]
if st.session_state.get('dstv_file') not in ids:
    st.session_state.dstv_file=active
selected=st.selectbox('Aktives Einzelteil',ids,format_func=lambda i:f'{documents[i].name} · Pos. {documents[i].part.header.values.get("position","—")} · {i[:8]}',key='dstv_file')
st.session_state.dstv_active_id=selected
doc=documents[selected]
part=doc.part
with st.sidebar:
    st.write(doc.name)
    st.caption(f'{doc.encoding} · BOM: {bool(doc.bom)} · Revision {doc.revision}')
    st.caption('Geändert' if doc.text!=doc.original_text else 'Originalzustand')
    reset=st.checkbox('Aktiven Entwurf verwerfen bestätigen',key='dstv_reset_confirm')
    if st.button('Aktive Datei zurücksetzen',disabled=not reset,key='dstv_reset'):
        doc.reset()
        st.session_state.pop('dstv_editor_context',None)
        st.rerun()

left,right=st.columns([1,1.35])
with left:
    widget_key=f'dstv_editor_{doc.id}'
    context=(doc.id,doc.revision)
    if st.session_state.get('dstv_editor_context')!=context or widget_key not in st.session_state:
        st.session_state[widget_key]=doc.text
        st.session_state.dstv_editor_context=context
    st.text_area('DSTV-Text',height=430,key=widget_key,on_change=commit,args=(doc.id,widget_key))
    st.caption('Automatische Auswertung beim übernommenen Änderungsereignis; sichtbare Umbrüche verändern den Text nicht.')
    if st.button('Übernehmen und prüfen',key='dstv_commit'):
        commit(doc.id,widget_key)
        st.rerun()
    if doc.newline_note:
        st.info(doc.newline_note)
    with st.expander('Headerdaten und Quellzeilen'):
        st.dataframe([{'Feld':key,'Wert':str(value),'Quellzeile':part.header.sources[key].number if key in part.header.sources else None} for key,value in part.header.values.items()],hide_index=True,width='stretch')
    for d in part.diagnostics:
        (st.error if d.severity=='error' else st.warning)(f'{d.filename} · {d.block} · Zeile {d.line} · {d.code}: {d.message}')
    for reason in doc.dependency_reasons():
        st.warning(reason)

with right:
    compare=st.checkbox('Original grau gestrichelt anzeigen',key='dstv_compare')
    labels=st.checkbox('Bohrungsmaße beschriften',value=True,key='dstv_labels')
    st.caption('Einzelne Bearbeitungsflächen in mm, gleicher Achsmaßstab. Keine zusammenhängende Abwicklung oder vollständige 3D-Geometrie.')
    st.write({'Struktur/Syntax':part.syntax_ok,'Unterstützte Flächen':sum(f.supported for f in part.faces.values()),
              'Geometrische Plausibilität':all(f.plausible for f in part.faces.values()) if part.faces else False,
              'Nicht unterstützte Inhalte':any(d.code.startswith('unsupported') for d in part.diagnostics)})
    codes=list(part.faces) or list(doc.last_valid)
    if not codes:
        st.info('Keine unterstützte Flächenvorschau verfügbar.')
    for tab,code in zip(st.tabs([f'{c} · {(part.faces.get(c) or doc.last_valid[c][2]).name}' for c in codes]) if codes else [],codes):
        with tab:
            current=part.faces.get(code)
            valid=part.syntax_ok and current is not None and (current.supported or current.partial_display) and current.plausible
            snapshot=doc.last_valid.get(code)
            if valid:
                view_part,face=part,current
                if current.partial_display:
                    st.warning("Unvollständige Fläche – nur unterstützte AK/IK/BO-Bearbeitungen dargestellt. Markierungs-/Beschriftungsblöcke PU/KO/SI bleiben im Text erhalten, werden aber nicht gezeichnet. Geprüfter Export gesperrt.")
            elif snapshot:
                revision,view_part,face=snapshot
                st.warning(f'Letzter gültiger Stand – aktueller Text enthält Fehler oder nicht unterstützte Inhalte (Vorschau Revision {revision}). Eigenschaften und Bearbeitungstabelle darunter gehören zum angezeigten Stand.')
            else:
                st.warning('Fläche unvollständig: nicht unterstützte Bearbeitungen oder Geometriefehler. Vorschau gesperrt; andere sicher interpretierbare Flächen bleiben verfügbar.')
                continue
            st.caption(f'{face.view} · Ursprung x=0/q=0 · x+ rechts, q+ {"oben" if face.q_sign>0 else "unten"}. Standardansicht als Ganzes gedreht, Dateikoordinaten bleiben unverändert.')
            st.caption('Grundkontur aus Header abgeleitet' if face.derived else 'Explizite AK-Außenkontur; Headerrechteck nur als Bezug')
            entries=face.outers+face.inners+face.holes
            table=[{'Element':e.id,'Block':e.block,'Quellzeile':e.lines[0].number,'Fläche':e.face,
                    'x [mm]':e.x,'q [mm]':e.q,'Ø [mm]':e.diameter,
                    'Konturpunkte':len(e.points) if e.points else None,
                    'Koordinaten x/q [mm]':'; '.join(f'{x:g}/{q:g}' for x,q in e.points) if e.points else None,
                    'Quellzeilen':', '.join(str(line.number) for line in e.lines),'Ankörnung':e.marking} for e in entries]
            table_selection=st.dataframe(table,hide_index=True,width='stretch',height=160,on_select='rerun',selection_mode='single-row',key=f'dstv_table_{doc.id}_{code}')
            st.caption('Eine Tabellenzeile anklicken, um die Bearbeitung in Orange hervorzuheben.')
            element_ids=[e.id for e in entries]
            highlight=st.selectbox('Bearbeitung hervorheben',['']+element_ids,key=f'dstv_element_{doc.id}_{code}',format_func=lambda i:i or 'Keine')
            element=next((e for e in entries if e.id==highlight),None)
            selected_rows=table_selection.selection.rows
            if selected_rows and selected_rows[0]<len(entries):
                element=entries[selected_rows[0]]
            original=doc.original_part.faces.get(code) if compare else None
            st.plotly_chart(face_figure(face,selected=element,original=original,labels=labels),key=f'dstv_plot_{doc.id}_{code}',width='stretch',config={'scrollZoom':True})
            st.caption(f'Angezeigte Maße: Länge {face.length:g} mm · Flächenmaß {face.extent:g} mm · Profil {view_part.header.values.get("profile")}')
            st.plotly_chart(cross_section(view_part,code),key=f'dstv_section_{doc.id}_{code}',width='stretch')
            st.caption('Schematischer Querschnitt nach Headermaßen, ohne Walzausrundungen. Orange: ausgewählte Fläche; keine Positionierung anderer Teile.')

st.divider()
st.subheader('Datei sichern')
base=Path(doc.name).stem
extension=Path(doc.name).suffix or '.nc1'
c1,c2,c3=st.columns(3)
c1.download_button('Original herunterladen',doc.original_bytes,file_name=doc.name,key='dstv_download_original')
try:
    draft=doc.bytes()
    c2.download_button('Entwurf herunterladen (ungeprüft)',draft,file_name=base+'_entwurf'+extension,key='dstv_download_draft')
except UnicodeError as exc:
    draft=None
    st.error(f'{doc.name}: Text ist im Encoding {doc.encoding} nicht darstellbar: {exc}')
reasons=export_reasons(part)+doc.dependency_reasons()
checked=None
try:
    checked=checked_bytes(doc)
except (ValueError,UnicodeError) as exc:
    if not reasons:
        reasons=[str(exc)]
c3.download_button('Export nach unterstützten Prüfungen',checked or b'',file_name=base+'_geprueft'+extension,disabled=checked is None,key='dstv_download_checked')
st.caption('Prüfumfang: ST/EN und Headerstruktur, Profilmaße, Standardbohrungen/Ankörnungen, geschlossene geradlinige AK/IK-Konturen, Laufrichtung, Konturüberschneidungen, Lage im Material und Headergrenzen. Keine Tragfähigkeits-, Mindestabstands-, Werkzeug- oder Maschinenfreigabe. DSTV verwendet hier keine BVBS-Prüfsumme.')
if reasons:
    with st.expander('Warum ist der geprüfte Export gesperrt?'):
        for reason in reasons:
            st.write('• '+reason)
else:
    st.success('Die implementierten Prüfungen sind bestanden. Der Export erhält den Text unverändert.')
