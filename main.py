import numpy as np
import trimesh

def analyser_modele_3d(mesh):
    print(f"--- Analyse du modèle 3D ---")
    print(f"Nombre de sommets : {len(mesh.vertices)}")
    print(f"Nombre de faces : {len(mesh.faces)}")
    print(f"Volume : {mesh.volume:.2f} mm³")
    
    # On lance le découpage en tranches juste après l'analyse
    decouper_en_tranches(mesh, hauteur_rang=5.0)

def decouper_en_tranches(mesh, hauteur_rang=5.0):import numpy as np
import trimesh

def analyser_modele_3d(mesh):
    print(f"--- Analyse du modèle 3D ---")
    print(f"Nombre de sommets : {len(mesh.vertices)}")
    print(f"Nombre de faces : {len(mesh.faces)}")
    print(f"Volume : {mesh.volume:.2f} mm³")
    
    # On lance le découpage en tranches juste après l'analyse
    decouper_en_tranches(mesh, hauteur_rang=5.0)

def decouper_en_tranches(mesh, hauteur_rang=5.0):
    print(f"\n--- Début du découpage (hauteur par rang : {hauteur_rang} mm) ---")
    
    # 1. Récupérer les limites basse et haute du modèle sur l'axe Z (la hauteur)
    z_min = mesh.bounds[0][2]
    z_max = mesh.bounds[1][2]
    
    print(f"Base (Z min) : {z_min:.2f} mm | Sommet (Z max) : {z_max:.2f} mm")
    
    # 2. Générer les hauteurs de chaque rang du bas vers le haut
    hauteurs_coupes = np.arange(z_min + hauteur_rang, z_max, hauteur_rang)
    print(f"Nombre total de rangs calculés : {len(hauteurs_coupes)}")
    
    # 3. Parcourir chaque hauteur pour couper la sphère
    for i, z in enumerate(hauteurs_coupes):
        # Définition d'un plan horizontal à la hauteur z
        plan_origine = [0, 0, z]
        plan_normale = [0, 0, 1] # Pointe vers le haut
        
        # Extraction de la section (l'intersection entre le plan et le maillage 3D)
        section = mesh.section(plane_origin=plan_origine, plane_normal=plan_normale)
        
        if section is not None:
            # Transformation de la coupe 3D en un chemin 2D pour mesurer sa longueur (périmètre)
            path_2d, _ = section.to_2D()
            perimetre = path_2d.length
            
            print(f"Rang {i+1} (Z = {z:.1f} mm) -> Périmètre de la tranche : {perimetre:.2f} mm")
        else:
            print(f"Rang {i+1} (Z = {z:.1f} mm) -> Tranche vide.")

def main():
    print("Génération d'une sphère 3D virtuelle pour le test...")
    # Création d'une sphère de test parfaite (rayon de 50 mm)
    mesh_sphere = trimesh.creation.icosphere(subdivisions=3, radius=50.0)
    
    # On lance l'analyse de cette sphère
    analyser_modele_3d(mesh_sphere)

if __name__ == "__main__":
    main()
    print(f"\n--- Début du découpage (hauteur par rang : {hauteur_rang} mm) ---")
    
    # 1. Récupérer les limites basse et haute du modèle sur l'axe Z (la hauteur)
    z_min = mesh.bounds[0][2]
    z_max = mesh.bounds[1][2]
    
    print(f"Base (Z min) : {z_min:.2f} mm | Sommet (Z max) : {z_max:.2f} mm")
    
    # 2. Générer les hauteurs de chaque rang du bas vers le haut
    hauteurs_coupes = np.arange(z_min + hauteur_rang, z_max, hauteur_rang)
    print(f"Nombre total de rangs calculés : {len(hauteurs_coupes)}")
    
    # 3. Parcourir chaque hauteur pour couper la sphère
    for i, z in enumerate(hauteurs_coupes):
        # Définition d'un plan horizontal à la hauteur z
        plan_origine = [0, 0, z]
        plan_normale = [0, 0, 1] # Pointe vers le haut
        
        # Extraction de la section (l'intersection entre le plan et le maillage 3D)
        section = mesh.section(plane_origin=plan_origine, plane_normal=plan_normale)
        
        if section is not None:
            # Transformation de la coupe 3D en un chemin 2D pour mesurer sa longueur (périmètre)
            path_2d, _ = section.to_2D()
            perimetre = path_2d.length
            
            print(f"Rang {i+1} (Z = {z:.1f} mm) -> Périmètre de la tranche : {perimetre:.2f} mm")
        else:
            print(f"Rang {i+1} (Z = {z:.1f} mm) -> Tranche vide.")

def main():
    print("Génération d'une sphère 3D virtuelle pour le test...")
    # Création d'une sphère de test parfaite (rayon de 50 mm)
    mesh_sphere = trimesh.creation.icosphere(subdivisions=3, radius=50.0)
    
    # On lance l'analyse de cette sphère
    analyser_modele_3d(mesh_sphere)

if __name__ == "__main__":
    main()