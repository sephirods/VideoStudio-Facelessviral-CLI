import os

path = r"C:\MoneyPrinterTurbo\config.toml"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip().startswith("# video_codec ="):
        new_lines.append('video_codec = "h264_nvenc"\n')
    elif line.strip().startswith("# video_clip_concurrency ="):
        new_lines.append('video_clip_concurrency = 4\n')
    elif line.strip().startswith("# material_concurrency ="):
        new_lines.append('material_concurrency = 4\n')
    else:
        new_lines.append(line)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("NVENC and Concurrency successfully updated in config.toml")
