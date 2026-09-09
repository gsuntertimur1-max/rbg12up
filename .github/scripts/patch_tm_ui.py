from pathlib import Path

path = Path("src/App.jsx")
s = path.read_text(encoding="utf-8")

def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"Patch target not found: {label}")
    s = s.replace(old, new, 1)

# Group traceability by TM Hasil + MO Utama while keeping current UI data shape.
start = s.find("  const traceabilityResults = useMemo(() => {")
end = s.find("\n\n  const handleDownloadProductionReport = () => {", start)
if start < 0 or end < 0:
    raise SystemExit("Patch target not found: traceability block")

new_trace = r'''  const traceabilityResults = useMemo(() => {
    const query = String(traceTmQuery || "").trim().toUpperCase();
    if (!query) return [];

    const productions = transactions.filter(
      (t) =>
        t.type === "REBAGGING" &&
        String(t.resultTmNumber || "").toUpperCase().includes(query)
    );
    const grouped = {};

    productions.forEach((production) => {
      const resultTmNumber = String(production.resultTmNumber || "").trim();
      const mainMoNumber = getPrimaryMoNumber(production);
      const key = `${resultTmNumber.toUpperCase()}|${mainMoNumber.toUpperCase()}`;

      if (!grouped[key]) {
        grouped[key] = { resultTmNumber, mainMoNumber, productions: [] };
      }
      grouped[key].productions.push(production);
    });

    return Object.entries(grouped).map(([key, group]) => {
      const productionIds = new Set(group.productions.map((p) => p.id));
      const sortedProductions = group.productions
        .slice()
        .sort((a, b) => new Date(a.date) - new Date(b.date));
      const first = sortedProductions[0];

      const totals = sortedProductions.reduce(
        (acc, p) => {
          acc.outputPack += Number(p.outputQty ?? p.processedQty ?? 0);
          acc.outputKg += Number(p.netWeightKg || 0);
          return acc;
        },
        { outputPack: 0, outputKg: 0 }
      );

      const production = {
        ...first,
        id: `TRACE-${key}`,
        mainMoNumber: group.mainMoNumber,
        resultTmNumber: group.resultTmNumber,
        batchCount: sortedProductions.length,
        outputQty: totals.outputPack,
        netWeightKg: totals.outputKg,
        materials: sortedProductions.flatMap((p) =>
          (Array.isArray(p.materials) ? p.materials : []).map((material) => ({
            ...material,
            productionBatchId: p.batchId || "",
            productionDate: p.date || "",
          }))
        ),
      };

      const outbound = transactions.filter(
        (t) =>
          t.type === "OUTBOUND" &&
          String(t.resultTmNumber || "").trim().toUpperCase() ===
            group.resultTmNumber.toUpperCase()
      );

      const materialDamage = transactions.filter(
        (t) =>
          t.type === "MATERIAL_DAMAGE" &&
          productionIds.has(String(t.parentTransactionId || ""))
      );

      return { production, outbound, materialDamage };
    });
  }, [transactions, traceTmQuery]);'''

s = s[:start] + new_trace + s[end:]

rep(
'''        Produk: t.skuName,
        "TM Hasil": t.resultTmNumber || "",''',
'''        Produk: t.skuName,
        "Nomor Batch": t.batchId || "",
        "MO Utama": getPrimaryMoNumber(t),
        "TM Hasil": t.resultTmNumber || "",''',
"production report batch/main MO")

rep(
'''                          <p className="mt-2 text-xs text-green-700">TM Hasil dibuat pada proses Rebagging, menjadi referensi utama Outbound, dan harus unik untuk setiap produksi.</p>''',
'''                          <div className="mt-2 space-y-1 text-xs text-green-700">
                            <p>TM Hasil boleh digunakan kembali selama tetap terikat pada MO Utama yang sama.</p>
                            <p className="font-bold">Batch otomatis: {formData.rebagTargetSkuId || 'SKU'}-{getProductionDateCode(formData.useBackdate && formData.backdateDateTime ? new Date(formData.backdateDateTime) : new Date()) || 'YYMMDD'}-NN</p>
                          </div>''',
"TM hint")

rep(
'''                                  {activeRebagMaterials.map((item)=>(''',
'''                                  {activeRebagMaterials.map((item,index)=>(''',
"composition material index")

rep(
'''                                      {item.calculationMode === 'per_output' && (
                                        <span className="rounded-full bg-green-50 px-1.5 py-0.5 text-[9px] font-black text-green-700">
                                          AUTO 1/{item.outputPerUnit}
                                        </span>
                                      )}''',
'''                                      {index === 0 && (
                                        <span className="rounded-full bg-violet-50 px-1.5 py-0.5 text-[9px] font-black text-violet-700">
                                          MO UTAMA
                                        </span>
                                      )}
                                      {item.calculationMode === 'per_output' && (
                                        <span className="rounded-full bg-green-50 px-1.5 py-0.5 text-[9px] font-black text-green-700">
                                          AUTO 1/{item.outputPerUnit}
                                        </span>
                                      )}''',
"composition main MO badge")

rep(
'''                            {activeRebagMaterials.map((recipeMaterial)=>{''',
'''                            {activeRebagMaterials.map((recipeMaterial, materialIndex)=>{''',
"material card index")

rep(
'''                                      {recipeMaterial.calculationMode === 'per_output' && (
                                        <span className="rounded-full bg-green-50 px-2.5 py-1 text-[10px] font-black text-green-700">
                                          AUTO · 1/{recipeMaterial.outputPerUnit}
                                        </span>
                                      )}''',
'''                                      {materialIndex === 0 && (
                                        <span className="rounded-full bg-violet-50 px-2.5 py-1 text-[10px] font-black text-violet-700">
                                          MO UTAMA / PENGIKAT TM
                                        </span>
                                      )}
                                      {recipeMaterial.calculationMode === 'per_output' && (
                                        <span className="rounded-full bg-green-50 px-2.5 py-1 text-[10px] font-black text-green-700">
                                          AUTO · 1/{recipeMaterial.outputPerUnit}
                                        </span>
                                      )}''',
"material main MO badge")

rep(
'''                    <p className="mt-1 text-xs text-slate-500">Telusuri bahan, MO/TM sumber, komposisi versi produksi, material damage, dan outbound.</p>''',
'''                    <p className="mt-1 text-xs text-slate-500">Satu TM Hasil dapat memiliki beberapa batch produksi selama semuanya terikat ke MO Utama yang sama.</p>''',
"traceability description")

rep(
'''                            <div className="mt-1 text-xs text-slate-500">
                              {new Date(production.date).toLocaleString('id-ID')} · Komposisi v{production.recipeVersion||1}
                            </div>''',
'''                            <div className="mt-1 text-xs text-slate-500">
                              MO Utama: <span className="font-black text-violet-700">{getPrimaryMoNumber(production)||'-'}</span> · {production.batchCount||1} batch produksi
                            </div>''',
"traceability header")

rep(
'''                                <tr key={`${production.id}-${material.skuId}`}>''',
'''                                <tr key={`${production.id}-${material.productionBatchId||''}-${material.skuId}`}>''',
"trace material key")

rep(
'''                                  <td className="p-2 font-mono text-[10px] text-slate-500">{material.batchId}</td>''',
'''                                  <td className="p-2 text-[10px] text-slate-500">
                                    <div className="font-mono font-black text-blue-600">Prod: {material.productionBatchId||'-'}</div>
                                    <div className="mt-0.5 font-mono">Bahan: {material.batchId}</div>
                                  </td>''',
"trace batch display")

path.write_text(s, encoding="utf-8")
print("TM UI/report patch applied.")
