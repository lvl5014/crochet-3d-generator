import os
import trimesh
import numpy as np

# ==========================================
# 🧶 CONFIGURATION DU MATÉRIEL (CALIBRAGE)
# ==========================================
# Modifie ces valeurs selon ton matériel de crochet :
CROCHET_TAILLE = "3.5 mm"                    # Taille de ton crochet (ex: 2.5 mm, 3.5 mm, 5.0 mm)
TYPE_FIL = "Coton classique (Sport / DK)"    # Type de fil (ex: Fil fin, Coton, Laine Peluche/Chenille)
LARGEUR_MAILLE_MM = 8.0                      # Largeur d'une maille (plus le crochet est gros, plus c'est grand)
HAUTEUR_COUCHE_MM = 2.0                      # Hauteur d'un rang en mm
# ==========================================

def detecter_couleur_dominante(sub_mesh):
    """Analyse les couleurs du sous-mesh (vertex ou face colors)"""
    colors = None
    if hasattr(sub_mesh.visual, 'vertex_colors') and sub_mesh.visual.vertex_colors is not None:
        colors = sub_mesh.visual.vertex_colors
    elif hasattr(sub_mesh.visual, 'face_colors') and sub_mesh.visual.face_colors is not None:
        colors = sub_mesh.visual.face_colors
        
    if colors is not None and len(colors) > 0:
        couleur_moyenne = np.mean(colors[:, :3], axis=0)
        r, g, b = int(couleur_moyenne[0]), int(couleur_moyenne[1]), int(couleur_moyenne[2])
        
        if r > 150 and g < 100 and b < 100: return "Rouge"
        elif r < 100 and g < 100 and b > 150: return "Bleu"
        elif r < 100 and g > 150 and b < 100: return "Vert"
        elif r > 200 and g > 200 and b > 200: return "Blanc"
        elif r < 50 and g < 50 and b < 50: return "Noir"
        elif r > 180 and g > 130 and b < 120: return "Peau / Chair"
        return f"RGB({r},{g},{b})"
    return "Standard"

def formater_instruction_amigurumi(i, nb_mailles, dernier_nb_mailles):
    """Traduit les variations mathématiques en vrai langage de crochet amigurumi"""
    if i == 0:
        return f"* **R{i+1}** : Cercle magique de **{nb_mailles} ms** (mailles serrées)"
    
    diff = nb_mailles - dernier_nb_mailles
    if diff > 0:
        if diff == dernier_nb_mailles:
            return f"* **R{i+1}** : [1 ms, 1 aug] répéter {dernier_nb_mailles} fois (**{nb_mailles} ms**)"
        else:
            return f"* **R{i+1}** : Travailler en ms avec **{diff} augmentations (aug)** réparties (**{nb_mailles} ms**)"
    elif diff < 0:
        nb_dim = abs(diff)
        return f"* **R{i+1}** : Travailler en ms avec **{nb_dim} diminutions (dim)** réparties (**{nb_mailles} ms**)"
    else:
        return f"* **R{i+1}** : Travailler tout droit : 1 ms dans chaque maille (**{nb_mailles} ms**)"

