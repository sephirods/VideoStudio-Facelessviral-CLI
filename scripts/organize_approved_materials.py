import os
import shutil
import json
import datetime

# Root paths
ROOT_DIR = r"C:\Users\Juan\Desktop\CanalesYoutube"
BROLL_DIR = os.path.join(ROOT_DIR, "assets", "b-roll", "pesca")
HISTORY_FILE = os.path.join(ROOT_DIR, "config", "stock_history.json")
RUNS_DIR = os.path.join(ROOT_DIR, "pipeline_runs", "demo_pesca")
MATERIALS_JSON_PATH = os.path.join(RUNS_DIR, "approved_materials.json")

os.makedirs(BROLL_DIR, exist_ok=True)
os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

# 17 Approved clips (full paths)
approved_list = [
    # Batch 1 (Pixabay)
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-bcbf309f07a5dd4d1ad0fe5e5f803efc.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-559ca1beafa9558e300f19bb3c7bfe8a.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-39232a3d190b290ca09e0cb5484a8c49.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-9c882086eb83ed159685d1e2471dd462.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-c0c8a4ae0f9b0d9923d7d6adec532e18.mp4",
    # Batch 2 (Complementary Pixabay)
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-206783.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-111288.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-154653.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-10008.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-4260.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-44534.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-199308.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-199307.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-931.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-2263.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-144934.mp4",
    r"C:\MoneyPrinterTurbo\storage\cache_videos\vid-pixabay-263131.mp4",
]

# Rejected clips with explicit reasons
rejected_list = [
    {
        "file": "vid-f17a899f9417d61d67f0cc1a979fbc4d.mp4",
        "reason": "Desconexión temática: toma de bosque otoñal en tierra firme sin agua ni peces."
    },
    {
        "file": "vid-5b964d3f0f2b254014fefd8ff6b06732.mp4",
        "reason": "Render 3D de monedas y anillos de oro flotando sobre fondo negro plano."
    },
    {
        "file": "vid-de390400f6858f40b0b9b37ed1ed5073.mp4",
        "reason": "Desconexión temática: paisaje invernal nevado en montaña alpina con banco vacío."
    },
    {
        "file": "vid-c2da6374a615e1363c59164bcc35de16.mp4",
        "reason": "Desconexión temática: paisaje marino soleado costero con gaviota y yate turístico."
    },
    {
        "file": "vid-f4dd64714d293e93cf69112274019a94.mp4",
        "reason": "Desconexión temática: medusas en acuario sobre fondo completamente negro."
    },
    {
        "file": "vid-21a1a5af0fef85cf7d295162c76d4e6a.mp4",
        "reason": "Desconexión temática: faro y playa costera con niebla espesa marina."
    },
    {
        "file": "vid-3bc8dff468e3689b0d0d45e19ed15db3.mp4",
        "reason": "Desconexión temática: bote solitario lejano en mar abierto azul sin acción de pesca."
    },
    {
        "file": "vid-0af7c652eb55ac528a1bd7cb5aa7394f.mp4",
        "reason": "Reciclaje ajeno de nicho financiero: conteo de fajos de billetes de euro."
    },
    {
        "file": "vid-d32d4f5f27223e07b5f347ef5b30bd27.mp4",
        "reason": "Desconexión temática: curva de autopista de montaña con automóviles."
    },
    {
        "file": "vid-6eec1b94098cfa82e0c6910e31d79399.mp4",
        "reason": "Desconexión temática: arrecife de coral y peces tropicales en acuario marino."
    },
    {
        "file": "vid-a6822374d1f960ca9a21babaed2c0f02.mp4",
        "reason": "Desconexión temática absurda: gatito doméstico en jardín por coincidencia de palabra 'catfish'."
    },
    {
        "file": "vid-2dc431a28fc20a39045e32388f83b685.mp4",
        "reason": "Reciclaje administrativo: factura y bolígrafo sobre escritorio por coincidencia con 'river bank'."
    },
    {
        "file": "vid-179595d66657233b73b863b2459972a0.mp4",
        "reason": "Animación 3D de fajos de dólares cayendo sobre fondo negro plano."
    },
    {
        "file": "vid-pixabay-211373.mp4",
        "reason": "Desconexión marina: tiburones y peces de arrecife en acuario de agua salada."
    }
]

print("1. Copying approved clips to B-Roll archive...")
broll_paths = []
for clip_path in approved_list:
    fname = os.path.basename(clip_path)
    dest_clip = os.path.join(BROLL_DIR, fname)
    if os.path.exists(clip_path):
        shutil.copy2(clip_path, dest_clip)
        broll_paths.append(dest_clip)
        print(f"  Copied to b-roll: {fname}")
    else:
        print(f"  Warning: Clip not found: {clip_path}")

print("\n2. Purging rejected clips from storage...")
cache_dir = r"C:\MoneyPrinterTurbo\storage\cache_videos"
for rej in rejected_list:
    rej_path = os.path.join(cache_dir, rej["file"])
    if os.path.exists(rej_path):
        os.remove(rej_path)
        print(f"  Purged: {rej['file']}")
    else:
        print(f"  Already absent: {rej['file']}")

print("\n3. Updating stock history rotation...")
history = []
if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        history = []

now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
for clip_path in approved_list:
    fname = os.path.basename(clip_path)
    history.append({
        "file": fname,
        "category": "pesca",
        "used_at": now_iso,
        "task_id": "demo_pesca_task"
    })

with open(HISTORY_FILE, "w", encoding="utf-8") as f:
    json.dump(history, f, indent=2, ensure_ascii=False)
print(f"  Stock history updated at {HISTORY_FILE} with {len(history)} entries.")

print("\n4. Generating approved_materials.json...")
materials_data = {
    "task_id": "demo_pesca_task",
    "total_downloaded": len(approved_list) + len(rejected_list),
    "approved_clips": approved_list,
    "rejected_clips": rejected_list,
    "review_status": "APPROVED",
    "broll_archive": "assets/b-roll/pesca"
}

with open(MATERIALS_JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(materials_data, f, indent=2, ensure_ascii=False)

print(f"Successfully generated: {MATERIALS_JSON_PATH}")
