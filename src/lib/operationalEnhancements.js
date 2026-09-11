import * as XLSX from "xlsx";

const EPSILON = 0.0001;
const numberOf = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};
const textOf = (value) => String(value ?? "").trim();
const absDiff = (a, b) => Math.abs(numberOf(a) - numberOf(b));

export const checkClosedPeriod = (dateValue, closedThroughMonth = "") => {
  const locked = textOf(closedThroughMonth);
  if (!locked) return { closed: false, transactionMonth: "", closedThroughMonth: "" };
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) {
    return { closed: false, transactionMonth: "", closedThroughMonth: locked };
  }
  const transactionMonth = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
  return {
    closed: transactionMonth <= locked,
    transactionMonth,
    closedThroughMonth: locked,
  };
};

const ensureLedger = (ledger, batchId) => {
  const key = textOf(batchId);
  if (!key) return null;
  if (!ledger.has(key)) {
    ledger.set(key, { batchId: key, current: 0, process: 0, damage: 0, sources: [] });
  }
  return ledger.get(key);
};

export const buildStockIntegrityReport = (transactions = [], inventoryBatches = []) => {
  const ledger = new Map();
  const warnings = [];
  const criticalIssues = [];
  const duplicateBatchIds = [];
  const seenBatchIds = new Set();

  inventoryBatches.forEach((batch) => {
    const id = textOf(batch?.batchId);
    if (!id) return;
    if (seenBatchIds.has(id)) duplicateBatchIds.push(id);
    seenBatchIds.add(id);
  });
  if (duplicateBatchIds.length) {
    criticalIssues.push(`Batch ID duplikat: ${[...new Set(duplicateBatchIds)].join(", ")}`);
  }

  const sortedTransactions = [...transactions].sort(
    (a, b) => new Date(a?.date || 0).getTime() - new Date(b?.date || 0).getTime()
  );

  sortedTransactions.forEach((tx) => {
    const type = textOf(tx?.type).toUpperCase();
    if (!type) return;

    if (type === "INBOUND") {
      const line = ensureLedger(ledger, tx.batchId);
      if (line) {
        line.current += numberOf(tx.qtyChange);
        line.sources.push(tx.id || type);
      }
      return;
    }

    if (type === "REBAGGING") {
      const target = ensureLedger(ledger, tx.batchId);
      if (target) {
        target.current += numberOf(tx.goodQty ?? tx.qtyChange);
        target.process += numberOf(tx.processQty);
        target.damage += numberOf(tx.damageQty);
        target.sources.push(tx.id || type);
      }

      const materials = Array.isArray(tx.materials) ? tx.materials : [];
      if (!materials.length && Array.isArray(tx.sourceBatchIds) && tx.sourceBatchIds.length) {
        warnings.push(`Transaksi ${tx.id || "REBAGGING"} tidak memiliki snapshot material lengkap; rekonsiliasi bahan dapat bersifat parsial.`);
      }
      materials.forEach((material) => {
        const source = ensureLedger(ledger, material.batchId);
        if (!source) return;
        const totalMaterial = numberOf(
          material.qty ??
          material.totalQty ??
          (numberOf(material.usedQty) + numberOf(material.damageQty))
        );
        source.current -= totalMaterial;
        source.sources.push(tx.id || type);
      });
      return;
    }

    if (type === "OUTBOUND") {
      const line = ensureLedger(ledger, tx.batchId);
      if (line) {
        line.current -= numberOf(tx.qtyChange);
        line.sources.push(tx.id || type);
      }
      return;
    }

    if (type === "MUTATION") {
      const qty = numberOf(tx.mutationQty);
      const source = ensureLedger(ledger, tx.sourceBatchId);
      const target = ensureLedger(ledger, tx.targetBatchId || tx.batchId);
      if (source) {
        source.current -= qty;
        source.sources.push(tx.id || type);
      }
      if (target) {
        target.current += qty;
        target.sources.push(tx.id || type);
      }
      return;
    }

    if (type === "PROCESS_TO_GOOD") {
      const qty = numberOf(tx.resolutionQty);
      const line = ensureLedger(ledger, tx.batchId);
      if (line) {
        line.process -= qty;
        line.current += qty;
        line.sources.push(tx.id || type);
      }
      return;
    }

    if (type === "PROCESS_TO_DAMAGE") {
      const qty = numberOf(tx.resolutionQty);
      const line = ensureLedger(ledger, tx.batchId);
      if (line) {
        line.process -= qty;
        line.damage += qty;
        line.sources.push(tx.id || type);
      }
      return;
    }

    if (type === "MATERIAL_DAMAGE" && tx.stockAlreadyApplied !== true) {
      const qty = numberOf(tx.damageQty || tx.qtyChange);
      const line = ensureLedger(ledger, tx.batchId);
      if (line) {
        line.current -= qty;
        line.sources.push(tx.id || type);
      }
    }
  });

  const actualMap = new Map(
    inventoryBatches
      .filter((batch) => textOf(batch?.batchId))
      .map((batch) => [textOf(batch.batchId), batch])
  );
  const discrepancies = [];

  inventoryBatches.forEach((batch) => {
    const batchId = textOf(batch.batchId);
    const expected = ledger.get(batchId);
    const actualCurrent = numberOf(batch.currentQty);
    const actualProcess = numberOf(batch.processQty);
    const actualDamage = numberOf(batch.damageQty);

    if (actualCurrent < -EPSILON || actualProcess < -EPSILON || actualDamage < -EPSILON) {
      criticalIssues.push(`Batch ${batchId} memiliki saldo negatif.`);
    }

    if (!expected) {
      if (Math.abs(actualCurrent) > EPSILON || Math.abs(actualProcess) > EPSILON || Math.abs(actualDamage) > EPSILON) {
        discrepancies.push({
          batchId,
          actualCurrent,
          expectedCurrent: null,
          actualProcess,
          expectedProcess: null,
          actualDamage,
          expectedDamage: null,
          reason: "Batch aktif tidak memiliki jejak ledger yang dapat direkonstruksi.",
        });
      }
      return;
    }

    const currentDiff = absDiff(actualCurrent, expected.current);
    const processDiff = absDiff(actualProcess, expected.process);
    const damageDiff = absDiff(actualDamage, expected.damage);
    if (currentDiff > EPSILON || processDiff > EPSILON || damageDiff > EPSILON) {
      discrepancies.push({
        batchId,
        actualCurrent,
        expectedCurrent: expected.current,
        actualProcess,
        expectedProcess: expected.process,
        actualDamage,
        expectedDamage: expected.damage,
        reason: "Saldo batch berbeda dengan rekonstruksi transaksi.",
      });
    }
  });

  ledger.forEach((expected, batchId) => {
    if (actualMap.has(batchId)) return;
    if (
      Math.abs(expected.current) > EPSILON ||
      Math.abs(expected.process) > EPSILON ||
      Math.abs(expected.damage) > EPSILON
    ) {
      criticalIssues.push(
        `Ledger batch ${batchId} masih memiliki saldo tetapi dokumen batch tidak ditemukan.`
      );
    }
  });

  return {
    ok: discrepancies.length === 0 && criticalIssues.length === 0,
    generatedAt: new Date().toISOString(),
    checkedBatches: inventoryBatches.length,
    checkedTransactions: transactions.length,
    discrepancies,
    criticalIssues: [...new Set(criticalIssues)],
    warnings: [...new Set(warnings)].slice(0, 20),
  };
};

