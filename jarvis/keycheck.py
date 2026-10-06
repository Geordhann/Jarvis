"""Diagnostic de la clé Claude : python -m jarvis --tester-cle"""

from __future__ import annotations

from . import config


def _masked(key: str) -> str:
    return f"{key[:10]}…{key[-4:]} ({len(key)} caractères)" if len(key) > 16 else f"({len(key)} caractères)"


def run() -> bool:
    import anthropic

    saved = config.load().get("cle_api") or ""
    env = config.ORIGINAL_ENV_KEY
    print("━━━ Diagnostic de la clé Claude ━━━")
    if saved:
        print(f"Clé enregistrée dans Jarvis : {_masked(saved)}")
    else:
        print("Aucune clé enregistrée dans Jarvis.")
    if env and env != saved:
        print(f"⚠ Une variable Windows ANTHROPIC_API_KEY existe aussi : {_masked(env)}")
        print("  Jarvis utilise quand même la clé enregistrée. Pour supprimer la variable :")
        print('  [Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $null, "User")')
    key = saved or env
    if not key:
        print('\n✘ Pas de clé. Lance : python -m jarvis --cle "sk-ant-…"')
        return False
    if not key.startswith("sk-ant-"):
        print("\n✘ La clé ne commence pas par « sk-ant- » : ce n'est pas une clé Anthropic, ou le collage a raté.")
        return False
    if len(key) < 60:
        print("\n✘ La clé est trop courte : le collage a probablement coupé une partie.")
        return False

    client = anthropic.Anthropic(api_key=key, max_retries=0, timeout=30)
    print("\n1/2 Connexion et clé…", end=" ", flush=True)
    try:
        client.models.list(limit=1)
        print("✔ clé acceptée")
    except anthropic.AuthenticationError:
        print("✘ clé refusée")
        print("   → La clé est fausse, incomplète, supprimée ou expirée. Crée-en une nouvelle sur")
        print('     https://console.anthropic.com/settings/keys puis : python -m jarvis --cle "sk-ant-…"')
        return False
    except anthropic.PermissionDeniedError as exc:
        print(f"✘ accès refusé : {exc.message}")
        return False
    except anthropic.APIConnectionError:
        print("✘ impossible de joindre api.anthropic.com")
        print("   → Vérifie Internet, un VPN, un antivirus ou un pare-feu qui bloquerait Python.")
        return False

    print("2/2 Crédit et modèle…", end=" ", flush=True)
    try:
        client.messages.create(model="claude-haiku-4-5", max_tokens=5,
                               messages=[{"role": "user", "content": "Réponds juste OK."}])
        print("✔ Claude répond (coût du test : moins d'un centième de centime)")
    except anthropic.BadRequestError as exc:
        print("✘ requête refusée")
        if "credit" in str(exc).lower() or "billing" in str(exc).lower():
            print("   → Plus de crédit : ajoute du crédit sur https://console.anthropic.com/settings/billing")
        else:
            print(f"   → {exc.message}")
        return False
    except anthropic.RateLimitError:
        print("✘ limite atteinte : attends une minute, ou vérifie les limites de ton compte dans la console.")
        return False
    except anthropic.APIStatusError as exc:
        print(f"✘ erreur {exc.status_code} : {exc.message}")
        return False
    print("\nTout est bon ! Lance : python -m jarvis")
    return True
