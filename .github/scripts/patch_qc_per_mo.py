from pathlib import Path

p=Path('src/App.jsx')
s=p.read_text(encoding='utf-8')

def rep(old,new,label):
    global s
    if old not in s:
        raise SystemExit(f'Patch target not found: {label}')
    s=s.replace(old,new,1)

# Form field for incoming MO selection
rep('''  return {\n    batchId: "",\n    decision: isIncoming ? "ACCEPT" : "RELEASE",''','''  return {\n    moNumber: "",\n    batchId: "",\n    decision: isIncoming ? "ACCEPT" : "RELEASE",''','qc form mo field')

# Derived incoming QC groups per MO
marker='''  const outboundSelectedSku = skus.find((s) => s.id === formData.outSkuId);'''
insert=r'''  const incomingQcMoGroups = useMemo(() => {
    const unresolvedStatuses = new Set(["PENDING_QC", "HOLD", "REJECTED"]);
    const groups = {};

    inventoryBatches.forEach((batch) => {
      const sku = skus.find((item) => item.id === batch.skuId);
      if (
        sku?.type !== "bulk" ||
        Number(batch.currentQty || 0) <= 0 ||
        !unresolvedStatuses.has(batch.qcStatus)
      ) return;

      const moNumber = String(batch.moNumber || "").trim();
      if (!moNumber) return;

      if (!groups[moNumber]) {
        groups[moNumber] = {
          moNumber,
          items: [],
          tmNumbers: new Set(),
          latestAt: 0,
        };
      }

      const item = {
        batchId: batch.batchId,
        skuId: batch.skuId,
        skuName: sku?.name || batch.skuId || "",
        unit: sku?.unit || "",
        tmNumber: batch.tmNumber || "",
        administrativeWarehouse:
          batch.administrativeWarehouse ||
          getBatchAdministrativeWarehouse(batch, sku, systemConfig) || "",
        physicalLocation: getBatchPhysicalLocation(batch, systemConfig) || "",
        expiryDate: batch.expiryDate || "",
        qtySnapshot: Number(batch.currentQty || 0),
        qcStatus: batch.qcStatus || "PENDING_QC",
      };

      groups[moNumber].items.push(item);
      if (item.tmNumber) groups[moNumber].tmNumbers.add(item.tmNumber);
      groups[moNumber].latestAt = Math.max(
        groups[moNumber].latestAt,
        new Date(batch.date || 0).getTime() || 0
      );
    });

    return Object.values(groups)
      .map((group) => ({
        ...group,
        tmNumbers: [...group.tmNumbers].sort((a, b) =>
          String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" })
        ),
        items: group.items.sort((a, b) => {
          const tmCompare = String(a.tmNumber).localeCompare(String(b.tmNumber), undefined, {
            numeric: true,
            sensitivity: "base",
          });
          if (tmCompare !== 0) return tmCompare;
          return String(a.skuName).localeCompare(String(b.skuName), undefined, {
            numeric: true,
            sensitivity: "base",
          });
        }),
      }))
      .sort((a, b) => b.latestAt - a.latestAt);
  }, [inventoryBatches, skus, systemConfig]);

'''
rep(marker,insert+marker,'incoming QC groups')

