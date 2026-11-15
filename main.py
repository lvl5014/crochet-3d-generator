import os
import trimesh
import numpy as np

# ==========================================
# 🧶 CONFIGURATION DU MATÉRIEL (CALIBRAGE)
# ==========================================
CROCHET_TAILLE = "3.5 mm"
TYPE_FIL = "Coton classique (Sport / DK)"
LARGEUR_MAILLE_MM = 8.0
HAUTEUR_COUCHE_MM = 2.0
# ==========================================

def classifier_couleur(rgb):
    r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
    if r > 150 and g < 100 and b < 100: return "Rouge"
    elif r < 100 and g < 100 and b > 150: return "Bleu"
    elif r < 100 and g > 150 and b < 100: return "Vert"
    elif r > 200 and g > 200 and b > 200: return "Blanc"
    elif r < 50 and g < 50 and b < 50: return "Noir"
    elif r > 180 and g > 130 and b < 120: return "Peau"
    return f"RGB({r},{g},{b})"

def detecter_couleurs_jacquard_tranche(sub_mesh, z_hauteur):
    if not hasattr(sub_mesh.visual, 'vertex_colors') and not hasattr(sub_mesh.visual, 'face_colors'):
        return "100% Couleur unie"

    face_centers = sub_mesh.triangles_center
    masque_tranche = np.abs(face_centers[:, 2] - z_hauteur) <= (HAUTEUR_COUCHE_MM / 2.0)
    
    if not np.any(masque_tranche):
        return "Travailler tout droit"

    colors = None
    if hasattr(sub_mesh.visual, 'face_colors') and sub_mesh.visual.face_colors is not None:
        colors = sub_mesh.visual.face_colors[masque_tranche]
    elif hasattr(sub_mesh.visual, 'vertex_colors') and sub_mesh.visual.vertex_colors is not None:
        colors = sub_mesh.visual.vertex_colors[:len(masque_tranche)]

    if colors is None or len(colors) == 0:
        return "100% Couleur unie"

    centres_sec = face_centers[masque_tranche]
    x, y = centres_sec[:, 0], centres_sec[:, 1]
    
    quadrants = {
        "Avant": colors[(y > 0) & (np.abs(x) >= np.abs(y))],
        "Arrière": colors[(y < 0) & (np.abs(x) >= np.abs(y))],
        "Droite": colors[(x > 0) & (np.abs(y) > np.abs(x))],
        "Gauche": colors[(x < 0) & (np.abs(y) > np.abs(x))]
    }

    changements = []
    for zone, col_arr in quadrants.items():
        if len(col_arr) > 0:
            moy = np.mean(col_arr[:, :3], axis=0)
            nom_c = classifier_couleur(moy)
            changements.append(f"{nom_c} ({zone})")

    if len(set(changements)) <= 1:
        return "100% Couleur unie"
    else:
        return "Multicolore / Jacquard : " + " | ".join(set(changements))

def calculer_simulation_physique(sub_mesh):
    try:
        volume_cm3 = abs(sub_mesh.volume) / 1000.0
    except:
        volume_cm3 = 10.0
    poids_ouate_g = volume_cm3 * 0.015
    bounds = sub_mesh.bounds
    largeur = bounds[1][0] - bounds[0][0]
    profondeur = bounds[1][1] - bounds[0][1]
    hauteur = bounds[1][2] - bounds[0][2]
    besoin_armature = (largeur < 15.0 or profondeur < 15.0) and hauteur > 20.0
    return volume_cm3, poids_ouate_g, besoin_armature

