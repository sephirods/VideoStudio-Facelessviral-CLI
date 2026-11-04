#!/usr/bin/env python3
"""
Stock Video API Configuration & Sync Manager
Gestiona las credenciales de APIs de stock (Pixabay y Pexels):
1. Soporta arquitectura multi-proveedor: solo Pixabay, solo Pexels o Ambos (Modo Híbrido).
2. En modo Híbrido, el sistema prioriza Pexels (por resolución 4K) y respalda automáticamente con Pixabay.
3. Muestra instrucciones paso a paso para conseguir claves gratuitas de ambas plataformas.
   (Incluye aviso de que Pexels mantiene pausadas nuevas solicitudes en su web temporalmente).
4. Sincroniza las claves de forma transparente con MoneyPrinterTurbo (config.toml).
5. Almacena las claves localmente en config/stock_credentials.json (protegido en .gitignore).
"""

import json
import os
import re
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STOCK_CREDS_PATH = os.path.join(ROOT_DIR, "config", "stock_credentials.json")

ENGINE_CANDIDATES = [
    os.path.join(ROOT_DIR, "engine", "MoneyPrinterTurbo", "config.toml"),
    r"C:\MoneyPrinterTurbo\config.toml" if sys.platform.startswith("win") else "/opt/MoneyPrinterTurbo/config.toml"
]


def get_engine_config_path() -> str | None:
    for p in ENGINE_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def show_api_instructions():
    print("\n" + "=" * 70)
    print("  GUIA PASO A PASO: COMO OBTENER TUS API KEYS DE STOCK GRATIS")
    print("=" * 70)
    print("\n1. PIXABAY (100% Activa e Instantánea - Recomendada para empezar):")
    print("   • Ve a: https://pixabay.com/api/docs/")
    print("   • Inicia sesión con tu cuenta de Google o regístrate en 10 segundos.")
    print("   • En esa misma página, baja a la sección 'Parameters'.")
    print("   • Verás tu clave personal resaltada:")
    print("     key (str): Your API key: XXXXXXXX-XXXXXXXXXXXXXXXXXXXXXXXXX")
    print("   • Cópiala directamente.")

    print("\n2. PEXELS (Material cinematográfico 4K vertical de máxima fidelidad):")
    print("   • Ve a: https://www.pexels.com/api/")
    print("   • Si ya tienes una cuenta/clave previa o cuando reabran el registro:")
    print("     - Inicia sesión y ve a 'Your API Key'.")
    print("     - Cópiala y pégala aquí.")
    print("   • [AVISO ACTUAL]: Pexels pausó temporalmente la entrega de NUEVAS API keys")
    print("     a nuevos usuarios en su sitio web. Si no tienes una clave de Pexels,")
    print("     puedes usar Pixabay que está totalmente abierta y operativa.")
    print("=" * 70)


