# Claude Copilot pour DCS World

Copilote vocal : tu **parles**, Claude lit ta télémétrie DCS et te **répond à
l'oral**. Étape actuelle = **lecture seule** (position, altitude, cap, vitesse).
Le spawn d'unités et l'aide au pilotage viendront ensuite.

```
Push-to-talk → faster-whisper (STT fr) → Claude API (outil get_telemetry) → SAPI (voix)
                                              ▲
        DCS Export.lua ──UDP 5010──► écouteur Python (dernier état de vol)
```

## Contenu du dossier (tout est portable, aucune install système)

| Élément | Rôle |
|---------|------|
| `python\` | Python 3.11 embarqué (runtime) |
| `libs\` | dépendances Python (folder séparé) |
| `models\` | modèle Whisper `small` (déjà téléchargé, marche hors-ligne) |
| `app.py` | **programme unique** : interface web + copilote ensemble |
| `core.py` | état partagé (config en mémoire, réglages à la volée) |
| `copilot.py` / `configurator.py` | boucle du copilote / interface web |
| `tts.py` `ptt.py` `audioio.py` `srs.py` `dcs_grpc_client.py` | modules |
| `piper\` | voix neuronales Piper (fr) + binaire |
| `dcs_claude_export.lua` | exporteur de télémétrie à déposer dans DCS (inclus via `dofile`) |
| `dcs_claude_control.lua` | hook de commande (afficher/spawn) → `Scripts\Hooks\` |
| `run.bat` | **lance tout** (interface + copilote) |
| `config.json` | réglages (modifiables à la volée depuis l'interface) |
| `apikey.txt` | *(à créer)* ta clé API Anthropic, une ligne |

---

## Mise en place — 3 étapes

### 1) Installer l'exporteur dans DCS (une seule ligne à ajouter)

**a.** Copie `dcs_claude_export.lua` de ce dossier vers :
```
%USERPROFILE%\Saved Games\DCS\Scripts\dcs_claude_export.lua
```
> Selon ta version, le dossier peut être `Saved Games\DCS.openbeta\Scripts\`.
> Si le sous-dossier `Scripts` n'existe pas, crée-le.

**b.** Ouvre (ou crée) ton `Export.lua` dans ce même dossier `Scripts\` et
ajoute **à la toute fin** cette **unique ligne** :
```lua
dofile(lfs.writedir()..[[Scripts\dcs_claude_export.lua]])
```

C'est tout — pas de gros bloc à coller. La ligne doit être **à la fin** pour que
le script chaîne proprement les callbacks des autres outils (SRS, Tacview,
SimShaker…) sans les casser.

> `lfs.writedir()` = ton dossier `Saved Games\DCS\`, donc la ligne marche quel
> que soit ton chemin exact. Aucune modification de `MissionScripting.lua`
> n'est nécessaire : l'environnement d'export a déjà accès au réseau.

### 2) Préparer la mission

Bonne nouvelle : pour la **télémétrie (lecture seule), aucune modification de
mission n'est requise.** `Export.lua` lit directement l'appareil que tu pilotes.
Il te suffit d'être **aux commandes d'un avion, en vol** (pas dans l'écran de
briefing ni en spectateur).

> Les modifications de mission ne deviendront nécessaires qu'aux étapes
> suivantes :
> - **menaces / trafic** : ajout d'un script déclencheur dans la mission ;
> - **spawn escorte / ennemis** : ajout de groupes en *late activation* servant
>   de gabarits + chargement de MOOSE.
> On s'en occupera le moment venu.

### 3) Premier démarrage, clé API et réinitialisation

- **Lance `run.bat`.** Au **tout premier démarrage**, il **installe automatiquement
  les librairies Python** dans `libs\` (quelques minutes, connexion requise) — le
  dossier livré est donc léger, `libs\` n'est pas fourni.
- **Clé API** : saisis-la dans l'interface (carte **« Cerveau (IA) »**). Elle est
  stockée dans `apikey.txt` (ou `openai_key.txt`) et affichée masquée. Tant qu'aucune
  clé n'est fournie, le copilote **attend** (l'interface, elle, s'ouvre).
- **`reset.bat`** : remet à zéro — supprime la clé API, la config, les voix Piper
  téléchargées, les librairies (`libs\`) et les modèles Whisper (`models\`). Tout
  se réinstalle/re-télécharge au besoin. Pratique pour **alléger le dossier avant
  de le copier/partager**.

---

## Configuration (interface web) — intégrée, en direct

**`run.bat` lance l'interface ET le copilote en même temps.** La page s'ouvre
seule dans ton navigateur (`http://127.0.0.1:5001`). **Tout changement s'applique
à la volée** — pas besoin de redémarrer. Tu peux y :

