from pathlib import Path

path = Path("src/App.jsx")
s = path.read_text(encoding="utf-8")

def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"Patch target not found: {label}")
    s = s.replace(old, new, 1)

# Defaults + standards snapshot helper.
rep(
'''const STACK_LOCATIONS = ["Unit Pengolahan 20", "RTR 60", "Gula 17"];
const DEFAULT_USERS = [''',
'''const STACK_LOCATIONS = ["Unit Pengolahan 20", "RTR 60", "Gula 17"];

const DEFAULT_SYSTEM_CONFIG = {
  name: "Sistem Rebagging Terpadu",
  logo: null,
  rebagDocumentCode: "",
  rebagDocumentRevision: "",
  rebagDocumentEffectiveDate: "",
  rebagSopRef: "",
  rebagSsopRef: "",
  rebagHaccpRef: "",
  rebagScaleId: "",
  rebagScaleCalibrationDue: "",
  rebagApproverName: "IRSA MAULIAN NUGRAHA",
};

const getRebagStandards = (productName = "") => {
  const upperName = String(productName || "").toUpperCase();
  return {
    fsms: "SNI ISO 22000:2018 + Amd1:2024",
    prpManufacturing: "ISO 22002-1:2025",
    prpCommon: "ISO 22002-100:2025",
    cppob: "CPPOB - PerBPOM No. 22 Tahun 2021",
    productQuality: upperName.includes("GULA")
      ? "SNI 3140.3:2010/Amd1:2011 - Gula kristal, Bagian 3: Putih"
      : "Spesifikasi internal / COA produk yang berlaku",
  };
};

const DEFAULT_USERS = [''',
"system config defaults")

rep(
'''  const [systemConfig, setSystemConfig] = useState({ name: "Sistem Rebagging Terpadu", logo: null });''',
'''  const [systemConfig, setSystemConfig] = useState(DEFAULT_SYSTEM_CONFIG);''',
"system config state")

rep(
'''      (snap) => {
        if (snap.exists()) setSystemConfig(snap.data());
      },''',
'''      (snap) => {
        if (snap.exists()) {
          setSystemConfig({ ...DEFAULT_SYSTEM_CONFIG, ...snap.data() });
        } else {
          setSystemConfig(DEFAULT_SYSTEM_CONFIG);
        }
      },''',
"config listener merge")

# Add document snapshot before Rebag Firestore transaction.
rep(
'''        const materialDamageLineCount = selectedMaterials.filter(
          (material) => Number(material.damageQty || 0) > 0
        ).length;

        await runTransaction(db, async (transaction) => {''',
'''        const materialDamageLineCount = selectedMaterials.filter(
          (material) => Number(material.damageQty || 0) > 0
        ).length;

        const documentControlSnapshot = {
          code: systemConfig.rebagDocumentCode || "",
          revision: systemConfig.rebagDocumentRevision || "",
          effectiveDate: systemConfig.rebagDocumentEffectiveDate || "",
          sopRef: systemConfig.rebagSopRef || "",
          ssopRef: systemConfig.rebagSsopRef || "",
          haccpRef: systemConfig.rebagHaccpRef || "",
          scaleId: systemConfig.rebagScaleId || "",
          scaleCalibrationDue: systemConfig.rebagScaleCalibrationDue || "",
          approverName: systemConfig.rebagApproverName || "IRSA MAULIAN NUGRAHA",
          standards: getRebagStandards(targetSku.name),
          capturedAt: recordedAt,
        };

        await runTransaction(db, async (transaction) => {''',
"document control snapshot")

# Store snapshot in finished batch.
rep(
'''            recipeSnapshot: recipe
              ? {
                  id: recipe.id,
                  version: Number(recipe.version || 1),
                  label: recipe.label || "",
                  targetSku: recipe.targetSku || targetSku.id,
                  materials: normalizeRecipeMaterials(recipe),
                }
              : null,
            moNumber: sourceMoNumbers.join(", "),''',
'''            recipeSnapshot: recipe
              ? {
                  id: recipe.id,
                  version: Number(recipe.version || 1),
                  label: recipe.label || "",
                  targetSku: recipe.targetSku || targetSku.id,
                  materials: normalizeRecipeMaterials(recipe),
                }
              : null,
            documentControl: documentControlSnapshot,
            moNumber: sourceMoNumbers.join(", "),''',
"finished batch document snapshot")

