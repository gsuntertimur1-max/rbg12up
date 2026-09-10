from pathlib import Path

path = Path('src/App.jsx')
s = path.read_text(encoding='utf-8')

def rep(old, new, label, count=1):
    global s
    if old not in s:
        raise SystemExit(f'Patch target not found: {label}')
    for _ in range(count):
        s = s.replace(old, new, 1)

# 1) Inbound terminology + physical-location explanation.
rep(
'''                                  <label className="block text-sm font-bold text-slate-700 mb-2">Gudang Asal</label>''',
'''                                  <label className="block text-sm font-bold text-slate-700 mb-2">Gudang Administrasi / Asal</label>''',
'inbound admin warehouse label'
)
rep(
'''                                    placeholder="Contoh: GST I / Gudang asal lain"
                                    required
                                  />
                                </div>''',
'''                                    placeholder="Contoh: GST I / Unit 18"
                                    required
                                  />
                                  <p className="mt-1.5 text-[10px] leading-4 text-slate-400">
                                    Untuk Beras/Gula, gudang ini tetap menjadi pemilik stok secara administrasi. Lokasi fisik setelah diterima: {getProcessingLocation(systemConfig)}.
                                  </p>
                                </div>''',
'inbound physical note'
)
rep(
'''                                Satu penerimaan dapat berisi beberapa SKU. Setiap SKU menyimpan batch, MO, TM bahan, qty, dan gudang asalnya sendiri.''',
'''                                Satu penerimaan dapat berisi beberapa SKU. Beras/Gula mempertahankan Gudang Administrasi asal, sementara lokasi fisiknya berada di Gudang Olah. Kemasan/kardus dicatat sebagai stok operasional Gudang Olah.''',
'inbound info semantics'
)

# 2) Rebag operator no longer sees editable TM Hasil.
old_tm = '''                        <div className="rounded-2xl border border-green-200 bg-green-50/60 p-4">
                          <label className="block text-sm font-black text-green-900 mb-2">TM Hasil</label>
                          <input
                            type="text"
                            className="w-full p-3 border border-green-300 rounded-lg bg-white outline-none focus:border-green-600 font-bold text-green-900"
                            value={formData.rebagResultTmNumber}
                            onChange={e=>setFormData({...formData,rebagResultTmNumber:e.target.value})}
                            placeholder="Masukkan TM hasil produksi"
                            required
                          />
                          <div className="mt-2 space-y-1 text-xs text-green-700">
                            <p>TM Hasil boleh digunakan kembali selama tetap terikat pada MO Utama yang sama.</p>
                            <p className="font-bold">Batch otomatis: {formData.rebagTargetSkuId || 'SKU'}-{getProductionDateCode(formData.useBackdate && formData.backdateDateTime ? new Date(formData.backdateDateTime) : new Date()) || 'YYMMDD'}-NN</p>
                          </div>
                        </div>'''
new_tm = '''                        <div className="rounded-2xl border border-violet-200 bg-violet-50/60 p-4">
                          <div className="flex items-start gap-3">
                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-100 text-violet-700">
                              <ClipboardList size={18}/>
                            </div>
                            <div>
                              <div className="text-sm font-black text-violet-900">TM Hasil diisi pada QC Produk Jadi</div>
                              <p className="mt-1 text-xs leading-5 text-violet-700">
                                Operator tidak perlu mengisi TM Hasil. Setelah produksi tersimpan, QC/Admin mengisi TM Hasil sebagai data administrasi sebelum status RELEASE.
                              </p>
                              <p className="mt-2 text-xs font-black text-violet-800">
                                Batch otomatis: {formData.rebagTargetSkuId || 'SKU'}-{getProductionDateCode(formData.useBackdate && formData.backdateDateTime ? new Date(formData.backdateDateTime) : new Date()) || 'YYMMDD'}-NN
                              </p>
                            </div>
                          </div>
                        </div>'''
rep(old_tm, new_tm, 'replace operator TM input')