const signatureDuplicates = (rows, builder) => {
  const seen = new Map();
  const duplicates = [];
  rows.forEach((row, index) => {
    const signature = builder(row);
    if (!signature) return;
    if (seen.has(signature)) duplicates.push([seen.get(signature), index + 1]);
    else seen.set(signature, index + 1);
  });
  return duplicates;
};

export const buildLegacyImportPreview = ({
  importedInbound = [],
  importedRebagging = [],
  importedQc = [],
  importedOutbound = [],
} = {}) => {
  const blockingIssues = [];
  const warnings = [];
  const qcTmByMo = new Map();
  const qcTms = new Set();

  importedQc.forEach((row) => {
    const tm = textOf(row.resultTmNumber).toUpperCase();
    const mo = textOf(row.moNumber).toUpperCase();
    if (tm) qcTms.add(tm);
    if (mo && tm) qcTmByMo.set(mo, tm);
    if (!tm) blockingIssues.push(`QC baris ${row.rowNo}: TM Hasil kosong.`);
  });

  const productionByTm = new Map();
  const earliestProductionByTm = new Map();
  importedRebagging.forEach((row) => {
    const mo = textOf(row.moNumber).toUpperCase();
    const tm = (textOf(row.resultTmNumber) || qcTmByMo.get(mo) || "").toUpperCase();
    if (!tm) {
      blockingIssues.push(`Rebagging baris ${row.rowNo}: TM Hasil tidak dapat ditentukan.`);
      return;
    }
    productionByTm.set(tm, numberOf(productionByTm.get(tm)) + numberOf(row.productQty));
    const date = new Date(row.date);
    if (!Number.isNaN(date.getTime())) {
      const current = earliestProductionByTm.get(tm);
      if (!current || date.getTime() < current.getTime()) earliestProductionByTm.set(tm, date);
    }
  });

  const outboundByTm = new Map();
  importedOutbound.forEach((row) => {
    const tm = textOf(row.resultTmNumber).toUpperCase();
    if (!tm) {
      blockingIssues.push(`Outbound baris ${row.rowNo}: TM Hasil kosong.`);
      return;
    }
    if (!qcTms.has(tm) && !productionByTm.has(tm)) {
      blockingIssues.push(`Outbound baris ${row.rowNo}: TM Hasil ${tm} tidak ditemukan pada QC/Rebagging.`);
    }
    const productionDate = earliestProductionByTm.get(tm);
    const outboundDate = new Date(row.date);
    if (
      productionDate &&
      !Number.isNaN(outboundDate.getTime()) &&
      outboundDate.getTime() < productionDate.getTime()
    ) {
      blockingIssues.push(
        `Outbound baris ${row.rowNo}: tanggal ${row.date} lebih awal dari produksi TM ${tm} (${productionDate.toISOString().slice(0, 10)}).`
      );
    }
    outboundByTm.set(tm, numberOf(outboundByTm.get(tm)) + numberOf(row.qty));
  });

  let predictedFinishedBalance = 0;
  const tmBalances = [];
  productionByTm.forEach((produced, tm) => {
    const outbound = numberOf(outboundByTm.get(tm));
    const balance = produced - outbound;
    predictedFinishedBalance += balance;
    tmBalances.push({ tm, produced, outbound, balance });
    if (balance < -EPSILON) {
      blockingIssues.push(`TM ${tm}: Outbound (${outbound}) melebihi hasil produksi (${produced}).`);
    }
  });

  outboundByTm.forEach((outbound, tm) => {
    if (productionByTm.has(tm)) return;
    if (outbound > EPSILON) blockingIssues.push(`TM ${tm}: ada Outbound ${outbound} tanpa hasil produksi.`);
  });

  const duplicateChecks = [
    ["Inbound", importedInbound, (r) => `${r.date}|${r.moNumber}|${r.tmNumber}|${r.skuId}|${r.qty}`],
    ["Rebagging", importedRebagging, (r) => `${r.date}|${r.moNumber}|${r.resultTmNumber}|${r.productSkuId}|${r.productQty}`],
    ["QC", importedQc, (r) => `${r.date}|${r.moNumber}|${r.resultTmNumber}|${r.skuId}|${r.qty}`],
    ["Outbound", importedOutbound, (r) => `${r.date}|${r.soNumber}|${r.resultTmNumber}|${r.skuId}|${r.qty}`],
  ];
  duplicateChecks.forEach(([name, rows, builder]) => {
    const duplicates = signatureDuplicates(rows, builder);
    if (duplicates.length) warnings.push(`${name}: ${duplicates.length} kemungkinan baris duplikat.`);
  });

  const allDates = [
    ...importedInbound.map((r) => r.date),
    ...importedRebagging.map((r) => r.date),
    ...importedQc.map((r) => r.date),
    ...importedOutbound.map((r) => r.date),
  ]
    .map((value) => new Date(value))
    .filter((date) => !Number.isNaN(date.getTime()))
    .sort((a, b) => a - b);

  return {
    counts: {
      inbound: importedInbound.length,
      rebagging: importedRebagging.length,
      qc: importedQc.length,
      outbound: importedOutbound.length,
      tm: new Set([...productionByTm.keys(), ...qcTms]).size,
    },
    earliestDate: allDates[0]?.toISOString().slice(0, 10) || "-",
    latestDate: allDates.at(-1)?.toISOString().slice(0, 10) || "-",
    predictedFinishedBalance,
    tmBalances: tmBalances.sort((a, b) => a.tm.localeCompare(b.tm)),
    blockingIssues: [...new Set(blockingIssues)],
    warnings: [...new Set(warnings)],
  };
};

