from pathlib import Path

path = Path("src/App.jsx")
s = path.read_text(encoding="utf-8")

start = s.find('''                            {activeRebagMaterials.map((recipeMaterial, materialIndex)=>{''')
end_marker = '''                            })}
                          </div>
                        )}'''
end = s.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit("Rebag material UI block not found")
end += len('''                            })}''')

new_ui = r'''                            {activeRebagMaterials.map((recipeMaterial, materialIndex)=>{
                              const materialSkuId=recipeMaterial.skuId;
                              const materialSku=skus.find(s=>s.id===materialSkuId);
                              const rawAllocations=normalizeRebagAllocations(rebagMaterialSelections[materialSkuId]);
                              const allocations=rawAllocations.length>0 ? rawAllocations : [createRebagAllocation()];
                              const referenceDate=formData.useBackdate && formData.backdateDateTime
                                ? new Date(formData.backdateDateTime)
                                : new Date();
                              const batchOptions=sortBatchesFefoFifo(
                                inventoryBatches.filter(
                                  b=>b.skuId===materialSkuId && Number(b.currentQty||0)>0
                                ),
                                referenceDate
                              );
                              const calculatedUsage=Number(getCalculatedMaterialQty(recipeMaterial, formData.qtyToProcess)||0);
                              const totalUsed=allocations.reduce((sum,row)=>sum+Number(row.qty||0),0);
                              const totalDamage=allocations.reduce((sum,row)=>sum+Number(row.damageQty||0),0);
                              const totalMaterialOut=totalUsed+totalDamage;
                              const primaryMos=[
                                ...new Set(
                                  allocations
                                    .map(row=>inventoryBatches.find(b=>b.batchId===row.batchId)?.moNumber)
                                    .filter(Boolean)
                                )
                              ];
                              return (
                                <div key={materialSkuId} className={`rounded-2xl border bg-white p-4 shadow-sm ${recipeMaterial.required ? 'border-slate-200' : 'border-blue-200'}`}>
                                  <div className="mb-3 flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                                    <div>
                                      <div className="font-mono text-xs font-black text-red-600">{materialSkuId}</div>
                                      <div className="font-bold text-slate-800">{materialSku?.name || 'SKU belum ada di master'}</div>
                                      <p className="mt-1 text-[10px] text-slate-400">Urutan batch mengikuti FEFO; jika tidak ada expiry, FIFO.</p>
                                    </div>
                                    <div className="flex flex-wrap gap-1.5">
                                      {materialIndex === 0 && (
                                        <span className="rounded-full bg-violet-50 px-2.5 py-1 text-[10px] font-black text-violet-700">
                                          MO UTAMA / PENGIKAT TM
                                        </span>
                                      )}
                                      {recipeMaterial.calculationMode === 'per_output' && (
                                        <span className="rounded-full bg-green-50 px-2.5 py-1 text-[10px] font-black text-green-700">
                                          STANDAR {calculatedUsage} {materialSku?.unit||''}
                                        </span>
                                      )}
                                      <span className={`rounded-full px-2.5 py-1 text-[10px] font-black ${recipeMaterial.required ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'}`}>
                                        {recipeMaterial.required ? 'WAJIB' : 'OPSIONAL'}
                                      </span>
                                    </div>
                                  </div>

                                  <div className="space-y-3">
                                    {allocations.map((allocation,sourceIndex)=>{
                                      const selectedBatch=batchOptions.find(b=>b.batchId===allocation.batchId);
                                      const expiryInfo=getBatchExpiryInfo(selectedBatch,referenceDate);
                                      const recommendation=selectedBatch
                                        ? getBatchRecommendationLabel(selectedBatch,batchOptions,referenceDate)
                                        : '';
                                      const usedQty=Number(allocation.qty||0);
                                      const damageQty=Number(allocation.damageQty||0);
                                      const usedOther=totalUsed-usedQty;
                                      const remainingStandard=Math.max(0,calculatedUsage-usedOther);
                                      const alreadySelected=new Set(
                                        allocations
                                          .filter(row=>row.rowId!==allocation.rowId)
                                          .map(row=>row.batchId)
                                          .filter(Boolean)
                                      );

                                      return (
                                        <div key={allocation.rowId} className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                                          <div className="mb-2 flex items-center justify-between gap-3">
                                            <div className="text-xs font-black text-slate-500">Sumber Batch {sourceIndex+1}</div>
                                            {allocations.length>1 && (
                                              <button
                                                type="button"
                                                onClick={()=>removeRebagAllocation(materialSkuId,allocation.rowId)}
                                                className="rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 text-[10px] font-black text-red-600 hover:bg-red-100"
                                              >
                                                Hapus Sumber
                                              </button>
                                            )}
                                          </div>

                                          <select
                                            className="w-full p-3 border border-slate-300 rounded-lg bg-white outline-none focus:border-red-500 text-sm"
                                            value={allocation.batchId||''}
                                            onChange={e=>{
                                              updateRebagAllocation(materialSkuId,allocation.rowId,'batchId',e.target.value);
                                              if(
                                                recipeMaterial.calculationMode==='per_output' &&
                                                allocations.length===1 &&
                                                !allocation.qty
                                              ){
                                                updateRebagAllocation(materialSkuId,allocation.rowId,'qty',String(calculatedUsage));
                                              }
                                            }}
                                            required={recipeMaterial.required && sourceIndex===0}
                                          >
                                            <option value="">-- Pilih Batch Bahan --</option>
                                            {batchOptions.map(b=>{
                                              const info=getBatchExpiryInfo(b,referenceDate);
                                              const label=getBatchRecommendationLabel(b,batchOptions,referenceDate);
                                              return (
                                                <option
                                                  key={b.batchId}
                                                  value={b.batchId}
                                                  disabled={
                                                    alreadySelected.has(b.batchId) ||
                                                    (info.isExpired && !isVerifiedSuperAdmin)
                                                  }
                                                >
                                                  [{label}] {b.sourceWarehouse||'-'} · MO: {b.moNumber||'-'} · TM: {b.tmNumber||'-'} · Stok: {b.currentQty}{b.expiryDate ? ` · Exp: ${formatPdfDate(b.expiryDate)}` : ''}
                                                </option>
                                              );
                                            })}
                                          </select>

                                          <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
                                            <div>
                                              <div className="mb-1.5 flex items-center justify-between gap-2">
                                                <label className="block text-xs font-bold text-slate-500">Qty Dipakai</label>
                                                {recipeMaterial.calculationMode==='per_output' && (
                                                  <button
                                                    type="button"
                                                    onClick={()=>updateRebagAllocation(materialSkuId,allocation.rowId,'qty',String(remainingStandard))}
                                                    className="text-[9px] font-black text-green-700 hover:underline"
                                                  >
                                                    Isi Sisa Standar
                                                  </button>
                                                )}
                                              </div>
                                              <input
                                                type="number"
                                                min="0"
                                                max={selectedBatch?.currentQty||undefined}
                                                className="w-full p-3 border border-slate-300 rounded-lg bg-white outline-none focus:border-red-500 font-bold"
                                                value={allocation.qty||''}
                                                onChange={e=>updateRebagAllocation(materialSkuId,allocation.rowId,'qty',e.target.value)}
                                                placeholder="0"
                                                disabled={!allocation.batchId}
                                              />
                                            </div>
                                            <div>
                                              <label className="mb-1.5 block text-xs font-bold text-red-600">Qty Rusak</label>
                                              <input
                                                type="number"
                                                min="0"
                                                max={selectedBatch ? Math.max(0,Number(selectedBatch.currentQty||0)-usedQty) : undefined}
                                                className="w-full p-3 border border-red-200 rounded-lg bg-red-50/50 outline-none focus:border-red-500 font-bold text-red-700"
                                                value={allocation.damageQty||''}
                                                onChange={e=>updateRebagAllocation(materialSkuId,allocation.rowId,'damageQty',e.target.value)}
                                                placeholder="0"
                                                disabled={!allocation.batchId}
                                              />
                                            </div>
                                            <div>
                                              <label className="mb-1.5 block text-xs font-bold text-slate-500">Total Keluar Sumber</label>
                                              <div className="flex min-h-[46px] items-center justify-between rounded-lg border border-slate-200 bg-white px-3">
                                                <span className="text-sm font-black text-slate-800">{usedQty+damageQty}</span>
                                                <span className="text-xs font-bold text-slate-400">{materialSku?.unit||''}</span>
                                              </div>
                                            </div>
                                          </div>

                                          {selectedBatch && (
                                            <div className="mt-3 flex flex-wrap gap-2 text-[10px]">
                                              <span className="rounded-lg bg-blue-50 px-2.5 py-1.5 font-bold text-blue-700">MO: {selectedBatch.moNumber||'-'}</span>
                                              <span className="rounded-lg bg-violet-50 px-2.5 py-1.5 font-bold text-violet-700">TM: {selectedBatch.tmNumber||'-'}</span>
                                              <span className="rounded-lg bg-slate-100 px-2.5 py-1.5 font-bold text-slate-600">Gudang: {selectedBatch.sourceWarehouse||'-'}</span>
                                              <span className={`rounded-lg px-2.5 py-1.5 font-black ${expiryInfo.isExpired?'bg-red-100 text-red-700':expiryInfo.daysRemaining!==null && expiryInfo.daysRemaining<=30?'bg-orange-100 text-orange-700':expiryInfo.daysRemaining!==null && expiryInfo.daysRemaining<=90?'bg-amber-100 text-amber-700':'bg-green-50 text-green-700'}`}>
                                                {recommendation}{expiryInfo.daysRemaining!==null ? ` · ${expiryInfo.daysRemaining} hari` : ''}
                                              </span>
                                            </div>
                                          )}
                                        </div>
                                      );
                                    })}
                                  </div>

                                  <button
                                    type="button"
                                    onClick={()=>addRebagAllocation(materialSkuId)}
                                    className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-black text-blue-700 hover:bg-blue-100"
                                  >
                                    <PlusCircle size={14}/> Tambah Batch Sumber
                                  </button>

                                  <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                                    <div className="rounded-lg bg-slate-100 px-3 py-2">
                                      <div className="text-[9px] font-black text-slate-400">DIPAKAI</div>
                                      <div className="mt-1 font-black text-slate-800">{totalUsed} {materialSku?.unit||''}</div>
                                    </div>
                                    <div className="rounded-lg bg-red-50 px-3 py-2">
                                      <div className="text-[9px] font-black text-red-400">RUSAK</div>
                                      <div className="mt-1 font-black text-red-700">{totalDamage} {materialSku?.unit||''}</div>
                                    </div>
                                    <div className="rounded-lg bg-blue-50 px-3 py-2">
                                      <div className="text-[9px] font-black text-blue-400">TOTAL KELUAR</div>
                                      <div className="mt-1 font-black text-blue-700">{totalMaterialOut} {materialSku?.unit||''}</div>
                                    </div>
                                    <div className={`rounded-lg px-3 py-2 ${recipeMaterial.calculationMode==='per_output' && Math.abs(totalUsed-calculatedUsage)>0.0001?'bg-amber-50':'bg-green-50'}`}>
                                      <div className="text-[9px] font-black text-slate-400">STATUS</div>
                                      <div className={`mt-1 font-black ${recipeMaterial.calculationMode==='per_output' && Math.abs(totalUsed-calculatedUsage)>0.0001?'text-amber-700':'text-green-700'}`}>
                                        {recipeMaterial.calculationMode==='per_output'
                                          ? (Math.abs(totalUsed-calculatedUsage)<=0.0001?'SESUAI STANDAR':`SELISIH ${calculatedUsage-totalUsed}`)
                                          : `${allocations.length} sumber`}
                                      </div>
                                    </div>
                                  </div>

                                  {materialIndex===0 && primaryMos.length>1 && (
                                    <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-black text-red-700">
                                      MO Utama tidak konsisten: {primaryMos.join(', ')}. Seluruh batch bahan utama wajib memakai MO yang sama.
                                    </div>
                                  )}
                                </div>
                              );
                            })}'''

