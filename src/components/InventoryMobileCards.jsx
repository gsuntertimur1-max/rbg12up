import React from "react";

export default function InventoryMobileCards({ skus, inventoryBatches, activeInvTab, onDownload, inferWeightPerPackKg }) {
  const rows = skus.filter((sku) => sku.type === activeInvTab).map((sku) => {
    const batches = inventoryBatches.filter((batch) => {
      if (batch.skuId !== sku.id) return false;
      return activeInvTab === "rebagged"
        ? Number(batch.currentQty || 0) > 0 || Number(batch.processQty || 0) > 0 || Number(batch.damageQty || 0) > 0
        : Number(batch.currentQty || 0) > 0;
    });
    const good = batches.reduce((sum, b) => sum + Number(b.currentQty || 0), 0);
    const process = batches.reduce((sum, b) => sum + Number(b.processQty || 0), 0);
    const damage = batches.reduce((sum, b) => sum + Number(b.damageQty || 0), 0);
    const total = activeInvTab === "rebagged" ? good + process + damage : good;
    const weight = inferWeightPerPackKg?.(sku) || 0;
    const goodKg = activeInvTab === "rebagged" ? batches.reduce((sum, b) => sum + (Number(b.goodKg) || Number(b.currentQty || 0) * (Number(b.weightPerPackKg) || weight)), 0) : 0;
    const sources = [...new Set(batches.map((b) => b.sourceWarehouse).filter(Boolean))].join(", ") || "-";
    return { sku, batches, good, process, damage, total, goodKg, sources };
  });

  return (
    <div className="space-y-3 md:hidden">
      {rows.map(({ sku, batches, good, process, damage, total, goodKg, sources }) => (
        <div key={sku.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="font-mono text-[10px] font-black text-blue-600">{sku.id}</div>
              <div className="mt-1 font-black text-slate-900">{sku.name}</div>
              <div className="mt-1 text-xs text-slate-500">{batches.length} batch · {sources}</div>
            </div>
            <button type="button" onClick={() => onDownload?.(sku)} className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-[10px] font-black text-blue-700">Kartu Stok</button>
          </div>
          {activeInvTab === "rebagged" ? (
            <div className="mt-4 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-xl bg-emerald-50 p-2"><div className="text-[9px] font-black text-emerald-600">GOOD</div><div className="mt-1 font-black text-emerald-800">{good.toLocaleString("id-ID")}</div></div>
              <div className="rounded-xl bg-amber-50 p-2"><div className="text-[9px] font-black text-amber-600">PROCESS</div><div className="mt-1 font-black text-amber-800">{process.toLocaleString("id-ID")}</div></div>
              <div className="rounded-xl bg-red-50 p-2"><div className="text-[9px] font-black text-red-600">DAMAGE</div><div className="mt-1 font-black text-red-800">{damage.toLocaleString("id-ID")}</div></div>
              <div className="col-span-3 rounded-xl bg-slate-50 p-2 text-xs font-bold text-slate-600">Total {total.toLocaleString("id-ID")} Pack · GOOD {goodKg.toLocaleString("id-ID", { maximumFractionDigits: 2 })} Kg</div>
            </div>
          ) : (
            <div className="mt-4 rounded-xl bg-blue-50 p-3"><div className="text-[10px] font-black text-blue-600">STOK AKTIF</div><div className="mt-1 text-xl font-black text-blue-900">{total.toLocaleString("id-ID")} <span className="text-xs">{sku.unit}</span></div></div>
          )}
        </div>
      ))}
    </div>
  );
}
