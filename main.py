import sys
import trimesh

def analyser_modele_3d(mesh):
    print("--- Analyse du modèle 3D ---")
    try:
        print(f"Nombre de sommets (points) : {len(mesh.vertices)}")
        print(f"Nombre de faces (triangles) : {len(mesh.faces)}")
        print(f"Modèle étanche (watertight) : {mesh.is_watertight}")
        
        # Dimensions de la boîte englobante (largeur, hauteur, profondeur)
        bounds = mesh.extents
        print(f"Dimensions (X, Y, Z) : {bounds}")
        
    except Exception as e:
        print(f"Erreur lors de l'analyse : {e}")

def main():
    print("--- Projet Crochet 3D Generator ---")
    
    # Création d'une sphère de test parfaite (rayon de 50 mm)
    print("Génération d'une sphère 3D virtuelle pour le test...")
    mesh_sphere = trimesh.creation.icosphere(subdivisions=3, radius=50.0)
    
    # On lance l'analyse de cette sphère
    analyser_modele_3d(mesh_sphere)

if __name__ == "__main__":
    main()
#test