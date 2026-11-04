#!/usr/bin/env python3
"""
Conector 100% Automatico de Cuentas.
Abre Google Chrome en modo interactivo, espera a que el usuario inicie sesion,
detecta el exito con cookies reales de autenticacion, guarda la sesion
en config/sessions/[canal]/ y cierra la ventana sola.
"""

import argparse
import os
import sys
import time
from playwright.sync_api import sync_playwright

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SESSIONS_DIR = os.path.join(ROOT_DIR, "config", "sessions")


def is_youtube_authenticated(url: str, cookies: list) -> bool:
    if "accounts.google.com" in url:
        return False
    # Requiere cookies reales de sesion de YouTube
    has_auth_cookie = any(
        c.get("name") in ("LOGIN_INFO", "SSID", "SID") and "youtube.com" in c.get("domain", "")
        for c in cookies
    )
    is_studio_channel = "studio.youtube.com" in url and ("channel" in url or "video" in url)
    return has_auth_cookie or is_studio_channel


def is_tiktok_authenticated(url: str, cookies: list) -> bool:
    if "/login" in url:
        return False
    return any("sessionid" in c.get("name", "").lower() for c in cookies)


def is_instagram_authenticated(url: str, cookies: list) -> bool:
    if "accounts/login" in url:
        return False
    return any(c.get("name") == "sessionid" for c in cookies)


PLATFORM_CONFIG = {
    "youtube": {
        "name": "YouTube Studio",
        "url": "https://studio.youtube.com",
        "validator": is_youtube_authenticated
    },
    "tiktok": {
        "name": "TikTok",
        "url": "https://www.tiktok.com/login",
        "validator": is_tiktok_authenticated
    },
    "instagram": {
        "name": "Instagram",
        "url": "https://www.instagram.com/accounts/login/",
        "validator": is_instagram_authenticated
    }
}


def connect(channel_id: str, platform: str) -> bool:
    platform = platform.lower()
    if platform not in PLATFORM_CONFIG:
        print(f"Error: Plataforma '{platform}' no valida.", flush=True)
        return False

    cfg = PLATFORM_CONFIG[platform]
    channel_dir = os.path.join(SESSIONS_DIR, channel_id)
    os.makedirs(channel_dir, exist_ok=True)
    session_file = os.path.join(channel_dir, f"{platform}_session.json")

    print(f"[CONECTOR] Abriendo ventana de Chrome para {cfg['name']}...", flush=True)

    with sync_playwright() as p:
        # Usar Chrome del sistema para evitar bloqueos de Google
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ],
            ignore_default_args=["--enable-automation"]
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        try:
            page.goto(cfg["url"], wait_until="domcontentloaded")
            print(f"[CONECTOR] Ventana abierta en pantalla. Esperando inicio de sesion...", flush=True)

            logged_in = False
            # Esperar hasta 5 minutos a que el usuario complete el login
            for second in range(300):
                if page.is_closed():
                    break
                
                try:
                    current_url = page.url
                    cookies = context.cookies()
                    if cfg["validator"](current_url, cookies):
                        print("[CONECTOR] ¡Inicio de sesion detectado! Guardando sesion...", flush=True)
                        time.sleep(2.5)  # Tiempo para asentar tokens y cookies
                        context.storage_state(path=session_file)
                        logged_in = True
                        print(f"[CONECTOR] Sesion guardada exitosamente en {session_file}", flush=True)
                        break
                except Exception:
                    pass

                time.sleep(1)

            return logged_in

        except Exception as e:
            print(f"[CONECTOR] Error durante la vinculacion: {e}", flush=True)
            return False
        finally:
            try:
                browser.close()
            except Exception:
                pass


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True)
    parser.add_argument("--platform", required=True, choices=["youtube", "tiktok", "instagram"])
    args = parser.parse_args()

    success = connect(args.channel, args.platform)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
