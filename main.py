import numpy as np
import trimesh

def analyser_modele_3d(mesh):
    print(f"--- Analyse du modèle 3D ---")
    print(f"Nombre de sommets : {len(mesh.vertices)}")
    print(f"Nombre de faces : {len(mesh.faces)}")
    print(f"Volume : {mesh.volume:.2f} mm³")
    
    # 1. Découpage en tranches
    perimetres = decouper_en_tranches(mesh, hauteur_rang=5.0)
    
    # 2. Traduction en mailles de crochet
    if perimetres:
        traduire_en_crochet(perimetres, largeur_maille=8.0)

def decouper_en_tranches(mesh, hauteur_rang=5.0):
    print(f"\n--- Début du découpage (hauteur par rang : {hauteur_rang} mm) ---")
    
    z_min = mesh.bounds[0][2]
    z_max = mesh.bounds[1][2]
    
    hauteurs_coupes = np.arange(z_min + hauteur_rang, z_max, hauteur_rang)
    perimetres = []
    
    for i, z in enumerate(hauteurs_coupes):
        plan_origine = [0, 0, z]
        plan_normale = [0, 0, 1]
        
        section = mesh.section(plane_origin=plan_origine, plane_normal=plan_normale)
        
        if section is not None:
            path_2d, _ = section.to_2D()
            perimetre = path_2d.length
            perimetres.append(perimetre)
            print(f"Rang {i+1} (Z = {z:.1f} mm) -> Périmètre : {perimetre:.2f} mm")
        else:
            print(f"Rang {i+1} (Z = {z:.1f} mm) -> Tranche vide.")
            
    return perimetres

def traduire_en_crochet(perimetres, largeur_maille=8.0):
    print(f"\n--- Génération du patron de crochet ---")
    print(f"Taille estimée d'une maille : {largeur_maille} mm\n")
    
    dernier_nb_mailles = 0
    
    for i, perimetre in enumerate(perimetres):
        # On calcule le nombre de mailles nécessaires pour faire le tour de la tranche
        nb_mailles = int(round(perimetre / largeur_maille))
        nb_mailles = max(nb_mailles, 4) # Minimum 4 mailles pour tenir un cercle
        
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
                
        print(f"Rang {i+1} : {nb_mailles} mailles — ({action})")
        dernier_nb_mailles = nb_mailles

def main():
    print("Génération d'une sphère 3D virtuelle pour le test...")
    mesh_sphere = trimesh.creation.icosphere(subdivisions=3, radius=50.0)
    analyser_modele_3d(mesh_sphere)

if __name__ == "__main__":
    main()
