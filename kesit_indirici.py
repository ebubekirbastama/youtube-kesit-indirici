import subprocess
import customtkinter as ctk
from tkinter import messagebox
import threading
import re
import shutil

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

PCT_RE = re.compile(r'(\d+(?:\.\d+)?)%')  # "34.5%" gibi yüzdeyi yakalar
FILENAME_SAFE_RE = re.compile(r'[^A-Za-z0-9_\-ğüşöçıİĞÜŞÖÇ\s]')  # Türkçe harfler + boşluk + _ -

def sanitize_filename(name: str) -> str:
    if not name:
        return None
    name = name.strip()
    name = FILENAME_SAFE_RE.sub('', name)
    name = re.sub(r'\s+', '_', name)
    return name if name else None

def log_yaz(metin):
    log_box.configure(state="normal")
    log_box.insert("end", metin + "\n")
    log_box.see("end")
    log_box.configure(state="disabled")

def set_progress(value: float):
    try:
        progressbar.set(value)
        progress_label.configure(text=f"%{int(value*100)}")
        app.update_idletasks()
    except Exception:
        pass

def set_progress_indeterminate(on: bool):
    if on:
        progressbar.start()
        progress_label.configure(text="İşleniyor…")
    else:
        progressbar.stop()

def ffmpeg_var_mi():
    return shutil.which("ffmpeg") is not None

def secilen_format_str():
    mode = format_mode_var.get()
    # 1080p sınırı her modda korunuyor
    if mode == "MP4+M4A (önerilen)":
        return "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]"
    elif mode == "Tek Akış MP4":
        return "b[ext=mp4][height<=1080]/best[ext=mp4][height<=1080]"
    else:  # Otomatik (eski)
        return "bestvideo[height<=1080]+bestaudio/best[height<=1080]"

def indir_aralik(url, start, end, output_suffix, base_name=None):
    """
    Belirli zaman aralığını 1080p MP4 olarak indirir.
    İlerlemeyi log ve progress bar'a yazar.
    base_name: kullanıcı tarafından verilen video ismi (sanitiz edilmiş) veya None
    """
    app.after(0, lambda: set_progress(0.0))
    app.after(0, lambda: set_progress_indeterminate(False))
    app.after(0, lambda: status_label.configure(text=f"{output_suffix}. kesit indiriliyor…"))

    if base_name:
        out_name = f"{base_name}_kesit_{output_suffix}_1080p.mp4"
    else:
        out_name = f"YOUTUBE_KESIT_{output_suffix}_1080p.mp4"

    fmt = secilen_format_str()
    force_kf = bool(force_keyframes_var.get())

    cmd = [
        "yt-dlp", url,
        "--download-sections", f"*{start}-{end}",
        "--merge-output-format", "mp4",
        "--format", fmt,
        "--postprocessor-args", "ffmpeg:-c copy -movflags +faststart -avoid_negative_ts make_zero",
        "--newline",
        "-o", out_name
    ]
    if force_kf:
        # Kullanıcı isterse kesin kesim (keyframe zorlama)
        cmd.insert(3, "--force-keyframes-at-cuts")

    log_yaz(f"▶ Mod: {format_mode_var.get()} | Kesin kesim: {'Açık' if force_kf else 'Kapalı'}")
    log_yaz(f"▶ Çıktı: {out_name}")
    log_yaz(f"▶ Komut: yt-dlp ... --format \"{fmt}\" -o {out_name}")

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, universal_newlines=True
        )

        for line in process.stdout:
            s = line.strip()
            if not s:
                continue
            log_yaz(s)

            # Yüzdeyi yakala ve progress bar'a uygula
            m = PCT_RE.search(s)
            if m:
                try:
                    pct = float(m.group(1))
                    app.after(0, lambda p=pct: set_progress(p/100.0))
                except ValueError:
                    pass

            # Birleştirme/işleme aşamasında indeterminate moda geç
            if "Merging formats" in s or "Post-process" in s or "Destination" in s:
                app.after(0, lambda: set_progress_indeterminate(True))

        process.wait()
        app.after(0, lambda: set_progress_indeterminate(False))

        if process.returncode == 0:
            log_yaz(f"✅ {output_suffix}. aralık indirildi: {out_name}\n")
            app.after(0, lambda: set_progress(1.0))
            app.after(0, lambda: status_label.configure(text=f"{output_suffix}. kesit tamamlandı"))
        else:
            log_yaz(f"❌ {output_suffix}. aralık indirilemedi!\n")
            app.after(0, lambda: status_label.configure(text=f"{output_suffix}. kesitte hata"))

    except Exception as e:
        log_yaz(f"⚠️ Hata: {str(e)}")
        app.after(0, lambda: status_label.configure(text=f"{output_suffix}. kesitte hata"))

