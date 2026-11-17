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

def generer_via_cloud(chemin_image):
    # 1. Essai avec TencentARC/InstantMesh (rapide et gratuit)
    try:
        client = Client("TencentARC/InstantMesh")
        img_nettoyee = client.predict(
            input_image=handle_file(chemin_image),
            do_remove_background=True,
            api_name="/preprocess"
        )
        mv_images = client.predict(
            input_image=handle_file(img_nettoyee),
            sample_steps=30,
            sample_seed=42,
            api_name="/generate_mvs"
        )
        res_3d = client.predict(api_name="/make3d")
        return res_3d[0] if isinstance(res_3d, (list, tuple)) else res_3d
    except Exception:
        pass

    # 2. Bascule automatique vers JeffreyXiang/TRELLIS
    client = Client("JeffreyXiang/TRELLIS")
    client.predict(api_name="/start_session")
    img_prete = client.predict(
        image=handle_file(chemin_image),
        api_name="/preprocess_image"
    )
    client.predict(
        image=handle_file(img_prete),
        multiimages=[],
        seed=42,
        ss_guidance_strength=7.5,
        ss_sampling_steps=12,
        slat_guidance_strength=3.0,
        slat_sampling_steps=12,
        multiimage_algo="stochastic",
        api_name="/image_to_3d"
    )
    glb_path = client.predict(
        mesh_simplify=0.95,
        texture_size=512,
        api_name="/extract_glb"
    )
    return glb_path[0] if isinstance(glb_path, (list, tuple)) else glb_path

col1, col2 = st.columns([1, 1])

with col1:
    fichier_image = st.file_uploader("📸 1. Importe ta photo 2D (PNG, JPG)", type=["png", "jpg", "jpeg"])
    taille_mm = st.slider("📏 Hauteur finale (mm)", 50, 300, 150, 10)

    if fichier_image is not None and st.button("✨ 1. Générer le modèle 3D", type="primary", use_container_width=True):
        with st.spinner("🧠 Détourage et sculpture 3D en cours (30 à 60 secondes)..."):
            temp_img = "input_temp.png"
            with open(temp_img, "wb") as f_img:
                f_img.write(fichier_image.getbuffer())

            try:
                chemin_mesh = generer_via_cloud(temp_img)
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
                st.error(f"Les serveurs 3D publics sont saturés pour le moment : {e}")

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
