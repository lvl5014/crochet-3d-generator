import os
import trimesh
import numpy as np

def generer_patron_partie(nom_partie, perimetres_tranches, hauteur_couche=2.0, largeur_maille=8.0):
    if len(perimetres_tranches) == 0 or max(perimetres_tranches) == 0:
        return
        
    lignes_patron = []
    lignes_patron.append(f"--- Patron de crochet : {nom_partie.upper()} ---")
    lignes_patron.append(f"Hauteur d'un rang : {hauteur_couche:.1f} mm | Taille maille : {largeur_maille} mm\n")
    
    dernier_nb_mailles = 0
    
    for i, perimetre in enumerate(perimetres_tranches):
        nb_mailles = int(round(perimetre / largeur_maille))
        nb_mailles = max(nb_mailles, 4) # Cercle magique minimum
        
        if i == 0:
            action = "Base / Cercle magique"
        else:
            diff = nb_mailles - dernier_nb_mailles
            if diff > 0:
                action = f"Augmenter de {diff} maille(s)"
            elif diff < 0:
                action = f"Diminuer de {abs(diff)} maille(s)"
            else:
                action = "Travailler tout droit"
                
        ligne = f"Rang {i+1} : {nb_mailles} mailles – ({action})"
        lignes_patron.append(ligne)
        dernier_nb_mailles = nb_mailles
        
    nom_fichier_sortie = f"patron_{nom_partie}.md"
    with open(nom_fichier_sortie, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes_patron))
    print(f"[Succès] Mini-patron généré : {nom_fichier_sortie}")

def extraire_tranches_mesh(sub_mesh, hauteur_couche=2.0):
    bounds = sub_mesh.bounds
    z_min, z_max = bounds[0][2], bounds[1][2]
    hauteurs = np.arange(z_min + hauteur_couche/2, z_max, hauteur_couche)
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
    print("\n--- Scanner intelligent de détails et d'accessoires ---")
    if not mesh.is_watertight:
        trimesh.repair.fill_holes(mesh)
        trimesh.repair.fix_normals(mesh)
        
    # Centrage de la figurine
    mesh.apply_translation(-mesh.centroid)
    
    bounds = mesh.bounds
    z_min, z_max = bounds[0][2], bounds[1][2]
    hauteur_totale = z_max - z_min
    
    if hauteur_totale < 5.0:
        mesh.apply_scale(100.0)
        bounds = mesh.bounds
        z_min, z_max = bounds[0][2], bounds[1][2]
        hauteur_totale = z_max - z_min

    print(f"Hauteur de l'objet analysée : {hauteur_totale:.1f} mm")

    face_centers = mesh.triangles_center

    # 1. SCANNER DU CORPS PRINCIPAL (Jambes, Torse, Tête)
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
                generer_patron_partie(nom, perims)

    # 2. SCANNER DES DÉTAILS ET ACCESSOIRES (Chapeau, Moustaches, Oreilles)
    mask_chapeau = face_centers[:, 2] >= z_tete_limite
    if np.any(mask_chapeau):
        sub_chapeau = mesh.submesh([mask_chapeau], append=True)
        if not sub_chapeau.is_empty and len(sub_chapeau.faces) > 5:
            perims = extraire_tranches_mesh(sub_chapeau)
            generer_patron_partie("detail_chapeau_casquette", perims)

    mask_moustache = (face_centers[:, 1] > (mesh.bounds[1][1] * 0.4)) & (face_centers[:, 2] > z_jambes_limite) & (face_centers[:, 2] < z_tete_limite)
    if np.any(mask_moustache):
        sub_mous = mesh.submesh([mask_moustache], append=True)
        if not sub_mous.is_empty and len(sub_mous.faces) > 5:
            perims = extraire_tranches_mesh(sub_mous)
            generer_patron_partie("detail_moustache_nez", perims)

    x_seuil = (mesh.bounds[1][0] - mesh.bounds[0][0]) * 0.25
    mask_lateral = (np.abs(face_centers[:, 0]) > x_seuil) & (face_centers[:, 2] >= z_jambes_limite) & (face_centers[:, 2] < z_tete_limite)
    if np.any(mask_lateral):
        sub_lat = mesh.submesh([mask_lateral], append=True)
        if not sub_lat.is_empty and len(sub_lat.faces) > 5:
            perims = extraire_tranches_mesh(sub_lat)
            generer_patron_partie("detail_oreilles_cornes_bras", perims)

def main():
    fichiers_stl = [f for f in os.listdir('.') if f.lower().endswith('.stl')]
    nom_fichier = "mario.stl"
    
    if not os.path.exists(nom_fichier) and len(fichiers_stl) > 0:
        nom_fichier = fichiers_stl[0]
        
    if os.path.exists(nom_fichier):
        print(f"Chargement du fichier : {nom_fichier} ...")
        mesh = trimesh.load(nom_fichier)
    else:
        print("Aucun fichier .stl trouvé. Sphère de test par défaut...")
        mesh = trimesh.creation.icosphere(subdivisions=3, radius=50.0)
        
    scanner_details_et_zones(mesh)

if __name__ == "__main__":
    main()
