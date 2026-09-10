from pathlib import Path

path = Path('src/App.jsx')
s = path.read_text(encoding='utf-8')

def rep(old, new, label, count=1):
    global s
    if old not in s:
        raise SystemExit(f'Patch target not found: {label}')
    for _ in range(count):
        s = s.replace(old, new, 1)

# 1) Operations tabs: add Mutasi Internal.
old = '''                      <button
                        onClick={()=>setActiveOpTab('outbound')}
                        className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all ${activeOpTab==='outbound'?'bg-orange-500 text-white shadow-lg shadow-orange-100':'text-slate-500 hover:bg-white hover:text-slate-800'}`}
                      >
                        <ArrowRightLeft size={17}/> Outbound
                      </button>'''
new = '''                      <button
                        onClick={()=>setActiveOpTab('internal_move')}
                        className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all ${activeOpTab==='internal_move'?'bg-cyan-600 text-white shadow-lg shadow-cyan-100':'text-slate-500 hover:bg-white hover:text-slate-800'}`}
                      >
                        <ArrowRightLeft size={17}/> Mutasi Internal
                      </button>
                      <button
                        onClick={()=>setActiveOpTab('outbound')}
                        className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all ${activeOpTab==='outbound'?'bg-orange-500 text-white shadow-lg shadow-orange-100':'text-slate-500 hover:bg-white hover:text-slate-800'}`}
                      >
                        <ArrowRightLeft size={17}/> Outbound
                      </button>'''
rep(old, new, 'internal move tab')

# 2) Backdate note includes internal move.
rep(
'''<div className="text-xs text-amber-700">Berlaku untuk Inbound, Rebagging, dan Outbound.</div>''',
'''<div className="text-xs text-amber-700">Berlaku untuk Inbound, Mutasi Internal, Rebagging, dan Outbound.</div>''',
'backdate note'
)

# 3) Inbound explanation.
rep(
'''Satu penerimaan dapat berisi beberapa SKU. Beras/Gula mempertahankan Gudang Administrasi asal, sementara lokasi fisiknya berada di Gudang Olah. Kemasan/kardus dicatat sebagai stok operasional Gudang Olah.''',
'''Satu penerimaan dapat berisi beberapa SKU. Gudang Administrasi dan Lokasi Fisik dicatat terpisah. Untuk kemasan/kardus, Gudang Administrasi otomatis mengikuti Lokasi Fisik yang dipilih.''',
'inbound location explanation'
)

# Replace inbound admin warehouse block with admin + physical-location selection.
old = '''                                <div>
                                  <label className="block text-sm font-bold text-slate-700 mb-2">Gudang Administrasi / Asal</label>
                                  {(() => {
                                    const selectedSku = skus.find((s) => s.id === line.skuId);
                                    const supportMaterial = isPackagingMaterialSku(selectedSku);
                                    return (
                                      <>
                                        <input
                                          type="text"
                                          className={`w-full p-3 border rounded-lg outline-none ${supportMaterial ? "border-cyan-200 bg-cyan-50 font-bold text-cyan-800" : "border-slate-300 focus:border-blue-500"}`}
                                          value={supportMaterial ? getProcessingLocation(systemConfig) : line.sourceWarehouse}
                                          onChange={e=>!supportMaterial && updateInboundLine(line.rowId,'sourceWarehouse',e.target.value)}
                                          placeholder="Contoh: GST I / Unit 18"
                                          readOnly={supportMaterial}
                                          required={!supportMaterial}
                                        />
                                        <p className="mt-1.5 text-[10px] leading-4 text-slate-400">
                                          {supportMaterial
                                            ? `Kemasan/kardus otomatis menjadi stok administrasi dan fisik ${getProcessingLocation(systemConfig)}.`
                                            : `Untuk Beras/Gula, gudang ini tetap menjadi pemilik stok administrasi. Lokasi fisik setelah diterima: ${getProcessingLocation(systemConfig)}.`}
                                        </p>
                                      </>
                                    );
                                  })()}
                                </div>'''
