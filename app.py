import os
import subprocess
import streamlit as st
import streamlit.components.v1 as components
import torch
import trimesh
import numpy as np
import plotly.graph_objects as go
from PIL import Image
from rembg import remove
from huggingface_hub import hf_hub_download

st.set_page_config(page_title="Patron Amigurumi Pro 3D", page_icon="🐉", layout="wide")
st.title("🐉 Générateur Universel 2D → 3D & Patron Amigurumi")

@st.cache_resource
def charger_moteur_3d():
    ckpt_path = hf_hub_download(repo_id="stabilityai/TripoSR", filename="model.ckpt")
    raw_ckpt = torch.load(ckpt_path, map_location="cpu")

    clean_ckpt = {}
    for k, v in raw_ckpt.items():
        nk = k.replace("encoder.layer.", "layers.")
        nk = nk.replace("attention.attention.query.", "attention.q_proj.")
        nk = nk.replace("attention.attention.key.", "attention.k_proj.")
        nk = nk.replace("attention.attention.value.", "attention.v_proj.")
        nk = nk.replace("attention.output.dense.", "attention.o_proj.")
        nk = nk.replace("intermediate.dense.", "mlp.fc1.")
        nk = nk.replace("output.dense.", "mlp.fc2.")
        clean_ckpt[nk] = v

    _orig_torch_load = torch.load
    torch.load = lambda *args, **kwargs: clean_ckpt if str(args[0]).endswith("model.ckpt") else _orig_torch_load(*args, **kwargs)

    from tsr.system import TSR
    model = TSR.from_pretrained("stabilityai/TripoSR", config_name="config.yaml", weight_name="model.ckpt")
    torch.load = _orig_torch_load

    model.renderer.set_chunk_size(4096)
    model.to("cpu")
    return model

from tsr.utils import resize_foreground

if "mesh_valide" not in st.session_state:
    st.session_state.mesh_valide = False

col1, col2 = st.columns([1, 1])

with col1:
    fichier_image = st.file_uploader("📸 1. Importe ta photo 2D (PNG, JPG)", type=["png", "jpg", "jpeg"])
    taille_mm = st.slider("📏 Hauteur finale (mm)", 50, 300, 150, 10)
    
    if fichier_image is not None and st.button("✨ 1. Générer le modèle 3D", type="primary", use_container_width=True):
        with st.spinner("🧠 Détourage et sculpture 3D en cours..."):
            model = charger_moteur_3d()
            image_brute = Image.open(fichier_image).convert("RGBA")
            image_sans_fond = remove(image_brute)
            image_prete = resize_foreground(image_sans_fond, 0.85)
            fond_gris = Image.new("RGBA", image_prete.size, (127, 127, 127, 255))
            image_finale = Image.alpha_composite(fond_gris, image_prete).convert("RGB")

            with torch.no_grad():
                scene_codes = model([image_finale], device="cpu")

            meshes = model.extract_mesh(scene_codes, has_vertex_color=True, resolution=192)
            mesh_3d = meshes[0]

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

            # Sauvegarde sous le nom attendu par main.py
            mesh_3d.export("mario_ia_genere.obj")
            st.session_state.mesh_valide = True

with col2:
    if st.session_state.mesh_valide and os.path.exists("mario_ia_genere.obj"):
        mesh_apercu = trimesh.load("mario_ia_genere.obj")
        v, f = mesh_apercu.vertices, mesh_apercu.faces
        c = mesh_apercu.visual.vertex_colors[:, :3] if hasattr(mesh_apercu.visual, "vertex_colors") else np.full((len(v), 3), 180)
        fig = go.Figure(data=[go.Mesh3d(
            x=v[:, 0], y=v[:, 1], z=v[:, 2],
            i=f[:, 0], j=f[:, 1], k=f[:, 2],
            vertexcolor=[f"rgb({r},{g},{b})" for r, g, b in c],
            flatshading=True
        )])
        fig.update_layout(scene=dict(aspectmode="data"), height=380, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

        if st.button("🧶 2. Valider le 3D et Créer le Patron Complet", type="primary", use_container_width=True):
            with st.spinner("⚙️ Exécution de main.py et calcul des rangs de crochet..."):
                subprocess.run(["python", "main.py"], check=False)
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
