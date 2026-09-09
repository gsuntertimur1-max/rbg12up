from pathlib import Path

path = Path("src/App.jsx")
s = path.read_text(encoding="utf-8")

def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"Patch target not found: {label}")
    s = s.replace(old, new, 1)

rep(
'''  txt("No. MO", 20, 133.5);
  txt(":", 79, 133.5);
  txt(tx.moNumber || "", 86, 133.5, { bold: true });
  txt("Tanggal", 341.5, 133.5);
  txt(":", 397, 133.5);
  txt(formatPdfDate(tx.productionDate || tx.date), 404, 133.5, { bold: true });''',
'''  txt("MO Utama", 20, 133.5);
  txt(":", 79, 133.5);
  txt(tx.mainMoNumber || getPrimaryMoNumber(tx) || "", 86, 133.5, { bold: true });
  txt("TM Hasil", 341.5, 133.5);
  txt(":", 397, 133.5);
  txt(tx.resultTmNumber || "", 404, 133.5, { bold: true });''',
"PDF MO/TM")

start = s.find('''  const sourceQty = Number(tx.sourceQty ?? tx.processedQty ?? tx.qtyChange ?? 0);''')
end = s.find('''

  section("4. PROSES REBAGGING", 299);''', start)
if start < 0 or end < 0:
    raise SystemExit("PDF material section not found")

block = r'''  const sourceQty = Number(tx.sourceQty ?? tx.processedQty ?? tx.qtyChange ?? 0);
  const outputQty = Number(tx.outputQty ?? tx.processedQty ?? 0);
  const finishedQty = Number(tx.finishedQty ?? tx.goodQty ?? tx.qtyChange ?? 0);
  const goodQty = Number(tx.goodQty ?? finishedQty ?? 0);
  const processQty = Number(tx.processQty ?? 0);
  const damageQty = Number(tx.damageQty ?? 0);
  const reconciledQty = goodQty + processQty + damageQty;
  const netWeightKg = Number(
    tx.netWeightKg ?? outputQty * Number(tx.weightPerPackKg || 0)
  );
  const sourceUnit = tx.sourceUnit || "KG";
  const finishedUnit = tx.finishedUnit || tx.unit || "Pack";
  const executor = tx.executor || "KOPEL JAYA";
  const supervisor = tx.supervisor || tx.operator || "";

  const groupedMaterials = {};
  if (Array.isArray(tx.materials)) {
    tx.materials.forEach((material) => {
      const key = `${material.skuId || "UNKNOWN"}|${material.unit || ""}`;
      if (!groupedMaterials[key]) {
        groupedMaterials[key] = {
          skuId: material.skuId || "",
          skuName: material.skuName || material.skuId || "",
          unit: material.unit || "",
          usedQty: 0,
          damageQty: 0,
          standardQty:
            material.standardQty !== null && material.standardQty !== undefined
              ? Number(material.standardQty)
              : null,
          batchIds: new Set(),
        };
      }

      const damage = Number(material.damageQty || 0);
      const total = Number(material.totalQty ?? material.qty ?? 0);
      const used = Number(material.usedQty ?? Math.max(0, total - damage));

      groupedMaterials[key].usedQty += used;
      groupedMaterials[key].damageQty += damage;
      if (material.batchId) groupedMaterials[key].batchIds.add(material.batchId);
    });
  }

  const materialRows = Object.values(groupedMaterials)
    .slice(0, 5)
    .map((material) => {
      const batchCount = material.batchIds.size;
      const name = `${material.skuId} ${material.skuName}${batchCount > 1 ? ` (${batchCount} batch)` : ""}`.trim();
      const standard =
        material.standardQty !== null && Number.isFinite(material.standardQty)
          ? `${formatStockNumber(material.standardQty)} ${material.unit}`
          : "-";
      const actual =
        `${formatStockNumber(material.usedQty)} ${material.unit}` +
        (material.damageQty > 0
          ? ` + rusak ${formatStockNumber(material.damageQty)}`
          : "");
      return [name, standard, actual, executor, supervisor];
    });

  const materials =
    materialRows.length > 0
      ? materialRows
      : [
          ["Bahan Baku Utama", "-", sourceQty ? sourceQty + " " + sourceUnit : "", executor, supervisor],
          ["Produk Jadi", "-", finishedQty ? finishedQty + " " + finishedUnit : "", executor, supervisor],
        ];

  materials.forEach((row, i) => {
    const y = 251.5 + i * 9;
    txt(row[0], 20, y, { maxWidth: 142 });
    txt(row[1], 234, y, { align: "center", size: 5.8 });
    txt(row[2], 320, y, { align: "center", size: 5.8 });
    txt(row[3], 359, y, { align: "center", size: 5.4 });
    txt(row[4], 474, y, { align: "center", size: 5.4 });
  });
'''
s = s[:start] + block + s[end:]

