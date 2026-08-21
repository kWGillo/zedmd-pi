"""Aggiornamento via rete dal repository GitHub.

Il controllo legge `version.py` dal ramo indicato e lo confronta con la
versione installata. L'installazione scarica l'archivio del ramo, lo verifica
e solo allora sostituisce i file.

La sicurezza sta tutta nell'ordine delle operazioni:

  1. scarica in una cartella temporanea
  2. verifica che ci siano i file attesi e che tutto il Python compili
  3. salva una copia dell'installazione corrente
  4. sostituisce i file e riavvia il servizio
  5. interroga la web UI per capire se il servizio e' davvero ripartito
  6. se non risponde, ripristina la copia e riavvia di nuovo

Il passo 6 e' il motivo per cui l'installazione gira in un processo separato
e staccato: deve sopravvivere al riavvio del servizio che la ha avviata.
"""

import io
import json
import os
import py_compile
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request

INSTALL_DIR = "/opt/dmd"
BACKUP_DIR = "/var/lib/dmd/backup"
LOG_PATH = "/var/lib/dmd/ota.log"
USER_AGENT = "zedmd-pi OTA"

# File e cartelle che compongono l'installazione.
PAYLOAD_FILES = ["dmdd.py", "dmdconf.py", "display.py", "webui.py", "ota.py",
                 "zedmd_http.py", "i18n.py", "libcheck.py", "version.py", "config.json",
                 "dmd.service", "install.sh", "update.sh", "setup_share.sh",
                 "verify.sh", "manifest.md5", "manifest-install.md5"]
PAYLOAD_DIRS = ["sources", "templates", "static"]

# Presenza minima perche' un archivio sia considerato valido.
REQUIRED = ["dmdd.py", "version.py", "webui.py", "i18n.py", "libcheck.py",
            "sources", "templates"]


def log(message):
    line = "%s  %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), message)
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def tail_log(lines=25):
    try:
        with open(LOG_PATH) as handle:
            return "".join(handle.readlines()[-lines:])
    except OSError:
        return ""


