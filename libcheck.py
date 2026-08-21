"""Controllo aggiornamenti della libreria della matrice.

Il fork `kingdo9/rpi-rgb-led-matrix_pwm_experiment` e' l'unico software che
pilota i pannelli S-PWM. Non viene versionato con dei tag: si aggiorna a
commit, quindi il confronto e' fra il commit installato in locale e quello
in cima al ramo remoto.

**Questo modulo non aggiorna niente, e la scelta e' voluta.** Aggiornare la
libreria significa ricompilarla e reinstallare i binding Python: dieci minuti
buoni su una Pi Zero 2 W, con il pannello fermo e la possibilita' concreta di
ritrovarsi una taratura che non funziona piu'. Una cosa del genere si fa
guardando il terminale, non premendo un pulsante e sperando. Qui si controlla
soltanto, e si mostrano i comandi da dare.
"""

import json
import os
import subprocess
import time
import urllib.request

USER_AGENT = "zedmd-pi library check"
REPO = "kingdo9/rpi-rgb-led-matrix_pwm_experiment"
BRANCH = "master"

# Percorsi in cui cercare la libreria, se la configurazione non lo dice.
FALLBACK_DIRS = [
    "/home/gillo/rpi-rgb-led-matrix_pwm_experiment",
    os.path.expanduser("~/rpi-rgb-led-matrix_pwm_experiment"),
    "/opt/rpi-rgb-led-matrix_pwm_experiment",
]


def library_dir(cfg):
    """Cartella della libreria: da configurazione, dedotta, o cercata."""
    panel = cfg.get("panel", {})
    explicit = (panel.get("library_dir") or "").strip()
    if explicit:
        return explicit

    # `profile_dir` punta a <libreria>/lib/spwm/registertest/data: da li' si
    # risale alla radice senza chiedere niente all'utente.
    profile = (panel.get("profile_dir") or "").strip()
    marker = os.path.join("lib", "spwm", "registertest", "data")
    if profile.endswith(marker):
        return profile[: -(len(marker) + 1)]

    for path in FALLBACK_DIRS:
        if os.path.isdir(os.path.join(path, ".git")):
            return path
    return FALLBACK_DIRS[0]


def _git(path, *args):
    result = subprocess.run(["git", "-C", path] + list(args),
                            capture_output=True, text=True, timeout=20)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip() or "git ha fallito")
    return result.stdout.strip()


def local_commit(path):
    """Commit installato: sha, data e prima riga del messaggio."""
    if not os.path.isdir(os.path.join(path, ".git")):
        raise RuntimeError("cartella senza repository git: %s" % path)
    sha = _git(path, "rev-parse", "HEAD")
    when = _git(path, "log", "-1", "--format=%cI")
    subject = _git(path, "log", "-1", "--format=%s")
    return {"sha": sha, "date": when, "subject": subject}


def _get_json(url, timeout=15):
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def remote_commit(repo=REPO, branch=BRANCH):
    """Commit in cima al ramo remoto, letto dall'API di GitHub."""
    data = _get_json("https://api.github.com/repos/%s/commits/%s" % (repo, branch))
    commit = data.get("commit") or {}
    author = commit.get("author") or {}
    return {
        "sha": data.get("sha", ""),
        "date": author.get("date", ""),
        "subject": (commit.get("message") or "").splitlines()[0] if commit.get("message") else "",
    }


def short(sha):
    return (sha or "")[:7]


def check(cfg):
    """Confronta locale e remoto. Non solleva: l'esito sta nel risultato."""
    path = library_dir(cfg)
    result = {
        "ok": False,
        "error": "",
        "path": path,
        "repo": REPO,
        "branch": BRANCH,
        "local": {},
        "remote": {},
        "behind": False,
        "checked": time.time(),
    }

    try:
        result["local"] = local_commit(path)
    except Exception as exc:
        result["error"] = str(exc)
        return result

    try:
        result["remote"] = remote_commit()
    except Exception as exc:
        # Il commit locale l'abbiamo comunque: e' un'informazione utile
        # anche senza la controparte remota.
        result["error"] = str(exc)
        return result

    local_sha = result["local"].get("sha", "")
    remote_sha = result["remote"].get("sha", "")
    result["ok"] = bool(local_sha and remote_sha)
    result["behind"] = bool(result["ok"] and local_sha != remote_sha)
    return result


def update_commands(path):
    """I comandi da dare a mano per aggiornare, nell'ordine giusto."""
    return [
        "sudo systemctl stop dmd",
        "cd %s && git pull && make" % path,
        "sudo pip install . --break-system-packages",
        "sudo systemctl start dmd",
    ]