# Add incoming-MO branch to QC submit before legacy single-batch path
old='''    if (!db) return alert("Database belum siap.");\n    if (!qcForm.batchId) return alert("Pilih batch yang akan diperiksa.");'''
new=r'''    if (!db) return alert("Database belum siap.");
    const isIncoming = activeQcTab === "incoming";

    if (isIncoming) {
      if (!qcForm.moNumber) return alert("Pilih MO bahan yang akan diperiksa.");
      const group = incomingQcMoGroups.find(
        (item) => String(item.moNumber).toUpperCase() === String(qcForm.moNumber).toUpperCase()
      );
      if (!group || group.items.length === 0) {
        return alert("Tidak ada batch bahan unresolved pada MO tersebut.");
      }

      const failedChecks = Object.entries(qcForm.checks)
        .filter(([, value]) => !value)
        .map(([key]) => key);
      if (qcForm.decision === "ACCEPT" && failedChecks.length > 0) {
        return alert(`Tidak dapat ACCEPT. Masih ada ${failedChecks.length} parameter QC yang Tidak Sesuai.`);
      }
      if (["HOLD", "REJECT"].includes(qcForm.decision) && !String(qcForm.nonconformity || "").trim()) {
        return alert("Penyimpangan/Ketidaksesuaian wajib diisi untuk HOLD atau REJECT.");
      }
      if (qcForm.decision === "REJECT" && !String(qcForm.correctiveAction || "").trim()) {
        return alert("Tindakan koreksi/disposisi wajib diisi untuk REJECT.");
      }

      const inspectedAt = new Date().toISOString();
      const recordId = `QC-IN-MO-${Date.now()}`;
      const batchStatus = qcForm.decision === "ACCEPT"
        ? "ACCEPTED"
        : qcForm.decision === "HOLD"
        ? "HOLD"
        : "REJECTED";
      const batchIds = group.items.map((item) => item.batchId);
      const tmNumbers = [...group.tmNumbers];
      const administrativeWarehouses = [
        ...new Set(group.items.map((item) => item.administrativeWarehouse).filter(Boolean)),
      ];
      const physicalLocations = [
        ...new Set(group.items.map((item) => item.physicalLocation).filter(Boolean)),
      ];
      const record = {
        id: recordId,
        qcType: "INCOMING",
        scope: "MO",
        moNumber: group.moNumber,
        mainMoNumber: group.moNumber,
        batchId: "",
        batchIds,
        tmNumber: tmNumbers.join(", "),
        tmNumbers,
        itemCount: group.items.length,
        skuCount: new Set(group.items.map((item) => item.skuId)).size,
        skuId: "",
        skuName: `${group.items.length} item bahan / ${tmNumbers.length} TM`,
        unit: "",
        administrativeWarehouse: administrativeWarehouses.join(", "),
        administrativeWarehouses,
        physicalLocation: physicalLocations.join(", "),
        physicalLocations,
        qtySnapshot: null,
        items: group.items,
        coaNumber: String(qcForm.coaNumber || "").trim(),
        checks: qcForm.checks,
        decision: qcForm.decision,
        batchStatus,
        inspectionNote: String(qcForm.inspectionNote || "").trim(),
        nonconformity: String(qcForm.nonconformity || "").trim(),
        correctiveAction: String(qcForm.correctiveAction || "").trim(),
        inspectedAt,
        inspectedBy: currentUser.username,
        inspectedRole: currentUser.role,
      };

      try {
        setQcSaving(true);
        const batchRefs = batchIds.map((batchId) =>
          doc(db, "artifacts", appId, "public", "data", "batches", batchId)
        );
        const relatedInboundTxs = batchIds
          .map((batchId) => transactions.find((item) => item.type === "INBOUND" && item.batchId === batchId))
          .filter(Boolean);
        const txRefs = relatedInboundTxs.map((item) =>
          doc(db, "artifacts", appId, "public", "data", "transactions", item.id)
        );

        await runTransaction(db, async (transaction) => {
          const allSnaps = await Promise.all(
            [...batchRefs, ...txRefs].map((ref) => transaction.get(ref))
          );
          const batchSnaps = allSnaps.slice(0, batchRefs.length);
          const txSnaps = allSnaps.slice(batchRefs.length);
          const unresolvedStatuses = new Set(["PENDING_QC", "HOLD", "REJECTED"]);

          batchSnaps.forEach((snap, index) => {
            if (!snap.exists()) throw new Error(`Batch ${batchIds[index]} sudah tidak ditemukan.`);
            const liveBatch = snap.data();
            if (String(liveBatch.moNumber || "").trim().toUpperCase() !== String(group.moNumber).toUpperCase()) {
              throw new Error(`Batch ${batchIds[index]} tidak lagi berada pada MO ${group.moNumber}.`);
            }
            if (!unresolvedStatuses.has(liveBatch.qcStatus)) {
              throw new Error(`Status QC batch ${batchIds[index]} sudah berubah. Muat ulang halaman QC.`);
            }
          });

          batchRefs.forEach((ref) => {
            transaction.update(ref, {
              qcStatus: batchStatus,
              qcType: "INCOMING",
              qcScope: "MO",
              qcMoNumber: group.moNumber,
              qcLastRecordId: recordId,
              qcUpdatedAt: inspectedAt,
              qcUpdatedBy: currentUser.username,
              qcDecision: qcForm.decision,
            });
          });

          txRefs.forEach((ref, index) => {
            if (!txSnaps[index]?.exists()) return;
            transaction.update(ref, {
              qcStatus: batchStatus,
              qcScope: "MO",
              qcMoNumber: group.moNumber,
              qcLastRecordId: recordId,
              qcUpdatedAt: inspectedAt,
              qcUpdatedBy: currentUser.username,
              qcDecision: qcForm.decision,
            });
          });

          transaction.set(
            doc(db, "artifacts", appId, "public", "data", "qc_records", recordId),
            record
          );
        });

        showNotif(`QC MO ${group.moNumber}: ${qcForm.decision} · ${group.items.length} item / ${tmNumbers.length} TM`);
        resetQcForm(activeQcTab);
      } catch (error) {
        console.error("QC MO Save Error:", error);
        alert(`Gagal menyimpan QC MO: ${error.message || "Terjadi kesalahan."}`);
      } finally {
        setQcSaving(false);
      }
      return;
    }

    if (!qcForm.batchId) return alert("Pilih batch yang akan diperiksa.");'''
