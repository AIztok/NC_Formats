from pathlib import Path
import hashlib
import streamlit as st
from ui.state import Document
from ui.plots import figure
from bvbs.geometry import radius_preview, radius_rows
from bvbs.parser import parse
from bvbs.serializer import repair_document
from bvbs.validation import export_reasons

ROOT = Path(__file__).resolve().parents[1]

# Keep existing live sessions when upgrading the previous unprefixed ABS page.
for old_key in ['doc', 'editor_generation', 'editor_context', 'chosen', 'active', 'editor', 'seen_upload', 'pending_upload', 'editor_state_version', 'show_radii']:
    new_key = "bvbs_" + old_key
    if new_key not in st.session_state and old_key in st.session_state:
        st.session_state[new_key] = st.session_state[old_key]



def install(data, name, encoding="Automatisch"):
    st.session_state.bvbs_doc = Document.load(data, name, encoding)
    st.session_state.bvbs_editor_generation = st.session_state.get("bvbs_editor_generation", 0) + 1
    st.session_state.pop("bvbs_editor_context", None)
    st.session_state.pop("bvbs_chosen", None)
    st.session_state.pop("bvbs_active", None)
    st.session_state.pop("bvbs_editor", None)


def commit(target, widget_key):
    # Bind the target when rendering, never read a mutable current selection.
    doc = st.session_state.bvbs_doc
    doc.apply(target, st.session_state[widget_key])
    st.session_state.bvbs_editor_context = (widget_key, doc.revision)


def label(r):
    return f"#{r.id + 1} · Pos. {r.header.get('p', '—')} · {r.kind} · Plan {r.header.get('r', '—')} / {r.header.get('i', '—')}"


st.title("ABS · Bewehrung lesen und bearbeiten")
st.caption("BVBS 3.1 · lokale Verarbeitung · Text und Biegeform im Zusammenhang")
st.markdown("<style>textarea {font-family:Consolas,monospace !important;}</style>", unsafe_allow_html=True)
with st.sidebar:
    encoding = st.selectbox("Import-Encoding", ["Automatisch", "utf-8", "cp1252"], key="bvbs_import_encoding")
    upload = st.file_uploader("ABS-Datei öffnen", type=["abs"], key="bvbs_upload")
    if upload is not None:
        data = upload.getvalue()
        signature = (hashlib.sha256(data).hexdigest(), upload.name, encoding)
        if signature != st.session_state.get("bvbs_seen_upload"):
            st.session_state.bvbs_pending_upload = (data, upload.name, encoding, signature)
            if "bvbs_doc" not in st.session_state or st.session_state.bvbs_doc.text == st.session_state.bvbs_doc.original_text and not st.session_state.bvbs_doc.drafts:
                try:
                    install(data, upload.name, encoding)
                    st.session_state.bvbs_seen_upload = signature
                    st.session_state.pop("bvbs_pending_upload", None)
                except (UnicodeError, ValueError) as exc:
                    st.error(f"Datei konnte nicht dekodiert werden: {exc}")
        if "bvbs_pending_upload" in st.session_state:
            st.warning("Neue Datei wartet. Bestehenden Entwurf vorher herunterladen.")
            if st.button("Neue Datei laden und Entwurf verwerfen", key="bvbs_new_file"):
                data, name, enc, sig = st.session_state.bvbs_pending_upload
                try:
                    install(data, name, enc)
                    st.session_state.bvbs_seen_upload = sig
                    st.session_state.pop("bvbs_pending_upload", None)
                    st.rerun()
                except (UnicodeError, ValueError) as exc:
                    st.error(str(exc))
    if st.button("Beispieldatei laden", key="bvbs_example", disabled="bvbs_doc" in st.session_state and (st.session_state.bvbs_doc.text != st.session_state.bvbs_doc.original_text or bool(st.session_state.bvbs_doc.drafts))):
        path = ROOT / "examples" / "mehrere_positionen.abs"
        install(path.read_bytes(), path.name)
        st.rerun()

