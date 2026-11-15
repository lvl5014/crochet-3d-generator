import os
import trimesh
import numpy as np

def generer_patron_partie(nom_partie, perimetres_tranches, hauteur_couche=2.0, largeur_maille=8.0):
    if len(perimetres_tranches) == 0 or max(perimetres_tranches) == 0:
        return
        
    lignes_patron = []
    lignes_patron.append(f"# 🧶 Patron de crochet : {nom_partie.upper()}\n")
    
    # Calculs préparatoires pour les métadonnées
    nb_rangs = len(perimetres_tranches)
    hauteur_finale_mm = nb_rangs * hauteur_couche
    
    # Simulation du calcul de fil (environ 15 mm par maille en moyenne pour un amigurumi)
    total_mailles = 0
    instructions_rangs = []
    dernier_nb_mailles = 0
    
    for i, perimetre in enumerate(perimetres_tranches):
        nb_mailles = int(round(perimetre / largeur_maille))
        nb_mailles = max(nb_mailles, 4) # Cercle magique minimum
        total_mailles += nb_mailles
        
        if i == 0:
            action = "Base / Cercle magique initial"
        else:
            diff = nb_mailles - dernier_nb_mailles
            if diff > 0:
                action = f"**Augmenter** de {diff} maille(s)"
            elif diff < 0:
                action = f"**Diminuer** de {abs(diff)} maille(s)"
            else:
                action = "Travailler tout droit (sans modification)"
                
        ligne = f"* **Rang {i+1}** : {nb_mailles} mailles – ({action})"
        instructions_rangs.append(ligne)
        dernier_nb_mailles = nb_mailles

    # Estimation de la longueur de fil en mètres (15 mm = 0.015 m par maille)
    fil_estime_metres = (total_mailles * 15.0) / 1000.0

    # Informations techniques enrichies
    lignes_patron.append("### 📋 Informations techniques :")
    lignes_patron.append(f"- **Hauteur finale estimée** : {hauteur_finale_mm:.1f} mm ({hauteur_finale_mm / 10.0:.1f} cm)")
    lignes_patron.append(f"- **Nombre total de rangs** : {nb_rangs}")
    lignes_patron.append(f"- **Quantité de fil estimée** : ~{fil_estime_metres:.1f} mètres")
    lignes_patron.append(f"- **Taille estimée d'une maille** : {largeur_maille} mm\n")
    
    lignes_patron.append("---")
    lignes_patron.append("### 🧵 Instructions pas à pas :\n")
    lignes_patron.extend(instructions_rangs)
    
    lignes_patron.append("\n---")
    lignes_patron.append("> 💡 **Conseil amigurumi** : Pense à rembourrer la pièce au fur et à mesure, et prévois toujours 10% à 20% de fil en plus pour les coutures et les sécurisations.")
    
    nom_fichier_sortie = f"patron_{nom_partie}.md"
    with open(nom_fichier_sortie, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes_patron))
    print(f"[Succès] Patron complet généré : {nom_fichier_sortie} (~{fil_estime_metres:.1f}m de fil)")

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
    print("\n--- Scanner intelligent : Hauteur & Quantité de fil ---")
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
                generer_patron_partie(nom, perims)

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