new = '''                                <div>
                                  <label className="block text-sm font-bold text-slate-700 mb-2">Gudang Administrasi / Asal</label>
                                  {(() => {
                                    const selectedSku = skus.find((s) => s.id === line.skuId);
                                    const supportMaterial = isPackagingMaterialSku(selectedSku);
                                    const selectedPhysical = locations.find((location)=>location.id===line.physicalLocationId);
                                    return (
                                      <>
                                        <input
                                          type="text"
                                          className={`w-full p-3 border rounded-lg outline-none ${supportMaterial ? "border-cyan-200 bg-cyan-50 font-bold text-cyan-800" : "border-slate-300 focus:border-blue-500"}`}
                                          value={supportMaterial ? (getLocationDisplayName(selectedPhysical) || "Pilih Lokasi Fisik") : line.sourceWarehouse}
                                          onChange={e=>!supportMaterial && updateInboundLine(line.rowId,'sourceWarehouse',e.target.value)}
                                          placeholder="Contoh: GST I / Unit 18"
                                          readOnly={supportMaterial}
                                          required={!supportMaterial}
                                        />
                                        <p className="mt-1.5 text-[10px] leading-4 text-slate-400">
                                          {supportMaterial
                                            ? "Kemasan/kardus tidak mewarisi Gudang Administrasi bahan utama. Nilainya mengikuti lokasi fisik stok kemasan."
                                            : "Gudang ini tetap menjadi pemilik stok secara administrasi meskipun barang dipindahkan ke lokasi proses."}
                                        </p>
                                      </>
                                    );
                                  })()}
                                </div>'''
rep(old, new, 'inbound admin warehouse dynamic')

# Add physical-location selector after qty/admin grid.
marker = '''                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                  <label className="block text-sm font-bold text-slate-700 mb-2">No. MO Bahan</label>'''
insert = '''                              <div>
                                <label className="block text-sm font-bold text-cyan-700 mb-2">Lokasi Fisik Saat Diterima</label>
                                <select
                                  className="w-full p-3 border border-cyan-300 bg-cyan-50/40 rounded-lg outline-none focus:border-cyan-600 font-bold text-cyan-900"
                                  value={line.physicalLocationId || ""}
                                  onChange={e=>updateInboundLine(line.rowId,'physicalLocationId',e.target.value)}
                                  required
                                >
                                  <option value="">-- Pilih Lokasi Fisik --</option>
                                  {locations.filter(location=>location.active!==false && locationSupportsStorage(location)).map(location=>(
                                    <option key={location.id} value={location.id}>
                                      {location.code || location.id} · {getLocationDisplayName(location)} · {location.type}
                                    </option>
                                  ))}
                                </select>
                                <p className="mt-1.5 text-[10px] leading-4 text-cyan-700">
                                  Ini adalah posisi fisik barang, terpisah dari Gudang Administrasi.
                                </p>
                              </div>

''' + marker
rep(marker, insert, 'inbound physical selector')

# 4) Rebag process + finished locations before quantity.
marker = '''                        <div>
                          <label className="block text-sm font-bold text-slate-700 mb-2">Kuantitas Hasil yang Diproses</label>'''
insert = '''                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-black text-red-700 mb-2">Lokasi Proses Rebagging</label>
                            <select
                              className="w-full p-3 border border-red-300 bg-red-50/30 rounded-lg outline-none focus:border-red-600 font-bold"
                              value={formData.rebagProcessingLocationId || ""}
                              onChange={e=>setFormData(prev=>({
                                ...prev,
                                rebagProcessingLocationId:e.target.value,
                                rebagFinishedLocationId: prev.rebagFinishedLocationId || e.target.value,
                              }))}
                              required
                            >
                              <option value="">-- Pilih Lokasi Proses --</option>
                              {locations
                                .filter(location=>locationSupportsRebag(location,selectedRebagTargetSku))
                                .map(location=>(
                                  <option key={location.id} value={location.id}>
                                    {location.code || location.id} · {getLocationDisplayName(location)} · {location.type}
                                  </option>
                                ))}
                            </select>
                            <p className="mt-1.5 text-[10px] text-slate-500">Bisa UP, RTR, GBB, atau Multi Purpose sesuai fungsi di Master Lokasi.</p>
                          </div>
                          <div>
                            <label className="block text-sm font-black text-cyan-700 mb-2">Lokasi Produk Jadi</label>
                            <select
                              className="w-full p-3 border border-cyan-300 bg-cyan-50/30 rounded-lg outline-none focus:border-cyan-600 font-bold"
                              value={formData.rebagFinishedLocationId || ""}
                              onChange={e=>setFormData(prev=>({...prev,rebagFinishedLocationId:e.target.value}))}
                              required
                            >
                              <option value="">-- Pilih Lokasi Produk Jadi --</option>
                              {locations.filter(location=>locationSupportsStorage(location)).map(location=>(
                                <option key={location.id} value={location.id}>
                                  {location.code || location.id} · {getLocationDisplayName(location)}
                                </option>
                              ))}
                            </select>
                            <p className="mt-1.5 text-[10px] text-slate-500">Default mengikuti lokasi proses, tetapi dapat dipilih lokasi penyimpanan lain.</p>
                          </div>
                        </div>

''' + marker
rep(marker, insert, 'rebag process and finished locations')

