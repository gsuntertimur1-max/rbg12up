from pathlib import Path

p = Path('src/App.jsx')
s = p.read_text(encoding='utf-8')

def rep(old, new, label, count=1):
    global s
    if old not in s:
        raise SystemExit(f'Patch target not found: {label}')
    for _ in range(count):
        s = s.replace(old, new, 1)

# 1) Default operator process-deviation state.
rep(
'''    rebagCoaNumber: "", rebagQualityStatus: "MENUNGGU",
    rebagDeviation: "", rebagCorrectiveAction: "",''',
'''    rebagCoaNumber: "", rebagQualityStatus: "TIDAK_ADA_PENYIMPANGAN",
    rebagDeviation: "", rebagCorrectiveAction: "",''',
'initial process deviation state'
)

# 2) No./Kode Tumpukan is optional; Exp Date remains mandatory.
rep(
'''        if (!formData.rebagExpiryDate) return alert("Tanggal kedaluwarsa wajib diisi.");
        if (!formData.rebagTargetStack) return alert("Pilih lokasi tumpukan tujuan.");''',
'''        if (!formData.rebagExpiryDate) return alert("Tanggal kedaluwarsa wajib diisi.");''',
'optional finished stack validation'
)

# 3) Operator records process deviations, not a final quality decision.
old = '''        const qualityStatus = formData.rebagQualityStatus || "MENUNGGU";
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
        };'''
new = '''        const processDeviationStatus =
          formData.rebagQualityStatus === "ADA_PENYIMPANGAN"
            ? "ADA_PENYIMPANGAN"
            : "TIDAK_ADA_PENYIMPANGAN";
        const hasProcessDeviation = processDeviationStatus === "ADA_PENYIMPANGAN";
        const deviation = String(formData.rebagDeviation || "").trim();
        const correctiveAction = String(formData.rebagCorrectiveAction || "").trim();

        if (hasProcessDeviation && (!deviation || !correctiveAction)) {
          return alert(
            "Jika ada penyimpangan proses, Kejadian/Penyimpangan dan Tindakan yang Dilakukan wajib diisi."
          );
        }

        const processDeviationSnapshot = {
          status: processDeviationStatus,
          hasDeviation: hasProcessDeviation,
          description: hasProcessDeviation ? deviation : "",
          actionTaken: hasProcessDeviation ? correctiveAction : "",
          recordedAt,
          recordedBy: currentUser.username,
        };

        // Legacy qualityControl fields are retained so old PDFs/history stay readable.
        // Final quality approval remains the responsibility of QC Produk Jadi.
        const qualityControlSnapshot = {
          coaNumber: String(formData.rebagCoaNumber || "").trim(),
          qualityStatus: "MENUNGGU_QC",
          deviation: processDeviationSnapshot.description,
          correctiveAction: processDeviationSnapshot.actionTaken,
          effectiveness: "",
          processDeviation: processDeviationSnapshot,
        };'''
rep(old, new, 'process deviation validation and snapshot')

# Explicit new field on batch and transaction, while keeping old snapshot compatible.
rep(
'''            documentControl: documentControlSnapshot,
            qualityControl: qualityControlSnapshot,
            moNumber:''',
'''            documentControl: documentControlSnapshot,
            qualityControl: qualityControlSnapshot,
            processDeviation: processDeviationSnapshot,
            moNumber:''',
'finished batch process deviation'
)
rep(
'''              documentControl: documentControlSnapshot,
              qualityControl: qualityControlSnapshot,
              ...auditMeta,''',
'''              documentControl: documentControlSnapshot,
              qualityControl: qualityControlSnapshot,
              processDeviation: processDeviationSnapshot,
              ...auditMeta,''',
'rebag transaction process deviation'
)

# 4) Operator UI: replace Status Mutu with Penyimpangan Proses.
old = '''                            <div>
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
                            </div>'''
new = '''                            <div>
                              <label className="block text-xs font-bold text-slate-600 mb-1.5">Penyimpangan Proses</label>
                              <select
                                className="w-full rounded-lg border border-slate-300 bg-white p-3 outline-none focus:border-blue-500 font-bold"
                                value={formData.rebagQualityStatus}
                                onChange={e=>setFormData({
                                  ...formData,
                                  rebagQualityStatus:e.target.value,
                                  ...(e.target.value === "TIDAK_ADA_PENYIMPANGAN"
                                    ? { rebagDeviation:"", rebagCorrectiveAction:"" }
                                    : {})
                                })}
                              >
                                <option value="TIDAK_ADA_PENYIMPANGAN">TIDAK ADA PENYIMPANGAN</option>
                                <option value="ADA_PENYIMPANGAN">ADA PENYIMPANGAN</option>
                              </select>
                              <p className="mt-1.5 text-[10px] leading-4 text-slate-500">
                                Operator hanya mencatat kejadian selama proses. Keputusan mutu akhir tetap dilakukan pada QC Produk Jadi.
                              </p>
                            </div>'''
