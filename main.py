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
    masque_tranche = np.abs(face_centers[:, 2] - z_hauteur) <= 2.0
    
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

    hauteurs_tranches = np.arange(z_min + 1.0, z_max, max(2.0, hauteur_totale / 5.0))
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

def compiler_master_document(parties_donnees, mesh):
    if not parties_donnees:
        bounds = mesh.bounds
        parties_donnees = [{
            "nom": "corps_principal",
            "z_min": float(bounds[0][2]),
            "z_max": float(bounds[1][2]),
            "hauteur_totale": float(bounds[1][2] - bounds[0][2]),
            "vol_cm3": 15.0,
            "poids_ouate": 5.0,
            "armature": False,
            "couleur_partie": "Royal Blue (Hobbii 88)",
            "tranches_couleurs": [[("#1e64c8", "Royal Blue (Hobbii 88)")] * 12]
        }]

    vertices_json = json.dumps(mesh.vertices.tolist())
    faces_json = json.dumps(mesh.faces.tolist())
    parties_json = json.dumps(parties_donnees)
    
    manifest_content = {
        "name": "Patron Amigurumi Pro",
        "short_name": "AmigurumiPro",
        "start_url": "patron_global_ultime.html",
        "display": "standalone",
        "background_color": "#fdfdfd",
        "theme_color": "#3498db",
        "icons": []
    }
    with open("manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_content, f, indent=2)

    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Patron Amigurumi Pro - Mobile & Tablette</title>
    <link rel="manifest" href="manifest.json">
    <meta name="theme-color" content="#3498db">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 15px; color: #333; line-height: 1.6; background-color: #fdfdfd; -webkit-tap-highlight-color: transparent; }}
        h1 {{ color: #2c3e50; text-align: center; border-bottom: 3px solid #3498db; padding-bottom: 15px; font-size: 22px; }}
        h2 {{ color: #e74c3c; border-bottom: 2px solid #bdc3c7; padding-top: 20px; font-size: 18px; }}
        h3 {{ color: #2980b9; font-size: 16px; }}
        ul {{ list-style-type: disc; padding-left: 20px; }}
        li {{ margin-bottom: 6px; font-size: 14px; }}
        
        .config-panel {{ background: #e8f4fc; border: 2px solid #3498db; padding: 15px; border-radius: 8px; margin: 15px 0; display: flex; justify-content: space-around; flex-wrap: wrap; gap: 12px; text-align: center; font-weight: bold; }}
        .config-group select {{ padding: 10px; font-size: 16px; border-radius: 5px; border: 1px solid #3498db; background: white; cursor: pointer; margin-top: 5px; width: 100%; max-width: 250px; display: block; }}

        .timer-banner {{ background: #27ae60; color: white; padding: 12px; border-radius: 8px; text-align: center; font-size: 15px; font-weight: bold; margin: 15px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .blueprint-container {{ background: #eef9f2; border: 2px solid #27ae60; padding: 15px; border-radius: 8px; margin: 15px 0; }}
        .blueprint-container h3 {{ color: #27ae60; margin-top: 0; }}

        .viewer-container {{ background: #1a1a1a; border: 2px solid #3498db; border-radius: 8px; margin: 20px 0; padding: 8px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }}
        #webgl-container {{ width: 100%; height: 280px; border-radius: 6px; touch-action: none; overflow: hidden; }}
        .viewer-title {{ color: #fff; font-size: 14px; margin-bottom: 6px; font-weight: bold; }}

        .part-container {{ background: #fff; border: 1px solid #ddd; padding: 15px; border-radius: 8px; margin: 15px 0; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        .row-chart {{ display: flex; align-items: center; margin: 4px 0; flex-wrap: wrap; }}
        .row-label {{ width: 100px; font-size: 12px; font-weight: bold; color: #555; }}
        .stitch-cell {{ width: 14px; height: 14px; display: inline-block; margin: 1px; border: 1px solid #bbb; border-radius: 2px; }}
        
        .tapestry-tip {{ background: #fdf2e9; border: 1px solid #f39c12; padding: 10px; border-radius: 5px; margin: 10px 0; font-size: 12px; color: #d35400; }}

        .color-widget {{ background: #eef2f7; border: 2px dashed #3498db; padding: 12px; border-radius: 8px; text-align: center; margin: 20px 0; }}
        .color-widget input {{ padding: 10px; width: 80%; max-width: 240px; border: 1px solid #bdc3c7; border-radius: 4px; font-size: 15px; }}
        
        .no-print {{ text-align: center; margin: 15px 0; display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; }}
        .btn {{ background: #e74c3c; color: white; padding: 12px 18px; text-decoration: none; font-weight: bold; border-radius: 6px; display: inline-block; cursor: pointer; border: none; font-size: 14px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); -webkit-appearance: none; }}
        .btn:active {{ transform: scale(0.98); }}
        .btn-export {{ background: #2980b9; }}
        
        @media (min-width: 768px) {{
            body {{ max-width: 900px; padding: 25px; }}
            h1 {{ font-size: 28px; }}
            #webgl-container {{ height: 350px; }}
        }}

        @media print {{ .no-print, .color-widget, .viewer-container, .config-panel, .timer-banner {{ display: none; }} body {{ margin: 10px; background: white; }} }}
    </style>
</head>
<body>
    <div class="no-print">
        <button class="btn" onclick="window.print()">🖨️ PDF / Imprimer</button>
        <button class="btn btn-export" onclick="exporterJSON()">📥 JSON</button>
        <button class="btn btn-export" onclick="exporterCSV()">📊 CSV</button>
    </div>
    
    <h1>🌟 Amigurumi Pro - Mobile & Tablette 🌟</h1>
    
    <div class="config-panel">
        <div class="config-group">
            <label for="hookSize">🧶 Crochet :</label>
            <select id="hookSize" onchange="mettreAJourPatron()">
                <option value="2.0">Crochet 2.0 mm</option>
                <option value="2.5">Crochet 2.5 mm</option>
                <option value="3.0">Crochet 3.0 mm</option>
                <option value="3.5" selected>Crochet 3.5 mm</option>
                <option value="4.0">Crochet 4.0 mm</option>
                <option value="4.5">Crochet 4.5 mm</option>
                <option value="5.0">Crochet 5.0 mm</option>
            </select>
        </div>
        <div class="config-group">
            <label for="yarnType">🧵 Fil / Laine :</label>
            <select id="yarnType" onchange="mettreAJourPatron()">
                <option value="lace">Lace (Très fin)</option>
                <option value="sport" selected>Coton Sport / DK</option>
                <option value="worsted">Aran / Worsted</option>
                <option value="bulky">Bulky (Épais)</option>
                <option value="velvet">Chenille / Peluche</option>
            </select>
        </div>
        <div class="config-group">
            <label for="speedLevel">⏱️ Vitesse :</label>
            <select id="speedLevel" onchange="mettreAJourPatron()">
                <option value="12">Débutant (12s/m)</option>
                <option value="8" selected>Intermédiaire (8s/m)</option>
                <option value="5">Expert (5s/m)</option>
            </select>
        </div>
    </div>
    
    <div class="timer-banner" id="timerBanner">
        ⏱️ Temps de crochet estimé : Calcul en cours...
    </div>

    <div class="blueprint-container">
        <h3>📍 Plan d'Assemblage & Épinglage 3D</h3>
        <ul id="blueprintList">
            <li>Calcul des repères en cours...</li>
        </ul>
    </div>

    <div class="viewer-container">
        <div class="viewer-title">🌐 Visualiseur 3D Tactile (Glissez avec un doigt pour pivoter, pincez pour zoomer)</div>
        <div id="webgl-container"></div>
    </div>

    <div class="color-widget">
        <h3>🎨 Encyclopédie & Testeur RGB</h3>
        <p style="font-size: 13px;">Tapez un nom (ex: <i>rouge</i>) ou RGB (ex: <i>234,172,121</i>) :</p>
        <input type="text" id="colorInput" placeholder="Ex: rouge ou 234,172,121">
        <button class="btn" style="padding: 8px 12px; margin-top: 8px; background: #3498db;" onclick="chercherCouleur()">Rechercher</button>
        <div id="colorResult" style="margin-top: 8px; font-weight: bold; font-size: 14px;"></div>
    </div>

    <div id="contenu-patron"></div>

    <script>
        const verticesData = {vertices_json};
        const facesData = {faces_json};
        const partiesData = {parties_json};

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

        function analyserTapestrySequence(paletteTranche) {{
            if (!paletteTranche || paletteTranche.length === 0) return "Fil continu unicolore - Aucune contrainte Tapestry.";
            let maxConsecutif = 1;
            let courant = 1;
            for (let i = 1; i < paletteTranche.length; i++) {{
                if (paletteTranche[i][0] === paletteTranche[i-1][0]) {{
                    courant++;
                    if (courant > maxConsecutif) maxConsecutif = courant;
                }} else {{
                    courant = 1;
                }}
            }}
            if (maxConsecutif > 5) {{
                return `💡 <b>Conseil Tapestry</b> : Séquence longue (${{maxConsecutif}} ms). Utilisez le <i>fil flottant sur l'envers</i>.`;
            }} else {{
                return `💡 <b>Conseil Tapestry</b> : Alternance rapide. Emprisonnez le fil inactif.`;
            }}
        }}

        function mettreAJourPatron() {{
            try {{
                let hookSize = parseFloat(document.getElementById('hookSize').value);
                let yarnVal = document.getElementById('yarnType').value;
                let secondsPerStitch = parseFloat(document.getElementById('speedLevel').value);
                
                let yarnMultiplier = 1.0;
                let nomLaineTexte = "Coton Sport / DK";
                if(yarnVal === 'lace') {{ yarnMultiplier = 0.8; nomLaineTexte = "Lace / Fingering"; }}
                else if(yarnVal === 'sport') {{ yarnMultiplier = 1.0; nomLaineTexte = "Coton Sport / DK"; }}
                else if(yarnVal === 'worsted') {{ yarnMultiplier = 1.3; nomLaineTexte = "Aran / Worsted"; }}
                else if(yarnVal === 'bulky') {{ yarnMultiplier = 1.6; nomLaineTexte = "Bulky / Chunky"; }}
                else if(yarnVal === 'velvet') {{ yarnMultiplier = 2.0; nomLaineTexte = "Chenille / Velvet"; }}

                let largeurMaille = (hookSize * 2.2) * (yarnMultiplier * 0.9); 
                let hauteurCouche = (hookSize * 0.6) * yarnMultiplier;

                let htmlFinal = "<h2>🗺️ Guide d'assemblage & Cartographie</h2><hr>";
                let blueprintHTML = "";
                let grandTotalMailles = 0;

                if (!partiesData || partiesData.length === 0) {{
                    document.getElementById('timerBanner').innerHTML = "⚠️ Aucune partie détectée.";
                    return;
                }}

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
                    let tapestryAdvice = analyserTapestrySequence(partie.tranches_couleurs[0]);

                    let nomP = partie.nom.toLowerCase();
                    if(nomP.includes('tete') || nomP.includes('head')) {{
                        blueprintHTML += `<li><b>TÊTE</b> : À fixer sur le sommet du CORPS entre les rangs supérieurs.</li>`;
                    }} else if(nomP.includes('corps') || nomP.includes('body')) {{
                        blueprintHTML += `<li><b>CORPS</b> : Base centrale. Insérer armature et ouate.</li>`;
                    }} else if(nomP.includes('jambe') || nomP.includes('leg')) {{
                        blueprintHTML += `<li><b>JAMBES</b> : À positionner symétriquement de part et d'autre.</li>`;
                    }} else if(nomP.includes('chapeau') || nomP.includes('casquette')) {{
                        blueprintHTML += `<li><b>ACCESSOIRE</b> : À poser et coudre sur le sommet de la TÊTE.</li>`;
                    }} else {{
                        blueprintHTML += `<li><b>${{partie.nom.toUpperCase()}}</b> : À coudre sur la zone latérale.</li>`;
                    }}

                    htmlFinal += `<div class='part-container'>`;
                    htmlFinal += `<h2>🧶 Partie : ${{partie.nom.toUpperCase()}}</h2>`;
                    htmlFinal += `<h3>📋 Spécifications (${{hookSize}}mm | ${{nomLaineTexte}}) :</h3>`;
                    htmlFinal += `<ul>`;
                    htmlFinal += `<li><b>Fil recommandé</b> : 🎨 ${{partie.couleur_partie}}</li>`;
                    htmlFinal += `<li><b>Hauteur estimée</b> : ${{hauteurEstimeeMM.toFixed(1)}} mm (${{(hauteurEstimeeMM/10.0).toFixed(1)}} cm)</li>`;
                    htmlFinal += `<li><b>Fil estimé</b> : ~${{filEstimeMetres.toFixed(1)}}m (~${{pelotes}} pelote(s)) | <b>Ouate</b> : ~${{partie.poids_ouate.toFixed(1)}}g</li>`;
                    if(partie.armature) htmlFinal += `<li><b>Armature</b> : ⚠️ Fil de fer conseillé.</li>`;
                    htmlFinal += `</ul>`;
                    htmlFinal += `<div class='tapestry-tip'>${{tapestryAdvice}}</div>`;
                    htmlFinal += `<div class='jacquard-container'><h4>📊 Grille Visuelle (${{partie.nom.toUpperCase()}})</h4>` + grillesHTML.join('') + `</div>`;
                    htmlFinal += `<h3>🧵 Instructions :</h3><ul>` + instructions.join('') + `</ul>`;
                    htmlFinal += `</div>`;
                }});

                document.getElementById('blueprintList').innerHTML = blueprintHTML;

                let totalSeconds = grandTotalMailles * secondsPerStitch;
                let totalHours = Math.floor(totalSeconds / 3600);
                let totalMinutes = Math.round((totalSeconds % 3600) / 60);
                
                let tempsTexte = totalHours > 0 ? `${{totalHours}}h ${{totalMinutes}}min` : `${{totalMinutes}} minutes`;
                document.getElementById('timerBanner').innerHTML = `⏱️ Temps estimé (~${{grandTotalMailles}} mailles) : <b>${{tempsTexte}} de travail</b>`;

                document.getElementById('contenu-patron').innerHTML = htmlFinal;
            }} catch (err) {{
                console.error("Erreur attrapée dans mettreAJourPatron:", err);
                document.getElementById('timerBanner').innerHTML = "⚠️ Erreur : " + err.message;
            }}
        }}

        function exporterJSON() {{
            let configExport = {{
                hookSize: document.getElementById('hookSize').value,
                yarnType: document.getElementById('yarnType').value,
                speedLevel: document.getElementById('speedLevel').value,
                parties: partiesData
            }};
            let blob = new Blob([JSON.stringify(configExport, null, 2)], {{type: 'application/json'}});
            let url = URL.createObjectURL(blob);
            let a = document.createElement('a');
            a.href = url;
            a.download = 'patron_amigurumi_donnees.json';
            a.click();
        }}

        function exporterCSV() {{
            let csvContent = "Partie,Couleur_Principale,Hauteur_cm,Fil_Estime_m,Ouate_g,Armature_Conseillee\\n";
            let hookSize = parseFloat(document.getElementById('hookSize').value);
            let yarnVal = document.getElementById('yarnType').value;
            let yarnMultiplier = yarnVal === 'lace' ? 0.8 : (yarnVal === 'sport' ? 1.0 : (yarnVal === 'worsted' ? 1.3 : (yarnVal === 'bulky' ? 1.6 : 2.0)));
            let hauteurCouche = (hookSize * 0.6) * yarnMultiplier;

            partiesData.forEach(p => {{
                let nbRangs = Math.max(4, Math.round(p.hauteur_totale / hauteurCouche));
                let diametreMoyenMM = (p.z_max - p.z_min) * 0.8;
                if(diametreMoyenMM < 10) diametreMoyenMM = 20;
                let largeurMaille = (hookSize * 2.2) * (yarnMultiplier * 0.9);
                let totalMaillesPartie = 0;
                for(let i = 0; i < nbRangs; i++) {{
                    let facteurForme = Math.sin((i / nbRangs) * Math.PI);
                    if(facteurForme < 0.2) facteurForme = 0.2;
                    totalMaillesPartie += Math.max(4, Math.round((diametreMoyenMM * facteurForme * Math.PI) / largeurMaille));
                }}
                let hauteurEstimeeMM = nbRangs * hauteurCouche;
                let filMetres = (totalMaillesPartie * (hookSize * 4.5 * yarnMultiplier)) / 1000.0;
                csvContent += `"${{p.nom}}","${{p.couleur_partie}}",${{(hauteurEstimeeMM/10.0).toFixed(1)}},${{filMetres.toFixed(1)}},${{p.poids_ouate.toFixed(1)}},${{p.armature ? "Oui" : "Non"}}\\n`;
            }});

            let blob = new Blob([csvContent], {{type: 'text/csv;charset=utf-8;'}});
            let url = URL.createObjectURL(blob);
            let a = document.createElement('a');
            a.href = url;
            a.download = 'recapitulatif_fournitures_amigurumi.csv';
            a.click();
        }}

        function init3DViewer() {{
            if (typeof THREE === 'undefined') {{
                throw new Error("Three.js non chargé");
            }}
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
            controls.enableZoom = true;

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
            if(!val) {{ resDiv.innerHTML = "Entrez un nom ou RGB."; return; }}
            if(val.includes(',')) {{
                let rgb = val.split(',').map(Number);
                if(rgb.length === 3 && !rgb.some(isNaN)) {{
                    let hex = `rgb(${{rgb[0]}},${{rgb[1]}},${{rgb[2]}})`;
                    resDiv.innerHTML = `<span style="display:inline-block; width:16px; height:16px; background:${{hex}}; vertical-align:middle; border:1px solid #000; border-radius:3px; margin-right:6px;"></span> RGB(${{rgb.join(',')}})`;
                    return;
                }}
            }}
            let f = encyclopedie.find(c => c.nom.includes(val));
            if(f) {{
                resDiv.innerHTML = `<span style="display:inline-block; width:16px; height:16px; background:${{f.hex}}; vertical-align:middle; border:1px solid #000; border-radius:3px; margin-right:6px;"></span> ${{f.nom.toUpperCase()}} - RGB(${{f.rgb.join(',')}})`;
            }} else {{
                resDiv.innerHTML = "Couleur introuvable.";
            }}
        }}

        window.onload = function() {{
            mettreAJourPatron();
            try {{
                init3DViewer();
            }} catch (e) {{
                console.warn("Visualiseur 3D indisponible :", e);
                document.getElementById('webgl-container').innerHTML = "<p style='color:#aaa; padding-top:110px; font-size:13px;'>Aperçu 3D non disponible hors-ligne.</p>";
            }}
        }};
    </script>
</body>
</html>
"""
    with open("patron_global_ultime.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("[Succès] Application PWA mobile/tablette (avec manifest.json & responsive tactile) générée avec succès !")

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
    print(f"\n--- Scanner intelligent & Station PWA Mobile ---")
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

    compiler_master_document(parties_donnees, mesh)

def main():
    nom_fichier = "mario_ia_genere.obj" if os.path.exists("mario_ia_genere.obj") else "mario.stl"
    if os.path.exists(nom_fichier):
        mesh = trimesh.load(nom_fichier)
    else:
        mesh = trimesh.creation.icosphere(subdivisions=3, radius=50.0)
    scanner_details_et_zones(mesh)

if __name__ == "__main__":
    main()