# Clarify material source labels on Rebagging.
rep(
'''                                              <span className="rounded-lg bg-slate-100 px-2.5 py-1.5 font-bold text-slate-600">Gudang: {selectedBatch.sourceWarehouse||'-'}</span>''',
'''                                              <span className="rounded-lg bg-slate-100 px-2.5 py-1.5 font-bold text-slate-600">Admin: {getBatchAdministrativeWarehouse(selectedBatch, materialSku, systemConfig)||'-'}</span>
                                              <span className="rounded-lg bg-cyan-50 px-2.5 py-1.5 font-bold text-cyan-700">Fisik: {getBatchPhysicalLocation(selectedBatch, systemConfig)||'-'}</span>''',
'rebag selected batch admin physical'
)

# 3) QC batch selection prefills existing TM, if any.
rep(
'''value={qcForm.batchId} onChange={e=>setQcForm({...qcForm,batchId:e.target.value})} required>''',
'''value={qcForm.batchId} onChange={e=>{const selected=inventoryBatches.find(batch=>batch.batchId===e.target.value);setQcForm({...qcForm,batchId:e.target.value,resultTmNumber:activeQcTab==="finished"?(selected?.resultTmNumber||""):""});}} required>''',
'QC batch select TM prefill'
)

# Selected QC summary: separate administrative and physical locations.
old_summary = '''<div><span className="font-black text-slate-400">{activeQcTab==="incoming"?"MO / TM Bahan":"MO Utama / TM Hasil"}</span><div className="mt-1 font-bold text-slate-800">{activeQcTab==="incoming"?((selected.moNumber||"-")+" / "+(selected.tmNumber||"-")):((selected.mainMoNumber||getPrimaryMoNumber(selected)||"-")+" / "+(selected.resultTmNumber||"-"))}</div></div><div><span className="font-black text-slate-400">Gudang / Tumpukan</span><div className="mt-1 font-bold text-slate-800">{selected.sourceWarehouse||selected.targetStack||"-"}</div></div>'''
new_summary = '''<div><span className="font-black text-slate-400">{activeQcTab==="incoming"?"MO / TM Bahan":"MO Utama / TM Hasil"}</span><div className="mt-1 font-bold text-slate-800">{activeQcTab==="incoming"?((selected.moNumber||"-")+" / "+(selected.tmNumber||"-")):((selected.mainMoNumber||getPrimaryMoNumber(selected)||"-")+" / "+(qcForm.resultTmNumber||selected.resultTmNumber||"MENUNGGU QC/ADMIN"))}</div></div><div><span className="font-black text-slate-400">Gudang Administrasi</span><div className="mt-1 font-bold text-slate-800">{selected.administrativeWarehouse||(Array.isArray(selected.administrativeWarehouses)?selected.administrativeWarehouses.join(", "):"")||getBatchAdministrativeWarehouse(selected,sku,systemConfig)||"-"}</div></div><div><span className="font-black text-slate-400">Lokasi Fisik / Tumpukan</span><div className="mt-1 font-bold text-slate-800">{getBatchPhysicalLocation(selected,systemConfig)||"-"}{selected.targetStack?` · ${selected.targetStack}`:""}</div></div>'''
rep(old_summary, new_summary, 'QC selected batch location summary')

# 4) Insert finished-goods TM Hasil admin input before COA/decision grid.
marker = '''                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3"><div><label className="mb-1.5 block text-xs font-bold text-slate-600">No. COA / Hasil Uji (Opsional)</label>'''
insert = '''                  {activeQcTab==="finished" && (
                    <div className="rounded-2xl border border-violet-200 bg-violet-50/60 p-4">
                      <label className="mb-2 block text-sm font-black text-violet-900">TM Hasil (Data Administrasi)</label>
                      <input
                        type="text"
                        className="w-full rounded-xl border border-violet-300 bg-white p-3 font-black text-violet-900 outline-none focus:border-violet-600"
                        value={qcForm.resultTmNumber||""}
                        onChange={e=>setQcForm({...qcForm,resultTmNumber:e.target.value})}
                        placeholder="Masukkan TM Hasil dari data administrasi"
                        required={qcForm.decision==="RELEASE"}
                      />
                      <p className="mt-2 text-xs leading-5 text-violet-700">
                        Wajib sebelum RELEASE. TM Hasil boleh digunakan kembali untuk batch produksi lain selama tetap terikat pada MO Utama yang sama.
                      </p>
                    </div>
                  )}
''' + marker
rep(marker, insert, 'QC finished TM admin input')

# 5) Settings: configurable physical processing location.
marker = '''                  <div>
                    <label className="block font-bold text-slate-700 mb-1">URL Logo (Opsional)</label>'''