s = s[:start] + new_ui + s[end:]

old = '''                                  options={inventoryBatches
                                    .filter(b=>b.skuId===formData.bulkSkuId && Number(b.currentQty||0)>0)
                                    .map(b=>({value:b.batchId,label:`${b.sourceWarehouse||'-'} · MO: ${b.moNumber||'-'} · TM: ${b.tmNumber||'-'} · Stok: ${b.currentQty}`}))}'''
new = '''                                  options={sortBatchesFefoFifo(
                                    inventoryBatches.filter(b=>b.skuId===formData.bulkSkuId && Number(b.currentQty||0)>0)
                                  ).map(b=>({
                                    value:b.batchId,
                                    label:`[${getBatchRecommendationLabel(b,inventoryBatches.filter(x=>x.skuId===formData.bulkSkuId && Number(x.currentQty||0)>0))}] ${b.sourceWarehouse||'-'} · MO: ${b.moNumber||'-'} · TM: ${b.tmNumber||'-'} · Stok: ${b.currentQty}${b.expiryDate?` · Exp: ${formatPdfDate(b.expiryDate)}`:''}`
                                  }))}'''
if old not in s:
    raise SystemExit("Manual fallback batch options not found")
s = s.replace(old,new,1)

path.write_text(s, encoding="utf-8")
print("Multi-batch UI patch applied.")