def baslat():
    url = entry_url.get().strip()
    s1 = entry_start1.get().strip()
    e1 = entry_end1.get().strip()
    s2 = entry_start2.get().strip()
    e2 = entry_end2.get().strip()
    raw_video_name = entry_video_name.get().strip()

    if not url or not s1 or not e1:
        messagebox.showwarning("Eksik Bilgi", "En az ilk zaman aralığını doldurmalısın!")
        return

    if not ffmpeg_var_mi():
        messagebox.showerror("ffmpeg eksik", "ffmpeg bulunamadı. Lütfen ffmpeg kurup PATH'e ekleyin.")
        return

    safe_name = sanitize_filename(raw_video_name)
    if raw_video_name and not safe_name:
        messagebox.showwarning("Geçersiz İsim", "Video ismi geçersiz karakterler içeriyor; isim devre dışı bırakıldı ve varsayılan isim kullanılacak.")
        safe_name = None

    log_yaz("🚀 İndirme başlatıldı…\n")
    log_yaz(f"📛 Video ismi: {safe_name if safe_name else '(varsayılan)'}")
    messagebox.showinfo("Başladı", "1080p kesit indirme işlemi başladı.")
    status_label.configure(text="İşlem başladı")

    def run():
        indir_aralik(url, s1, e1, "1", base_name=safe_name)
        if s2 and e2:
            indir_aralik(url, s2, e2, "2", base_name=safe_name)
        log_yaz("📁 Tüm kesitler tamamlandı. MP4 dosyaları YouTube’a hazır.\n")
        messagebox.showinfo("Tamamlandı", "Tüm kesitler başarıyla indirildi!")
        status_label.configure(text="Tüm kesitler tamamlandı")

    threading.Thread(target=run, daemon=True).start()

# === GUI ===
app = ctk.CTk()
app.title("🎬 YouTube Yayın Kesit İndirici (1080p / Scrollbar + ProgressBar)")
app.geometry("820x760")

frame = ctk.CTkFrame(app)
frame.pack(padx=20, pady=20, fill="both", expand=True)

ctk.CTkLabel(frame, text="🎥 YouTube Yayın Linki").pack(pady=(10, 5))
entry_url = ctk.CTkEntry(frame, width=700)
entry_url.pack()

ctk.CTkLabel(frame, text="📝 Video İsmi (opsiyonel, dosya adına eklenecek)").pack(pady=(10, 5))
entry_video_name = ctk.CTkEntry(frame, width=700, placeholder_text="Örn: KanalAdı_Yayını_2025-10-15")
entry_video_name.pack()

# İLERİ SEÇENEKLER
adv_row = ctk.CTkFrame(frame)
adv_row.pack(pady=(12,6), fill="x")

# Kesin kesim anahtarı (varsayılan: kapalı – ses uç kaybını azaltır)
force_keyframes_var = ctk.BooleanVar(value=False)
force_kf_switch = ctk.CTkSwitch(adv_row, text="Kesin Kesim (keyframe zorlama)", variable=force_keyframes_var)
force_kf_switch.pack(side="left", padx=6)

# Format modu
ctk.CTkLabel(adv_row, text="Format modu:").pack(side="left", padx=(18,6))
format_mode_var = ctk.StringVar(value="MP4+M4A (önerilen)")
format_combo = ctk.CTkComboBox(
    adv_row,
    values=["MP4+M4A (önerilen)", "Tek Akış MP4", "Otomatik (eski)"],
    variable=format_mode_var,
    width=220
)
format_combo.pack(side="left")

ctk.CTkLabel(frame, text="⏱ 1. Zaman Aralığı (Başlangıç - Bitiş)").pack(pady=(12, 5))
row1 = ctk.CTkFrame(frame)
row1.pack()
entry_start1 = ctk.CTkEntry(row1, width=120, placeholder_text="00:10:00")
entry_start1.pack(side="left", padx=5)
entry_end1 = ctk.CTkEntry(row1, width=120, placeholder_text="00:15:00")
entry_end1.pack(side="left", padx=5)

ctk.CTkLabel(frame, text="⏱ 2. Zaman Aralığı (Başlangıç - Bitiş)").pack(pady=(10, 5))
row2 = ctk.CTkFrame(frame)
row2.pack()
entry_start2 = ctk.CTkEntry(row2, width=120, placeholder_text="00:30:00")
entry_start2.pack(side="left", padx=5)
entry_end2 = ctk.CTkEntry(row2, width=120, placeholder_text="00:35:00")
entry_end2.pack(side="left", padx=5)

status_label = ctk.CTkLabel(frame, text="Hazır")
status_label.pack(pady=(15, 5))

progressbar = ctk.CTkProgressBar(frame)
progressbar.pack(fill="x", padx=10)
progressbar.set(0.0)

progress_label = ctk.CTkLabel(frame, text="%0")
progress_label.pack(pady=(5, 10))

ctk.CTkButton(frame, text="📥 1080p Kesitleri İndir", command=baslat).pack(pady=10)

# LOG + SCROLLBAR
log_frame = ctk.CTkFrame(frame)
log_frame.pack(pady=(10, 5), fill="both", expand=True)

log_box = ctk.CTkTextbox(log_frame, width=780, height=320)
log_box.pack(side="left", fill="both", expand=True)
log_box.configure(state="disabled")

scrollbar = ctk.CTkScrollbar(log_frame, command=log_box.yview)
scrollbar.pack(side="right", fill="y")
log_box.configure(yscrollcommand=scrollbar.set)

app.mainloop()
