import os
import trimesh
import numpy as np

def generer_patron_partie(nom_partie, perimetres_tranches, hauteur_couche=3.0, largeur_maille=8.0):
    lignes_patron = []
    lignes_patron.append(f"--- Patron de crochet : {nom_partie.upper()} ---")
    lignes_patron.append(f"Hauteur d'un rang : {hauteur_couche:.1f} mm | Taille maille : {largeur_maille} mm\n")
    
    dernier_nb_mailles = 0
    
    for i, perimetre in enumerate(perimetres_tranches):
        nb_mailles = int(round(perimetre / largeur_maille))
        nb_mailles = max(nb_mailles, 4)
        
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
        
    # Sauvegarde dans un fichier dédié à la partie
    nom_fichier_sortie = f"patron_{nom_partie}.md"
    with open(nom_fichier_sortie, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes_patron))
    print(f"[Succès] Fichier généré : {nom_fichier_sortie}")

def extraire_tranches_zone(mesh, z_start, z_end):
    # Découpe une portion spécifique de l'objet entre z_start et z_end
    hauteur_couche = 3.0
    hauteurs = np.arange(z_start + hauteur_couche/2, z_end, hauteur_couche)
    perimetres = []
    
    for z in hauteurs:
        section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if section is not None:
            path_2d, _ = section.to_2D()
            perimetre_cumule = path_2d.length
            perimetres.append(perimetre_cumule)
        else:
            perimetres.append(0.0)
    return perimetres

def analyser_modele_par_zones(mesh):
    print("\n--- Analyse anatomique et découpage par zones ---")
    if not mesh.is_watertight:
        trimesh.repair.fill_holes(mesh)
        trimesh.repair.fix_normals(mesh)
        
    # Centrage et normalisation
    mesh.apply_translation(-mesh.centroid)
    
    bounds = mesh.bounds
    z_min, z_max = bounds[0][2], bounds[1][2]
    hauteur_totale = z_max - z_min
    
    if hauteur_totale < 5.0:
        mesh.apply_scale(100.0)
        bounds = mesh.bounds
        z_min, z_max = bounds[0][2], bounds[1][2]
        hauteur_totale = z_max - z_min

    print(f"Hauteur totale de la figurine : {hauteur_totale:.1f} mm")

    # Définition des frontières des zones (en pourcentages de la hauteur)
    # Zone 1 : Jambes (30% du bas)
    # Zone 2 : Corps et Torse (40% du milieu)
    # Zone 3 : Tête et Casquette (30% du haut)
    z_limite_1 = z_min + (hauteur_totale * 0.3)
    z_limite_2 = z_min + (hauteur_totale * 0.7)

    print("Génération des patrons par parties...")
    
    # 1. Les Jambes
    perim_jambes = extraire_tranches_zone(mesh, z_min, z_limite_1)
    if len(perim_jambes) > 0:
        generer_patron_partie("jambes", perim_jambes)

    # 2. Le Corps
    perim_corps = extraire_tranches_zone(mesh, z_limite_1, z_limite_2)
    if len(perim_corps) > 0:
        generer_patron_partie("corps", perim_corps)

    # 3. La Tête
    perim_tete = extraire_tranches_zone(mesh, z_limite_2, z_max)
    if len(perim_tete) > 0:
        generer_patron_partie("tete", perim_tete)

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
        
    analyser_modele_par_zones(mesh)

if __name__ == "__main__":
    main()
