import sys
import trimesh

def analyser_modele_3d(chemin_fichier):
    print(f"--- Analyse du fichier : {chemin_fichier} ---")
    
    try:
        # Chargement du modèle 3D (ex: .obj ou .stl)
        mesh = trimesh.load(chemin_fichier)
        
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)
            
        print(f"Nombre de sommets (points) : {len(mesh.vertices)}")
        print(f"Nombre de faces (triangles) : {len(mesh.faces)}")
        print(f"Modèle étanche (watertight) : {mesh.is_watertight}")
        
    except Exception as e:
        print(f"Erreur lors du chargement du fichier 3D : {e}")

def main():
    print("--- Projet Crochet 3D Generator ---")
    print("Environnement configuré avec succès.")
    # Exemple d'appel (quand tu auras un fichier 3D de test)
    # analyser_modele_3d("mon_objet.obj")

if __name__ == "__main__":
    main()