rep(old,new,'incoming MO submit branch')

# Remove duplicate isIncoming declaration and collapse finished validation
rep('''    const isIncoming = activeQcTab === "incoming";\n    if (isIncoming && sku?.type !== "bulk") return alert("QC Bahan Masuk hanya untuk SKU bahan baku/kemasan.");\n    if (!isIncoming && sku?.type !== "rebagged") return alert("QC Produk Jadi hanya untuk SKU hasil Rebagging.");''','''    if (sku?.type !== "rebagged") return alert("QC Produk Jadi hanya untuk SKU hasil Rebagging.");''','finished validation after incoming branch')

# Replace QC selector/detail block with per-MO incoming + per-batch finished
start_marker='''                  <div><label className="mb-2 block text-sm font-bold text-slate-700">Pilih Batch</label>'''
end_marker='''                  <div><h3 className="mb-3 font-black text-slate-800">Parameter Pemeriksaan</h3>'''
start=s.find(start_marker)
end=s.find(end_marker,start)
if start<0 or end<0:
    raise SystemExit('QC selector UI markers not found')
ui=r'''                  {activeQcTab === "incoming" ? (
                    <>
                      <div>
                        <label className="mb-2 block text-sm font-bold text-slate-700">Pilih MO Bahan</label>
                        <select
                          className="w-full rounded-xl border border-slate-300 bg-white p-3 outline-none focus:border-blue-500 font-medium"
                          value={qcForm.moNumber || ""}
                          onChange={e=>setQcForm({...qcForm,moNumber:e.target.value,batchId:""})}
                          required
                        >
                          <option value="">-- Pilih MO untuk QC --</option>
                          {incomingQcMoGroups.map(group=>(
                            <option key={group.moNumber} value={group.moNumber}>
                              MO {group.moNumber} · {group.tmNumbers.length} TM · {group.items.length} item/batch
                            </option>
                          ))}
                        </select>
                        <p className="mt-1.5 text-xs text-slate-500">
                          Satu keputusan QC berlaku untuk seluruh batch bahan unresolved di bawah MO yang dipilih.
                        </p>
                      </div>

                      {qcForm.moNumber && (()=>{
                        const group=incomingQcMoGroups.find(item=>item.moNumber===qcForm.moNumber);
                        if(!group) return null;
                        return (
                          <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-4 space-y-4">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                              <div>
                                <div className="text-[10px] font-black uppercase tracking-[0.14em] text-blue-500">Cakupan QC Incoming</div>
                                <div className="mt-1 text-lg font-black text-slate-900">MO {group.moNumber}</div>
                              </div>
                              <div className="flex flex-wrap gap-2 text-[10px] font-black">
                                <span className="rounded-full bg-violet-100 px-3 py-1.5 text-violet-700">{group.tmNumbers.length} TM BAHAN</span>
                                <span className="rounded-full bg-blue-100 px-3 py-1.5 text-blue-700">{group.items.length} ITEM/BATCH</span>
                              </div>
                            </div>
                            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
                              <table className="w-full min-w-[900px] text-xs">
                                <thead className="bg-slate-50 text-slate-500">
                                  <tr>
                                    <th className="p-2.5 text-left">TM Bahan</th>
                                    <th className="p-2.5 text-left">SKU / Bahan</th>
                                    <th className="p-2.5 text-left">Batch</th>
                                    <th className="p-2.5 text-right">Qty</th>
                                    <th className="p-2.5 text-left">Gudang Administrasi</th>
                                    <th className="p-2.5 text-left">Lokasi Fisik</th>
                                    <th className="p-2.5 text-center">Status</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                  {group.items.map(item=>(
                                    <tr key={item.batchId}>
                                      <td className="p-2.5 font-mono font-black text-violet-700">{item.tmNumber||"-"}</td>
                                      <td className="p-2.5"><div className="font-mono text-[10px] font-black text-blue-600">{item.skuId}</div><div className="mt-0.5 font-bold text-slate-800">{item.skuName}</div></td>
                                      <td className="p-2.5 font-mono text-[10px] text-slate-500">{item.batchId}</td>
                                      <td className="p-2.5 text-right font-black text-slate-800">{item.qtySnapshot.toLocaleString("id-ID")} {item.unit}</td>
                                      <td className="p-2.5 font-bold text-slate-600">{item.administrativeWarehouse||"-"}</td>
                                      <td className="p-2.5 font-bold text-cyan-700">{item.physicalLocation||"-"}</td>
                                      <td className="p-2.5 text-center"><span className="rounded-full bg-amber-50 px-2 py-1 text-[9px] font-black text-amber-700">{item.qcStatus}</span></td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                            <div className="text-xs text-slate-600">
                              TM: <span className="font-mono font-black text-violet-700">{group.tmNumbers.join(", ") || "-"}</span>
                            </div>
                          </div>
                        );
                      })()}
                    </>
                  ) : (
                    <>
                      <div>
                        <label className="mb-2 block text-sm font-bold text-slate-700">Pilih Batch Produk Jadi</label>
                        <select
                          className="w-full rounded-xl border border-slate-300 bg-white p-3 outline-none focus:border-emerald-500 font-medium"
                          value={qcForm.batchId}
                          onChange={e=>{
                            const selected=inventoryBatches.find(batch=>batch.batchId===e.target.value);
                            setQcForm({...qcForm,batchId:e.target.value,resultTmNumber:selected?.resultTmNumber||""});
                          }}
                          required
                        >
                          <option value="">-- Pilih Batch Produk Jadi untuk QC --</option>
                          {inventoryBatches
                            .filter(batch=>{
                              const sku=skus.find(item=>item.id===batch.skuId);
                              const pendingStatuses=["PENDING_QC","HOLD","REJECTED"];
                              return Number(batch.currentQty||0)>0 && pendingStatuses.includes(batch.qcStatus) && sku?.type==="rebagged";
                            })
                            .sort((a,b)=>new Date(b.productionDate||b.date||0)-new Date(a.productionDate||a.date||0))
                            .map(batch=>{
                              const sku=skus.find(item=>item.id===batch.skuId);
                              return <option key={batch.batchId} value={batch.batchId}>[{getQcStatusLabel(batch)}] {batch.batchId} · {sku?.name||batch.skuId} · Stok {batch.currentQty}</option>;
                            })}
                        </select>
                      </div>
                      {qcForm.batchId && (()=>{
                        const selected=inventoryBatches.find(batch=>batch.batchId===qcForm.batchId);
                        const sku=skus.find(item=>item.id===selected?.skuId);
                        return selected?(<div className="grid grid-cols-1 sm:grid-cols-2 gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs"><div><span className="font-black text-slate-400">SKU / Produk</span><div className="mt-1 font-bold text-slate-800">{selected.skuId} · {sku?.name||"-"}</div></div><div><span className="font-black text-slate-400">Status QC</span><div className="mt-1 font-black text-emerald-700">{getQcStatusLabel(selected)}</div></div><div><span className="font-black text-slate-400">MO Utama / TM Hasil</span><div className="mt-1 font-bold text-slate-800">{(selected.mainMoNumber||getPrimaryMoNumber(selected)||"-")+" / "+(qcForm.resultTmNumber||selected.resultTmNumber||"MENUNGGU QC/ADMIN")}</div></div><div><span className="font-black text-slate-400">Gudang Administrasi</span><div className="mt-1 font-bold text-slate-800">{selected.administrativeWarehouse||(Array.isArray(selected.administrativeWarehouses)?selected.administrativeWarehouses.join(", "):"")||getBatchAdministrativeWarehouse(selected,sku,systemConfig)||"-"}</div></div><div><span className="font-black text-slate-400">Lokasi Fisik / Tumpukan</span><div className="mt-1 font-bold text-slate-800">{getBatchPhysicalLocation(selected,systemConfig)||"-"}{selected.targetStack?` · ${selected.targetStack}`:""}</div></div><div><span className="font-black text-slate-400">Expiry</span><div className="mt-1 font-bold text-slate-800">{formatPdfDate(selected.expiryDate)||"-"}</div></div><div><span className="font-black text-slate-400">Stok Saat Ini</span><div className="mt-1 font-bold text-slate-800">{Number(selected.currentQty||0).toLocaleString("id-ID")} {sku?.unit||""}</div></div></div>):null;
                      })()}
                    </>
                  )}
'''
s=s[:start]+ui+s[end:]

