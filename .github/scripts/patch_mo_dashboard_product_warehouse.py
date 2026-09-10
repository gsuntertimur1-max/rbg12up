from pathlib import Path

path = Path("src/App.jsx")
s = path.read_text(encoding="utf-8")

def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"Patch target not found: {label}")
    s = s.replace(old, new, 1)

# 1) Aggregate finished goods by product + final warehouse/stack inside each MO.
old = '''        const productRows = group.productRows.sort((a, b) => {
          const warehouseCompare = a.sourceWarehouses.localeCompare(
            b.sourceWarehouses,
            undefined,
            { numeric: true, sensitivity: "base" }
          );
          if (warehouseCompare !== 0) return warehouseCompare;
          return String(a.batchId).localeCompare(String(b.batchId), undefined, {
            numeric: true,
            sensitivity: "base",
          });
        });

        const consumedKg = group.rawUsedKg + group.rawDamageKg;'''
new = '''        const productRows = group.productRows.sort((a, b) => {
          const warehouseCompare = a.sourceWarehouses.localeCompare(
            b.sourceWarehouses,
            undefined,
            { numeric: true, sensitivity: "base" }
          );
          if (warehouseCompare !== 0) return warehouseCompare;
          return String(a.batchId).localeCompare(String(b.batchId), undefined, {
            numeric: true,
            sensitivity: "base",
          });
        });

        const finishedWarehouseMap = {};
        productRows.forEach((row) => {
          const warehouse = String(row.targetStack || "-");
          const key = `${row.skuId}|${warehouse}`;
          if (!finishedWarehouseMap[key]) {
            finishedWarehouseMap[key] = {
              key,
              skuId: row.skuId,
              name: row.name,
              warehouse,
              good: 0,
              process: 0,
              damage: 0,
              batchCount: 0,
              tmResults: new Set(),
              qcStatuses: new Set(),
            };
          }

          finishedWarehouseMap[key].good += Number(row.good || 0);
          finishedWarehouseMap[key].process += Number(row.process || 0);
          finishedWarehouseMap[key].damage += Number(row.damage || 0);
          finishedWarehouseMap[key].batchCount += 1;
          if (row.tmResult) finishedWarehouseMap[key].tmResults.add(row.tmResult);
          if (row.qcStatus) finishedWarehouseMap[key].qcStatuses.add(row.qcStatus);
        });

        const finishedWarehouseRows = Object.values(finishedWarehouseMap)
          .map((row) => ({
            ...row,
            tmResult: [...row.tmResults].sort().join(", "),
            qcStatus: [...row.qcStatuses].sort().join(", ") || "-",
            total: row.good + row.process + row.damage,
          }))
          .sort((a, b) => {
            const warehouseCompare = a.warehouse.localeCompare(
              b.warehouse,
              undefined,
              { numeric: true, sensitivity: "base" }
            );
            if (warehouseCompare !== 0) return warehouseCompare;
            return a.name.localeCompare(b.name, undefined, {
              numeric: true,
              sensitivity: "base",
            });
          });

        const consumedKg = group.rawUsedKg + group.rawDamageKg;'''
rep(old, new, "finished goods warehouse aggregation")

old = '''          warehouses,
          productRows,
          consumedKg,
          progress,'''
new = '''          warehouses,
          productRows,
          finishedWarehouseRows,
          consumedKg,
          progress,'''
rep(old, new, "return finishedWarehouseRows")

# 2) Avoid duplicated MO prefix in the card badge.
old = '''                                MO {group.mo}'''
new = '''                                {String(group.mo).trim().toUpperCase().startsWith("MO") ? group.mo : `MO ${group.mo}`}'''
rep(old, new, "MO badge duplicate")

# 3) Update compact sublabel.
old = '''                                {group.warehouses.length} gudang/SKU sumber · {group.productRows.length} batch produk jadi aktif'''
new = '''                                {group.warehouses.length} gudang/SKU sumber · {group.finishedWarehouseRows.length} produk/gudang · {group.productRows.length} batch aktif'''
rep(old, new, "MO compact sublabel")

# 4) Fix second MO label and replace per-batch finished-goods table with per-product/per-warehouse summary.
old = '''                          <h3 className="font-black text-slate-900">Produk Jadi dari MO {group.mo}</h3>'''
new = '''                          <h3 className="font-black text-slate-900">Produk Jadi · {String(group.mo).trim().toUpperCase().startsWith("MO") ? group.mo : `MO ${group.mo}`}</h3>'''
rep(old, new, "product heading MO duplicate")