insert = '''                  <div>
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

''' + marker
rep(marker, insert, 'processing location settings input')

# 6) Dashboard raw warehouses become administrative warehouse + physical location.
rep(
'''          qcStatuses: new Set(),
        };''',
'''          qcStatuses: new Set(),
          physicalLocations: new Set(),
        };''',
'dashboard raw physical set'
)
rep(
'''        const row = ensureWarehouse(group, tx.sourceWarehouse, sku);
        const qty = Number(tx.qtyChange || 0);''',
'''        const row = ensureWarehouse(
          group,
          tx.administrativeWarehouse || tx.sourceWarehouse,
          sku
        );
        row.physicalLocations.add(tx.physicalLocation || getProcessingLocation(systemConfig));
        const qty = Number(tx.qtyChange || 0);''',
'dashboard inbound admin physical'
)
rep(
'''          const row = ensureWarehouse(group, material.sourceWarehouse, sku);
          const damageQty = Number(material.damageQty || 0);''',
'''          const row = ensureWarehouse(
            group,
            material.administrativeWarehouse || material.sourceWarehouse,
            sku
          );
          row.physicalLocations.add(material.physicalLocation || getProcessingLocation(systemConfig));
          const damageQty = Number(material.damageQty || 0);''',
'dashboard rebag material admin physical'
)
rep(
'''      const row = ensureWarehouse(group, batch.sourceWarehouse, sku);
      const qty = Number(batch.currentQty || 0);''',
'''      const row = ensureWarehouse(
        group,
        getBatchAdministrativeWarehouse(batch, sku, systemConfig),
        sku
      );
      row.physicalLocations.add(getBatchPhysicalLocation(batch, systemConfig));
      const qty = Number(batch.currentQty || 0);''',
'dashboard live raw admin physical'
)
rep(
'''            qcStatus:
              [...row.qcStatuses].sort().join(", ") ||
              (row.currentQty > 0 ? "LEGACY" : "-"),''',
'''            qcStatus:
              [...row.qcStatuses].sort().join(", ") ||
              (row.currentQty > 0 ? "LEGACY" : "-"),
            physicalLocation:
              [...row.physicalLocations].sort().join(", ") ||
              getProcessingLocation(systemConfig),''',
'dashboard raw mapped physical'
)

# Finished product row derives administrative owner from batch, not physical stack/source.
old_product_fields = '''      group.productRows.push({
        batchId: batch.batchId || "",
        skuId: sku.id,
        name: sku.name,
        tmResult: batch.resultTmNumber || "",
        sourceWarehouses:
          sourceWarehouses.length > 0
            ? sourceWarehouses.join(", ")
            : batch.sourceWarehouse || "-",
        targetStack: batch.targetStack || "-",
        productionDate: batch.productionDate || batch.date || "",'''
new_product_fields = '''      const primaryAdministrativeWarehouses = [
        ...new Set(
          (Array.isArray(batch.administrativeWarehouses) && batch.administrativeWarehouses.length > 0
            ? batch.administrativeWarehouses
            : (Array.isArray(batch.materials) ? batch.materials : [])
                .filter((material) => material.isPrimaryMaterial)
                .map((material) => material.administrativeWarehouse || material.sourceWarehouse)
          ).filter(Boolean)
        ),
      ];
      const finishedAdministrativeWarehouse =
        batch.administrativeWarehouse ||
        primaryAdministrativeWarehouses.join(", ") ||
        (sourceWarehouses.length > 0 ? sourceWarehouses.join(", ") : batch.sourceWarehouse || "-");

      group.productRows.push({
        batchId: batch.batchId || "",
        skuId: sku.id,
        name: sku.name,
        tmResult: batch.resultTmNumber || "",
        sourceWarehouses:
          sourceWarehouses.length > 0
            ? sourceWarehouses.join(", ")
            : batch.sourceWarehouse || "-",
        administrativeWarehouse: finishedAdministrativeWarehouse,
        administrativeWarehouses:
          batch.administrativeWarehouses || primaryAdministrativeWarehouses,
        physicalLocation: getBatchPhysicalLocation(batch, systemConfig),
        targetStack: batch.targetStack || "-",
        productionDate: batch.productionDate || batch.date || "",'''