def generer_patron_partie(nom_partie, perimetres_tranches, sub_mesh=None):
    if len(perimetres_tranches) == 0 or max(perimetres_tranches) == 0:
        return
        
    couleur_partie = "Standard"
    if sub_mesh is not None:
        couleur_partie = detecter_couleur_dominante(sub_mesh)

    lignes_patron = []
    lignes_patron.append(f"# 🧶 Patron de crochet : {nom_partie.upper()}\n")
    
    nb_rangs = len(perimetres_tranches)
    hauteur_finale_mm = nb_rangs * HAUTEUR_COUCHE_MM
    
    total_mailles = 0
    instructions_rangs = []
    dernier_nb_mailles = 0
    
    for i, perimetre in enumerate(perimetres_tranches):
        nb_mailles = int(round(perimetre / LARGEUR_MAILLE_MM))
        nb_mailles = max(nb_mailles, 4)
        total_mailles += nb_mailles
        
        instruction_ligne = formater_instruction_amigurumi(i, nb_mailles, dernier_nb_mailles)
        instructions_rangs.append(instruction_ligne)
        dernier_nb_mailles = nb_mailles

    fil_estime_metres = (total_mailles * 15.0) / 1000.0

    # Informations techniques intégrant la jauge de matériel
    lignes_patron.append("### 📋 Informations techniques & Calibrage :")
    lignes_patron.append(f"- **Crochet recommandé** : 🪝 {CROCHET_TAILLE}")
    lignes_patron.append(f"- **Type de fil** : 🧶 {TYPE_FIL}")
    lignes_patron.append(f"- **Couleur principale** : 🎨 {couleur_partie}")
    lignes_patron.append(f"- **Hauteur finale estimée** : {hauteur_finale_mm:.1f} mm ({hauteur_finale_mm / 10.0:.1f} cm)")
    lignes_patron.append(f"- **Nombre total de rangs** : {nb_rangs}")
    lignes_patron.append(f"- **Quantité de fil estimée** : ~{fil_estime_metres:.1f} mètres")
    lignes_patron.append(f"- **Légende** : `ms` = maille serrée | `aug` = augmentation | `dim` = diminution\n")
    
    lignes_patron.append("---")
    lignes_patron.append("### 🧵 Instructions pas à pas :\n")
    lignes_patron.extend(instructions_rangs)
    
    lignes_patron.append("\n---")
    lignes_patron.append(f"> 💡 **Conseil amigurumi** : Utiliser un crochet de **{CROCHET_TAILLE}** avec un fil **{couleur_partie}**. Rembourrer au fur et à mesure.")
    
    nom_fichier_sortie = f"patron_{nom_partie}.md"
    with open(nom_fichier_sortie, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes_patron))
    print(f"[Succès] Patron calibré généré : {nom_fichier_sortie} (Crochet: {CROCHET_TAILLE})")

def extraire_tranches_mesh(sub_mesh):
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
    return perimetres

def scanner_details_et_zones(mesh):
    print(f"\n--- Scanner intelligent (Calibrage : Crochet {CROCHET_TAILLE}) ---")
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

    for nom, (z_s, z_e) in zones_corps.items():
        mask = (face_centers[:, 2] >= z_s) & (face_centers[:, 2] < z_e)
        if np.any(mask):
            sub = mesh.submesh([mask], append=True)
            if not sub.is_empty:
                perims = extraire_tranches_mesh(sub)
                generer_patron_partie(nom, perims, sub)

    mask_chapeau = face_centers[:, 2] >= z_tete_limite
    if np.any(mask_chapeau):
        sub_chapeau = mesh.submesh([mask_chapeau], append=True)
        if not sub_chapeau.is_empty and len(sub_chapeau.faces) > 5:
            perims = extraire_tranches_mesh(sub_chapeau)
            generer_patron_partie("detail_chapeau_casquette", perims, sub_chapeau)

    mask_moustache = (face_centers[:, 1] > (mesh.bounds[1][1] * 0.4)) & (face_centers[:, 2] > z_jambes_limite) & (face_centers[:, 2] < z_tete_limite)
    if np.any(mask_moustache):
        sub_mous = mesh.submesh([mask_moustache], append=True)
        if not sub_mous.is_empty and len(sub_mous.faces) > 5:
            perims = extraire_tranches_mesh(sub_mous)
            generer_patron_partie("detail_moustache_nez", perims, sub_mous)

    x_seuil = (mesh.bounds[1][0] - mesh.bounds[0][0]) * 0.25
    mask_lateral = (np.abs(face_centers[:, 0]) > x_seuil) & (face_centers[:, 2] >= z_jambes_limite) & (face_centers[:, 2] < z_tete_limite)
    if np.any(mask_lateral):
        sub_lat = mesh.submesh([mask_lateral], append=True)
        if not sub_lat.is_empty and len(sub_lat.faces) > 5:
            perims = extraire_tranches_mesh(sub_lat)
            generer_patron_partie("detail_oreilles_cornes_bras", perims, sub_lat)

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
