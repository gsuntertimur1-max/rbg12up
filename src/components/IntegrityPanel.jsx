import React from "react";

export default function IntegrityPanel({ report, onCheck }) {
  return (
    <div className="rounded-2xl border border-cyan-200 bg-cyan-50/60 p-4 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="text-xs font-black uppercase tracking-[0.14em] text-cyan-700">Integritas Data</div>
          <h4 className="mt-1 font-black text-slate-900">Cek Konsistensi Stok & Ledger</h4>
          <p className="mt-1 max-w-xl text-xs leading-5 text-slate-600">
            Membandingkan saldo batch dengan rekonstruksi Inbound, Rebagging, Mutasi, Outbound, dan resolusi PROCESS. Pemeriksaan ini tidak mengubah database.
          </p>
        </div>
        <button type="button" onClick={onCheck} className="shrink-0 rounded-xl bg-cyan-700 px-4 py-2.5 text-xs font-black text-white hover:bg-cyan-800">
          Cek Konsistensi Data
        </button>
      </div>

      {report && (
        <div className={`mt-4 rounded-xl border p-4 ${report.ok ? "border-emerald-200 bg-emerald-50" : "border-red-200 bg-red-50"}`}>
          <div className={`font-black ${report.ok ? "text-emerald-800" : "text-red-800"}`}>
            {report.ok ? "SESUAI — tidak ditemukan selisih saldo." : "PERLU DICEK — ditemukan ketidaksesuaian."}
          </div>
          <div className="mt-1 text-xs text-slate-600">
            {report.checkedBatches} batch · {report.checkedTransactions} transaksi diperiksa.
          </div>

          {report.criticalIssues?.length > 0 && (
            <div className="mt-3 space-y-1 text-xs font-bold text-red-700">
              {report.criticalIssues.slice(0, 10).map((item, i) => <div key={i}>• {item}</div>)}
            </div>
          )}

          {report.discrepancies?.length > 0 && (
            <div className="mt-3 max-h-64 space-y-2 overflow-auto">
              {report.discrepancies.slice(0, 30).map((item) => (
                <div key={item.batchId} className="rounded-lg border border-red-100 bg-white p-3 text-xs">
                  <div className="font-mono font-black text-red-700">{item.batchId}</div>
                  <div className="mt-1 grid grid-cols-1 gap-1 sm:grid-cols-3 text-slate-600">
                    <span>GOOD/Stok: {item.actualCurrent} → {item.expectedCurrent ?? "?"}</span>
                    <span>PROCESS: {item.actualProcess} → {item.expectedProcess ?? "?"}</span>
                    <span>DAMAGE: {item.actualDamage} → {item.expectedDamage ?? "?"}</span>
                  </div>
                  <div className="mt-1 text-slate-400">{item.reason}</div>
                </div>
              ))}
            </div>
          )}

          {report.warnings?.length > 0 && (
            <div className="mt-3 text-[11px] leading-5 text-amber-700">
              {report.warnings.map((item, i) => <div key={i}>• {item}</div>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