export const formatLegacyImportPreview = (preview) => {
  const lines = [
    "PREVIEW IMPORT DATA LAMA",
    "",
    `Inbound     : ${preview.counts.inbound} baris`,
    `Rebagging   : ${preview.counts.rebagging} baris`,
    `QC          : ${preview.counts.qc} baris`,
    `Outbound    : ${preview.counts.outbound} baris`,
    `TM Hasil    : ${preview.counts.tm}`,
    `Periode     : ${preview.earliestDate} s.d. ${preview.latestDate}`,
    `Prediksi saldo produk jadi: ${preview.predictedFinishedBalance.toLocaleString("id-ID")}`,
  ];
  if (preview.blockingIssues.length) {
    lines.push("", "ERROR PEMBLOKIR:");
    preview.blockingIssues.slice(0, 12).forEach((item, i) => lines.push(`${i + 1}. ${item}`));
    if (preview.blockingIssues.length > 12) lines.push(`... ${preview.blockingIssues.length - 12} error lainnya`);
  }
  if (preview.warnings.length) {
    lines.push("", "PERINGATAN:");
    preview.warnings.slice(0, 8).forEach((item, i) => lines.push(`${i + 1}. ${item}`));
  }
  return lines.join("\n");
};

const encodeArchiveCell = (value) => {
  if (value === undefined) return "";
  if (value === null) return "__JSON__:null";
  if (value instanceof Date) return value.toISOString();
  if (Array.isArray(value) || (typeof value === "object" && value !== null)) {
    return `__JSON__:${JSON.stringify(value)}`;
  }
  return value;
};

