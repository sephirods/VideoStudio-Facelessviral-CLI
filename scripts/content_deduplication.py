#!/usr/bin/env python3
"""
Motor de Deduplicación y Control de Cooldown (Anti-Fatiga de Audiencia)
1. Control de Temas: Impide repetir el mismo tema en el mismo canal o grupo de canales hasta pasados 30 días.
2. Control de Miniaturas / Fotos: Impide reusar la misma imagen dentro del grupo de canales salvo necesidad estricta.
3. Registro Persistente: Almacena el historial en config/history/publication_history.json.
"""

import os
import sys
import json
import hashlib
import re
import argparse
from datetime import datetime, timedelta
from PIL import Image

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HISTORY_DIR = os.path.join(WORKSPACE_DIR, "config", "history")
HISTORY_FILE = os.path.join(HISTORY_DIR, "publication_history.json")
CHANNELS_FILE = os.path.join(WORKSPACE_DIR, "config", "channels.json")

SPANISH_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "a", "al", "en",
    "por", "para", "con", "sin", "sobre", "entre", "este", "esta", "estos", "estas",
    "que", "como", "cual", "mas", "menos", "muy", "todo", "toda", "todos", "todas"
}

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(history):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def get_channel_group(channel_id):
    """Obtiene el grupo al que pertenece el canal o su nicho como grupo por defecto."""
    if not os.path.exists(CHANNELS_FILE):
        return channel_id or "default_group"
    try:
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        channels = data.get("channels", {})
        if channel_id in channels:
            ch = channels[channel_id]
            # Si tiene 'group' explícito, úsalo; si no, usa 'niche'; si no, el propio channel_id
            return ch.get("group") or ch.get("niche") or channel_id
    except Exception:
        pass
    return channel_id or "default_group"