if "bvbs_doc" not in st.session_state:
    st.info("ABS-Datei hochladen oder links die Beispieldatei laden.")
    st.stop()
doc = st.session_state.bvbs_doc
if not hasattr(doc, "ui"):
    doc.ui = {}
records = doc.records
# Recover only demonstrably unchanged full-file values left by the former
# shared editor widget; keep any genuine user edits intact.
if st.session_state.get("bvbs_editor_state_version") != 2:
    unchanged_file = doc.text.replace("\r\n", "\n").strip("\r\n")
    stale = [rid for rid, value in doc.drafts.items()
             if value.replace("\r\n", "\n").strip("\r\n") == unchanged_file]
    for rid in stale:
        doc.drafts.pop(rid)
    if stale and not doc.drafts:
        doc.error = ""
    st.session_state.bvbs_editor_state_version = 2
with st.sidebar:
    st.write(doc.name)
    st.caption(f"Encoding: {doc.encoding} · BOM: {'ja' if doc.bom else 'nein'} · Revision {doc.revision}")
    st.write(f"{len(records)} Datensätze · {sum(r.points is not None for r in records)} darstellbar")
    st.write(f"{sum(r.checksum_ok for r in records)} bestätigte Prüfsummen")
    st.caption("Geänderte Datei" if doc.text != doc.original_text or doc.drafts else "Originalzustand")
    reset = st.checkbox("Zurücksetzen bestätigen: Entwurf verwerfen", key="bvbs_reset_confirm")
    if st.button("Änderungen zurücksetzen", disabled=not reset, key="bvbs_reset"):
        install(doc.original_bytes, doc.name, doc.encoding)
        st.rerun()

f1, f2 = st.columns([2, 1])
search = f1.text_input("Position filtern", key="bvbs_search")
status = f2.multiselect("Status filtern", ["Darstellbar", "Prüfsummenwarnung", "Textfehler", "Nicht unterstützt"], key="bvbs_status")
filtered = [r for r in records if search.casefold() in str(r.header.get("p", "")).casefold() and (not status or r.status in status)]
st.dataframe([{"Datensatz": r.id + 1, "Position": r.header.get("p"), "Typ": r.kind,
               "Ø [mm]": r.header.get("d"), "Stückzahl": r.header.get("n"),
               "Headerlänge [mm]": r.header.get("l"), "Einzelgewicht [kg]": r.header.get("e"),
               "Status": r.status} for r in filtered], hide_index=True, height=220, width="stretch")
ids = [r.id for r in filtered]
# Avoid losing selected positions on ordinary reruns; reconcile after a whole-file edit.
if "bvbs_chosen" not in st.session_state:
    st.session_state.bvbs_chosen = [i for i in doc.ui.get("chosen", ids[:1]) if i in ids]
if "bvbs_chosen" in st.session_state:
    st.session_state.bvbs_chosen = [i for i in st.session_state.bvbs_chosen if i in ids]
selected = st.multiselect("Positionen auswählen", ids, default=ids[:1] if "bvbs_chosen" not in st.session_state else None,
                          format_func=lambda i: label(records[i]), key="bvbs_chosen")
doc.ui["chosen"] = selected
if selected:
    if "bvbs_active" not in st.session_state:
        st.session_state.bvbs_active = doc.ui.get("active", selected[0])
    if st.session_state.get("bvbs_active") not in selected:
        st.session_state.bvbs_active = selected[0]
    active = st.selectbox("Aktive Position für den Editor", selected, format_func=lambda i: label(records[i]), key="bvbs_active")
else:
    active = None