# Store snapshot in transaction (second recipeSnapshot occurrence).
needle='''              recipeSnapshot: recipe
                ? {
                    id: recipe.id,
                    version: Number(recipe.version || 1),
                    label: recipe.label || "",
                    targetSku: recipe.targetSku || targetSku.id,
                    materials: normalizeRecipeMaterials(recipe),
                  }
                : null,
              ...auditMeta,''';
replacement='''              recipeSnapshot: recipe
                ? {
                    id: recipe.id,
                    version: Number(recipe.version || 1),
                    label: recipe.label || "",
                    targetSku: recipe.targetSku || targetSku.id,
                    materials: normalizeRecipeMaterials(recipe),
                  }
                : null,
              documentControl: documentControlSnapshot,
              ...auditMeta,''';
rep(needle,replacement,"transaction document snapshot")

# Pass current config as fallback for legacy transactions.
rep(
'''      await generateRebaggingBatchPdf({
        ...transaction,
        sourceWarehouse: transaction.sourceWarehouse || sourceBatch?.sourceWarehouse || "",
        sourceSkuName: transaction.sourceSkuName || sourceSku?.name || "Gula Curah",
        sourceUnit: transaction.sourceUnit || sourceSku?.unit || "KG",
        sourceQty: transaction.sourceQty ?? transaction.qtyChange,
        finishedQty: transaction.finishedQty ?? transaction.qtyChange,
        finishedUnit: transaction.finishedUnit || transaction.unit || "Pack",
      });''',
'''      await generateRebaggingBatchPdf({
        ...transaction,
        sourceWarehouse: transaction.sourceWarehouse || sourceBatch?.sourceWarehouse || "",
        sourceSkuName: transaction.sourceSkuName || sourceSku?.name || "Gula Curah",
        sourceUnit: transaction.sourceUnit || sourceSku?.unit || "KG",
        sourceQty: transaction.sourceQty ?? transaction.qtyChange,
        finishedQty: transaction.finishedQty ?? transaction.qtyChange,
        finishedUnit: transaction.finishedUnit || transaction.unit || "Pack",
      }, systemConfig);''',
"PDF config fallback")

# Add controlled-document settings under system config.
old='''                  <div>
                    <label className="block font-bold text-slate-700 mb-1">URL Logo (Opsional)</label>
                    <p className="text-xs text-slate-500 mb-3">Biarkan kosong jika ingin menggunakan ikon kotak default.</p>
                    <input className="w-full border border-slate-300 p-3 rounded-lg outline-none focus:border-red-500" value={systemConfig.logo || ""} onChange={e=>setSystemConfig({...systemConfig, logo: e.target.value})} placeholder="Contoh: /logo.png" />
                  </div>
                  <button className="w-full sm:w-auto bg-slate-800 text-white font-bold px-6 py-3 rounded-lg hover:bg-slate-900 shadow-md">Simpan Perubahan Sistem</button>''';