def formater_instruction_amigurumi_jacquard(i, nb_mailles, dernier_nb_mailles, sub_mesh, z_val):
    if i == 0:
        return f"* **R{i+1}** : Cercle magique de **{nb_mailles} ms** (mailles serrées)"
    
    diff = nb_mailles - dernier_nb_mailles
    action_base = ""
    if diff > 0:
        if diff == dernier_nb_mailles:
            action_base = f"[1 ms, 1 aug] répéter {dernier_nb_mailles} fois"
        else:
            action_base = f"ms avec {diff} aug réparties"
    elif diff < 0:
        action_base = f"ms avec {abs(diff)} dim réparties"
    else:
        action_base = "1 ms dans chaque maille (tout droit)"

    detail_jacquard = detecter_couleurs_jacquard_tranche(sub_mesh, z_val)
    return f"* **R{i+1}** : {action_base} (**{nb_mailles} ms**) — *Note Jacquard : {detail_jacquard}*"

def generer_patron_partie(nom_partie, perimetres_tranches, hauteurs_z, sub_mesh=None):
    if len(perimetres_tranches) == 0 or max(perimetres_tranches) == 0:
        return None
        
    couleur_partie = "Standard"
    if sub_mesh is not None:
        colors = sub_mesh.visual.vertex_colors if hasattr(sub_mesh.visual, 'vertex_colors') else getattr(sub_mesh.visual, 'face_colors', None)
        if colors is not None and len(colors) > 0:
            couleur_partie = classifier_couleur(np.mean(colors[:, :3], axis=0))

    vol_cm3, poids_ouate, armature = calculer_simulation_physique(sub_mesh) if sub_mesh else (10.0, 0.5, False)

    lignes_patron = []
    lignes_patron.append(f"## 🧶 Partie : {nom_partie.upper()}\n")
    
    nb_rangs = len(perimetres_tranches)
    hauteur_finale_mm = nb_rangs * HAUTEUR_COUCHE_MM
    
    total_mailles = 0
    instructions_rangs = []
    dernier_nb_mailles = 0
    
    for i, (perimetre, z_val) in enumerate(zip(perimetres_tranches, hauteurs_z)):
        nb_mailles = int(round(perimetre / LARGEUR_MAILLE_MM))
        nb_mailles = max(nb_mailles, 4)
        total_mailles += nb_mailles
        
        instruction_ligne = formater_instruction_amigurumi_jacquard(i, nb_mailles, dernier_nb_mailles, sub_mesh, z_val)
        instructions_rangs.append(instruction_ligne)
        dernier_nb_mailles = nb_mailles

    fil_estime_metres = (total_mailles * 15.0) / 1000.0

    lignes_patron.append("### 📋 Spécifications :")
    lignes_patron.append(f"- **Couleur principale** : 🎨 {couleur_partie}")
    lignes_patron.append(f"- **Hauteur estimée** : {hauteur_finale_mm:.1f} mm ({hauteur_finale_mm / 10.0:.1f} cm)")
    lignes_patron.append(f"- **Rangs** : {nb_rangs} | **Fil estimé** : ~{fil_estime_metres:.1f}m | **Ouate** : ~{poids_ouate:.1f}g")
    if armature:
        lignes_patron.append(f"- **Armature** : ⚠️ Fil de fer conseillé.")
    lignes_patron.append("\n### 🧵 Instructions :")
    lignes_patron.extend(instructions_rangs)
    lignes_patron.append("\n---")
    
    contenu_texte = "\n".join(lignes_patron)
    
    # Sauvegarde individuelle également
    with open(f"patron_{nom_partie}.md", "w", encoding="utf-8") as f:
        f.write(contenu_texte)
        
    return contenu_texte