const decodeArchiveCell = (value) => {
  if (typeof value !== "string") return value;
  if (value === "[object Object]") {
    throw new Error("Arsip memakai format lama yang kehilangan struktur object. Buat arsip baru dari versi aplikasi terbaru sebelum Restore.");
  }
  if (!value.startsWith("__JSON__:")) return value;
  return JSON.parse(value.slice("__JSON__:".length));
};

export const serializeOperationalArchiveRows = (rows = []) =>
  rows.map((row) =>
    Object.fromEntries(Object.entries(row || {}).map(([key, value]) => [key, encodeArchiveCell(value)]))
  );

export const parseOperationalArchiveWorkbook = (workbook) => {
  const sheetMap = [
    ["transactions", "Transactions"],
    ["batches", "Batches"],
    ["tm_mo_bindings", "TM-MO"],
    ["batch_sequences", "Batch Sequence"],
    ["result_tms", "Legacy TM"],
    ["qc_records", "Quality Control"],
  ];
  const result = {};
  sheetMap.forEach(([collectionName, sheetName]) => {
    const sheet = workbook.Sheets[sheetName];
    if (!sheet) {
      result[collectionName] = [];
      return;
    }
    const rawRows = XLSX.utils.sheet_to_json(sheet, { defval: "", raw: true });
    result[collectionName] = rawRows
      .filter((row) => textOf(row.Keterangan) !== "Tidak ada data")
      .map((row, index) => {
        const decoded = Object.fromEntries(
          Object.entries(row).map(([key, value]) => [key, decodeArchiveCell(value)])
        );
        const docId = textOf(decoded._docId);
        if (!docId) throw new Error(`${sheetName} baris ${index + 2}: _docId tidak ditemukan.`);
        return decoded;
      });
  });
  return result;
};