def _get(url, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def parse_version(text):
    """Estrae __version__ senza eseguire il file scaricato."""
    for line in text.splitlines():
        if line.strip().startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"\'')
    return ""


def version_tuple(value):
    parts = []
    for chunk in str(value).split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer(remote, local):
    return version_tuple(remote) > version_tuple(local)


def check(cfg):
    """Confronta la versione remota con quella installata."""
    from version import __version__ as current
    ota = cfg["ota"]
    url = "https://raw.githubusercontent.com/%s/%s/version.py" % (ota["repo"], ota["branch"])
    try:
        remote = parse_version(_get(url, timeout=15).decode("utf-8", "replace"))
    except Exception as exc:
        return {"ok": False, "error": str(exc), "current": current,
                "latest": "", "available": False, "checked": time.time()}
    if not remote:
        return {"ok": False, "error": "version.py remoto illeggibile", "current": current,
                "latest": "", "available": False, "checked": time.time()}
    return {"ok": True, "error": "", "current": current, "latest": remote,
            "available": is_newer(remote, current), "checked": time.time()}


def start_update(cfg):
    """Avvia l'installazione in un processo staccato, che sopravvive al riavvio."""
    ota = cfg["ota"]
    args = [sys.executable, os.path.join(INSTALL_DIR, "ota.py"), "--apply",
            "--repo", ota["repo"], "--branch", ota["branch"],
            "--port", str(cfg["web"]["port"])]
    subprocess.Popen(args, start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------------------------------------------------------------- installazione


def download_source(repo, branch, workdir):
    """Scarica ed estrae l'archivio del ramo. Restituisce la cartella radice."""
    url = "https://codeload.github.com/%s/tar.gz/refs/heads/%s" % (repo, branch)
    log("scarico %s" % url)
    blob = _get(url, timeout=120)
    log("archivio ricevuto: %d kB" % (len(blob) // 1024))

    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
        for member in archive.getmembers():
            # Nessun percorso assoluto o risalita fuori dalla cartella di lavoro.
            if member.name.startswith("/") or ".." in member.name.split("/"):
                raise RuntimeError("archivio sospetto: %s" % member.name)
        archive.extractall(workdir)

    entries = [os.path.join(workdir, e) for e in os.listdir(workdir)]
    roots = [e for e in entries if os.path.isdir(e)]
    if len(roots) != 1:
        raise RuntimeError("struttura dell'archivio inattesa")
    return roots[0]


def verify(source):
    """L'archivio deve contenere i file attesi e compilare senza errori."""
    for name in REQUIRED:
        if not os.path.exists(os.path.join(source, name)):
            raise RuntimeError("manca %s" % name)

    remote = parse_version(open(os.path.join(source, "version.py")).read())
    if not remote:
        raise RuntimeError("version.py senza numero di versione")

    count = 0
    for base, dirs, files in os.walk(source):
        dirs[:] = [d for d in dirs if d not in (".git", "docs", "__pycache__")]
        for name in files:
            if name.endswith(".py"):
                py_compile.compile(os.path.join(base, name), doraise=True)
                count += 1

    check_manifest(source)
    log("verifica superata: %d file Python compilano, versione %s" % (count, remote))
    return remote


def check_manifest(source):
    """Confronta i file con le impronte, se l'archivio le porta con se'.

    La compilazione non basta: un template o un foglio di stile corrotto passa
    inosservato perche' non e' codice Python.
    """
    manifest = os.path.join(source, "manifest-install.md5")
    if not os.path.exists(manifest):
        return  # archivio precedente alla 1.7.2: nulla da confrontare

    import hashlib
    bad = []
    with open(manifest) as handle:
        for line in handle:
            parts = line.split()
            if len(parts) != 2:
                continue
            expected, name = parts
            path = os.path.join(source, name)
            if not os.path.exists(path):
                bad.append("%s mancante" % name)
                continue
            digest = hashlib.md5(open(path, "rb").read()).hexdigest()
            if digest != expected:
                bad.append("%s alterato" % name)
    if bad:
        raise RuntimeError("archivio non integro: %s" % ", ".join(bad[:5]))
    log("impronte verificate: nessun file alterato")


def backup():
    if os.path.exists(BACKUP_DIR):
        shutil.rmtree(BACKUP_DIR, ignore_errors=True)
    os.makedirs(os.path.dirname(BACKUP_DIR), exist_ok=True)
    shutil.copytree(INSTALL_DIR, BACKUP_DIR)
    log("copia di sicurezza in %s" % BACKUP_DIR)


def install_files(source, destination=None):
    # Risolta alla chiamata, non all'importazione: la cartella puo' cambiare.
    destination = destination or INSTALL_DIR
    os.makedirs(destination, exist_ok=True)
    for name in PAYLOAD_FILES:
        src = os.path.join(source, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(destination, name))
    for name in PAYLOAD_DIRS:
        src = os.path.join(source, name)
        if not os.path.isdir(src):
            continue
        dst = os.path.join(destination, name)
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def restore():
    if not os.path.isdir(BACKUP_DIR):
        log("nessuna copia di sicurezza disponibile")
        return False
    install_files(BACKUP_DIR)
    log("versione precedente ripristinata")
    return True


def service(action):
    subprocess.run(["systemctl", action, "dmd"], capture_output=True, timeout=60)


def healthy(port, attempts=20, delay=2.0):
    """Il servizio e' vivo se la web UI risponde con uno stato coerente."""
    url = "http://127.0.0.1:%d/api/status" % port
    for _ in range(attempts):
        time.sleep(delay)
        try:
            data = json.loads(_get(url, timeout=5).decode("utf-8", "replace"))
            if data.get("version"):
                return data["version"]
        except Exception:
            continue
    return ""


def apply_update(repo, branch, port):
    log("=== aggiornamento da %s ramo %s ===" % (repo, branch))
    workdir = tempfile.mkdtemp(prefix="dmd-ota-")
    try:
        source = download_source(repo, branch, workdir)
        remote = verify(source)

        backup()
        install_files(source)
        log("file installati, riavvio del servizio")
        service("restart")

        running = healthy(port)
        if running:
            log("aggiornamento riuscito: in esecuzione la versione %s" % running)
            return 0

        log("il servizio non risponde dopo l'aggiornamento: ripristino")
        if restore():
            service("restart")
            back = healthy(port)
            log("ripristino %s" % ("riuscito, versione %s" % back if back
                                   else "eseguito ma il servizio non risponde"))
        return 1
    except Exception as exc:
        log("aggiornamento fallito: %s" % exc)
        return 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main(argv):
    if "--apply" not in argv:
        print("uso: ota.py --apply --repo utente/progetto [--branch main] [--port 8080]")
        return 2

    def option(name, default):
        return argv[argv.index(name) + 1] if name in argv else default

    return apply_update(option("--repo", ""), option("--branch", "main"),
                        int(option("--port", "8080")))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