old = '''                            <thead className="bg-slate-50 text-slate-500">
                              <tr>
                                <th className="p-3 text-left">Gudang Asal</th>
                                <th className="p-3 text-left">Produk</th>
                                <th className="p-3 text-left">TM Hasil</th>
                                <th className="p-3 text-left">Batch</th>
                                <th className="p-3 text-left">Tgl Produksi</th>
                                <th className="p-3 text-right">GOOD</th>
                                <th className="p-3 text-right">PROCESS</th>
                                <th className="p-3 text-right">DAMAGE</th>
                                <th className="p-3 text-left">Tumpukan</th>
                                <th className="p-3 text-center">QC</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {group.productRows.map(row=>(
                                <tr key={row.batchId}>
                                  <td className="p-3 font-bold text-slate-700">{row.sourceWarehouses}</td>
                                  <td className="p-3">
                                    <div className="font-mono text-[10px] font-black text-emerald-600">{row.skuId}</div>
                                    <div className="mt-1 font-bold text-slate-900">{row.name}</div>
                                  </td>
                                  <td className="p-3 text-xs font-bold text-green-700">{row.tmResult || "-"}</td>
                                  <td className="p-3 font-mono text-xs font-black text-blue-700">{row.batchId}</td>
                                  <td className="p-3 text-xs">{formatPdfDate(row.productionDate) || "-"}</td>
                                  <td className="p-3 text-right font-black text-emerald-700">{row.good.toLocaleString("id-ID")}</td>
                                  <td className="p-3 text-right font-bold text-amber-700">{row.process ? row.process.toLocaleString("id-ID") : "-"}</td>
                                  <td className="p-3 text-right font-bold text-red-700">{row.damage ? row.damage.toLocaleString("id-ID") : "-"}</td>
                                  <td className="p-3 font-bold text-slate-600">{row.targetStack}</td>
                                  <td className="p-3 text-center text-[10px] font-black text-slate-500">{row.qcStatus}</td>
                                </tr>
                              ))}
                            </tbody>'''
new = '''                            <thead className="bg-slate-50 text-slate-500">
                              <tr>
                                <th className="p-3 text-left">Produk</th>
                                <th className="p-3 text-left">Gudang / Tumpukan</th>
                                <th className="p-3 text-left">TM Hasil</th>
                                <th className="p-3 text-center">Batch</th>
                                <th className="p-3 text-right">GOOD</th>
                                <th className="p-3 text-right">PROCESS</th>
                                <th className="p-3 text-right">DAMAGE</th>
                                <th className="p-3 text-right">TOTAL</th>
                                <th className="p-3 text-center">QC</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {group.finishedWarehouseRows.map(row=>(
                                <tr key={row.key}>
                                  <td className="p-3">
                                    <div className="font-mono text-[10px] font-black text-emerald-600">{row.skuId}</div>
                                    <div className="mt-1 font-bold text-slate-900">{row.name}</div>
                                  </td>
                                  <td className="p-3 font-bold text-slate-700">{row.warehouse}</td>
                                  <td className="p-3 text-xs font-bold text-green-700">{row.tmResult || "-"}</td>
                                  <td className="p-3 text-center font-bold text-slate-600">{row.batchCount}</td>
                                  <td className="p-3 text-right font-black text-emerald-700">{row.good.toLocaleString("id-ID")}</td>
                                  <td className="p-3 text-right font-bold text-amber-700">{row.process ? row.process.toLocaleString("id-ID") : "-"}</td>
                                  <td className="p-3 text-right font-bold text-red-700">{row.damage ? row.damage.toLocaleString("id-ID") : "-"}</td>
                                  <td className="p-3 text-right font-black text-slate-900">{row.total.toLocaleString("id-ID")}</td>
                                  <td className="p-3 text-center text-[10px] font-black text-slate-500">{row.qcStatus}</td>
                                </tr>
                              ))}
                            </tbody>'''
rep(old, new, "finished goods per product warehouse table")

old = '''                          {group.productRows.length===0 && ('''
new = '''                          {group.finishedWarehouseRows.length===0 && ('''
rep(old, new, "finished empty state")

path.write_text(s, encoding="utf-8")
print("MO dashboard product/warehouse patch applied.")
