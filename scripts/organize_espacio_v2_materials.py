import os
import shutil
import json
import datetime

ROOT_DIR = r"C:\Users\Juan\Desktop\CanalesYoutube"
BROLL_DIR = os.path.join(ROOT_DIR, "assets", "b-roll", "espacio")
HISTORY_FILE = os.path.join(ROOT_DIR, "config", "stock_history.json")
RUNS_DIR = os.path.join(ROOT_DIR, "pipeline_runs", "demo_espacio_v2")
MATERIALS_JSON_PATH = os.path.join(RUNS_DIR, "approved_materials.json")

os.makedirs(BROLL_DIR, exist_ok=True)
os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

approved_list = [
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-2cb9c70ba1f1f235523895a495691813.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-fda27b0571bb3ec5abaf96fe5d1c1e36.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-6e2c574381a3207f6113feb132828183.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-d3ae5047721121aaa0112fe41c8f8e7e.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-1d0cecb9981348f72887a9f311e97cd8.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-ab309c9b02ba633602e29252faff72ab.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-3fcd1cff05737406bb541c9e50cb5534.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-6da527270665793798cdd717f7444ecb.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-b46c16019f17a2e03d2e477079750b58.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-f0c5fef3b7388e6d7f9476f0d4ace565.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-space-140733.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-space-139586.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-space-175323.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-space-212024.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-space-231596.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-space-145577.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-space-132253.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-space-31495.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-space-101817.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-space-10.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-space-6433.mp4"
]

rejected_list = [
    {
        "file": "vid-5fdcba529f6e60cd32068f3bbb2ce8cb.mp4",
        "reason": "Diagrama y animación 2D de órbitas celestes estilizadas sobre fondo negro plano."
    },
    {
        "file": "vid-0981f4a5022d33599aeec6d6670461f8.mp4",
        "reason": "Desconexión temática total: estela de barco en océano turquesa marino sin relación astronómica."
    },
    {
        "file": "vid-3d0106a3b6a6ff21dc604a4296adf966.mp4",
        "reason": "Render 3D básico de Júpiter aislado sobre fondo negro plano sin estrellas ni contexto cósmico."
    },
    {
        "file": "vid-f12b6f79909e35552c7cf18583f3ac33.mp4",
        "reason": "Desconexión temática: entorno surrealista de fantasía oscura y caverna roja con escaleras."
    },
    {
        "file": "vid-03d8e0ce6e8d47de8024581a74c46279.mp4",
        "reason": "Diagrama esquemático 2D vectorial con círculos concéntricos de órbitas sobre fondo negro."
    },
    {
        "file": "vid-8ca8428d031d00ab957549b9d470b6b2.mp4",
        "reason": "Render 3D abstracto de esfera metálica dorada flotando sobre fondo negro plano."
    },
    {
        "file": "vid-7889f07e67d29b2b5376ce9ab5d39b04.mp4",
        "reason": "Render monocromático plano de silueta lunar recortada sin profundidad espacial."
    },
    {
        "file": "vid-6b84a0430d82cffc510ed9a606771163.mp4",
        "reason": "Defecto técnico: cuadro blanco completamente sobreexpuesto/quemado sin información visual."
    },
    {
        "file": "vid-1761b99e1fbd458aefe8951d4743c605.mp4",
        "reason": "Render 3D plano de planeta aislado flotando sobre fondo negro plano."
    },
    {
        "file": "vid-pixabay-space-143016.mp4",
        "reason": "Silueta estilizada de astronauta animado no cinematográfico (no encaja con tono documental cósmico)."
    },
    {
        "file": "vid-pixabay-space-42586.mp4",
        "reason": "Modelo 3D de túnel de gusano con marco lateral negro plano vacío."
    },
    {
        "file": "vid-pixabay-space-5346.mp4",
        "reason": "Destello blanco plano sobreexpuesto y distorsión sin contexto estelar."
    },
    {
        "file": "vid-pixabay-space-156444.mp4",
        "reason": "Desconexión temática terrestre: tomas de paneles de energía solar."
    },
    {
        "file": "vid-pixabay-space-168801.mp4",
        "reason": "Desconexión temática terrestre: tejados residenciales con celdas solares."
    },
    {
        "file": "vid-pixabay-space-128666.mp4",
        "reason": "Desconexión temática terrestre: luz solar filtrándose entre árboles de un bosque."
    },
    {
        "file": "vid-pixabay-space-28262.mp4",
        "reason": "Desconexión temática terrestre: costa rocosa y playa marítima de Oregon."
    },
    {
        "file": "vid-pixabay-space-28266.mp4",
        "reason": "Desconexión temática terrestre: olas de océano en rompiente costera."
    },
    {
        "file": "vid-pixabay-space-127522.mp4",
        "reason": "Desconexión temática terrestre: hojas de árbol de roble al sol."
    },
    {
        "file": "vid-pixabay-space-28269.mp4",
        "reason": "Desconexión temática terrestre: costa marina con rocas y sol bajo."
    },
    {
        "file": "vid-pixabay-space-384849.mp4",
        "reason": "Desconexión temática terrestre: puesta de sol en horizonte urbano."
    },
    {
        "file": "vid-pixabay-space-370344.mp4",
        "reason": "Desconexión temática terrestre: eclipse solar con silueta de copas de árboles terrestres."
    },
    {
        "file": "vid-pixabay-space-3136.mp4",
        "reason": "Desconexión temática terrestre: atardecer en horizonte rural."
    }
]

print("1. Copiando clips aprobados a la biblioteca permanente de B-Roll (assets/b-roll/espacio)...")
broll_paths = []
for p in approved_list:
    fname = os.path.basename(p)
    dest = os.path.join(BROLL_DIR, fname)
    if not os.path.exists(dest) or os.path.getsize(dest) != os.path.getsize(p):
        shutil.copy2(p, dest)
    broll_paths.append(dest)
print(f"   -> {len(broll_paths)} clips archivados en B-Roll.")

print("2. Registrando clips aprobados en config/stock_history.json para rotación de 7 días...")
history = []
if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        history = []

now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
for p in approved_list:
    fname = os.path.basename(p)
    history.append({
        "file": fname,
        "category": "espacio",
        "used_at": now_iso,
        "task_id": "demo_espacio_v2_task"
    })

with open(HISTORY_FILE, "w", encoding="utf-8") as f:
    json.dump(history, f, indent=2)
print("   -> Historial actualizado exitosamente.")

print("3. Purgando clips rechazados del almacenamiento de trabajo...")
purged_count = 0
cache_dir = r"C:\MoneyPrinterTurbo\storage\cache_videos"
for r in rejected_list:
    fname = r["file"]
    fpath = os.path.join(cache_dir, fname)
    if os.path.exists(fpath):
        try:
            os.remove(fpath)
            purged_count += 1
        except Exception as e:
            print(f"   Aviso: no se pudo eliminar {fpath}: {e}")
print(f"   -> {purged_count} clips rechazados eliminados del disco.")

print("4. Generando approved_materials.json oficial...")
materials_data = {
    "task_id": "demo_espacio_v2_task",
    "total_downloaded": len(approved_list) + len(rejected_list),
    "approved_clips": approved_list,
    "rejected_clips": rejected_list,
    "review_status": "APPROVED",
    "broll_archive": "assets/b-roll/espacio"
}

with open(MATERIALS_JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(materials_data, f, indent=2, ensure_ascii=False)

print(f"   -> Archivo guardado en {MATERIALS_JSON_PATH}")
print("[OK] Proceso de auditoría y almacenamiento finalizado con éxito.")
