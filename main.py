import os
import json
import trimesh
import numpy as np

# ==========================================
# 🧶 CONFIGURATION PAR DÉFAUT
# ==========================================
CROCHET_DEFAUT = 3.5
LAINE_DEFAUT = "sport"

CATALOGUE_FILS_REELS = [
    {"ref": "04", "nom": "True Red", "rgb": [215, 38, 56], "hex": "#d72638"},
    {"ref": "88", "nom": "Royal Blue", "rgb": [30, 100, 200], "hex": "#1e64c8"},
    {"ref": "01", "nom": "White", "rgb": [245, 245, 245], "hex": "#f5f5f5"},
    {"ref": "12", "nom": "Black", "rgb": [30, 30, 30], "hex": "#1e1e1e"},
    {"ref": "42", "nom": "Beige / Peau", "rgb": [235, 185, 150], "hex": "#ebb996"},
    {"ref": "73", "nom": "Green", "rgb": [40, 160, 80], "hex": "#28a050"},
    {"ref": "30", "nom": "Yellow", "rgb": [245, 210, 50], "hex": "#f5d232"}
]
# ==========================================

def rgb_vers_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

def trouver_fil_reel_le_plus_proche(rgb_cible):
    r_c, g_c, b_c = rgb_cible[0], rgb_cible[1], rgb_cible[2]
    meilleur_match = CATALOGUE_FILS_REELS[0]
    min_distance = float('inf')

    for fil in CATALOGUE_FILS_REELS:
        fr, fg, fb = fil["rgb"]
        dist = np.sqrt((r_c - fr)**2 + (g_c - fg)**2 + (b_c - fb)**2)
        if dist < min_distance:
            min_distance = dist
            meilleur_match = fil

    if min_distance > 40:
        hex_c = rgb_vers_hex(rgb_cible)
        return f"Nuance RGB({int(r_c)},{int(g_c)},{int(b_c)})", hex_c
    
    return f"{meilleur_match['nom']} (Hobbii {meilleur_match['ref']})", meilleur_match["hex"]

def extraire_couleurs_mailles_par_maille(sub_mesh, z_hauteur, nb_mailles):
    if not hasattr(sub_mesh.visual, 'vertex_colors') and not hasattr(sub_mesh.visual, 'face_colors'):
        return [("#1e64c8", "Royal Blue")] * nb_mailles

    face_centers = sub_mesh.triangles_center
    masque_tranche = np.abs(face_centers[:, 2] - z_hauteur) <= 1.0
    
    if not np.any(masque_tranche):
        return [("#1e64c8", "Royal Blue")] * nb_mailles

    colors = None
    if hasattr(sub_mesh.visual, 'face_colors') and sub_mesh.visual.face_colors is not None:
        colors = sub_mesh.visual.face_colors[masque_tranche]
    elif hasattr(sub_mesh.visual, 'vertex_colors') and sub_mesh.visual.vertex_colors is not None:
        colors = sub_mesh.visual.vertex_colors[:len(masque_tranche)]

    if colors is None or len(colors) == 0:
        return [("#1e64c8", "Royal Blue")] * nb_mailles

    centres_sec = face_centers[masque_tranche]
    angles_faces = np.arctan2(centres_sec[:, 1], centres_sec[:, 0])
    
    couleurs_mailles = []
    for k in range(nb_mailles):
        angle_cible = -np.pi + (k * 2.0 * np.pi / nb_mailles)
        delta_angles = np.abs(angles_faces - angle_cible)
        indices_proches = np.where(delta_angles < (np.pi / nb_mailles))[0]
        
        if len(indices_proches) > 0:
            moy_rgb = np.mean(colors[indices_proches][:, :3], axis=0)
        else:
            moy_rgb = np.mean(colors[:, :3], axis=0)
            
        nom_fil, hex_c = trouver_fil_reel_le_plus_proche(moy_rgb)
        couleurs_mailles.append((hex_c, nom_fil))
        
    return couleurs_mailles

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