new='''                  <div>
                    <label className="block font-bold text-slate-700 mb-1">URL Logo (Opsional)</label>
                    <p className="text-xs text-slate-500 mb-3">Biarkan kosong jika ingin menggunakan ikon kotak default.</p>
                    <input className="w-full border border-slate-300 p-3 rounded-lg outline-none focus:border-red-500" value={systemConfig.logo || ""} onChange={e=>setSystemConfig({...systemConfig, logo: e.target.value})} placeholder="Contoh: /logo.png" />
                  </div>

                  <div className="rounded-2xl border border-blue-200 bg-blue-50/50 p-4 sm:p-5 space-y-4">
                    <div>
                      <div className="text-xs font-black uppercase tracking-[0.14em] text-blue-600">Kontrol Dokumen Rebagging</div>
                      <h4 className="mt-1 font-black text-slate-900">ISO / SNI / CPPOB-ready</h4>
                      <p className="mt-1 text-xs leading-5 text-slate-600">
                        Isi kode dokumen resmi internal sebelum form digunakan sebagai dokumen terkendali. Jika kosong, PDF akan diberi status DRAFT / BELUM DITETAPKAN.
                      </p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div>
                        <label className="block text-xs font-bold text-slate-600 mb-1.5">Kode Dokumen</label>
                        <input className="w-full border border-slate-300 bg-white p-2.5 rounded-lg outline-none focus:border-blue-500" value={systemConfig.rebagDocumentCode || ""} onChange={e=>setSystemConfig({...systemConfig,rebagDocumentCode:e.target.value})} placeholder="Contoh: FRM-XXX-001"/>
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-slate-600 mb-1.5">Revisi</label>
                        <input className="w-full border border-slate-300 bg-white p-2.5 rounded-lg outline-none focus:border-blue-500" value={systemConfig.rebagDocumentRevision || ""} onChange={e=>setSystemConfig({...systemConfig,rebagDocumentRevision:e.target.value})} placeholder="Contoh: 00"/>
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-slate-600 mb-1.5">Tanggal Berlaku</label>
                        <input type="date" className="w-full border border-slate-300 bg-white p-2.5 rounded-lg outline-none focus:border-blue-500" value={systemConfig.rebagDocumentEffectiveDate || ""} onChange={e=>setSystemConfig({...systemConfig,rebagDocumentEffectiveDate:e.target.value})}/>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div>
                        <label className="block text-xs font-bold text-slate-600 mb-1.5">Referensi SOP / WI</label>
                        <input className="w-full border border-slate-300 bg-white p-2.5 rounded-lg outline-none focus:border-blue-500" value={systemConfig.rebagSopRef || ""} onChange={e=>setSystemConfig({...systemConfig,rebagSopRef:e.target.value})} placeholder="Nomor SOP/WI"/>
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-slate-600 mb-1.5">Referensi SSOP / PRP</label>
                        <input className="w-full border border-slate-300 bg-white p-2.5 rounded-lg outline-none focus:border-blue-500" value={systemConfig.rebagSsopRef || ""} onChange={e=>setSystemConfig({...systemConfig,rebagSsopRef:e.target.value})} placeholder="Nomor SSOP/PRP"/>
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-slate-600 mb-1.5">Referensi HACCP / Analisis Bahaya</label>
                        <input className="w-full border border-slate-300 bg-white p-2.5 rounded-lg outline-none focus:border-blue-500" value={systemConfig.rebagHaccpRef || ""} onChange={e=>setSystemConfig({...systemConfig,rebagHaccpRef:e.target.value})} placeholder="Nomor dokumen"/>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div>
                        <label className="block text-xs font-bold text-slate-600 mb-1.5">ID Timbangan Utama</label>
                        <input className="w-full border border-slate-300 bg-white p-2.5 rounded-lg outline-none focus:border-blue-500" value={systemConfig.rebagScaleId || ""} onChange={e=>setSystemConfig({...systemConfig,rebagScaleId:e.target.value})} placeholder="Contoh: WT-01"/>
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-slate-600 mb-1.5">Kalibrasi Berlaku s.d.</label>
                        <input type="date" className="w-full border border-slate-300 bg-white p-2.5 rounded-lg outline-none focus:border-blue-500" value={systemConfig.rebagScaleCalibrationDue || ""} onChange={e=>setSystemConfig({...systemConfig,rebagScaleCalibrationDue:e.target.value})}/>
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-slate-600 mb-1.5">Nama Persetujuan / Kepala GBB</label>
                        <input className="w-full border border-slate-300 bg-white p-2.5 rounded-lg outline-none focus:border-blue-500" value={systemConfig.rebagApproverName || ""} onChange={e=>setSystemConfig({...systemConfig,rebagApproverName:e.target.value})} placeholder="Nama penandatangan"/>
                      </div>
                    </div>

                    <div className="rounded-xl border border-slate-200 bg-white p-3 text-xs leading-5 text-slate-600">
                      <span className="font-black text-slate-800">Acuan tetap pada PDF:</span> SNI ISO 22000:2018 + Amd1:2024; ISO 22002-1:2025; ISO 22002-100:2025; CPPOB - PerBPOM No. 22 Tahun 2021. Untuk produk gula, PDF juga mencantumkan SNI 3140.3:2010/Amd1:2011.
                    </div>
                  </div>

                  <button className="w-full sm:w-auto bg-slate-800 text-white font-bold px-6 py-3 rounded-lg hover:bg-slate-900 shadow-md">Simpan Perubahan Sistem</button>''';

rep(old,new,"system settings document controls")

path.write_text(s, encoding="utf-8")
print("ISO/SNI document control core patch applied.")
