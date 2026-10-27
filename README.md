# valentino3112.github.io

Sites de révision personnels, statiques (HTML/CSS/JS sans build).

- **`/`** : **CEFI2** — Culture économique et financière de l'ingénieur 2 (Efrei) : fiches, formulaire,
  méthodes, 13 exercices corrigés, quiz, calculateurs. Fonctionne hors ligne (PWA).
- **`/signal/`** : Théorie du signal.

## Activer GitHub Pages

1. Pousser la branche `main` sur GitHub.
2. Sur GitHub : *Settings → Pages → Build and deployment → Source : Deploy from a branch*,
   branche **`main`**, dossier **`/ (root)`**, puis *Save*.
3. Le site est publié en une à deux minutes sur <https://valentino3112.github.io/>.

## Installer sur le téléphone (hors ligne)

Ouvrir le site **une fois avec du réseau** (le service worker télécharge alors tout le site), puis :

- **Android / Chrome** : menu ⋮ → *Ajouter à l'écran d'accueil* (ou *Installer l'application*).
- **iPhone / Safari** : bouton Partager → *Sur l'écran d'accueil*.

Le site fonctionne ensuite sans connexion. Les mises à jour sont récupérées en arrière-plan
et apparaissent au chargement suivant (pour forcer un rechargement complet, changer `VERSION` dans `sw.js`).

## Recalculer les corrigés

Les corrections des exercices sont calculées (et non saisies à la main) par :

```sh
python3 tools/verif.py
```

Le script recalcule les exemples des slides (et signale les coquilles), calcule les 13 exercices,
vérifie les réponses chiffrées du quiz, puis régénère `js/exos-data.js`. Il s'arrête avec un code
d'erreur si une vérification échoue. Les PDF de cours (`cours/`) ne sont pas publiés (`.gitignore`).