# Filter recipe batch options to chosen physical process location when set.
rep(
'''                                  b=>b.skuId===materialSkuId && Number(b.currentQty||0)>0 && isRawBatchQcUsable(b)
                                ),''',
'''                                  b=>{
                                    if (!(b.skuId===materialSkuId && Number(b.currentQty||0)>0 && isRawBatchQcUsable(b))) return false;
                                    if (!formData.rebagProcessingLocationId) return true;
                                    const processLocation=locations.find(location=>location.id===formData.rebagProcessingLocationId);
                                    if (!processLocation) return true;
                                    return b.physicalLocationId
                                      ? b.physicalLocationId===processLocation.id
                                      : getBatchPhysicalLocation(b,systemConfig).toUpperCase()===getLocationDisplayName(processLocation).toUpperCase();
                                  }
                                ),''',
'rebag recipe batch physical filter'
)

# Manual batch option filter to chosen process location.
rep(
'''                                    inventoryBatches.filter(b=>b.skuId===formData.bulkSkuId && Number(b.currentQty||0)>0 && isRawBatchQcUsable(b))
                                  ).map(b=>({''',
'''                                    inventoryBatches.filter(b=>{
                                      if (!(b.skuId===formData.bulkSkuId && Number(b.currentQty||0)>0 && isRawBatchQcUsable(b))) return false;
                                      if (!formData.rebagProcessingLocationId) return true;
                                      const processLocation=locations.find(location=>location.id===formData.rebagProcessingLocationId);
                                      if (!processLocation) return true;
                                      return b.physicalLocationId
                                        ? b.physicalLocationId===processLocation.id
                                        : getBatchPhysicalLocation(b,systemConfig).toUpperCase()===getLocationDisplayName(processLocation).toUpperCase();
                                    })
                                  ).map(b=>({''',
'rebag manual batch physical filter'
)

# Clarify batch dropdown location label.
rep(
'''[{label}] {b.sourceWarehouse||'-'} · MO: {b.moNumber||'-'} · TM: {b.tmNumber||'-'} · Stok: {b.currentQty}''',
'''[{label}] Fisik: {getBatchPhysicalLocation(b,systemConfig)||'-'} · Admin: {getBatchAdministrativeWarehouse(b,materialSku,systemConfig)||'-'} · MO: {b.moNumber||'-'} · TM: {b.tmNumber||'-'} · Stok: {b.currentQty}''',
'rebag recipe option location labels'
)