rep(old_product_fields, new_product_fields, 'dashboard finished admin physical fields')

# Finished aggregation key & fields.
rep(
'''          const warehouse = String(row.targetStack || "-");
          const key = `${row.skuId}|${warehouse}`;
          if (!finishedWarehouseMap[key]) {
            finishedWarehouseMap[key] = {
              key,
              skuId: row.skuId,
              name: row.name,
              warehouse,''',
'''          const administrativeWarehouse = String(row.administrativeWarehouse || "-");
          const physicalLocation = String(row.physicalLocation || getProcessingLocation(systemConfig));
          const targetStack = String(row.targetStack || "-");
          const key = `${row.skuId}|${administrativeWarehouse}|${physicalLocation}|${targetStack}`;
          if (!finishedWarehouseMap[key]) {
            finishedWarehouseMap[key] = {
              key,
              skuId: row.skuId,
              name: row.name,
              administrativeWarehouse,
              physicalLocation,
              targetStack,''',
'dashboard finished aggregation location key'
)
rep(
'''            const warehouseCompare = a.warehouse.localeCompare(
              b.warehouse,
              undefined,
              { numeric: true, sensitivity: "base" }
            );
            if (warehouseCompare !== 0) return warehouseCompare;
            return a.name.localeCompare(b.name, undefined, {''',
'''            const adminCompare = a.administrativeWarehouse.localeCompare(
              b.administrativeWarehouse,
              undefined,
              { numeric: true, sensitivity: "base" }
            );
            if (adminCompare !== 0) return adminCompare;
            const physicalCompare = a.physicalLocation.localeCompare(
              b.physicalLocation,
              undefined,
              { numeric: true, sensitivity: "base" }
            );
            if (physicalCompare !== 0) return physicalCompare;
            const stackCompare = a.targetStack.localeCompare(
              b.targetStack,
              undefined,
              { numeric: true, sensitivity: "base" }
            );
            if (stackCompare !== 0) return stackCompare;
            return a.name.localeCompare(b.name, undefined, {''',
'dashboard finished aggregation sort'
)
# Only the moDashboardData dependency occurrence expected.
rep(
'''  }, [inventoryBatches, skus, transactions]);

  const reportTransactions = useMemo(() => {''',
'''  }, [inventoryBatches, skus, transactions, systemConfig.processingLocation]);

  const reportTransactions = useMemo(() => {''',
'dashboard dependency processing location'
)

# Dashboard text labels raw.
rep('''                        <h3 className="font-black text-slate-900">Bahan Baku per Gudang Asal</h3>''','''                        <h3 className="font-black text-slate-900">Bahan Baku per Gudang Administrasi</h3>''','raw heading admin')
rep('''                                <th className="p-3 text-left">Gudang Asal</th>
                                <th className="p-3 text-left">Bahan</th>''','''                                <th className="p-3 text-left">Gudang Administrasi</th>
                                <th className="p-3 text-left">Lokasi Fisik</th>
                                <th className="p-3 text-left">Bahan</th>''','raw dashboard headers')
rep(
'''                                  <td className="p-3 font-bold text-slate-700">{row.warehouse}</td>
                                  <td className="p-3">''',
'''                                  <td className="p-3 font-bold text-slate-700">{row.warehouse}</td>
                                  <td className="p-3 font-bold text-cyan-700">{row.physicalLocation}</td>
                                  <td className="p-3">''',
'raw dashboard physical cell'
)

# Finished dashboard table: product/admin/physical/stack/TM.
old_headers = '''                                <th className="p-3 text-left">Produk</th>
                                <th className="p-3 text-left">Gudang / Tumpukan</th>
                                <th className="p-3 text-left">TM Hasil</th>'''
new_headers = '''                                <th className="p-3 text-left">Produk</th>
                                <th className="p-3 text-left">Gudang Administrasi</th>
                                <th className="p-3 text-left">Lokasi Fisik</th>
                                <th className="p-3 text-left">Tumpukan</th>
                                <th className="p-3 text-left">TM Hasil</th>'''