def generer_donnees_partie(nom_partie, sub_mesh):
    if sub_mesh is None or sub_mesh.is_empty:
        return None
        
    bounds = sub_mesh.bounds
    z_min, z_max = bounds[0][2], bounds[1][2]
    hauteur_totale = z_max - z_min
    if hauteur_totale <= 0: hauteur_totale = 10.0

    vol_cm3, poids_ouate, armature = calculer_simulation_physique(sub_mesh)
    
    couleur_partie = "Standard"
    colors = sub_mesh.visual.vertex_colors if hasattr(sub_mesh.visual, 'vertex_colors') else getattr(sub_mesh.visual, 'face_colors', None)
    if colors is not None and len(colors) > 0:
        nom_fil, _ = trouver_fil_reel_le_plus_proche(np.mean(colors[:, :3], axis=0))
        couleur_partie = nom_fil

    hauteurs_tranches = np.arange(z_min + 1.0, z_max, 2.0)
    tranches_couleurs = []
    for z in hauteurs_tranches:
        c_mailles = extraire_couleurs_mailles_par_maille(sub_mesh, z, 12)
        tranches_couleurs.append(c_mailles)

    return {
        "nom": nom_partie,
        "z_min": float(z_min),
        "z_max": float(z_max),
        "hauteur_totale": float(hauteur_totale),
        "vol_cm3": float(vol_cm3),
        "poids_ouate": float(poids_ouate),
        "armature": bool(armature),
        "couleur_partie": couleur_partie,
        "tranches_couleurs": tranches_couleurs
    }