def load_stock_credentials() -> dict:
    creds = {
        "provider_mode": "both",
        "pixabay_api_keys": [],
        "pexels_api_keys": []
    }

    # 1. Leer de config/stock_credentials.json si existe
    if os.path.exists(STOCK_CREDS_PATH):
        try:
            with open(STOCK_CREDS_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
                creds.update(saved)
                return creds
        except Exception:
            pass

    # 2. Si no existe, inspeccionar config.toml de MoneyPrinterTurbo
    engine_cfg = get_engine_config_path()
    if engine_cfg and os.path.exists(engine_cfg):
        try:
            with open(engine_cfg, "r", encoding="utf-8") as f:
                content = f.read()

            pix_match = re.search(r'pixabay_api_keys\s*=\s*\[(.*?)\]', content)
            if pix_match:
                raw_keys = pix_match.group(1)
                keys = [k.strip(' "\'') for k in raw_keys.split(',') if k.strip(' "\'')]
                creds["pixabay_api_keys"] = keys

            pex_match = re.search(r'pexels_api_keys\s*=\s*\[(.*?)\]', content)
            if pex_match:
                raw_keys = pex_match.group(1)
                keys = [k.strip(' "\'') for k in raw_keys.split(',') if k.strip(' "\'')]
                creds["pexels_api_keys"] = keys

            if creds["pixabay_api_keys"] and creds["pexels_api_keys"]:
                creds["provider_mode"] = "both"
            elif creds["pexels_api_keys"]:
                creds["provider_mode"] = "pexels"
            else:
                creds["provider_mode"] = "pixabay"

            # Si encontramos claves en config.toml, persistir en stock_credentials.json
            if creds["pixabay_api_keys"] or creds["pexels_api_keys"]:
                save_stock_credentials(creds, sync_engine=False)
        except Exception:
            pass

    return creds


def save_stock_credentials(creds: dict, sync_engine: bool = True):
    os.makedirs(os.path.dirname(STOCK_CREDS_PATH), exist_ok=True)
    with open(STOCK_CREDS_PATH, "w", encoding="utf-8") as f:
        json.dump(creds, f, indent=2, ensure_ascii=False)

    if sync_engine:
        sync_to_engine(creds)


def sync_to_engine(creds: dict):
    engine_cfg = get_engine_config_path()
    if not engine_cfg or not os.path.exists(engine_cfg):
        return

    try:
        with open(engine_cfg, "r", encoding="utf-8") as f:
            content = f.read()

        mode = creds.get("provider_mode", "both")
        has_pexels = bool(creds.get("pexels_api_keys"))
        has_pixabay = bool(creds.get("pixabay_api_keys"))

        if mode == "pexels" and has_pexels:
            primary_source = "pexels"
        elif mode == "pixabay" and has_pixabay:
            primary_source = "pixabay"
        elif mode == "both":
            primary_source = "pexels" if has_pexels else "pixabay"
        else:
            primary_source = "pixabay" if has_pixabay else ("pexels" if has_pexels else "pixabay")

        pix_json = json.dumps(creds.get("pixabay_api_keys", []))
        pex_json = json.dumps(creds.get("pexels_api_keys", []))

        content = re.sub(r'pixabay_api_keys\s*=\s*\[.*?\]', f'pixabay_api_keys = {pix_json}', content)
        content = re.sub(r'pexels_api_keys\s*=\s*\[.*?\]', f'pexels_api_keys = {pex_json}', content)
        content = re.sub(r'video_source\s*=\s*".*?"', f'video_source = "{primary_source}"', content)

        with open(engine_cfg, "w", encoding="utf-8") as f:
            f.write(content)

    except Exception as e:
        print(f"Aviso al sincronizar con MoneyPrinterTurbo: {e}", file=sys.stderr)


def get_active_stock_source() -> str:
    creds = load_stock_credentials()
    mode = creds.get("provider_mode", "both")
    has_pexels = bool(creds.get("pexels_api_keys"))
    has_pixabay = bool(creds.get("pixabay_api_keys"))

    if mode == "pexels" and has_pexels:
        return "pexels"
    if mode == "pixabay" and has_pixabay:
        return "pixabay"
    if mode == "both":
        return "pexels" if has_pexels else "pixabay"
    return "pixabay" if has_pixabay else ("pexels" if has_pexels else "pixabay")


def configure_interactive():
    print("\n" + "=" * 70)
    print("  CONFIGURACION DE APIS DE STOCK (PIXABAY Y PEXELS)")
    print("=" * 70)

    creds = load_stock_credentials()
    pix_keys = creds.get("pixabay_api_keys", [])
    pex_keys = creds.get("pexels_api_keys", [])
    mode = creds.get("provider_mode", "both")

    print(f"\nEstado actual de credenciales:")
    print(f" • Pixabay API: {'[CONFIGURADA: ' + str(len(pix_keys)) + ' clave(s)]' if pix_keys else '[NO CONFIGURADA]'}")
    print(f" • Pexels API:  {'[CONFIGURADA: ' + str(len(pex_keys)) + ' clave(s)]' if pex_keys else '[NO CONFIGURADA]'}")
    print(f" • Modo activo: {mode.upper()} (both=híbrido con respaldo, pexels=solo pexels, pixabay=solo pixabay)")

    print("\n¿Qué deseas hacer?")
    print("1) Configurar Pixabay (Disponible ahora mismo)")
    print("2) Configurar Pexels (Si ya tienes clave o para cuando reabran)")
    print("3) Configurar Ambas (Modo Híbrido Pexels + Pixabay)")
    print("4) Cambiar modo de proveedor activo ('both', 'pexels', 'pixabay')")
    print("5) Ver guía de cómo conseguir las claves")
    print("6) Mantener configuración actual y continuar")

    try:
        choice = input("\nElige una opción (1-6) [6]: ").strip() or "6"
    except (KeyboardInterrupt, EOFError):
        return

    if choice == "5":
        show_api_instructions()
        return configure_interactive()

    if choice in ("1", "3"):
        show_api_instructions()
        cur = pix_keys[0] if pix_keys else ""
        prompt = f"\nIntroduce tu API Key de Pixabay [{cur[:10]}...]: " if cur else "\nIntroduce tu API Key de Pixabay: "
        val = input(prompt).strip()
        if val:
            creds["pixabay_api_keys"] = [val]
        elif cur:
            creds["pixabay_api_keys"] = [cur]

    if choice in ("2", "3"):
        show_api_instructions()
        cur = pex_keys[0] if pex_keys else ""
        prompt = f"\nIntroduce tu API Key de Pexels [{cur[:10]}...]: " if cur else "\nIntroduce tu API Key de Pexels: "
        val = input(prompt).strip()
        if val:
            creds["pexels_api_keys"] = [val]
        elif cur:
            creds["pexels_api_keys"] = [cur]

    if choice == "1":
        creds["provider_mode"] = "pixabay"
    elif choice == "2":
        creds["provider_mode"] = "pexels"
    elif choice == "3":
        creds["provider_mode"] = "both"
    elif choice == "4":
        print("\nSelecciona el modo de proveedor:")
        print("1) both (Buscar en Pexels y respaldar con Pixabay si no hay clips)")
        print("2) pexels (Usar exclusivamente Pexels)")
        print("3) pixabay (Usar exclusivamente Pixabay)")
        m_choice = input("Modo (1-3) [1]: ").strip() or "1"
        if m_choice == "2":
            creds["provider_mode"] = "pexels"
        elif m_choice == "3":
            creds["provider_mode"] = "pixabay"
        else:
            creds["provider_mode"] = "both"

    save_stock_credentials(creds)
    print("\n[OK] Credenciales de stock guardadas y sincronizadas con el motor.")


def check_and_prompt_if_needed() -> bool:
    creds = load_stock_credentials()
    has_pix = bool(creds.get("pixabay_api_keys"))
    has_pex = bool(creds.get("pexels_api_keys"))

    if has_pix or has_pex:
        providers = []
        if has_pix:
            providers.append(f"Pixabay ({len(creds['pixabay_api_keys'])} clave)")
        if has_pex:
            providers.append(f"Pexels ({len(creds['pexels_api_keys'])} clave)")
        print(f"API de stock activa: {', '.join(providers)} | Modo: {creds.get('provider_mode', 'both').upper()}")
        return True

    print("\n[AVISO] No se detectó ninguna API Key de stock (Pixabay o Pexels).")
    print("Para descargar videos libres de derechos necesitas al menos una clave gratuita.")
    show_api_instructions()

    if sys.stdin.isatty():
        configure_interactive()
        return True
    else:
        print("Ejecuta 'python scripts/configure_stock_api.py' para registrar tu clave.", file=sys.stderr)
        return False


if __name__ == "__main__":
    configure_interactive()
