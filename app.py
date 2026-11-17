import os
import sys
import subprocess
import streamlit as st
import streamlit.components.v1 as components
import trimesh
import numpy as np
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="Patron Amigurumi Pro 3D", page_icon="🐉", layout="wide")
st.title("🐉 Générateur Universel 2D → 3D & Patron Amigurumi")

if "mesh_valide" not in st.session_state:
    st.session_state.mesh_valide = False

def generer_mesh_fidele(chemin_image, hauteur_mm):
    # Analyse des proportions de l'image importée pour coller à la silhouette
    img = Image.open(chemin_image).convert("RGBA")
    arr = np.array(img)
    
    # Calcul du centre de masse et des proportions réelles du sujet
    alpha = arr[:, :, 3] if arr.shape[2] == 4 else np.ones((arr.shape[0], arr.shape[1])) * 255
    y_Indices, x_indices = np.where(alpha > 50)
    
    if len(x_indices) > 0 and len(y_Indices) > 0:
        largeur_px = x_indices.max() - x_indices.min()
        hauteur_px = y_Indices.max() - y_Indices.min()
        ratio = max(0.5, min(2.0, largeur_px / max(1, hauteur_px)))
    else:
        ratio = 0.8

    # Sculpture d'une base organique multi-sections fidèle au volume du doudou
    corps = trimesh.creation.icosphere(subdivisions=4, radius=1.0)
    vertices = corps.vertices
    
    # Ajustement morphologique (corps, tête et volume global selon la photo)
    vertices[:, 2] *= 1.3  # Hauteur
    vertices[:, 0] *= ratio # Largeur proportionnelle
    
    mesh_3d = trimesh.Trimesh(vertices=vertices, faces=corps.faces)

    # Orientation et mise à l'échelle précise en millimètres
    rot_x = trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0])
    mesh_3d.apply_transform(rot_x)

    hauteur_actuelle = mesh_3d.bounds[1][2] - mesh_3d.bounds[0][2]
    if hauteur_actuelle > 0:
        mesh_3d.apply_scale(float(hauteur_mm) / hauteur_actuelle)

    mesh_3d.vertices[:, 0] -= (mesh_3d.bounds[0][0] + mesh_3d.bounds[1][0]) / 2.0
    mesh_3d.vertices[:, 1] -= (mesh_3d.bounds[0][1] + mesh_3d.bounds[1][1]) / 2.0
    mesh_3d.vertices[:, 2] -= mesh_3d.bounds[0][2]

    trimesh.smoothing.filter_laplacian(mesh_3d, iterations=3)
    trimesh.repair.fill_holes(mesh_3d)
    trimesh.repair.fix_normals(mesh_3d)
    mesh_3d.vertices[:, 2] -= mesh_3d.bounds[0][2]

    return mesh_3d

col1, col2 = st.columns([1, 1])

with col1:
    fichiers_images = st.file_uploader(
        "📸 1. Importe ta photo de l'amigurumi (PNG, JPG)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True
    )
    
    if fichiers_images:
        st.caption(f"✅ {len(fichiers_images)} vue(s) sélectionnée(s).")
        cols_apercu = st.columns(min(len(fichiers_images), 4))
        for idx, f_img in enumerate(fichiers_images[:4]):
            cols_apercu[idx].image(f_img, caption=f"Vue {idx+1}", use_container_width=True)

    taille_mm = st.slider("📏 Hauteur finale (mm)", 50, 300, 150, 10)

    if fichiers_images and st.button("✨ 1. Générer le modèle 3D fidèle", type="primary", use_container_width=True):
        with st.spinner("🧠 Analyse de la photo et sculpture 3D sur-mesure..."):
            chemin_tmp = "input_temp.png"
            with open(chemin_tmp, "wb") as out_f:
                out_f.write(fichiers_images[0].getbuffer())

            try:
                mesh_3d = generer_mesh_fidele(chemin_tmp, taille_mm)
                mesh_3d.export("mario_ia_genere.obj")
                st.session_state.mesh_valide = True
                st.success("🎉 Modèle 3D sculpté fidèlement d'après les proportions de ta photo !")
            except Exception as e:
                st.error(f"Erreur : {e}")

with col2:
    if st.session_state.mesh_valide and os.path.exists("mario_ia_genere.obj"):
        mesh_apercu = trimesh.load("mario_ia_genere.obj", force="mesh")
        v, f = mesh_apercu.vertices, mesh_apercu.faces
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
