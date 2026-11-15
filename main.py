import os
import trimesh
import numpy as np

def traduire_en_crochet(perimetres_tranches, hauteur_couche=5.0, largeur_maille=8.0):
    lignes_patron = []
    lignes_patron.append("--- Génération du patron de crochet (Formes Complexes) ---")
    lignes_patron.append(f"Hauteur d'un rang : {hauteur_couche} mm | Taille estimée d'une maille : {largeur_maille} mm\n")
    
    dernier_nb_mailles = 0
    
    for i, perimetre_total in enumerate(perimetres_tranches):
        nb_mailles = int(round(perimetre_total / largeur_maille))
        nb_mailles = max(nb_mailles, 4) # Minimum 4 mailles pour un cercle magique
        
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
        
    # Affichage dans la console
    for ligne in lignes_patron:
        print(ligne)
        
    # Sauvegarde automatique dans le fichier Markdown
    nom_sortie = "patron_crochet.md"
    with open(nom_sortie, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes_patron))
    print(f"\n[Succès] Patron complexe sauvegardé dans : {nom_sortie}")

def analyser_modele_3d(mesh):
    print("\n--- Analyse géométrique multi-contours ---")
    if not mesh.is_watertight:
        print("Attention : Le modèle n'est pas étanche. Réparation en cours...")
        trimesh.repair.fill_holes(mesh)
        trimesh.repair.fix_normals(mesh)
    else:
        print("Le modèle 3D est propre et étanche.")
        
    bounds = mesh.bounds
    z_min, z_max = bounds[0][2], bounds[1][2]
    hauteur_couche = 5.0 
    
    hauteurs = np.arange(z_min + hauteur_couche/2, z_max, hauteur_couche)
    perimetres_tranches = []
    
    for z in hauteurs:
        section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if section is not None:
            path_2d, _ = section.to_2D()
            
            # Gestion des contours multiples (si la tranche contient plusieurs entités séparées)
            perimetre_cumule = 0.0
            if hasattr(path_2d, 'entities') and len(path_2d.entities) > 0:
                # Si le chemin possède plusieurs entités distinctes
                try:
                    # On somme la longueur de tous les sous-contours détectés
                    perimetre_cumule = sum(entity.length(path_2d.vertices) for entity in path_2d.entities)
                except:
                    perimetre_cumule = path_2d.length
            else:
                perimetre_cumule = path_2d.length
                
            perimetres_tranches.append(perimetre_cumule)
        else:
            perimetres_tranches.append(0.0)
            
    if len(perimetres_tranches) > 0:
        traduire_en_crochet(perimetres_tranches, hauteur_couche=hauteur_couche)
    else:
        print("Erreur : Impossible de découper le modèle.")

def main():
    nom_fichier = "20mm_cube.stl"
    
    if os.path.exists(nom_fichier):
        print(f"Chargement du fichier 3D externe : {nom_fichier} ...")
        mesh = trimesh.load(nom_fichier)
    else:
        print(f"Fichier '{nom_fichier}' non trouvé dans le dossier.")
        print("Basculement automatique : génération d'une sphère 3D virtuelle de test...")
        mesh = trimesh.creation.icosphere(subdivisions=3, radius=50.0)
        
    analyser_modele_3d(mesh)

if __name__ == "__main__":
    main()