doc.ui["active"] = active
mode = st.radio("Editormodus", ["Gewählte Position", "Gesamte Datei"], horizontal=True, index=doc.ui.get("mode", 0), key="bvbs_mode")
doc.ui["mode"] = 1 if mode == "Gesamte Datei" else 0
compare = st.checkbox("Originalform grau gestrichelt anzeigen", disabled=not doc.comparison, key="bvbs_compare")
show_radii = st.checkbox("Biegeradien anzeigen (schematisch)", value=True, key="bvbs_show_radii")
if not doc.comparison:
    st.caption("Nach einer Änderung der gesamten Datei ist die Originalzuordnung deaktiviert. Zurücksetzen stellt sie wieder her.")
target = "file" if mode == "Gesamte Datei" else active
left, right = st.columns([1, 1.2])
with left:
    if target is not None:
        widget_key = f"bvbs_editor_{st.session_state.get('bvbs_editor_generation', 0)}_{target}"
        context = (widget_key, doc.revision)
        if st.session_state.get("bvbs_editor_context") != context or widget_key not in st.session_state:
            st.session_state[widget_key] = doc.drafts.get(target, doc.text if target == "file" else records[target].raw)
            st.session_state.bvbs_editor_context = context
        st.text_area("ABS-Text", key=widget_key, height=350, on_change=commit, args=(target, widget_key))
        st.caption("Der sichtbare Zeilenumbruch passt nur die Anzeige an und ändert den ABS-Text nicht.")
        st.caption("Automatische Auswertung nach dem von Streamlit übernommenen Änderungsereignis (z. B. beim Verlassen des Feldes).")
        if st.button("Übernehmen und prüfen", key="bvbs_commit"):
            commit(target, widget_key)
            st.rerun()
        if doc.error:
            st.error(doc.error)
        if st.button("Prüfsumme aktualisieren", key="bvbs_checksum"):
            try:
                affected = records if target == "file" else [records[target]]
                doc.apply("file" if target == "file" else target,
                          repair_document(doc.text, affected) if target == "file" else repair_document(records[target].raw, parse(records[target].raw)))
                st.session_state.pop("bvbs_editor_context", None)
                st.rerun()
            except (ValueError, UnicodeError) as exc:
                st.error(f"Prüfsumme nicht aktualisiert: {exc}")
    else:
        st.info("Eine Position auswählen oder den Modus Gesamte Datei öffnen.")
with right:
    st.caption("Schematische Biegeform – Rundungen aus Biegerolle/Stabdurchmesser, keine geprüfte Außenmaßumrechnung oder Abwicklung")
    st.caption("Schenkellängen sind übernommene BVBS-Außenmaße. Jede Ansicht zeigt eine einzelne Position.")
    original = doc.original_records if compare and doc.comparison else []
    limit = st.number_input("Maximal gleichzeitig angezeigte Formen", min_value=1, max_value=30, value=6, key="bvbs_render_limit")
    for rid in selected[:limit]:
        r = records[rid]
        st.subheader(label(r))
        preview = r if r.points else doc.last_valid.get(rid)
        if preview is not None:
            if r.points is None or rid in doc.drafts:
                st.warning("Veraltete Vorschau: letzte gültige Form. Der aktuelle Entwurf ist nicht darstellbar.")
            origin = original[rid] if rid < len(original) else None
            if show_radii:
                for warning in radius_preview(preview).warnings:
                    st.warning(warning)
            st.plotly_chart(figure(preview, origin, show_radii=show_radii), key=f"bvbs_plot_{rid}", width="stretch", config={"scrollZoom": True})
        else:
            st.info("Für diesen Datensatz ist keine gültige Vorschau verfügbar.")
        st.write({"Durchmesser [mm]": r.header.get("d"), "Stückzahl": r.header.get("n"),
                  "Headerlänge [mm]": r.header.get("l"), "Einzelgewicht [kg]": r.header.get("e"),
                  "Biegerollendurchmesser [mm]": r.header.get("s"),
                  "Text/Syntax gültig": r.syntax_ok and not any(d.code == "required" for d in r.diagnostics), "Geometrie darstellbar": r.points is not None,
                  "Prüfsumme korrekt": r.checksum_ok,
                  "Abhängige Angaben": "Länge/Gewicht plausibel" if not export_reasons([r], r.raw + "\r\n") else "Nicht vollständig bestätigt / möglicherweise veraltet",
                  "Fachliche Prüfung": "Eingeschränkte Prüfung gerader Stäbe" if r.points and len(r.points) == 2 else "Eingeschränkt: keine Prüfung von Biegeabzügen oder Abwicklung"})
        rows = radius_rows(r)
        if rows:
            st.caption("Biegeradien: Innenradius = s/2; Mittellinienradius = (s+d)/2. Orange markiert die schematischen Biegungen.")
            st.dataframe(rows, hide_index=True, width="stretch")
        for diagnostic in r.diagnostics:
            (st.error if diagnostic.severity == "error" else st.warning)(f"{diagnostic.code} · {diagnostic.message}")
        with st.expander("Geometrietokens und Quellpositionen"):
            st.dataframe([{"Schenkel/Biegung": i // 2 + 1, "Token": t.key + t.value,
                           "Bedeutung": "BVBS-Schenkellänge [mm]" if t.key == "l" else "Biegewinkel [°]" if t.key == "w" else "Nicht unterstützt",
                           "Zeichenoffset": r.start + t.start} for b in r.blocks if b.kind == "G" for i, t in enumerate(b.tokens)], hide_index=True)
    if len(selected) > limit:
        st.info(f"{len(selected) - limit} weitere ausgewählte Formen sind ausgeblendet.")