1. **Push-to-talk** — clique « Capturer », puis appuie sur la touche clavier **ou**
   le bouton **HOTAS/joystick** voulu. La **LED** s'allume quand le PTT est enfoncé
   (test intégré). *(Tout périphérique DirectInput est détecté, pas que le clavier.)*
2. **Micro** — choisis-le dans la liste (elle ne montre que les micros **actifs**,
   comme Windows ; mémorisé par nom). Bouton **« Tester le micro »** : parle 4 s,
   tu vois le niveau d'entrée et la transcription.
3. **Choisir la langue parlée** (règle la reconnaissance ET la langue des réponses
   de Claude) et le **modèle** (`base`/`small`/`medium`) — tout en local sur le CPU.
   Whisper est **multilingue** : un seul modèle gère toutes les langues (rien à
   télécharger par langue pour la reconnaissance). Pense juste à prendre une **voix
   Piper de la même langue** (le catalogue se cale automatiquement dessus).
4. **Choisir la sortie voix (TTS)** :
   - **Moteur** : Piper (voix neuronale locale) ou SAPI.
   - **Voix Piper** : menu déroulant des voix installées (siwis féminine,
     tom masculine fournies).
   - **Télécharger une voix** : choisis une **Langue** puis une **Voix** (catalogue
     complet Piper — 54 langues, 170+ voix, comme le site piper-samples), clique
     **⬇️ Télécharger** — l'app la récupère (~30-60 Mo) et elle devient
     sélectionnable aussitôt (✓ = déjà installée).
   - **Périphérique de sortie** : en VR, sélectionne ton **casque** (ex. « Oculus
     Virtual Audio Device ») puis « Tester la voix ».
5. **Affichage / actions en jeu** — bouton **« Tester »** : envoie un message à
   l'écran DCS (nécessite le hook `dcs_claude_control.lua` et une mission en cours).