rep(
'''  section("6. REKONSILIASI HASIL PRODUKSI", 524);
  line(L, 533, R, 533);
  line(L, 561, R, 561);
  [166.7, 339.7, 448.2].forEach((x) => line(x, 533, x, 561));
  txt("Besaran Batch", 20, 540.5);
  txt("Jumlah Aktual Produk Jadi", 169, 540.5);
  txt("Selisih", 342, 540.5);
  txt("Paraf", 451, 540.5);
  txt(sourceQty ? sourceQty + " " + sourceUnit : "", 20, 553, { bold: true });
  txt(finishedQty ? finishedQty + " " + finishedUnit : "", 169, 553, { bold: true });
  if (Number.isFinite(sourceQty) && Number.isFinite(reconciledQty)) {
    txt(String(reconciledQty - sourceQty), 342, 553, { bold: true });
  }
  txt(
    "GOOD: " + goodQty + " | PROCESS: " + processQty + " | DAMAGE: " + damageQty,
    169,
    559,
    { size: 5.2, bold: true }
  );''',
'''  section("6. REKONSILIASI HASIL PRODUKSI", 524);
  line(L, 533, R, 533);
  line(L, 561, R, 561);
  [166.7, 339.7, 448.2].forEach((x) => line(x, 533, x, 561));
  txt("Output Produksi", 20, 540.5);
  txt("Berat Netto", 169, 540.5);
  txt("GOOD / PROCESS / DAMAGE", 342, 540.5, { size: 5.6 });
  txt("Status", 451, 540.5);
  txt(formatStockNumber(outputQty) + " Pack", 20, 553, { bold: true });
  txt(formatStockNumber(netWeightKg) + " Kg", 169, 553, { bold: true });
  txt("G:" + goodQty + " / P:" + processQty + " / D:" + damageQty, 342, 553, { bold: true, size: 5.7 });
  txt(
    Math.abs(reconciledQty - outputQty) <= 0.0001 ? "SEIMBANG" : "TIDAK SESUAI",
    451,
    553,
    { bold: true }
  );
  txt(
    "Bahan baku/kemasan direkap per SKU dan satuannya; tidak dibandingkan langsung dengan Pack produk jadi.",
    20,
    559,
    { size: 4.8, bold: true, maxWidth: 540 }
  );''',
"PDF reconciliation")

rep(
'''  const moNumber =
    inbound.find((x) => x.moNumber)?.moNumber ||
    batches.find((b) => b.moNumber)?.moNumber ||
    transactions.find(
      (t) =>
        t.type === "REBAGGING" &&
        (t.sourceSkuId === sku.id || matchingBatchIds.has(t.sourceBatchId)) &&
        t.moNumber
    )?.moNumber ||
    "";''',
'''  const moNumber = [
    ...new Set(
      [
        ...inbound.map((item) => item.moNumber),
        ...batches.map((batch) => batch.moNumber),
      ].filter(Boolean)
    ),
  ].join(", ");''',
"stock card MO list")

rep(
'''    ["Jumlah Karung/Karton", currentStock ? formatStockNumber(currentStock) + " " + (sku.unit || "") : ""],''',
'''    ["Jumlah Stok Aktif", currentStock ? formatStockNumber(currentStock) + " " + (sku.unit || "") : ""],''',
"stock card meta")

rep(
'''    ["Jumlah (kg)", (132 + 210) / 2],''',
'''    [`Jumlah (${String(sku.unit || "").toUpperCase() || "UNIT"})`, (132 + 210) / 2],''',
"stock card unit in")

rep(
'''    ["Jumlah (kg)", (407 + 468) / 2],''',
'''    [`Jumlah (${String(sku.unit || "").toUpperCase() || "UNIT"})`, (407 + 468) / 2],''',
"stock card unit out")

path.write_text(s, encoding="utf-8")
print("PDF and stock card patch applied.")
