import React from "react";

const Action = ({ label, detail, value, tone, onClick, disabled = false }) => {
  const tones = {
    red: "border-red-200 bg-red-50 text-red-800",
    orange: "border-orange-200 bg-orange-50 text-orange-800",
    blue: "border-blue-200 bg-blue-50 text-blue-800",
    amber: "border-amber-200 bg-amber-50 text-amber-800",
  };
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`min-h-24 rounded-2xl border p-4 text-left transition-all ${tones[tone] || tones.blue} ${disabled ? "cursor-default opacity-70" : "hover:-translate-y-0.5 hover:shadow-md"}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-black uppercase tracking-wider">{label}</div>
          <div className="mt-1 text-xs font-semibold opacity-70">{detail}</div>
        </div>
        <div className="text-2xl font-black">{Number(value || 0).toLocaleString("id-ID")}</div>
      </div>
    </button>
  );
};

export default function OperationalActionCenter({ summary, onInventoryAction, onQcAction, onProcessAction }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 sm:p-5 shadow-sm">
      <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">Action Center</div>
          <h3 className="mt-1 font-black text-slate-900">Perlu Tindakan</h3>
        </div>
        <div className="text-[11px] font-bold text-slate-400">Tekan kartu untuk menuju tindak lanjut.</div>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Action label="Expired" detail="Batch perlu ditangani" value={summary.expiredCount} tone="red" onClick={() => onInventoryAction?.("expired")} disabled={!onInventoryAction}/>
        <Action label="≤ 30 Hari" detail="Prioritas FEFO" value={summary.nearExpired30} tone="orange" onClick={() => onInventoryAction?.("near30")} disabled={!onInventoryAction}/>
        <Action label="Pending QC" detail="Menunggu keputusan QC" value={summary.pendingQcTotal} tone="blue" onClick={onQcAction} disabled={!onQcAction}/>
        <Action label="Process" detail="Perlu resolusi GOOD/DAMAGE" value={summary.processPack} tone="amber" onClick={onProcessAction} disabled={!onProcessAction}/>
      </div>
    </div>
  );
}
