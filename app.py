import os
import sys
import subprocess
import streamlit as st
import streamlit.components.v1 as components
import trimesh
import numpy as np
import plotly.graph_objects as go
from gradio_client import Client, handle_file

st.set_page_config(page_title="Patron Amigurumi Pro 3D", page_icon="🐉", layout="wide")
st.title("🐉 Générateur Universel 2D → 3D & Patron Amigurumi")

if "mesh_valide" not in st.session_state:
    st.session_state.mesh_valide = False

col1, col2 = st.columns([1, 1])

with col1:
    fichier_image = st.file_uploader("📸 1. Importe ta photo 2D (PNG, JPG)", type=["png", "jpg", "jpeg"])
    taille_mm = st.slider("📏 Hauteur finale (mm)", 50, 300, 150, 10)

    if fichier_image is not None and st.button("✨ 1. Générer le modèle 3D", type="primary", use_container_width=True):
        with st.spinner("🧠 Détourage et sculpture 3D via le cloud gratuit en cours (20-40s)..."):
            temp_img = "input_temp.png"
            with open(temp_img, "wb") as f_img:
                f_img.write(fichier_image.getbuffer())

            try:
                client = Client("stabilityai/TripoSR")
                img_sans_fond = client.predict(handle_file(temp_img), api_name="/preprocess")
                resultat_3d = client.predict(
                    handle_file(img_sans_fond),
                    0.85,
                    192,
                    api_name="/generate"
                )
                chemin_mesh = resultat_3d[0] if isinstance(resultat_3d, (list, tuple)) else resultat_3d

                mesh_3d = trimesh.load(chemin_mesh, force="mesh")
                morceaux = mesh_3d.split(only_watertight=False)
                if len(morceaux) > 1:
                    mesh_3d = max(morceaux, key=lambda m: len(m.faces))

                rot_x = trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0])
                rot_z = trimesh.transformations.rotation_matrix(np.radians(90), [0, 0, 1])
                mesh_3d.apply_transform(rot_x)
                mesh_3d.apply_transform(rot_z)

                hauteur = mesh_3d.bounds[1][2] - mesh_3d.bounds[0][2]
                mesh_3d.apply_scale(float(taille_mm) / hauteur)
                mesh_3d.vertices[:, 0] -= (mesh_3d.bounds[0][0] + mesh_3d.bounds[1][0]) / 2.0
                mesh_3d.vertices[:, 1] -= (mesh_3d.bounds[0][1] + mesh_3d.bounds[1][1]) / 2.0
                mesh_3d.vertices[:, 2] -= mesh_3d.bounds[0][2]

                trimesh.smoothing.filter_laplacian(mesh_3d, iterations=2)
                trimesh.repair.fill_holes(mesh_3d)
                trimesh.repair.fix_normals(mesh_3d)
                mesh_3d.vertices[:, 2] -= mesh_3d.bounds[0][2]

                mesh_3d.export("mario_ia_genere.obj")
                st.session_state.mesh_valide = True
            except Exception as e:
                st.error(f"Le serveur 3D public est temporairement occupé : {e}")

with col2:
    if st.session_state.mesh_valide and os.path.exists("mario_ia_genere.obj"):
        mesh_apercu = trimesh.load("mario_ia_genere.obj", force="mesh")
        v, f = mesh_apercu.vertices, mesh_apercu.faces
        if hasattr(mesh_apercu.visual, "vertex_colors") and mesh_apercu.visual.vertex_colors is not None and len(mesh_apercu.visual.vertex_colors) == len(v):
            c = mesh_apercu.visual.vertex_colors[:, :3]
            fig = go.Figure(data=[go.Mesh3d(
                x=v[:, 0], y=v[:, 1], z=v[:, 2],
                i=f[:, 0], j=f[:, 1], k=f[:, 2],
                vertexcolor=[f"rgb({r},{g},{b})" for r, g, b in c],
                flatshading=True
            )])
        else:
            fig = go.Figure(data=[go.Mesh3d(
                x=v[:, 0], y=v[:, 1], z=v[:, 2],
                i=f[:, 0], j=f[:, 1], k=f[:, 2],
                color="#d97757",
                flatshading=True
            )])
        fig.update_layout(scene=dict(aspectmode="data"), height=380, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

        if st.button("🧶 2. Valider le 3D et Créer le Patron Complet", type="primary", use_container_width=True):
            with st.spinner("⚙️ Exécution de main.py et calcul des rangs de crochet..."):
                subprocess.run([sys.executable, "main.py"], check=False)
                if os.path.exists("patron_global_ultime.html"):
                    with open("patron_global_ultime.html", "r", encoding="utf-8") as f_html:
                        html_contenu = f_html.read()
                    st.success("🎉 Patron généré avec succès !")
                    st.download_button(
                        label="📥 Télécharger le Patron Complet (HTML)",
                        data=html_contenu,
                        file_name="patron_amigurumi_pro.html",
                        mime="text/html",
                        use_container_width=True
                    )
                    components.html(html_contenu, height=900, scrolling=True)
                else:
                    st.warning("⚠️ Vérifie le nom du fichier de sortie dans main.py (ex: patron_global_ultime.html).")