rep(old, new, 'operator process deviation selector')

old = '''                          <div>
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
                          </div>'''
new = '''                          {formData.rebagQualityStatus === "ADA_PENYIMPANGAN" && (
                            <>
                              <div>
                                <label className="block text-xs font-bold text-red-600 mb-1.5">Kejadian / Penyimpangan Proses</label>
                                <textarea
                                  rows="2"
                                  className="w-full rounded-lg border border-red-200 bg-red-50/40 p-3 outline-none focus:border-red-500 resize-y"
                                  value={formData.rebagDeviation}
                                  onChange={e=>setFormData({...formData,rebagDeviation:e.target.value})}
                                  placeholder="Jelaskan kejadian/penyimpangan yang terjadi saat proses."
                                  required
                                />
                              </div>

                              <div>
                                <label className="block text-xs font-bold text-amber-700 mb-1.5">Tindakan yang Dilakukan</label>
                                <textarea
                                  rows="2"
                                  className="w-full rounded-lg border border-amber-200 bg-amber-50/40 p-3 outline-none focus:border-amber-500 resize-y"
                                  value={formData.rebagCorrectiveAction}
                                  onChange={e=>setFormData({...formData,rebagCorrectiveAction:e.target.value})}
                                  placeholder="Jelaskan tindakan langsung yang dilakukan operator."
                                  required
                                />
                              </div>
                            </>
                          )}'''
rep(old, new, 'conditional process deviation fields')

# 5) Tumpukan is a specific optional position inside the already selected finished location.
old = '''                          <div>
                            <label className="block text-sm font-bold text-slate-700 mb-2">Tumpukan Tujuan</label>
                            <select className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-red-500 bg-white" value={formData.rebagTargetStack} onChange={e=>setFormData({...formData,rebagTargetStack:e.target.value})} required>
                              <option value="">-- Pilih Lokasi Tumpukan --</option>
                              {STACK_LOCATIONS.map(l=><option key={l} value={l}>{l}</option>)}
                            </select>
                          </div>'''
new = '''                          {formData.rebagFinishedLocationId && (
                            <div>
                              <label className="block text-sm font-bold text-slate-700 mb-2">No./Kode Tumpukan Produk Jadi <span className="font-normal text-slate-400">(Opsional)</span></label>
                              <input
                                type="text"
                                className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-red-500 bg-white"
                                value={formData.rebagTargetStack}
                                onChange={e=>setFormData({...formData,rebagTargetStack:e.target.value})}
                                placeholder="Contoh: Tumpukan A01 / Blok 3"
                              />
                              <p className="mt-1.5 text-[10px] leading-4 text-slate-500">
                                Posisi spesifik di dalam Lokasi Produk Jadi yang sudah dipilih. Kosongkan bila lokasi tersebut tidak memakai kode tumpukan.
                              </p>
                            </div>
                          )}'''
rep(old, new, 'optional specific finished stack')

# 6) Rebag PDF terminology follows the new operator responsibility.
rep(
'''    "Status mutu: " +
      (qualityControl.qualityStatus || "SESUAI [ ]  TIDAK SESUAI [ ]  MENUNGGU [ ]"),''',
'''    "Penyimpangan proses: " +
      (qualityControl.processDeviation?.hasDeviation || qualityControl.deviation
        ? "ADA"
        : "TIDAK ADA"),''',
'PDF process deviation status'
)
rep(
'''"Penyimpangan / ketidaksesuaian:"''',
'''"Kejadian / penyimpangan proses:"''',
'PDF deviation label'
)
rep(
'''"Tindakan koreksi / disposisi:"''',
'''"Tindakan yang dilakukan:"''',
'PDF action label'
)

# Finished-goods stock card also treats stack as a code/position, not the warehouse itself.
rep(
'''["Lokasi Tumpukan", batchMeta.targetStack || ""],''',
'''["No./Kode Tumpukan", batchMeta.targetStack || "-"],''',
'finished stock card stack label'
)

p.write_text(s, encoding='utf-8')
print('operator deviation + optional stack patch applied')