rep(old_headers, new_headers, 'finished dashboard headers')
rep(
'''                                  <td className="p-3 font-bold text-slate-700">{row.warehouse}</td>
                                  <td className="p-3 text-xs font-bold text-green-700">{row.tmResult || "-"}</td>''',
'''                                  <td className="p-3 font-bold text-slate-700">{row.administrativeWarehouse}</td>
                                  <td className="p-3 font-bold text-cyan-700">{row.physicalLocation}</td>
                                  <td className="p-3 font-bold text-slate-600">{row.targetStack}</td>
                                  <td className="p-3 text-xs font-bold text-violet-700">{row.tmResult || "MENUNGGU QC/ADMIN"}</td>''',
'finished dashboard location cells'
)

# 7) Inventory table: admin + physical columns.
rep(
'''                      <th className="p-4 font-semibold whitespace-nowrap">Gudang Asal</th>
                      {activeInvTab === 'rebagged' ? (''',
'''                      <th className="p-4 font-semibold whitespace-nowrap">Gudang Administrasi</th>
                      <th className="p-4 font-semibold whitespace-nowrap">Lokasi Fisik</th>
                      {activeInvTab === 'rebagged' ? (''',
'inventory admin physical headers'
)
rep(
'''                      const sources = [...new Set(batches.map(b=>b.sourceWarehouse).filter(Boolean))].join(", ") || "-";
                      return (''',
'''                      const administrativeSources = [
                        ...new Set(
                          batches
                            .map(b=>
                              b.administrativeWarehouse ||
                              (Array.isArray(b.administrativeWarehouses)
                                ? b.administrativeWarehouses.join(", ")
                                : getBatchAdministrativeWarehouse(b, sku, systemConfig))
                            )
                            .filter(Boolean)
                        )
                      ].join(", ") || "-";
                      const physicalLocations = [
                        ...new Set(
                          batches
                            .map(b=>getBatchPhysicalLocation(b, systemConfig))
                            .filter(Boolean)
                        )
                      ].join(", ") || "-";
                      return (''',
'inventory location aggregates'
)
rep(
'''                          <td className="p-4 text-slate-600">{sources}</td>
                          {activeInvTab === 'rebagged' ? (''',
'''                          <td className="p-4 text-slate-600">{administrativeSources}</td>
                          <td className="p-4 font-bold text-cyan-700">{physicalLocations}</td>
                          {activeInvTab === 'rebagged' ? (''',
'inventory location cells'
)

# 8) Outbound card displays physical/admin separately.
rep(
'''                                      <p className="font-bold text-slate-800 text-sm">{b.targetStack||b.sourceWarehouse||'-'}</p>''',
'''                                      <p className="font-bold text-slate-800 text-sm">{getBatchPhysicalLocation(b,systemConfig)||'-'}{b.targetStack?` · ${b.targetStack}`:""}</p>''',
'outbound physical title'
)
rep(
'''                                        <p className="text-xs text-slate-500 mt-1">MO Sumber: {(b.sourceMoNumbers||[]).join(', ') || b.moNumber || '-'}</p>
                                        <p className="text-xs text-slate-500 mt-1">TM Bahan: {(b.sourceTmNumbers||[]).join(', ') || '-'}</p>''',
'''                                        <p className="text-xs text-slate-500 mt-1">MO Sumber: {(b.sourceMoNumbers||[]).join(', ') || b.moNumber || '-'}</p>
                                        <p className="text-xs text-slate-500 mt-1">TM Bahan: {(b.sourceTmNumbers||[]).join(', ') || '-'}</p>
                                        <p className="text-xs font-bold text-cyan-700 mt-1">Gudang Administrasi: {b.administrativeWarehouse||(b.administrativeWarehouses||[]).join(', ')||'-'}</p>''',
'outbound admin location detail'
)

# 9) QC PDF distinguishes administrative warehouse and physical position.
rep(
'''      ["Gudang / Tumpukan",record.sourceWarehouse||record.targetStack||"-"],["Expiry",formatPdfDate(record.expiryDate)||"-"],''',
'''      ["Gudang Administrasi",record.administrativeWarehouse||record.sourceWarehouse||"-"],["Lokasi Fisik / Tumpukan",`${record.physicalLocation||"-"}${record.targetStack?` / ${record.targetStack}`:""}`],["Expiry",formatPdfDate(record.expiryDate)||"-"],''',
'QC PDF location rows'
)

path.write_text(s, encoding='utf-8')
print('UI/dashboard administrative and physical warehouse patch applied.')