# 5) Internal Move form before outbound UI.
marker = '''                    {activeOpTab === 'outbound' && ('''
move_ui = r'''                    {activeOpTab === 'internal_move' && (
                      <div className="space-y-5">
                        <div className="rounded-2xl border border-cyan-200 bg-cyan-50/60 p-4">
                          <div className="flex items-start gap-3">
                            <ArrowRightLeft size={20} className="mt-0.5 shrink-0 text-cyan-700"/>
                            <div>
                              <h3 className="font-black text-cyan-900">Mutasi Internal Lokasi Fisik</h3>
                              <p className="mt-1 text-xs leading-5 text-cyan-700">
                                Memindahkan posisi fisik stok tanpa mengubah Gudang Administrasi, MO, TM, atau identitas asal. Mutasi parsial otomatis membentuk batch lokasi turunan agar saldo per lokasi tetap akurat.
                              </p>
                            </div>
                          </div>
                        </div>

                        <div>
                          <label className="block text-sm font-bold text-slate-700 mb-2">Batch Sumber</label>
                          <select
                            className="w-full p-3 border border-slate-300 rounded-lg bg-white outline-none focus:border-cyan-600"
                            value={internalMoveForm.batchId}
                            onChange={e=>setInternalMoveForm(prev=>({...prev,batchId:e.target.value,qty:""}))}
                            required
                          >
                            <option value="">-- Pilih Batch Stok Aktif --</option>
                            {sortBatchesFefoFifo(inventoryBatches.filter(batch=>Number(batch.currentQty||0)>0)).map(batch=>{
                              const sku=skus.find(item=>item.id===batch.skuId);
                              return (
                                <option key={batch.batchId} value={batch.batchId}>
                                  {batch.batchId} · {sku?.name||batch.skuId} · {getBatchPhysicalLocation(batch,systemConfig)} · Stok {batch.currentQty} {sku?.unit||''}
                                </option>
                              );
                            })}
                          </select>
                        </div>

                        {internalMoveForm.batchId && (()=>{
                          const batch=inventoryBatches.find(item=>item.batchId===internalMoveForm.batchId);
                          const sku=skus.find(item=>item.id===batch?.skuId);
                          return batch ? (
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs">
                              <div><span className="font-black text-slate-400">Gudang Administrasi</span><div className="mt-1 font-bold text-slate-800">{batch.administrativeWarehouse||(batch.administrativeWarehouses||[]).join(', ')||getBatchAdministrativeWarehouse(batch,sku,systemConfig)||'-'}</div></div>
                              <div><span className="font-black text-slate-400">Lokasi Fisik Saat Ini</span><div className="mt-1 font-black text-cyan-700">{getBatchPhysicalLocation(batch,systemConfig)||'-'}</div></div>
                              <div><span className="font-black text-slate-400">MO / TM</span><div className="mt-1 font-bold text-slate-800">{batch.mainMoNumber||batch.moNumber||'-'} / {batch.resultTmNumber||batch.tmNumber||'-'}</div></div>
                            </div>
                          ) : null;
                        })()}

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-bold text-slate-700 mb-2">Qty Dipindahkan</label>
                            <input
                              type="number"
                              min="0"
                              max={inventoryBatches.find(batch=>batch.batchId===internalMoveForm.batchId)?.currentQty||undefined}
                              className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-cyan-600"
                              value={internalMoveForm.qty}
                              onChange={e=>setInternalMoveForm(prev=>({...prev,qty:e.target.value}))}
                              placeholder="0"
                              required
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-bold text-cyan-700 mb-2">Lokasi Fisik Tujuan</label>
                            <select
                              className="w-full p-3 border border-cyan-300 bg-cyan-50/40 rounded-lg outline-none focus:border-cyan-600 font-bold"
                              value={internalMoveForm.destinationLocationId}
                              onChange={e=>setInternalMoveForm(prev=>({...prev,destinationLocationId:e.target.value}))}
                              required
                            >
                              <option value="">-- Pilih Lokasi Tujuan --</option>
                              {locations.filter(location=>locationSupportsStorage(location)).map(location=>(
                                <option key={location.id} value={location.id}>{location.code||location.id} · {getLocationDisplayName(location)}</option>
                              ))}
                            </select>
                          </div>
                        </div>

                        <div>
                          <label className="block text-sm font-bold text-slate-700 mb-2">Alasan Mutasi</label>
                          <input
                            className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-cyan-600"
                            value={internalMoveForm.reason}
                            onChange={e=>setInternalMoveForm(prev=>({...prev,reason:e.target.value}))}
                            placeholder="Contoh: Dipindahkan ke UP 17 untuk proses Rebagging Gula"
                            required
                          />
                        </div>
                      </div>
                    )}

''' + marker
rep(marker, move_ui, 'internal move form')

# 6) Settings tab: Master Lokasi.
marker = '''                  <button
                    onClick={()=>setActiveTabSettings('recipes')}'''