# Pending QC card counts incoming MOs instead of incoming batches
s=s.replace('''<div className="text-[10px] font-black text-blue-500">BAHAN</div><div className="mt-1 text-2xl font-black text-blue-800">{inventoryBatches.filter(batch=>{const sku=skus.find(item=>item.id===batch.skuId);return sku?.type==="bulk"&&batch.qcStatus==="PENDING_QC";}).length}</div>''','''<div className="text-[10px] font-black text-blue-500">MO BAHAN</div><div className="mt-1 text-2xl font-black text-blue-800">{incomingQcMoGroups.filter(group=>group.items.some(item=>item.qcStatus==="PENDING_QC")).length}</div>''',1)

# History rows: incoming MO record should read as MO scope, not blank batch
old_start='{paginatedQcRecords.map(record=>(<tr key={record.id}'
pos=s.find(old_start)
if pos<0: raise SystemExit('QC history mapping start not found')
end=s.find('))}</tbody></table>',pos)
if end<0: raise SystemExit('QC history mapping end not found')
end += len('))}')
history=r'''{paginatedQcRecords.map(record=>(
                    <tr key={record.id} className="hover:bg-slate-50">
                      <td className="p-3 whitespace-nowrap">{new Date(record.inspectedAt).toLocaleString("id-ID")}</td>
                      <td className="p-3 font-black text-xs">{record.qcType==="INCOMING"?"BAHAN MASUK":"PRODUK JADI"}</td>
                      <td className="p-3">
                        {record.qcType==="INCOMING" && record.scope==="MO" ? (
                          <>
                            <div className="font-mono text-xs font-black text-blue-700">MO {record.moNumber||"-"}</div>
                            <div className="mt-1 text-xs text-slate-600">{record.itemCount||record.batchIds?.length||0} item/batch · {record.tmNumbers?.length||0} TM</div>
                          </>
                        ) : (
                          <>
                            <div className="font-mono text-xs font-black text-blue-700">{record.batchId}</div>
                            <div className="mt-1 text-xs text-slate-600">{record.skuName}</div>
                          </>
                        )}
                      </td>
                      <td className="p-3 text-xs">
                        {record.qcType==="INCOMING"
                          ? ((record.moNumber||"-")+" / "+((record.tmNumbers||[]).join(", ")||record.tmNumber||"-"))
                          : ((record.mainMoNumber||"-")+" / "+(record.resultTmNumber||"-"))}
                      </td>
                      <td className="p-3 text-center"><span className={"rounded-full px-3 py-1 text-[10px] font-black "+(["ACCEPT","RELEASE"].includes(record.decision)?"bg-emerald-100 text-emerald-700":record.decision==="HOLD"?"bg-amber-100 text-amber-700":"bg-red-100 text-red-700")}>{record.decision}</span></td>
                      <td className="p-3 text-xs">{record.inspectedBy}<div className="text-slate-400">{record.inspectedRole}</div></td>
                      <td className="p-3 text-center"><button type="button" onClick={()=>generateQcPdf(record)} className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-black text-blue-700 hover:bg-blue-100"><FileDown size={15}/> PDF QC</button></td>
                    </tr>
                  ))}'''