def compiler_master_document(toutes_les_parties, guide_texte):
    """Compile tout dans un document maître Markdown et HTML prêt pour impression PDF"""
    master_md = []
    master_md.append("# 🌟 PATRON GLOBAL AMIGURUMI - MASTER PRO 🌟\n")
    master_md.append(f"> **Matériel de référence** : Crochet {CROCHET_TAILLE} | Fil : {TYPE_FIL}\n")
    master_md.append("---")
    master_md.append(guide_texte)
    master_md.append("\n---")
    master_md.extend(toutes_les_parties)
    
    # 1. Écriture du Markdown Global
    with open("patron_global_ultime.md", "w", encoding="utf-8") as f:
        f.write("\n".join(master_md))
        
    # 2. Génération d'un fichier HTML stylisé pour conversion PDF instantanée
    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Patron Amigurumi Pro - Ultimate Edition</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; color: #333; line-height: 1.6; }}
        h1 {{ color: #2c3e50; text-align: center; border-bottom: 3px solid #3498db; padding-bottom: 15px; }}
        h2 {{ color: #e74c3c; border-bottom: 2px solid #bdc3c7; padding-top: 20px; }}
        h3 {{ color: #2980b9; }}
        blockquote {{ background: #f8f9fa; border-left: 5px solid #3498db; margin: 20px 0; padding: 15px; }}
        ul {{ list-style-type: disc; padding-left: 20px; }}
        li {{ margin-bottom: 6px; }}
        .no-print {{ text-align: center; margin: 30px 0; }}
        .btn {{ background: #e74c3c; color: white; padding: 12px 25px; text-decoration: none; font-weight: bold; border-radius: 5px; display: inline-block; cursor: pointer; }}
        @media print {{ .no-print {{ display: none; }} body {{ margin: 10px; }} }}
    </style>
</head>
<body>
    <div class="no-print">
        <button class="btn" onclick="window.print()">🖨️ Enregistrer en PDF / Imprimer le Patron</button>
    </div>
    <h1>🌟 Patron Global Amigurumi - Master Pro 🌟</h1>
    <p style="text-align: center;"><strong>Matériel :</strong> Crochet {CROCHET_TAILLE} | <strong>Fil :</strong> {TYPE_FIL}</p>
    <hr>
"""
    # Conversion basique des blocs Markdown pour l'affichage HTML propre
    corps_html = "\n".join(master_md).replace("# 🌟 ", "<h1>").replace("## 🧶 ", "<h2>").replace("### ", "<h3>").replace("* **", "<li><b>").replace("** : ", "</b> : ")
    html_content += f"<div>{corps_html}</div></body></html>"
    
    with open("patron_global_ultime.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("[Succès] Export Multi-Formats généré : 'patron_global_ultime.md' et 'patron_global_ultime.html'")

def extraire_tranches_mesh_avancees(sub_mesh):
    bounds = sub_mesh.bounds
    z_min, z_max = bounds[0][2], bounds[1][2]
    hauteurs = np.arange(z_min + HAUTEUR_COUCHE_MM/2, z_max, HAUTEUR_COUCHE_MM)
    perimetres = []
    
    for z in hauteurs:
        section = sub_mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if section is not None:
            path_2d, _ = section.to_2D()
            perimetre_total = path_2d.length
            if hasattr(path_2d, 'entities') and len(path_2d.entities) > 1:
                try:
                    perimetre_total = sum(e.length(path_2d.vertices) for e in path_2d.entities)
                except:
                    pass
            perimetres.append(perimetre_total)
        else:
            perimetres.append(0.0)
    return perimetres, hauteurs

def scanner_details_et_zones(mesh):
    print(f"\n--- Scanner intelligent & Export Master Multi-Formats ---")
    if not mesh.is_watertight:
        trimesh.repair.fill_holes(mesh)
        trimesh.repair.fix_normals(mesh)
        
    mesh.apply_translation(-mesh.centroid)
    
    bounds = mesh.bounds
    z_min, z_max = bounds[0][2], bounds[1][2]
    hauteur_totale = z_max - z_min
    
    if hauteur_totale < 5.0:
        mesh.apply_scale(100.0)
        bounds = mesh.bounds
        z_min, z_max = bounds[0][2], bounds[1][2]
        hauteur_totale = z_max - z_min

    print(f"Hauteur globale de l'objet : {hauteur_totale:.1f} mm")
    face_centers = mesh.triangles_center

    z_jambes_limite = z_min + (hauteur_totale * 0.3)
    z_corps_limite = z_min + (hauteur_totale * 0.65)
    z_tete_limite = z_min + (hauteur_totale * 0.85)

    zones_corps = {
        "jambes": (z_min, z_jambes_limite),
        "corps": (z_jambes_limite, z_corps_limite),
        "tete": (z_corps_limite, z_tete_limite)
    }

    toutes_les_parties = []

    for nom, (z_s, z_e) in zones_corps.items():
        mask = (face_centers[:, 2] >= z_s) & (face_centers[:, 2] < z_e)
        if np.any(mask):
            sub = mesh.submesh([mask], append=True)
            if not sub.is_empty:
                perims, h_z = extraire_tranches_mesh_avancees(sub)
                texte_partie = generer_patron_partie(nom, perims, h_z, sub)
                if texte_partie:
                    toutes_les_parties.append(texte_partie)

    details_trouves = []
    mask_chapeau = face_centers[:, 2] >= z_tete_limite
    if np.any(mask_chapeau):
        sub_chapeau = mesh.submesh([mask_chapeau], append=True)
        if not sub_chapeau.is_empty and len(sub_chapeau.faces) > 5:
            perims, h_z = extraire_tranches_mesh_avancees(sub_chapeau)
            texte_partie = generer_patron_partie("detail_chapeau_casquette", perims, h_z, sub_chapeau)
            if texte_partie: toutes_les_parties.append(texte_partie)
            details_trouves.append("detail_chapeau_casquette")

    mask_moustache = (face_centers[:, 1] > (mesh.bounds[1][1] * 0.4)) & (face_centers[:, 2] > z_jambes_limite) & (face_centers[:, 2] < z_tete_limite)
    if np.any(mask_moustache):
        sub_mous = mesh.submesh([mask_moustache], append=True)
        if not sub_mous.is_empty and len(sub_mous.faces) > 5:
            perims, h_z = extraire_tranches_mesh_avancees(sub_mous)
            texte_partie = generer_patron_partie("detail_moustache_nez", perims, h_z, sub_mous)
            if texte_partie: toutes_les_parties.append(texte_partie)
            details_trouves.append("detail_moustache_nez")

    x_seuil = (mesh.bounds[1][0] - mesh.bounds[0][0]) * 0.25
    mask_lateral = (np.abs(face_centers[:, 0]) > x_seuil) & (face_centers[:, 2] >= z_jambes_limite) & (face_centers[:, 2] < z_tete_limite)
    if np.any(mask_lateral):
        sub_lat = mesh.submesh([mask_lateral], append=True)
        if not sub_lat.is_empty and len(sub_lat.faces) > 5:
            perims, h_z = extraire_tranches_mesh_avancees(sub_lat)
            texte_partie = generer_patron_partie("detail_oreilles_cornes_bras", perims, h_z, sub_lat)
            if texte_partie: toutes_les_parties.append(texte_partie)
            details_trouves.append("detail_oreilles_cornes_bras")

    # Texte du guide d'assemblage
    guide_texte = "## 🗺️ Guide d'assemblage et de cartographie spatiale\n\n"
    if "detail_chapeau_casquette" in details_trouves: guide_texte += "- **Chapeau / Casquette** : À positionner au sommet de la tête.\n"
    if "detail_moustache_nez" in details_trouves: guide_texte += "- **Moustache / Nez** : À coudre sur la face avant de la tête.\n"
    if "detail_oreilles_cornes_bras" in details_trouves: guide_texte += "- **Membres / Accessoires latéraux** : À répartir symétriquement.\n"
    guide_texte += "\n> 💡 **Astuce** : Épingle toutes les pièces avant la couture définitive."

    # Compilation globale Master
    compiler_master_document(toutes_les_parties, guide_texte)

def main():
    nom_fichier = "mario_ia_genere.obj" if os.path.exists("mario_ia_genere.obj") else "mario.stl"
    if os.path.exists(nom_fichier):
        print(f"Chargement du modèle 3D : {nom_fichier} ...")
        mesh = trimesh.load(nom_fichier)
    else:
        print("Aucun fichier trouvé. Sphère de test...")
        mesh = trimesh.creation.icosphere(subdivisions=3, radius=50.0)
        
    scanner_details_et_zones(mesh)

if __name__ == "__main__":
    main()
