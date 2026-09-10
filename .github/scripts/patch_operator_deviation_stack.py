from pathlib import Path

p = Path('src/App.jsx')
s = p.read_text(encoding='utf-8')

def rep(old, new, label, count=1):
    global s
    if old not in s:
        raise SystemExit(f'Patch target not found: {label}')
    for _ in range(count):
        s = s.replace(old, new, 1)

# 1. Default operator process-deviation state.
rep(
'''    rebagCoaNumber: "", rebagQualityStatus: "MENUNGGU",
    rebagDeviation: "", rebagCorrectiveAction: "",''',
'''    rebagCoaNumber: "", rebagQualityStatus: "TIDAK_ADA_PENYIMPANGAN",
    rebagDeviation: "", rebagCorrectiveAction: "",''',
'initial process deviation state'
)

# 2. Validation + snapshots: operator records process deviations, not final quality decisions.
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

        // Dipertahankan untuk kompatibilitas PDF/riwayat lama. Keputusan mutu akhir tetap di QC Produk Jadi.
        const qualityControlSnapshot = {
          coaNumber: String(formData.rebagCoaNumber || "").trim(),
          qualityStatus: "MENUNGGU_QC",
          deviation: processDeviationSnapshot.description,
          correctiveAction: processDeviationSnapshot.actionTaken,
          effectiveness: "",
          processDeviation: processDeviationSnapshot,
        };'''
rep(old, new, 'process deviation validation and snapshot')

# Store explicit processDeviation on finished batch + rebagging transaction.
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
'rebag tx process deviation'
)

# 3. Operator UI: change quality language into process deviation recording.
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

# Replace always-visible deviation/action fields with conditional fields.
old = '''                          <div>
                            <label className="block text-xs font-bold text-slate-600 mb-1.5">Penyimpangan / Ketidaksesuaian</label>
                            <textarea
                              rows="2"
                              className="w-full rounded-lg border border-slate-300 bg-white p-3 outline-none focus:border-blue-500 resize-y"
                              value={formData.rebagDeviation}
                              onChange={e=>setFormData({...formData,rebagDeviation:e.target.value})}'''
new = '''                          {formData.rebagQualityStatus === "ADA_PENYIMPANGAN" && (
                            <div>
                              <label className="block text-xs font-bold text-red-600 mb-1.5">Kejadian / Penyimpangan Proses</label>
                              <textarea
                                rows="2"
                                className="w-full rounded-lg border border-red-200 bg-red-50/40 p-3 outline-none focus:border-red-500 resize-y"
                                value={formData.rebagDeviation}
                                onChange={e=>setFormData({...formData,rebagDeviation:e.target.value})}'''
rep(old, new, 'conditional deviation field opening')

# The original two fields sit consecutively; rename action and close conditional after the second field.
rep(
'''                            <label className="block text-xs font-bold text-slate-600 mb-1.5">Tindakan Koreksi</label>''',
'''                            <label className="block text-xs font-bold text-amber-700 mb-1.5">Tindakan yang Dilakukan</label>''',
'operator action label'
)

# Find the first corrective-action textarea closing block after operator form and wrap closing conditional.
needle = '''                              value={formData.rebagCorrectiveAction}
                              onChange={e=>setFormData({...formData,rebagCorrectiveAction:e.target.value})}
'''
pos = s.find(needle)
if pos < 0:
    raise SystemExit('Patch target not found: corrective action textarea')
close = s.find('''                            </div>''', pos)
if close < 0:
    raise SystemExit('Patch target not found: corrective action closing div')
close_end = close + len('''                            </div>''')
s = s[:close_end] + '''
                          )}''' + s[close_end:]

# 4. Tumpukan = optional specific position, not duplicate warehouse/location.
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
                                Hanya untuk posisi spesifik di dalam Lokasi Produk Jadi. Kosongkan bila lokasi tersebut tidak menggunakan kode tumpukan.
                              </p>
                            </div>
                          )}'''
rep(old, new, 'optional specific finished stack')

# 5. Rebag PDF terminology: operator deviation is not final QC decision.
rep(
'''    "Status mutu: " +
      (qualityControl.qualityStatus || "SESUAI [ ]  TIDAK SESUAI [ ]  MENUNGGU [ ]"),''',
'''    "Penyimpangan proses: " +
      (qualityControl.processDeviation?.hasDeviation || qualityControl.deviation
        ? "ADA"
        : "TIDAK ADA"),''',
'PDF process deviation status'
)
rep('''"Penyimpangan / ketidaksesuaian:"''','''"Kejadian / penyimpangan proses:"''','PDF deviation label')
rep('''"Tindakan koreksi:"''','''"Tindakan yang dilakukan:"''','PDF action label')

# 6. Stock card terminology for finished goods.
rep(
'''["Lokasi Tumpukan", batchMeta.targetStack || ""],''',
'''["No./Kode Tumpukan", batchMeta.targetStack || "-"],''',
'finished stock card stack label'
)

p.write_text(s, encoding='utf-8')
print('operator deviation + optional stack patch applied')
