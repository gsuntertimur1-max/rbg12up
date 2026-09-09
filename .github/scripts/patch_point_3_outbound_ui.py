from pathlib import Path

path = Path("src/App.jsx")
s = path.read_text(encoding="utf-8")

start = s.find('''                            {inventoryBatches
                              .filter(b=>
                                b.skuId===formData.outSkuId &&''')
end = s.find('''                            {inventoryBatches.filter(b=>
                              b.skuId===formData.outSkuId &&''', start)

if start < 0 or end < 0:
    raise SystemExit("Outbound batch UI block not found")

new_block = r'''                            {sortBatchesFefoFifo(
                              inventoryBatches.filter(b=>
                                b.skuId===formData.outSkuId &&
                                Number(b.currentQty||0)>0 &&
                                (!outboundIsFinishedGoods || b.resultTmNumber===formData.outTmNumber)
                              )
                            ).map(b=>{
                              const candidateBatches=inventoryBatches.filter(x=>
                                x.skuId===formData.outSkuId &&
                                Number(x.currentQty||0)>0 &&
                                (!outboundIsFinishedGoods || x.resultTmNumber===formData.outTmNumber)
                              );
                              const expiryInfo=getBatchExpiryInfo(b);
                              const recommendation=getBatchRecommendationLabel(b,candidateBatches);
                              const isRecommended=recommendation.includes('REKOMENDASI');
                              return (
                                <div
                                  key={b.batchId}
                                  className={`flex flex-col sm:flex-row justify-between sm:items-center p-3 rounded-lg border shadow-sm gap-3 ${expiryInfo.isExpired?'border-red-300 bg-red-50/60':isRecommended?'border-green-300 bg-green-50/40':'border-slate-200 bg-white'}`}
                                >
                                  <div>
                                    <div className="flex flex-wrap items-center gap-2">
                                      <p className="font-bold text-slate-800 text-sm">{b.targetStack||b.sourceWarehouse||'-'}</p>
                                      <span className={`rounded-full px-2 py-0.5 text-[9px] font-black ${expiryInfo.isExpired?'bg-red-100 text-red-700':isRecommended?'bg-green-100 text-green-700':expiryInfo.daysRemaining!==null && expiryInfo.daysRemaining<=30?'bg-orange-100 text-orange-700':expiryInfo.daysRemaining!==null && expiryInfo.daysRemaining<=90?'bg-amber-100 text-amber-700':'bg-slate-100 text-slate-600'}`}>
                                        {recommendation}
                                      </span>
                                    </div>
                                    <p className="text-xs text-slate-500 font-mono mt-1">Batch: {b.batchId}</p>
                                    {outboundIsFinishedGoods ? (
                                      <>
                                        <p className="text-xs text-green-700 font-bold mt-1">TM Hasil: {b.resultTmNumber||'-'}</p>
                                        <p className="text-xs text-violet-700 font-bold mt-1">MO Utama: {b.mainMoNumber||getPrimaryMoNumber(b)||'-'}</p>
                                        <p className="text-xs text-slate-500 mt-1">MO Sumber: {(b.sourceMoNumbers||[]).join(', ') || b.moNumber || '-'}</p>
                                        <p className="text-xs text-slate-500 mt-1">TM Bahan: {(b.sourceTmNumbers||[]).join(', ') || '-'}</p>
                                      </>
                                    ) : (
                                      <p className="text-xs text-slate-500 mt-1">MO: {b.moNumber||'-'} · TM: {b.tmNumber||'-'}</p>
                                    )}
                                    <p className="text-xs text-slate-500 mt-1">Stok GOOD: <span className="font-bold text-blue-600">{b.currentQty}</span></p>
                                    {b.expiryDate ? (
                                      <p className={`text-xs mt-1 font-bold ${expiryInfo.isExpired?'text-red-700':expiryInfo.daysRemaining!==null && expiryInfo.daysRemaining<=30?'text-orange-700':expiryInfo.daysRemaining!==null && expiryInfo.daysRemaining<=90?'text-amber-700':'text-slate-500'}`}>
                                        Expired: {formatPdfDate(b.expiryDate)} · {expiryInfo.isExpired?'SUDAH EXPIRED':`${expiryInfo.daysRemaining} hari lagi`}
                                      </p>
                                    ) : (
                                      <p className="text-xs text-slate-400 mt-1">Tanpa tanggal expiry · prioritas FIFO</p>
                                    )}
                                    {expiryInfo.isExpired && isVerifiedSuperAdmin && (
                                      <p className="mt-1 text-[10px] font-black text-red-600">SUPER ADMIN: dapat override dengan konfirmasi saat Simpan.</p>
                                    )}
                                  </div>
                                  <input
                                    type="number"
                                    min="0"
                                    max={b.currentQty}
                                    disabled={expiryInfo.isExpired && !isVerifiedSuperAdmin}
                                    className="border border-slate-300 p-2.5 w-full sm:w-28 rounded-md text-center font-bold outline-none focus:border-orange-500 disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed"
                                    placeholder={expiryInfo.isExpired && !isVerifiedSuperAdmin ? "BLOCK" : "0"}
                                    value={outboundSelections[b.batchId]||''}
                                    onChange={e=>setOutboundSelections({...outboundSelections,[b.batchId]:e.target.value})}
                                  />
                                </div>
                              );
                            })}
'''
s = s[:start] + new_block + s[end:]

path.write_text(s, encoding="utf-8")
print("Outbound FEFO/expiry UI patch applied.")