def compiler_master_document(parties_donnees, guide_texte, mesh):
    vertices_json = json.dumps(mesh.vertices.tolist())
    faces_json = json.dumps(mesh.faces.tolist())
    parties_json = json.dumps(parties_donnees)
    
    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Patron Amigurumi Pro - Chronoplanificateur Intégré</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 30px auto; padding: 20px; color: #333; line-height: 1.6; background-color: #fdfdfd; }}
        h1 {{ color: #2c3e50; text-align: center; border-bottom: 3px solid #3498db; padding-bottom: 15px; }}
        h2 {{ color: #e74c3c; border-bottom: 2px solid #bdc3c7; padding-top: 20px; }}
        h3 {{ color: #2980b9; }}
        blockquote {{ background: #f8f9fa; border-left: 5px solid #3498db; margin: 20px 0; padding: 15px; }}
        ul {{ list-style-type: disc; padding-left: 20px; }}
        li {{ margin-bottom: 6px; }}
        
        .config-panel {{ background: #e8f4fc; border: 2px solid #3498db; padding: 20px; border-radius: 8px; margin: 20px 0; display: flex; justify-content: space-around; flex-wrap: wrap; gap: 15px; text-align: center; font-weight: bold; }}
        .config-group select {{ padding: 8px 12px; font-size: 15px; border-radius: 5px; border: 1px solid #3498db; background: white; cursor: pointer; margin-top: 5px; display: block; }}

        .timer-banner {{ background: #27ae60; color: white; padding: 15px; border-radius: 8px; text-align: center; font-size: 17px; font-weight: bold; margin: 20px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}

        .viewer-container {{ background: #1a1a1a; border: 2px solid #3498db; border-radius: 8px; margin: 25px 0; padding: 10px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }}
        #webgl-container {{ width: 100%; height: 350px; border-radius: 6px; overflow: hidden; }}
        .viewer-title {{ color: #fff; font-size: 15px; margin-bottom: 8px; font-weight: bold; }}

        .part-container {{ background: #fff; border: 1px solid #ddd; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        .row-chart {{ display: flex; align-items: center; margin: 4px 0; flex-wrap: wrap; }}
        .row-label {{ width: 110px; font-size: 13px; font-weight: bold; color: #555; }}
        .stitch-cell {{ width: 16px; height: 16px; display: inline-block; margin: 1px; border: 1px solid #bbb; border-radius: 3px; }}
        
        .color-widget {{ background: #eef2f7; border: 2px dashed #3498db; padding: 15px; border-radius: 8px; text-align: center; margin: 25px 0; }}
        .color-widget input {{ padding: 8px; width: 260px; border: 1px solid #bdc3c7; border-radius: 4px; font-size: 15px; }}
        
        .no-print {{ text-align: center; margin: 20px 0; }}
        .btn {{ background: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; font-weight: bold; border-radius: 5px; display: inline-block; cursor: pointer; border: none; font-size: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .btn:hover {{ background: #c0392b; }}
        @media print {{ .no-print, .color-widget, .viewer-container, .config-panel, .timer-banner {{ display: none; }} body {{ margin: 10px; background: white; }} }}
    </style>
</head>
<body>
    <div class="no-print">
        <button class="btn" onclick="window.print()">🖨️ Enregistrer en PDF / Imprimer le Patron</button>
    </div>
    
    <h1>🌟 Patron Global Amigurumi - Master Pro 🌟</h1>
    
    <div class="config-panel">
        <div class="config-group">
            <label for="hookSize">🧶 Taille du Crochet :</label>
            <select id="hookSize" onchange="mettreAJourPatron()">
                <option value="2.0">Crochet 2.0 mm (Mini)</option>
                <option value="2.5">Crochet 2.5 mm (Fin)</option>
                <option value="3.0">Crochet 3.0 mm (Standard fin)</option>
                <option value="3.5" selected>Crochet 3.5 mm (Standard)</option>
                <option value="4.0">Crochet 4.0 mm (Moyen)</option>
                <option value="4.5">Crochet 4.5 mm (Large)</option>
                <option value="5.0">Crochet 5.0 mm (Gros fil)</option>
            </select>
        </div>
        <div class="config-group">
            <label for="yarnType">🧵 Type de Laine / Fil :</label>
            <select id="yarnType" onchange="mettreAJourPatron()">
                <option value="lace">Lace / Fingering (Très fin)</option>
                <option value="sport" selected>Coton Sport / DK (Standard)</option>
                <option value="worsted">Aran / Worsted (Épais)</option>
                <option value="bulky">Bulky / Chunky (Très épais)</option>
                <option value="velvet">Chenille / Velvet (Effet peluche)</option>
            </select>
        </div>
        <div class="config-group">
            <label for="speedLevel">⏱️ Vitesse de Crochet :</label>
            <select id="speedLevel" onchange="mettreAJourPatron()">
                <option value="12">Débutant (12s / maille)</option>
                <option value="8" selected>Intermédiaire (8s / maille)</option>
                <option value="5">Expert / Rapide (5s / maille)</option>
            </select>
        </div>
    </div>
    
    <div class="timer-banner" id="timerBanner">
        ⏱️ Temps de crochet estimé : Calcul en cours...
    </div>

    <div class="viewer-container">
        <div class="viewer-title">🌐 Visualiseur 3D Interactif (Glissez pour pivoter, molette pour zoomer)</div>
        <div id="webgl-container"></div>
    </div>

    <div class="color-widget">
        <h3>🎨 Encyclopédie & Testeur RGB Universel</h3>
        <p>Tapez un nom (ex: <i>rouge</i>, <i>beige</i>) ou un code RGB (ex: <i>234, 172, 121</i>) :</p>
        <input type="text" id="colorInput" placeholder="Ex: rouge ou 234,172,121">
        <button class="btn" style="padding: 8px 15px; margin-left: 10px; background: #3498db;" onclick="chercherCouleur()">Rechercher</button>
        <div id="colorResult" style="margin-top: 10px; font-weight: bold; font-size: 15px;"></div>
    </div>

    <div id="contenu-patron"></div>

    <script>
        const verticesData = {vertices_json};
        const facesData = {faces_json};
        const partiesData = {parties_json};
        const guideTexte = `{guide_texte}`;

        function genererInstructionOptimisee(ancienNb, nouveauNb) {{
            let diff = nouveauNb - ancienNb;
            if (diff === 0) return "1 ms dans chaque maille (tout droit)";
            if (ancienNb === 0) return `Cercle magique de <b>${{nouveauNb}} ms</b>`;

            if (diff > 0) {{
                let augs = diff;
                let base = Math.floor(ancienNb / augs);
                let reste = ancienNb % augs;
                if (base === 0) return `[1 aug] x ${{nouveauNb}} (<b>${{nouveauNb}} ms</b>)`;
                if (reste === 0) return `[${{base}} ms, 1 aug] x ${{augs}} (<b>${{nouveauNb}} ms</b>)`;
                return `[${{base+1}} ms, 1 aug] x ${{reste}}, [${{base}} ms, 1 aug] x ${{augs-reste}} (<b>${{nouveauNb}} ms</b>)`;
            }} else {{
                let dims = Math.abs(diff);
                let base = Math.floor(ancienNb / dims);
                let reste = ancienNb % dims;
                if (base <= 1) return `[1 dim] x ${{dims}} (<b>${{nouveauNb}} ms</b>)`;
                if (reste === 0) return `[${{base-1}} ms, 1 dim] x ${{dims}} (<b>${{nouveauNb}} ms</b>)`;
                return `[${{base}} ms, 1 dim] x ${{reste}}, [${{base-1}} ms, 1 dim] x ${{dims-reste}} (<b>${{nouveauNb}} ms</b>)`;
            }}
        }}

        function mettreAJourPatron() {{
            let hookSize = parseFloat(document.getElementById('hookSize').value);
            let yarnVal = document.getElementById('yarnType').value;
            let secondsPerStitch = parseFloat(document.getElementById('speedLevel').value);
            
            let yarnMultiplier = 1.0;
            let nomLaineTexte = "Coton Sport / DK";
            if(yarnVal === 'lace') {{ yarnMultiplier = 0.8; nomLaineTexte = "Lace / Fingering"; }}
            else if(yarnVal === 'sport') {{ yarnMultiplier = 1.0; nomLaineTexte = "Coton Sport / DK"; }}
            else if(yarnVal === 'worsted') {{ yarnMultiplier = 1.3; nomLaineTexte = "Aran / Worsted"; }}
            else if(yarnVal === 'bulky') {{ yarnMultiplier = 1.6; nomLaineTexte = "Bulky / Chunky"; }}
            else if(yarnVal === 'velvet') {{ yarnMultiplier = 2.0; nomLaineTexte = "Chenille / Velvet (Peluche)"; }}

            let largeurMaille = (hookSize * 2.2) * (yarnMultiplier * 0.9); 
            let hauteurCouche = (hookSize * 0.6) * yarnMultiplier;

            let htmlFinal = "<h2>🗺️ Guide d'assemblage et de cartographie spatiale</h2>" + guideTexte + "<hr>";
            let grandTotalMailles = 0;

            partiesData.forEach(partie => {{
                let nbRangs = Math.max(4, Math.round(partie.hauteur_totale / hauteurCouche));
                let diametreMoyenMM = (partie.z_max - partie.z_min) * 0.8;
                if(diametreMoyenMM < 10) diametreMoyenMM = 20;

                let instructions = [];
                let grillesHTML = [];
                let dernierMailles = 0;
                let totalMaillesPartie = 0;

                for(let i = 0; i < nbRangs; i++) {{
                    let facteurForme = Math.sin((i / nbRangs) * Math.PI);
                    if(facteurForme < 0.2) facteurForme = 0.2;
                    let nbMailles = Math.max(4, Math.round((diametreMoyenMM * facteurForme * Math.PI) / largeurMaille));
                    totalMaillesPartie += nbMailles;

                    let actionTexte = (i === 0) ? `Cercle magique de <b>${{nbMailles}} ms</b>` : genererInstructionOptimisee(dernierMailles, nbMailles);

                    let couleurIndex = i % partie.tranches_couleurs.length;
                    let paletteTranche = partie.tranches_couleurs[couleurIndex] || [["#3498db", "Blue"]];

                    let rowChart = `<div class='row-chart'><span class='row-label'>R${{i+1}} (${{nbMailles}}m) :</span>`;
                    for(let k = 0; k < nbMailles; k++) {{
                        let colorInfo = paletteTranche[k % paletteTranche.length];
                        let hexC = colorInfo[0];
                        let nomF = colorInfo[1];
                        rowChart += `<span class='stitch-cell' style='background-color: ${{hexC}};' title='${{nomF}}'></span>`;
                    }}
                    rowChart += `</div>`;
                    grillesHTML.push(rowChart);

                    instructions.push(`<li><b>R${{i+1}}</b> : ${{actionTexte}}</li>`);
                    dernierMailles = nbMailles;
                }}

                grandTotalMailles += totalMaillesPartie;

                let hauteurEstimeeMM = nbRangs * hauteurCouche;
                let filEstimeMetres = (totalMaillesPartie * (hookSize * 4.5 * yarnMultiplier)) / 1000.0;
                let pelotes = Math.max(1, Math.ceil(filEstimeMetres / 75.0));

                htmlFinal += `<div class='part-container'>`;
                htmlFinal += `<h2>🧶 Partie : ${{partie.nom.toUpperCase()}}</h2>`;
                htmlFinal += `<h3>📋 Spécifications & Fournitures (Crochet ${{hookSize}}mm | ${{nomLaineTexte}}) :</h3>`;
                htmlFinal += `<ul>`;
                htmlFinal += `<li><b>Fil recommandé</b> : 🎨 ${{partie.couleur_partie}}</li>`;
                htmlFinal += `<li><b>Hauteur estimée</b> : ${{hauteurEstimeeMM.toFixed(1)}} mm (${{(hauteurEstimeeMM/10.0).toFixed(1)}} cm)</li>`;
                htmlFinal += `<li><b>Fil estimé</b> : ~${{filEstimeMetres.toFixed(1)}}m (~${{pelotes}} pelote(s)) | <b>Ouate</b> : ~${{partie.poids_ouate.toFixed(1)}}g</li>`;
                if(partie.armature) htmlFinal += `<li><b>Armature</b> : ⚠️ Fil de fer conseillé.</li>`;
                htmlFinal += `</ul>`;
                htmlFinal += `<div class='jacquard-container'><h4>📊 Grille Visuelle & Références Fils (${{partie.nom.toUpperCase()}})</h4>` + grillesHTML.join('') + `</div>`;
                htmlFinal += `<h3>🧵 Instructions et Grille Jacquard :</h3><ul>` + instructions.join('') + `</ul>`;
                htmlFinal += `</div>`;
            }});

            let totalSeconds = grandTotalMailles * secondsPerStitch;
            let totalHours = Math.floor(totalSeconds / 3600);
            let totalMinutes = Math.round((totalSeconds % 3600) / 60);
            
            let tempsTexte = totalHours > 0 ? `${{totalHours}}h ${{totalMinutes}}min` : `${{totalMinutes}} minutes`;
            document.getElementById('timerBanner').innerHTML = `⏱️ Temps de crochet estimé (~${{grandTotalMailles}} mailles) : <b>${{tempsTexte}} de travail</b>`;

            document.getElementById('contenu-patron').innerHTML = htmlFinal;
        }}

        function init3DViewer() {{
            const container = document.getElementById('webgl-container');
            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0x1a1a1a);

            const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
            camera.position.set(0, -150, 100);

            const renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(container.clientWidth, container.clientHeight);
            container.appendChild(renderer.domElement);

            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;

            scene.add(new THREE.AmbientLight(0xffffff, 0.7));
            const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
            dirLight.position.set(100, 200, 300);
            scene.add(dirLight);

            const geometry = new THREE.BufferGeometry();
            const positions = [];
            facesData.forEach(face => {{
                face.forEach(vIdx => {{
                    let v = verticesData[vIdx];
                    positions.push(v[0], v[1], v[2]);
                }});
            }});
            geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
            geometry.computeVertexNormals();

            const material = new THREE.MeshStandardMaterial({{ color: 0x3498db, roughness: 0.4, metalness: 0.2, side: THREE.DoubleSide }});
            const mesh3D = new THREE.Mesh(geometry, material);
            scene.add(mesh3D);

            geometry.computeBoundingBox();
            mesh3D.position.sub(geometry.boundingBox.getCenter(new THREE.Vector3()));

            function animate() {{
                requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }}
            animate();
        }}

        const encyclopedie = [
            {{nom: "rouge", rgb: [255, 0, 0], hex: "#ff0000"}},
            {{nom: "bleu", rgb: [30, 144, 255], hex: "#1e90ff"}},
            {{nom: "vert", rgb: [0, 128, 0], hex: "#008000"}},
            {{nom: "jaune", rgb: [255, 255, 0], hex: "#ffff00"}},
            {{nom: "beige", rgb: [234, 172, 121], hex: "#eaac79"}},
            {{nom: "rose", rgb: [255, 192, 203], hex: "#ffc0cb"}},
            {{nom: "or", rgb: [255, 215, 0], hex: "#ffd700"}}
        ];

        function chercherCouleur() {{
            let val = document.getElementById('colorInput').value.toLowerCase().trim();
            let resDiv = document.getElementById('colorResult');
            if(!val) {{ resDiv.innerHTML = "Entrez un nom ou des valeurs RGB."; return; }}
            if(val.includes(',')) {{
                let rgb = val.split(',').map(Number);
                if(rgb.length === 3 && !rgb.some(isNaN)) {{
                    let hex = `rgb(${{rgb[0]}},${{rgb[1]}},${{rgb[2]}})`;
                    resDiv.innerHTML = `<span style="display:inline-block; width:20px; height:20px; background:${{hex}}; vertical-align:middle; border:1px solid #000; border-radius:3px; margin-right:8px;"></span> Nuance RGB(${{rgb.join(',')}})`;
                    return;
                }}
            }}
            let f = encyclopedie.find(c => c.nom.includes(val));
            if(f) {{
                resDiv.innerHTML = `<span style="display:inline-block; width:20px; height:20px; background:${{f.hex}}; vertical-align:middle; border:1px solid #000; border-radius:3px; margin-right:8px;"></span> ${{f.nom.toUpperCase()}} - RGB(${{f.rgb.join(',')}})`;
            }} else {{
                resDiv.innerHTML = "Couleur introuvable.";
            }}
        }}

        window.onload = function() {{
            init3DViewer();
            mettreAJourPatron();
        }};
    </script>
</body>
</html>
"""
    with open("patron_global_ultime.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("[Succès] Export HTML corrigé et généré avec succès !")

def extraire_tranches_mesh_avancees(sub_mesh):
    bounds = sub_mesh.bounds
    z_min, z_max = bounds[0][2], bounds[1][2]
    hauteurs = np.arange(z_min + 1.0, z_max, 2.0)
    perimetres = []
    for z in hauteurs:
        section = sub_mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if section is not None:
            path_2d, _ = section.to_2D()
            perimetres.append(path_2d.length)
        else:
            perimetres.append(0.0)
    return perimetres, hauteurs

def scanner_details_et_zones(mesh):
    print(f"\n--- Scanner intelligent & Chronoplanificateur ---")
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

    face_centers = mesh.triangles_center
    z_jambes = z_min + (hauteur_totale * 0.3)
    z_corps = z_min + (hauteur_totale * 0.65)
    z_tete = z_corps + ((z_max - z_corps) * 0.5)

    zones = {
        "jambes": (z_min, z_jambes),
        "corps": (z_jambes, z_corps),
        "tete": (z_corps, z_max)
    }

    parties_donnees = []
    for nom, (zs, ze) in zones.items():
        mask = (face_centers[:, 2] >= zs) & (face_centers[:, 2] < ze)
        if np.any(mask):
            sub = mesh.submesh([mask], append=True)
            if not sub.is_empty:
                pdata = generer_donnees_partie(nom, sub)
                if pdata: parties_donnees.append(pdata)

    details_trouves = []
    mask_chapeau = face_centers[:, 2] >= z_tete
    if np.any(mask_chapeau):
        sub_c = mesh.submesh([mask_chapeau], append=True)
        if not sub_c.is_empty and len(sub_c.faces) > 5:
            pdata = generer_donnees_partie("detail_chapeau_casquette", sub_c)
            if pdata: parties_donnees.append(pdata)
            details_trouves.append("detail_chapeau_casquette")

    guide_texte = "<ul>"
    if "detail_chapeau_casquette" in details_trouves: guide_texte += "<li><b>Chapeau / Casquette</b> : À positionner au sommet de la tête.</li>"
    guide_texte += "<li><b>Membres / Corps</b> : À assembler selon la morphologie globale.</li></ul><blockquote>💡 <b>Astuce</b> : Épingle toutes les pièces avant la couture définitive.</blockquote>"

    compiler_master_document(parties_donnees, guide_texte, mesh)

def main():
    nom_fichier = "mario_ia_genere.obj" if os.path.exists("mario_ia_genere.obj") else "mario.stl"
    if os.path.exists(nom_fichier):
        mesh = trimesh.load(nom_fichier)
    else:
        mesh = trimesh.creation.icosphere(subdivisions=3, radius=50.0)
    scanner_details_et_zones(mesh)

if __name__ == "__main__":
    main()