def compute_image_hash(image_path):
    """Calcula un dHash (perceptual hash de 64 bits) usando PIL para comparar imágenes visualmente similares."""
    if not os.path.exists(image_path):
        return None
    try:
        with Image.open(image_path) as img:
            # Reducir a 9x8 en escala de grises
            gray = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
            pixels = list(gray.getdata())
            # Comparar pixeles adyacentes horizontalmente
            diff = []
            for row in range(8):
                for col in range(8):
                    pixel_left = pixels[row * 9 + col]
                    pixel_right = pixels[row * 9 + col + 1]
                    diff.append("1" if pixel_left > pixel_right else "0")
            # Convertir a cadena hexadecimal de 16 caracteres
            decimal_val = int("".join(diff), 2)
            return f"{decimal_val:016x}"
    except Exception:
        # Fallback a sha256 del archivo
        try:
            with open(image_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        except Exception:
            return None

def normalize_text_tokens(text):
    """Limpia texto y extrae palabras significativas para comparación."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = [t.strip() for t in text.split() if len(t.strip()) > 2]
    return set(t for t in tokens if t not in SPANISH_STOPWORDS)

def calculate_topic_similarity(tokens1, tokens2):
    """Calcula el coeficiente Jaccard entre dos conjuntos de palabras clave."""
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    return intersection / union if union > 0 else 0.0

def check_topic_cooldown(topic, channel_id, cooldown_days=30):
    """
    Verifica si un tema ya fue publicado en el mismo canal o grupo en los últimos `cooldown_days`.
    Retorna un diccionario con el diagnóstico.
    """
    history = load_history()
    target_group = get_channel_group(channel_id)
    tokens_query = normalize_text_tokens(topic)
    
    now = datetime.now()
    cooldown_delta = timedelta(days=cooldown_days)
    
    recent_matches = []
    
    for item in history:
        item_channel = item.get("channel", "")
        item_group = item.get("group", item_channel)
        
        # Comparar solo si es del mismo grupo o mismo canal
        if item_group != target_group and item_channel != channel_id:
            continue
            
        pub_date_str = item.get("timestamp", "")
        try:
            pub_date = datetime.fromisoformat(pub_date_str)
        except Exception:
            continue
            
        elapsed = now - pub_date
        if elapsed < cooldown_delta:
            item_topic = item.get("topic", "")
            tokens_item = normalize_text_tokens(item_topic)
            sim = calculate_topic_similarity(tokens_query, tokens_item)
            
            # Si coincidencia >= 40% o si uno está completamente contenido en el otro
            is_contained = tokens_query.issubset(tokens_item) or tokens_item.issubset(tokens_query)
            if sim >= 0.40 or (is_contained and len(tokens_query) >= 2):
                days_left = cooldown_days - elapsed.days
                recent_matches.append({
                    "topic": item_topic,
                    "channel": item_channel,
                    "published_at": pub_date_str,
                    "days_ago": elapsed.days,
                    "days_remaining": days_left,
                    "similarity": round(sim, 2)
                })
                
    if recent_matches:
        # Ordenar por el más reciente
        recent_matches.sort(key=lambda x: x["days_ago"])
        most_recent = recent_matches[0]
        return {
            "allowed": False,
            "status": "COOLDOWN_ACTIVE",
            "reason": f"El tema '{topic}' coincide con '{most_recent['topic']}' publicado hace {most_recent['days_ago']} días.",
            "days_remaining": most_recent["days_remaining"],
            "group": target_group,
            "matched_item": most_recent
        }
        
    return {
        "allowed": True,
        "status": "APPROVED",
        "reason": "Tema fresco. No se ha tratado en los últimos 30 días en este grupo de canales.",
        "group": target_group
    }

def filter_candidate_images(candidates, channel_id, cooldown_days=30):
    """
    Evalúa una lista de candidatos a imagen (con ruta local 'path' y 'url')
    contra el historial del grupo. Retorna la lista anotada y la mejor opción fresca.
    """
    history = load_history()
    target_group = get_channel_group(channel_id)
    now = datetime.now()
    cooldown_delta = timedelta(days=cooldown_days)
    
    # Recolectar hashes y URLs usadas recientemente en este grupo
    used_hashes = {}
    used_urls = {}
    for item in history:
        item_group = item.get("group", item.get("channel", ""))
        if item_group != target_group and item.get("channel") != channel_id:
            continue
        try:
            pub_date = datetime.fromisoformat(item.get("timestamp", ""))
            if now - pub_date < cooldown_delta:
                h = item.get("image_hash")
                u = item.get("image_url")
                if h: used_hashes[h] = item
                if u: used_urls[u] = item
        except Exception:
            pass

    annotated = []
    first_fresh_idx = None
    
    for idx, cand in enumerate(candidates):
        cand_path = cand.get("path")
        cand_url = cand.get("url")
        cand_hash = compute_image_hash(cand_path) if cand_path else None
        
        is_used = False
        reason = None
        if cand_url and cand_url in used_urls:
            is_used = True
            reason = f"URL usada el {used_urls[cand_url].get('timestamp', '')[:10]}"
        elif cand_hash and cand_hash in used_hashes:
            is_used = True
            reason = f"Foto visualmente idéntica usada el {used_hashes[cand_hash].get('timestamp', '')[:10]}"
            
        annotated_item = dict(cand)
        annotated_item["already_used"] = is_used
        annotated_item["image_hash"] = cand_hash
        annotated_item["reuse_reason"] = reason
        annotated.append(annotated_item)
        
        if not is_used and first_fresh_idx is None:
            first_fresh_idx = idx + 1 # 1-based
            
    # Si todos fueron usados (caso extremo), se usa el candidato 1 con advertencia
    strictly_necessary = False
    if first_fresh_idx is None:
        first_fresh_idx = 1
        strictly_necessary = True
        
    return {
        "selected_index": first_fresh_idx,
        "is_strictly_necessary_reuse": strictly_necessary,
        "group": target_group,
        "candidates": annotated
    }

def register_publication(channel_id, topic, keywords, image_path, thumbnail_path, video_path, image_url=None):
    """Registra una publicación confirmada en el historial persistente."""
    history = load_history()
    target_group = get_channel_group(channel_id)
    img_hash = compute_image_hash(image_path) if image_path else None
    
    entry = {
        "id": f"pub_{int(datetime.now().timestamp())}",
        "channel": channel_id,
        "group": target_group,
        "topic": topic,
        "keywords": list(keywords) if isinstance(keywords, (list, set)) else [keywords],
        "image_hash": img_hash,
        "image_url": image_url,
        "thumbnail_path": os.path.abspath(thumbnail_path) if thumbnail_path else None,
        "video_path": os.path.abspath(video_path) if video_path else None,
        "timestamp": datetime.now().isoformat()
    }
    history.append(entry)
    save_history(history)
    return entry

def main():
    parser = argparse.ArgumentParser(description="Motor de Deduplicación y Cooldown de Temas y Miniaturas")
    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")
    
    # check-topic
    p_topic = subparsers.add_parser("check-topic", help="Verifica cooldown de un tema")
    p_topic.add_argument("--topic", required=True, help="Título o tema a verificar")
    p_topic.add_argument("--channel", default="default_channel", help="ID del canal")
    p_topic.add_argument("--days", type=int, default=30, help="Días de cooldown (default 30)")
    
    # register
    p_reg = subparsers.add_parser("register", help="Registra un video publicado en el historial")
    p_reg.add_argument("--channel", required=True, help="ID del canal")
    p_reg.add_argument("--topic", required=True, help="Tema del video")
    p_reg.add_argument("--image-path", help="Ruta de la hero_image")
    p_reg.add_argument("--thumbnail-path", help="Ruta de la miniatura")
    p_reg.add_argument("--video-path", help="Ruta del video final")
    p_reg.add_argument("--image-url", help="URL original de la imagen")
    
    args = parser.parse_args()
    
    if args.command == "check-topic":
        res = check_topic_cooldown(args.topic, args.channel, cooldown_days=args.days)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        if not res["allowed"]:
            sys.exit(2) # Código 2 indica bloqueo por cooldown
            
    elif args.command == "register":
        entry = register_publication(
            channel_id=args.channel,
            topic=args.topic,
            keywords=args.topic,
            image_path=args.image_path,
            thumbnail_path=args.thumbnail_path,
            video_path=args.video_path,
            image_url=args.image_url
        )
        print(f"[OK] Publicacion registrada con exito en historial: {entry['id']}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