st.divider()
st.subheader("Datei sichern")
base = Path(doc.name).stem
c1, c2, c3 = st.columns(3)
c1.download_button("Original herunterladen", doc.original_bytes, file_name=doc.name, key="bvbs_original_download", mime="application/octet-stream")
try:
    draft_bytes = doc.bytes()
    c2.download_button("Entwurf herunterladen (ungeprüft)", draft_bytes, file_name=f"{base}_entwurf.abs", key="bvbs_draft_download", mime="application/octet-stream")
except UnicodeError as exc:
    st.error(f"Export-Encoding {doc.encoding}: Text nicht kodierbar. {exc}")
    draft_bytes = None
reasons = export_reasons(records, doc.text)
if doc.error:
    reasons.append("Ein Einzelpositionsentwurf enthält Zeilenumbrüche und ist noch nicht übernehmbar. Er ist im Entwurfsdownload enthalten.")
if doc.bom:
    reasons.append("UTF-8-BOM wird verlustfrei erhalten, gehört jedoch nicht zur geprüften ASCII-Teilmenge.")
if draft_bytes is None:
    reasons.append("Entwurf kann nicht im ursprünglichen Encoding gespeichert werden.")
checked = None
if not reasons:
    checked = repair_document(doc.text, records).encode(doc.encoding)
c3.download_button("Geprüften ABS-Export herunterladen", checked or b"", file_name=f"{base}_geprueft.abs", key="bvbs_checked_download", disabled=bool(reasons), mime="application/octet-stream")
st.caption("Prüfumfang: BF2D ohne Zusatzblöcke, Pflichtfelder/Reihenfolge, ASCII/CRLF, positive Zahlen, gerade Geometrie, Headerlänge, nominales Einzelgewicht und neu berechnete Prüfsummen. Keine Maschinenfreigabe oder BVBS-Zertifizierung.")
if reasons:
    with st.expander("Warum ist der geprüfte Export gesperrt?", expanded=True):
        for reason in reasons[:30]:
            st.write("• " + reason)
        if len(reasons) > 30:
            st.caption(f"{len(reasons) - 30} weitere Einschränkungen.")
else:
    st.success("Implementierte Prüfungen bestanden. Prüfsummen werden für den Export kontrolliert aktualisiert.")