Le bouton **« Enregistrer »** persiste dans `config.json` (l'appli est déjà à jour).

> Astuce : pour capturer un bouton HOTAS, tu peux le faire **hors DCS**
> (DCS et l'outil peuvent lire la manette en même temps, mais c'est plus simple
> à configurer sans le jeu au premier plan).

## Voix à la radio en jeu (DCS-SRS) — optionnel, immersif

Pour entendre Claude **sur la radio du cockpit** (au lieu du casque en direct) :

### Installer DCS-SRS
1. Télécharge **DCS-SimpleRadio-Standalone** : https://github.com/ciribob/DCS-SimpleRadio-Standalone/releases
2. Installe-le (coche l'intégration DCS quand l'installeur le propose).
3. Pour le **solo**, lance le serveur local **`SR-Server.exe`** (dans le dossier
   d'install SRS). En multi, le serveur est celui de la mission.
4. Lance le **client SRS** (`SR-ClientRadio.exe`) et connecte-le (IP `127.0.0.1`
   en solo). En vol, règle une radio de l'appareil sur la **fréquence** choisie.

### Configurer dans l'interface
Dans l'interface → carte **« Radio en jeu (DCS-SRS) »** :
- coche **Radio SRS**,
- renseigne le chemin de **`DCS-SRS-ExternalAudio.exe`** (dans le dossier d'install
  SRS, souvent `C:\Program Files\DCS-SimpleRadio-Standalone\`),
- règle **fréquence** (MHz), **modulation** (AM/FM) et **coalition**,
- clique **« Tester la radio SRS »** (serveur + client SRS doivent tourner).

En jeu, tune ta radio sur la fréquence → tu entends Claude sur la radio. Si SRS
échoue au moment de parler, le copilote **repli automatiquement sur le casque**.

## Afficher / agir dans le jeu — optionnel

Un **canal de commande vers DCS** permet d'**afficher les réponses de Claude à
l'écran** (bandeau in-game) et, plus tard, de **spawner escortes/ennemis**. Deux
backends au choix dans l'interface (carte **« Affichage / actions en jeu »**) :

### Option A — Hook Lua (recommandé, sans mod, sans modif) ★
1. Copie **`dcs_claude_control.lua`** de ce dossier vers :
   ```
   %USERPROFILE%\Saved Games\DCS\Scripts\Hooks\dcs_claude_control.lua
   ```
   (crée le sous-dossier `Hooks` s'il n'existe pas)
2. Dans l'interface, **Canal = Hook Lua**, coche **Afficher les réponses**,
   lance une mission, puis **Tester** → un message apparaît à l'écran DCS.

Aucune DLL, aucune modification de `MissionScripting.lua`. Le hook ouvre un
socket loopback (127.0.0.1:5011) et exécute les commandes dans la mission via
`net.dostring_in`. Il se charge automatiquement pour toutes tes missions.

### Option B — DCS-gRPC (mod)
1. Télécharge `DCS-GRPC-0.8.1.zip` : https://github.com/DCS-gRPC/rust-server/releases
2. Extrais-le dans `%USERPROFILE%\Saved Games\DCS\` (voir wiki officiel).
   Serveur sur **127.0.0.1:50051** au lancement d'une mission.
3. Dans l'interface, **Canal = DCS-gRPC**, puis **Tester**.
   (Client Python + stubs 0.8.1 déjà inclus.)

Une fois activé, les réponses de Claude s'affichent en jeu **en plus** de la voix.

## Personas (multi-rôles)

Plusieurs opérateurs simultanés, chacun avec son **indicatif**, sa **fréquence**,
sa **langue**, sa **voix** et son **rôle**. Tu les configures dans la carte
**« Personas »** de l'interface (ajouter/supprimer, régler chaque champ, choisir
le persona « Défaut »).

Tu t'adresses à un persona **par son indicatif** au début de ta phrase :
- « **Magic**, fais apparaître deux MiG au nord. » (rôle *opérateur* : spawn, encadrement, procédures)
- « **Overlord**, picture. » (rôle *AWACS* : situation tactique)
- « **Two**, engage le bandit. » (rôle *ailier*)

Sans indicatif, la demande va au persona **Défaut**. Chaque persona répond dans
**sa** langue avec **sa** voix.

**Trois façons d'adresser un persona** (priorité PTT > fréquence > indicatif > défaut) :
- **Indicatif parlé** — « Overlord, picture ».
- **Bouton PTT dédié** — règle *Mode PTT = « Un PTT par persona »*, puis capture un
  bouton par persona (colonne « PTT dédié » 🎯). Appuyer sur ce bouton parle à ce persona.
- **Fréquence radio (F/A-18C)** — chaque persona a une fréquence ; si tu es réglé
  dessus (COMM1/COMM2), c'est lui qui répond. Coche *« Fréquence obligatoire »* pour
  n'autoriser QUE l'adressage par fréquence (indicatif/défaut désactivés).

> Personas par défaut : Magic (opérateur, 305.0), Overlord (AWACS, 251.0),
> IceMan (ailier, 133.0). La lecture de fréquence ne gère que le **F/A-18C** pour l'instant.

## Cerveau (IA) — Claude, OpenAI ou Ollama

Le « cerveau » qui décide des réponses et des actions est **interchangeable**
(carte **« Cerveau (IA) »** de l'interface) :
- **Anthropic (Claude)** — défaut, clé `ANTHROPIC_API_KEY`.
- **OpenAI** — clé `OPENAI_API_KEY` ; modèle ex. `gpt-4o-mini`.
- **Ollama (local, 100 % hors-ligne)** — `llm_base_url` = `http://localhost:11434/v1`,
  modèle ex. `llama3.1` (charge le GPU — attention en VR).

**Clé API** : saisis-la directement dans la carte (champ **Clé API**). Elle est
stockée localement (`apikey.txt` pour Anthropic, `openai_key.txt` pour OpenAI) et
n'est **affichée que masquée** (`sk-…1234`). **Au tout premier démarrage sans clé,
le copilote attend** que tu en renseignes une dans l'interface avant de démarrer
(l'interface, elle, s'ouvre tout de suite). Ollama ne demande aucune clé.

Le seul prérequis : le modèle doit gérer le **tool calling** (spawn, télémétrie…).
La reconnaissance (Whisper) et la voix (Piper/SAPI) restent locales et
indépendantes du fournisseur. *(Ceci utilise l'API du fournisseur, rien à voir avec
« Claude Code ».)*

## Utilisation

1. Lance **DCS** et démarre une mission ; prends les commandes d'un avion, **en vol**.
2. Double-clique **`run.bat`**.
   - Au 1er lancement, le chargement du modèle prend quelques secondes.
3. **Maintiens ton bouton push-to-talk** (celui choisi dans l'interface, `Ctrl droit`
   par défaut), pose ta question, **relâche**.

Exemples :
- « Donne-moi mon altitude et mon cap. »
- « Je suis à quelle vitesse ? »
- « Fais-moi un point situation. »
- « Envoie-moi une escorte de deux F-16 sur ma gauche. »
- « Fais apparaître deux MiG-29 à 20 nautiques au nord. »

> **Spawn** (nécessite le canal « Hook Lua » actif) : Claude fait apparaître des
> **avions, unités au sol et navires** (ami = ton camp / ennemi = camp opposé).
> Missions avion : cap, tanker (contactable radio), awacs. « Fais tirer mes alliés »
> = `order_engage`.
>
> **Paquets tactiques (prefabs)** : « pose un **site SA-10** », « une **colonne
> blindée** », « une **CAP de 4** », « un **groupe naval** » (variante amie/ennemie auto).
> **Marquage** : « marque la cible au **fumigène** », « trace un **cercle** » (carte F10).
> **Statiques** : dépôt carburant, entrepôt, FARP, tour comms, bunker…
>
> **Positionnement** : dis où — « devant moi / à mon 3 heures » (relatif), « au sud
> de \<ville\> », « près de \<aérodrome\> », « au bullseye », « à mon repère F10 »
> (pose un marqueur sur la carte F10), ou des coordonnées lat/long. Les unités sont
> **accrochées au terrain** (sol → terre, navires → eau) — plus de char dans l'eau.
> Base de villes intégrée (théâtres DCS) ; sinon, un repère F10 marche toujours.

Claude répond à voix haute (voix française SAPI si disponible).

---

## Réglages (`config.json`, généré par l'interface)

Le push-to-talk et le micro se règlent dans l'interface. Les
réglages avancés vivent aussi dans `config.json` (modifiable à la main) :

| Clé | Rôle |
|-----|------|
| `ptt` | binding push-to-talk (clavier ou joystick) — via l'interface |
| `mic_device` | index du micro — via l'interface |
| `whisper_model` | `small` (déf.), `medium`/`large-v3` = mieux mais + lourd |
| `whisper_device` / `whisper_compute` | `cpu`/`int8` (déf., marche partout) — passe à `cuda`/`float16` si GPU NVIDIA + cuDNN |
| `claude_model` | `claude-sonnet-4-6` (déf.), `claude-haiku-4-5-20251001` (+ rapide), `claude-opus-4-8` (+ malin) |
| `tts_voice_hint` | sous-chaîne du nom de voix SAPI à préférer (déf. `french`) |

---

## Dépannage

- **« Aucune donnée DCS reçue »** → tu n'es pas en vol, ou `Export.lua` n'est pas
  au bon endroit. Vérifie le chemin `Saved Games\DCS\Scripts\`.
- **Le push-to-talk ne réagit pas** → la capture clavier globale peut exiger les
  droits admin : clic droit sur `run.bat` → *Exécuter en tant qu'administrateur*.
- **Pas de son / mauvaise voix** → change `TTS_VOICE_HINT`, ou installe une voix
  française dans *Paramètres Windows → Heure et langue → Voix*.
- **Micro non capté** → vérifie le périphérique d'entrée par défaut de Windows.

---

## Feuille de route

1. ✅ **Télémétrie own-ship** (position/alt/cap/vitesse) — *actuel*.
2. ⬜ **Menaces / trafic** — scripting de mission (radar, `getDetectedTargets`).
3. ⬜ **Spawn escorte / ennemis** — MOOSE + gabarits late-activation + socket bidirectionnel.
4. ⬜ **Aide au pilotage** — DCS-BIOS (lecture/écriture cockpit).
