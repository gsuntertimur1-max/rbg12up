from pathlib import Path

path = Path("src/App.jsx")
s = path.read_text(encoding="utf-8")

def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"Patch target not found: {label}")
    s = s.replace(old, new, 1)

rep(
'''    rebagGoodQty: "", rebagProcessQty: "0", rebagDamageQty: "0",
    rebagResultTmNumber: "", rebagExpiryDate: getDefaultExpiryDate(),
    outSkuId: "", outTmNumber: "", outSoNumber: "", outCustomer: "",''',
'''    rebagGoodQty: "", rebagProcessQty: "0", rebagDamageQty: "0",
    rebagResultTmNumber: "", rebagExpiryDate: getDefaultExpiryDate(),
    rebagCoaNumber: "", rebagQualityStatus: "MENUNGGU",
    rebagDeviation: "", rebagCorrectiveAction: "",
    outSkuId: "", outTmNumber: "", outSoNumber: "", outCustomer: "",''',
"quality form defaults")

# Validate and capture quality record with the document snapshot.
rep(
'''        const documentControlSnapshot = {
          code: systemConfig.rebagDocumentCode || "",''',
'''        const qualityStatus = formData.rebagQualityStatus || "MENUNGGU";
        const deviation = String(formData.rebagDeviation || "").trim();
        const correctiveAction = String(formData.rebagCorrectiveAction || "").trim();

        if (
          qualityStatus === "TIDAK SESUAI" &&
          (!deviation || !correctiveAction)
        ) {
          return alert(
            "Jika status mutu TIDAK SESUAI, Penyimpangan dan Tindakan Koreksi wajib diisi."
          );
        }

        const qualityControlSnapshot = {
          coaNumber: String(formData.rebagCoaNumber || "").trim(),
          qualityStatus,
          deviation,
          correctiveAction,
          effectiveness: "",
        };

        const documentControlSnapshot = {
          code: systemConfig.rebagDocumentCode || "",''',
"quality snapshot validation")

rep(
'''            documentControl: documentControlSnapshot,
            moNumber: sourceMoNumbers.join(", "),''',
'''            documentControl: documentControlSnapshot,
            qualityControl: qualityControlSnapshot,
            moNumber: sourceMoNumbers.join(", "),''',
"finished batch quality snapshot")

rep(
'''              documentControl: documentControlSnapshot,
              ...auditMeta,''',
'''              documentControl: documentControlSnapshot,
              qualityControl: qualityControlSnapshot,
              ...auditMeta,''',
"transaction quality snapshot")

# Add quality record UI after reconciliation and before expiry/stack.
marker='''                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-bold text-slate-700 mb-2">Tanggal Kadaluwarsa</label>''';

insert='''                        <div className="rounded-2xl border border-blue-200 bg-blue-50/50 p-4 sm:p-5 space-y-4">
                          <div>
                            <div className="text-xs font-black uppercase tracking-[0.14em] text-blue-600">Mutu & Ketidaksesuaian</div>
                            <h4 className="mt-1 font-black text-slate-900">Catatan COA / Hasil Uji</h4>
                            <p className="mt-1 text-xs leading-5 text-slate-600">
                              Untuk produk gula, bukti kesesuaian SNI tetap menggunakan COA/hasil uji yang berlaku. Form produksi tidak menggantikan pengujian laboratorium.
                            </p>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <div>
                              <label className="block text-xs font-bold text-slate-600 mb-1.5">No. COA / Hasil Uji (Opsional)</label>
                              <input
                                className="w-full rounded-lg border border-slate-300 bg-white p-3 outline-none focus:border-blue-500"
                                value={formData.rebagCoaNumber}
                                onChange={e=>setFormData({...formData,rebagCoaNumber:e.target.value})}
                                placeholder="Nomor COA / laporan hasil uji"
                              />
                            </div>
                            <div>
                              <label className="block text-xs font-bold text-slate-600 mb-1.5">Status Mutu</label>
                              <select
                                className="w-full rounded-lg border border-slate-300 bg-white p-3 outline-none focus:border-blue-500 font-bold"
                                value={formData.rebagQualityStatus}
                                onChange={e=>setFormData({...formData,rebagQualityStatus:e.target.value})}
                              >
                                <option value="MENUNGGU">MENUNGGU VERIFIKASI</option>
                                <option value="SESUAI">SESUAI</option>
                                <option value="TIDAK SESUAI">TIDAK SESUAI</option>
                              </select>
                            </div>
                          </div>

                          <div>
                            <label className="block text-xs font-bold text-slate-600 mb-1.5">Penyimpangan / Ketidaksesuaian</label>
                            <textarea
                              rows="2"
                              className="w-full rounded-lg border border-slate-300 bg-white p-3 outline-none focus:border-blue-500 resize-y"
                              value={formData.rebagDeviation}
                              onChange={e=>setFormData({...formData,rebagDeviation:e.target.value})}
                              placeholder="Kosongkan bila tidak ada penyimpangan."
                            />
                          </div>

                          <div>
                            <label className="block text-xs font-bold text-slate-600 mb-1.5">Tindakan Koreksi / Disposisi</label>
                            <textarea
                              rows="2"
                              className="w-full rounded-lg border border-slate-300 bg-white p-3 outline-none focus:border-blue-500 resize-y"
                              value={formData.rebagCorrectiveAction}
                              onChange={e=>setFormData({...formData,rebagCorrectiveAction:e.target.value})}
                              placeholder="Wajib diisi bila Status Mutu = TIDAK SESUAI."
                            />
                          </div>
                        </div>

''';

if marker not in s:
    raise SystemExit("Quality UI insertion marker not found")
s = s.replace(marker, insert + marker, 1)

path.write_text(s, encoding="utf-8")
print("ISO/SNI quality record integration applied.")