locations_button = '''                  <button
                    onClick={()=>setActiveTabSettings('locations')}
                    className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all ${activeTabSettings==='locations'?'bg-slate-900 text-white shadow-lg':'text-slate-500 hover:bg-white hover:text-slate-800'}`}
                  >
                    <Home size={17}/> Master Lokasi
                  </button>
''' + marker
rep(marker, locations_button, 'master locations settings tab')

# Remove old single global processing location UI.
old = '''                  <div>
                    <label className="block font-bold text-slate-700 mb-2">Lokasi Fisik Gudang Olah</label>
                    <input
                      className="w-full border border-slate-300 p-3 rounded-lg outline-none focus:border-red-500"
                      value={systemConfig.processingLocation || "Unit Pengolahan 20"}
                      onChange={e=>setSystemConfig({...systemConfig,processingLocation:e.target.value})}
                      placeholder="Contoh: Unit Pengolahan 20"
                    />
                    <p className="mt-1.5 text-xs leading-5 text-slate-500">
                      Digunakan sebagai lokasi fisik bahan saat proses dan produk jadi. Gudang Administrasi tetap disimpan terpisah.
                    </p>
                  </div>

'''
rep(old, '', 'remove global processing location setting')

# Insert Master Lokasi UI before system form.
marker = '''              {activeTabSettings === 'system' && ('''
locations_ui = r'''              {activeTabSettings === 'locations' && (
                <div className="space-y-5">
                  <div className="rounded-2xl border border-blue-200 bg-blue-50/60 p-4">
                    <h3 className="font-black text-blue-900">Master Lokasi Fisik</h3>
                    <p className="mt-1 text-xs leading-5 text-blue-700">
                      Atur seluruh UP, RTR, GBB, dan Gudang Multi Purpose yang dapat menjadi lokasi penyimpanan maupun proses Rebagging. UP 17, UP 20, RTR 60, dan Multi Purpose disediakan sebagai data awal. Tambahkan 8 GBB sesuai nama/kode resmi gudang Anda.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
                    <form onSubmit={handleSaveLocation} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
                      <div><div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">{locationForm.id?'Edit Lokasi':'Lokasi Baru'}</div><h3 className="mt-1 font-black text-slate-900">Data Lokasi</h3></div>
                      <div><label className="block text-xs font-bold text-slate-600 mb-1.5">Kode Lokasi</label><input className="w-full rounded-lg border border-slate-300 p-3 outline-none focus:border-blue-500" value={locationForm.code} onChange={e=>setLocationForm({...locationForm,code:e.target.value})} placeholder="Contoh: GBB-01" required disabled={Boolean(locationForm.id)}/></div>
                      <div><label className="block text-xs font-bold text-slate-600 mb-1.5">Nama Lokasi</label><input className="w-full rounded-lg border border-slate-300 p-3 outline-none focus:border-blue-500" value={locationForm.name} onChange={e=>setLocationForm({...locationForm,name:e.target.value})} placeholder="Nama resmi gudang/lokasi" required/></div>
                      <div><label className="block text-xs font-bold text-slate-600 mb-1.5">Tipe Lokasi</label><select className="w-full rounded-lg border border-slate-300 bg-white p-3" value={locationForm.type} onChange={e=>setLocationForm({...locationForm,type:e.target.value})}><option value="UP">UP</option><option value="GBB">GBB</option><option value="RTR">RTR</option><option value="MULTI_PURPOSE">Multi Purpose</option></select></div>
                      <div>
                        <label className="block text-xs font-bold text-slate-600 mb-2">Fungsi Lokasi</label>
                        <div className="space-y-2">
                          {[["STORAGE","Penyimpanan"],["REBAG_GULA","Rebag Gula"],["REBAG_BERAS","Rebag Beras"]].map(([id,label])=>(
                            <label key={id} className="flex items-center gap-2 rounded-lg border border-slate-200 p-2.5 cursor-pointer"><input type="checkbox" className="h-4 w-4" checked={(locationForm.functions||[]).includes(id)} onChange={()=>handleLocationFunctionToggle(id)}/><span className="text-xs font-bold text-slate-700">{label}</span></label>
                          ))}
                        </div>
                      </div>
                      <label className="flex items-center gap-2"><input type="checkbox" checked={locationForm.active!==false} onChange={e=>setLocationForm({...locationForm,active:e.target.checked})}/><span className="text-xs font-bold text-slate-700">Lokasi Aktif</span></label>
                      <div className="flex gap-2"><button type="submit" className="flex-1 rounded-lg bg-slate-900 px-4 py-3 text-xs font-black text-white hover:bg-slate-800">{locationForm.id?'Simpan Perubahan':'Tambah Lokasi'}</button>{locationForm.id&&<button type="button" onClick={resetLocationForm} className="rounded-lg border border-slate-200 px-4 py-3 text-xs font-black text-slate-600">Batal</button>}</div>
                    </form>

                    <div className="xl:col-span-2 rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
                      <div className="border-b border-slate-200 p-4"><h3 className="font-black text-slate-900">Daftar Lokasi</h3><p className="mt-1 text-xs text-slate-500">Lokasi nonaktif tidak muncul pada transaksi baru, tetapi riwayat lama tetap tersimpan.</p></div>
                      <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-sm"><thead className="bg-slate-50 text-slate-500"><tr><th className="p-3 text-left">Kode / Nama</th><th className="p-3 text-left">Tipe</th><th className="p-3 text-left">Fungsi</th><th className="p-3 text-center">Status</th><th className="p-3 text-center">Aksi</th></tr></thead><tbody className="divide-y divide-slate-100">{locations.map(location=>(<tr key={location.id}><td className="p-3"><div className="font-mono text-xs font-black text-blue-700">{location.code||location.id}</div><div className="mt-1 font-bold text-slate-900">{getLocationDisplayName(location)}</div></td><td className="p-3 font-bold text-slate-600">{location.type}</td><td className="p-3"><div className="flex flex-wrap gap-1">{(location.functions||[]).map(fn=><span key={fn} className="rounded-full bg-slate-100 px-2 py-1 text-[9px] font-black text-slate-600">{fn}</span>)}</div></td><td className="p-3 text-center"><span className={`rounded-full px-2 py-1 text-[10px] font-black ${location.active!==false?'bg-emerald-100 text-emerald-700':'bg-slate-100 text-slate-500'}`}>{location.active!==false?'AKTIF':'NONAKTIF'}</span></td><td className="p-3 text-center"><div className="inline-flex gap-1"><button type="button" onClick={()=>handleEditLocation(location)} className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-[10px] font-black text-blue-700">Edit</button><button type="button" onClick={()=>handleDeleteLocation(location)} className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[10px] font-black text-red-700">Hapus</button></div></td></tr>))}</tbody></table></div>
                    </div>
                  </div>
                </div>
              )}

''' + marker
rep(marker, locations_ui, 'master locations settings UI')

