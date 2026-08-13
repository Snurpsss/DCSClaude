# 📖 Guide détaillé — Claude Copilot for DCS

Documentation complète (installation, interface, capacités, dépannage).
Pour la présentation, voir le [README](README.md).

## Sommaire
1. [Installation](#1-installation)
2. [Premier démarrage & clé API](#2-premier-démarrage--clé-api)
3. [Interface de configuration](#3-interface-de-configuration)
4. [Personas & adressage](#4-personas--adressage)
5. [Voix (TTS)](#5-voix-tts)
6. [Cerveau (IA) — fournisseurs](#6-cerveau-ia--fournisseurs)
7. [Actions en jeu — référence](#7-actions-en-jeu--référence)
8. [Positionnement des unités](#8-positionnement-des-unités)
9. [Réinitialisation & partage](#9-réinitialisation--partage)
10. [Dépannage](#10-dépannage)
11. [Architecture & fichiers](#11-architecture--fichiers)

---

## 1. Installation

### Côté DCS (une fois)

**a. Télémétrie (position, altitude, cap…)** — copie `dcs_claude_export.lua` dans :
```
%USERPROFILE%\Saved Games\DCS\Scripts\dcs_claude_export.lua
```
Puis ajoute **à la toute fin** de ton `Export.lua` (même dossier `Scripts\`, crée-le s'il n'existe pas) :
```lua
dofile(lfs.writedir()..[[Scripts\dcs_claude_export.lua]])
```
> ⚠️ Si tu as déjà un `Export.lua` (SRS, Tacview…), **n'écrase pas** : ajoute juste la ligne à la fin.
> Le script chaîne proprement les callbacks des autres outils. `lfs.writedir()` = ton `Saved Games\DCS\`.

**b. Actions en jeu (spawn, marquage, affichage…)** — copie `dcs_claude_control.lua` dans :
```
%USERPROFILE%\Saved Games\DCS\Scripts\Hooks\dcs_claude_control.lua
```
> Aucun mod, **aucune modification de `MissionScripting.lua`**. Le hook ouvre un socket local
> (127.0.0.1:5011) et exécute les commandes dans la mission via `net.dostring_in` + `a_do_script`.

### Côté PC
Rien à installer manuellement : **`run.bat`** télécharge automatiquement au premier démarrage le
Python embarqué, les librairies et Piper (voir §2).

---

## 2. Premier démarrage & clé API

Double-clique **`run.bat`**.

- **1er lancement** : téléchargement + installation automatiques (Python, librairies, Piper + une
  voix). Compte quelques minutes et une connexion internet. Les lancements suivants sont immédiats.
- L'**interface web** s'ouvre seule (`http://127.0.0.1:5001`) **et** le copilote démarre.
- **Clé API** : dans la carte **« Cerveau (IA) »**, colle ta clé. Elle est stockée localement
  (`apikey.txt` pour Anthropic, `openai_key.txt` pour OpenAI) et **affichée masquée** (`sk-…1234`).
  Tant qu'aucune clé n'est fournie, le copilote **attend** (l'interface reste utilisable). *Ollama :
  aucune clé.*
- En vol, prends les commandes d'un avion, **maintiens le push-to-talk** et parle.

---

## 3. Interface de configuration

`run.bat` lance l'interface **et** le copilote ; **tout changement s'applique à la volée** (pas de
redémarrage). Les cartes :

| Carte | Réglages |
|---|---|
| **Personas** | Ajouter/supprimer, indicatif, fréquence, langue, voix, rôle, persona « Défaut », **PTT dédié**, mode PTT (global/par persona), « fréquence obligatoire ». Bouton **« Tester un indicatif »**. |
| **Push-to-talk** | Capture d'une touche **ou** d'un bouton HOTAS/joystick. **LED** de test intégrée. |
| **Microphone** | Liste des micros **actifs** (comme Windows). Bouton **« Tester le micro »** (niveau + transcription). |
| **Reconnaissance vocale** | **Langue parlée** (règle la STT et la langue des réponses) + **modèle** Whisper (`base`/`small`/`medium`/`large-v3`). Multilingue : un seul modèle gère toutes les langues. |
| **Sortie voix (TTS)** | Moteur **Piper**/SAPI, **voix Piper**, **téléchargement de voix** (catalogue Langue → Voix, 54 langues), **périphérique de sortie** (ton casque), bouton **« Tester la voix »**. |
| **Radio en jeu (DCS-SRS)** | Optionnel : entendre le copilote **sur une fréquence** via `DCS-SRS-ExternalAudio.exe`. |
| **Affichage / actions en jeu** | Bouton **« Tester »** (envoie un message à l'écran DCS). Requiert le hook + une mission. |
| **Cerveau (IA)** | Fournisseur (Claude/OpenAI/Ollama), modèle, URL API, **clé API**. |

---

## 4. Personas & adressage

Plusieurs opérateurs cohabitent, chacun avec **indicatif, fréquence, langue, voix, rôle**. Par défaut :
**Magic** (opérateur, 305.0), **Overlord** (AWACS, 251.0), **IceMan** (ailier, 133.0).

### Rôles
- **Opérateur** — spawn (avion/sol/mer, prefabs, statiques), marquage, ordre de tir, **encadrement
  cockpit**, procédures.
- **AWACS** — situation tactique, marquage de cible.
- **Ailier** — exécute les ordres (à étoffer : tasking avancé).

### Trois façons d'adresser un persona
Priorité **PTT dédié > fréquence > indicatif > persona « Défaut »**.
1. **Indicatif parlé** — « Overlord, picture ». (Tolérant aux variantes de transcription.)
2. **Bouton PTT dédié** — carte Personas → *Mode PTT = « Un PTT par persona »*, puis capture (🎯) un
   bouton HOTAS par persona.
3. **Fréquence radio (F/A-18C)** — règle COMM1/COMM2 sur la fréquence d'un persona ; coche *« Fréquence
   obligatoire »* pour n'autoriser QUE l'adressage par fréquence.

Le pilote parle dans **sa** langue (réglage « Langue parlée ») ; chaque persona **répond** dans **sa**
langue avec **sa** voix, et garde son **historique** propre.

---

## 5. Voix (TTS)

- **Piper** (recommandé) : voix neuronales locales, rapides, multilingues, GPU libre pour la VR.
  Catalogue téléchargeable depuis l'interface (**Langue → Voix**, ~170 voix, 54 langues). Une voix par
  persona pour des timbres distincts.
- **SAPI** (voix Windows) : repli sans dépendance.
- **Sortie** : choisis ton **casque** (ex. « Oculus Virtual Audio Device ») pour l'entendre en VR.
- **Radio en jeu (DCS-SRS)** — optionnel : la voix passe sur une **fréquence radio** en jeu. Installe
  [DCS-SRS](https://github.com/ciribob/DCS-SimpleRadio-Standalone), lance le serveur + client, renseigne
  le chemin de `DCS-SRS-ExternalAudio.exe` dans la carte SRS.

La **phrase de test** est prononcée dans la langue de la voix sélectionnée.

---

## 6. Cerveau (IA) — fournisseurs

Le « cerveau » (décisions + appels d'outils) est **interchangeable** (carte « Cerveau (IA) ») :

| Fournisseur | Clé / URL | Exemple de modèle |
|---|---|---|
| **Anthropic (Claude)** | `ANTHROPIC_API_KEY` | `claude-sonnet-4-6` |
| **OpenAI** | `OPENAI_API_KEY` | `gpt-4o-mini` |
| **Ollama (local)** | URL `http://localhost:11434/v1`, aucune clé | `llama3.1` |

Prérequis : le modèle doit gérer le **tool calling**. Whisper (STT) et Piper (TTS) restent locaux et
indépendants du fournisseur. Changer de fournisseur réinitialise l'historique de conversation.

---

## 7. Actions en jeu — référence

Toutes ces actions passent par le **hook** (mission en cours requise).

| Capacité | Détails |
|---|---|
| **Télémétrie** | État de vol du joueur (via `Export.lua`). |
| **spawn_aircraft** | Avions ; `mission` = cap / cas / **tanker** (contactable radio) / **awacs**. |
| **spawn_ground** | Chars, DCA, SAM, véhicules, infanterie (accrochés à la terre). |
| **spawn_ship** | Navires, porte-avions, ravitailleurs (accrochés à l'eau). |
| **spawn_prefab** | Paquets tactiques : `sam_long` (S-300/SA-10/Patriot), `sam_med` (Buk/Hawk), `sam_short` (Tor/Avenger), `shorad`, `armor`, `convoy`, `infantry`, `cap` (×4), `strike`, `carrier`. Variante amie/ennemie auto. Reconnaît les désignations OTAN/russes. |
| **spawn_static** | Dépôt carburant, entrepôt, hangar, tour comms, bunker, FARP, container, tente. |
| **battlefield_mark** | Fumigène / fusée / cercle sur la carte F10 (couleur au choix). |
| **order_engage** | Toutes les unités **alliées** spawnées ouvrent le feu. |
| **highlight_cockpit_control** | **Encadre** une commande du cockpit (ex. « levier de train ») pour guider une procédure. |
| **Affichage écran** | Les réponses s'affichent aussi en jeu (bandeau). |

`side` = `friendly` (ton camp) ou `enemy` (camp opposé).

---

## 8. Positionnement des unités

Chaque spawn accepte un **point de référence** + un décalage cap/distance, avec **accrochage terrain**
(sol → terre, navire → eau).

| Référence | Exemple vocal |
|---|---|
| **player** (défaut) | « devant moi », « à mon 3 heures » (relatif au nez) |
| **mark** | « à mon repère F10 » (pose un marqueur sur la carte) |
| **bullseye** | « 30 nautiques sud du bullseye » |
| **airbase** | « près de \<aérodrome\> » |
| **city** | « au sud de \<ville\> » (base de villes → lat/long réelles) |
| **coords** | latitude / longitude |

> Le copilote ne **devine** jamais des coordonnées pour un lieu inconnu : il utilise ces références
> ou te demande un repère F10.

---

## 9. Réinitialisation & partage

**`reset.bat`** ramène le dossier à son état minimal : supprime clé API, config, voix Piper,
librairies (`libs\`), Python embarqué (`python\`), Piper (`piper\`) et modèles Whisper (`models\`).
Tout se re-télécharge au prochain `run.bat`.

**Partager un dossier léger** : copie le dossier, lance `reset.bat` dans la copie (ou supprime
`python/ libs/ piper/ models/`), puis zippe. Le destinataire n'a plus qu'à lancer `run.bat`.

---

## 10. Dépannage

| Symptôme | Piste |
|---|---|
| **Le PTT ne réagit pas** | La capture clavier globale peut exiger l'admin : lance `run.bat` en administrateur. Sur HOTAS WINWING, choisis un **bouton momentané** (la LED de test doit s'allumer/s'éteindre). |
| **« Aucune donnée DCS reçue »** | Sois **en vol** (aux commandes d'un avion) et vérifie l'install d'`Export.lua`. |
| **Rien ne se passe en jeu / pas d'affichage / pas de spawn** | Le hook exige une **mission active et non en pause** (`a_do_script` diffère l'exécution en pause). Vérifie `dcs_claude_control.lua` dans `Scripts\Hooks\` et clique « Tester » dans la carte Affichage. |
| **« Il ne peut pas faire X »** | **Relance `run.bat`** après toute mise à jour du code pour que la voix charge les nouveaux outils (le hook DCS, lui, n'a pas besoin d'être rechargé). |
| **Voix inaudible en VR** | Choisis ton **casque** comme sortie voix dans la carte TTS. |
| **Transcription moyenne** | Passe le modèle Whisper à `medium`, et choisis une **voix de ta langue**. |
| **Copilote « en attente »** | Aucune clé API : renseigne-la dans la carte « Cerveau (IA) ». |

---

## 11. Architecture & fichiers

```
run.bat / reset.bat / setup_python.ps1   lanceur / reset / install Python
bootstrap.py                             install libs + Piper au 1er démarrage
app.py                                   point d'entrée (interface + copilote)
core.py                                  état partagé, config à chaud, services
copilot.py                               boucle : PTT → STT → LLM+outils → voix
personas.py                              rôles, prompts, routage d'adressage
llm.py                                   adaptateurs LLM (Anthropic / OpenAI-compatible)
apikeys.py                               gestion des clés (fichier + masquage)
tts.py / audioio.py / ptt.py             voix / audio / push-to-talk
dcs_control.py                           client hook : spawn, marquage, statiques, télémétrie
cities.py / prefabs.py / voices.py       villes, paquets tactiques, catalogue de voix
srs.py                                   sortie radio DCS-SRS
configurator.py                          interface web (Flask)
dcs_claude_export.lua                    export télémétrie (Saved Games\DCS\Scripts\)
dcs_claude_control.lua                   hook d'action (Saved Games\DCS\Scripts\Hooks\)
```

**Chaîne** : voix → **faster-whisper** (STT local) → **LLM** (outils) → **hook Lua** (actions dans la
mission) → réponse → **Piper/SAPI** (voix) / affichage écran. La télémétrie remonte via `Export.lua`
(UDP). Interface web Flask, config partagée en mémoire (`core`), appliquée à la volée.

---

*Projet **Snurpsss & Claude**. Non affilié à Eagle Dynamics.*
