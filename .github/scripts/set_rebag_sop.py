from pathlib import Path

path = Path("src/App.jsx")
text = path.read_text(encoding="utf-8")

old_default = '  rebagSopRef: "",'
new_default = '  rebagSopRef: "41/PR/2023 – Prosedur Produksi, Rev. 1, 05 April 2023",'
if text.count(old_default) != 1:
    raise SystemExit(f"Expected exactly one empty rebagSopRef default, found {text.count(old_default)}")
text = text.replace(old_default, new_default, 1)

old_config = '''        if (snap.exists()) {
          setSystemConfig({ ...DEFAULT_SYSTEM_CONFIG, ...snap.data() });
        } else {
          setSystemConfig(DEFAULT_SYSTEM_CONFIG);
        }'''

new_config = '''        if (snap.exists()) {
          const savedConfig = snap.data();
          const mergedConfig = { ...DEFAULT_SYSTEM_CONFIG, ...savedConfig };
          if (!String(savedConfig.rebagSopRef || "").trim() && DEFAULT_SYSTEM_CONFIG.rebagSopRef) {
            mergedConfig.rebagSopRef = DEFAULT_SYSTEM_CONFIG.rebagSopRef;
            setDoc(
              doc(db, "artifacts", appId, "public", "data", "config", "system"),
              { rebagSopRef: DEFAULT_SYSTEM_CONFIG.rebagSopRef },
              { merge: true }
            ).catch((error) => console.error("Gagal mengisi referensi SOP/WI default:", error));
          }
          setSystemConfig(mergedConfig);
        } else {
          setSystemConfig(DEFAULT_SYSTEM_CONFIG);
          setDoc(
            doc(db, "artifacts", appId, "public", "data", "config", "system"),
            DEFAULT_SYSTEM_CONFIG,
            { merge: true }
          ).catch((error) => console.error("Gagal menginisialisasi konfigurasi sistem:", error));
        }'''

if text.count(old_config) != 1:
    raise SystemExit(f"Expected exactly one config snapshot block, found {text.count(old_config)}")
text = text.replace(old_config, new_config, 1)

path.write_text(text, encoding="utf-8")
print("SOP reference patch applied")