# 7) History: INTERNAL_MOVE badge and details.
rep(
'''${t.type === 'INBOUND' ? 'bg-blue-100 text-blue-700' : t.type === 'OUTBOUND' ? 'bg-orange-100 text-orange-700' : t.type === 'MATERIAL_DAMAGE' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}''',
'''${t.type === 'INBOUND' ? 'bg-blue-100 text-blue-700' : t.type === 'OUTBOUND' ? 'bg-orange-100 text-orange-700' : t.type === 'INTERNAL_MOVE' ? 'bg-cyan-100 text-cyan-700' : t.type === 'MATERIAL_DAMAGE' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}''',
'history internal move badge'
)
rep(
'''                          {t.type === 'MATERIAL_DAMAGE' ? (
                            <div>''',
'''                          {t.type === 'INTERNAL_MOVE' ? (
                            <div>
                              <div className="text-cyan-700">{t.qtyChange} {t.unit}</div>
                              <div className="mt-1 text-[10px] font-bold text-cyan-600">{t.fromPhysicalLocation || '-'} → {t.toPhysicalLocation || '-'}</div>
                            </div>
                          ) : t.type === 'MATERIAL_DAMAGE' ? (
                            <div>''',
'history internal move detail'
)

path.write_text(s, encoding='utf-8')
print('Location model UI patch applied.')