s=s[:pos]+history+s[end:]

# PDF metadata and incoming item snapshot table
meta_start=s.find('''    const meta=[\n      ["No. Rekaman",record.id]''')
meta_end=s.find('''    y+=8; box(L,y,W,18,235); txt("PARAMETER PEMERIKSAAN"''',meta_start)
if meta_start<0 or meta_end<0: raise SystemExit('QC PDF meta markers not found')
pdf_meta=r'''    const isMoIncoming = incoming && record.scope === "MO";
    const meta=isMoIncoming ? [
      ["No. Rekaman",record.id],
      ["Tanggal QC",new Date(record.inspectedAt).toLocaleString("id-ID")],
      ["No. MO",record.moNumber||"-"],
      ["Jumlah TM Bahan",String(record.tmNumbers?.length||0)],
      ["Jumlah Item / Batch",String(record.itemCount||record.batchIds?.length||0)],
      ["TM Bahan",(record.tmNumbers||[]).join(", ")||record.tmNumber||"-"],
      ["COA / Hasil Uji",record.coaNumber||"-"]
    ] : [
      ["No. Rekaman",record.id],["Tanggal QC",new Date(record.inspectedAt).toLocaleString("id-ID")],["SKU / Produk",`${record.skuId} - ${record.skuName}`],["Batch",record.batchId],
      incoming?["MO / TM Bahan",`${record.moNumber||"-"} / ${record.tmNumber||"-"}`]:["MO Utama / TM Hasil",`${record.mainMoNumber||"-"} / ${record.resultTmNumber||"-"}`],
      ["Gudang Administrasi",record.administrativeWarehouse||record.sourceWarehouse||"-"],["Lokasi Fisik / Tumpukan",`${record.physicalLocation||"-"}${record.targetStack?` / ${record.targetStack}`:""}`],["Expiry",formatPdfDate(record.expiryDate)||"-"],["Qty Saat QC",`${formatStockNumber(record.qtySnapshot)} ${record.unit||""}`],["COA / Hasil Uji",record.coaNumber||"-"]
    ];
    meta.forEach(([label,value])=>{box(L,y,W,18);txt(label,L+4,y+12,{size:6.2,bold:true});txt(":",L+120,y+12,{size:6.2});txt(value,L+130,y+12,{size:6.2,maxWidth:W-136,maxLines:1});y+=18;});

    if (isMoIncoming && Array.isArray(record.items) && record.items.length > 0) {
      y += 8;
      box(L,y,W,18,242);
      txt("DAFTAR TM / ITEM DALAM MO",L+4,y+12,{size:6.2,bold:true});
      y += 18;
      const cols=[72,158,62,105,W-397];
      const xs=[L]; cols.forEach(w=>xs.push(xs[xs.length-1]+w));
      box(L,y,W,18,248);
      ["TM Bahan","SKU / Bahan / Batch","Qty","Gudang Admin","Lokasi Fisik"].forEach((label,i)=>txt(label,(xs[i]+xs[i+1])/2,y+12,{size:5.4,bold:true,align:"center"}));
      y += 18;
      const shown=record.items.slice(0,4);
      shown.forEach(item=>{
        box(L,y,W,28);
        xs.slice(1,-1).forEach(x=>line(x,y,x,y+28,0.3));
        txt(item.tmNumber||"-",xs[0]+3,y+11,{size:5.2,bold:true,maxWidth:cols[0]-6,maxLines:2});
        txt(`${item.skuId||""} - ${item.skuName||""}\n${item.batchId||""}`,xs[1]+3,y+9,{size:4.9,maxWidth:cols[1]-6,maxLines:2});
        txt(`${formatStockNumber(item.qtySnapshot)} ${item.unit||""}`,xs[2]+cols[2]-3,y+16,{size:5.1,bold:true,align:"right",maxWidth:cols[2]-6,maxLines:1});
        txt(item.administrativeWarehouse||"-",xs[3]+3,y+11,{size:4.9,maxWidth:cols[3]-6,maxLines:2});
        txt(item.physicalLocation||"-",xs[4]+3,y+11,{size:4.9,maxWidth:cols[4]-6,maxLines:2});
        y += 28;
      });
      if (record.items.length > shown.length) {
        box(L,y,W,16);
        txt(`+ ${record.items.length-shown.length} item lainnya tersimpan pada rekaman digital QC ${record.id}`,L+4,y+11,{size:5.2,bold:true});
        y += 16;
      }
    }
'''
s=s[:meta_start]+pdf_meta+s[meta_end:]

# QC page wording
s=s.replace('''QC Bahan Masuk mengendalikan bahan yang boleh dipakai Rebagging. QC Produk Jadi mengendalikan batch yang boleh Outbound.''','''QC Bahan Masuk dilakukan per MO dan dapat mencakup beberapa TM bahan sekaligus. QC Produk Jadi tetap dilakukan per batch produksi sebelum Outbound.''',1)
s=s.replace('''{activeQcTab==="incoming" ? "Pemeriksaan Bahan Masuk" : "Pemeriksaan Produk Jadi"}''','''{activeQcTab==="incoming" ? "Pemeriksaan Bahan Masuk per MO" : "Pemeriksaan Produk Jadi per Batch"}''',1)
s=s.replace('''{qcSaving?"Menyimpan QC...":activeQcTab==="incoming"?"Simpan QC Bahan Masuk":"Simpan QC Produk Jadi"}''','''{qcSaving?"Menyimpan QC...":activeQcTab==="incoming"?"Simpan QC 1 MO":"Simpan QC Produk Jadi"}''',1)

p.write_text(s,encoding='utf-8')
print('QC per MO patch applied')
