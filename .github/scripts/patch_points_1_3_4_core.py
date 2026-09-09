from pathlib import Path

path = Path("src/App.jsx")
s = path.read_text(encoding="utf-8")

def rep(old, new, label, count=1):
    global s
    if old not in s:
        raise SystemExit(f"Patch target not found: {label}")
    s = s.replace(old, new, count)

# 1) Batch expiry / FEFO-FIFO helpers and multi-allocation normalization.
marker = '''const getSuggestedMaterialStandard = (targetSku, materialSku) => {'''
helpers = r'''const getBatchExpiryInfo = (batch, referenceDate = new Date()) => {
  const raw = batch?.expiryDate || batch?.expired || batch?.expiry || "";
  if (!raw) {
    return {
      hasExpiry: false,
      isExpired: false,
      daysRemaining: null,
      label: "FIFO",
      priority: 999999,
    };
  }

  const expiry = new Date(raw);
  if (Number.isNaN(expiry.getTime())) {
    return {
      hasExpiry: false,
      isExpired: false,
      daysRemaining: null,
      label: "FIFO",
      priority: 999999,
    };
  }

  const ref = new Date(referenceDate);
  ref.setHours(0, 0, 0, 0);
  expiry.setHours(23, 59, 59, 999);
  const daysRemaining = Math.ceil((expiry.getTime() - ref.getTime()) / 86400000);

  let label = "FEFO";
  if (daysRemaining < 0) label = "EXPIRED";
  else if (daysRemaining <= 30) label = "< 30 HARI";
  else if (daysRemaining <= 60) label = "< 60 HARI";
  else if (daysRemaining <= 90) label = "< 90 HARI";

  return {
    hasExpiry: true,
    isExpired: daysRemaining < 0,
    daysRemaining,
    label,
    priority: expiry.getTime(),
  };
};

const sortBatchesFefoFifo = (batches, referenceDate = new Date()) =>
  [...batches].sort((a, b) => {
    const aExpiry = getBatchExpiryInfo(a, referenceDate);
    const bExpiry = getBatchExpiryInfo(b, referenceDate);

    if (aExpiry.hasExpiry && bExpiry.hasExpiry) {
      if (aExpiry.priority !== bExpiry.priority) return aExpiry.priority - bExpiry.priority;
    } else if (aExpiry.hasExpiry !== bExpiry.hasExpiry) {
      return aExpiry.hasExpiry ? -1 : 1;
    }

    const aDate = new Date(a.date || a.productionDate || 0).getTime() || 0;
    const bDate = new Date(b.date || b.productionDate || 0).getTime() || 0;
    return aDate - bDate;
  });

const getBatchRecommendationLabel = (batch, allBatches, referenceDate = new Date()) => {
  const sorted = sortBatchesFefoFifo(allBatches, referenceDate);
  const firstUsable = sorted.find((item) => !getBatchExpiryInfo(item, referenceDate).isExpired);
  const expiryInfo = getBatchExpiryInfo(batch, referenceDate);
  const isRecommended = firstUsable?.batchId === batch?.batchId;

  if (expiryInfo.isExpired) return "EXPIRED";
  if (isRecommended) return expiryInfo.hasExpiry ? "REKOMENDASI FEFO" : "REKOMENDASI FIFO";
  return expiryInfo.label;
};

const createRebagAllocation = () => ({
  rowId: `SRC-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
  batchId: "",
  qty: "",
  damageQty: "",
});

const normalizeRebagAllocations = (selection) => {
  if (Array.isArray(selection)) return selection;
  if (Array.isArray(selection?.allocations)) return selection.allocations;
  if (selection && (selection.batchId || selection.qty || selection.damageQty)) {
    return [{
      rowId: selection.rowId || `LEGACY-${selection.batchId || Date.now()}`,
      batchId: selection.batchId || "",
      qty: selection.qty || "",
      damageQty: selection.damageQty || "",
    }];
  }
  return [];
};

'''
rep(marker, helpers + marker, "insert FEFO/multibatch helpers")

# Initialize material source rows when product target changes.
old = '''  const handleRebagTargetChange = (value) => {
    setFormData((prev) => ({
      ...prev,
      rebagTargetSkuId: value,
      bulkSkuId: "",
      bulkBatchId: "",
      rebagResultTmNumber: "",
    }));
    setRebagMaterialSelections({});
  };'''
new = '''  const handleRebagTargetChange = (value) => {
    setFormData((prev) => ({
      ...prev,
      rebagTargetSkuId: value,
      bulkSkuId: "",
      bulkBatchId: "",
      rebagResultTmNumber: "",
    }));

    const targetSku = skus.find((s) => s.id === value);
    const recipe = getRebagRecipe(targetSku, rebagRecipes);
    const initialSelections = {};
    normalizeRecipeMaterials(recipe).forEach((material) => {
      initialSelections[material.skuId] = [createRebagAllocation()];
    });
    setRebagMaterialSelections(initialSelections);
  };

  const updateRebagAllocation = (skuId, rowId, field, value) => {
    setRebagMaterialSelections((prev) => {
      const rows = normalizeRebagAllocations(prev[skuId]);
      return {
        ...prev,
        [skuId]: rows.map((row) =>
          row.rowId === rowId ? { ...row, [field]: value } : row
        ),
      };
    });
  };

  const addRebagAllocation = (skuId) => {
    setRebagMaterialSelections((prev) => ({
      ...prev,
      [skuId]: [
        ...normalizeRebagAllocations(prev[skuId]),
        createRebagAllocation(),
      ],
    }));
  };

  const removeRebagAllocation = (skuId, rowId) => {
    setRebagMaterialSelections((prev) => {
      const rows = normalizeRebagAllocations(prev[skuId]).filter(
        (row) => row.rowId !== rowId
      );
      return {
        ...prev,
        [skuId]: rows.length > 0 ? rows : [createRebagAllocation()],
      };
    });
  };'''
rep(old, new, "rebag allocation state handlers")

# Replace recipe material single-batch loop with multi-batch allocation loop.
start = s.find('''        if (recipe) {
          const recipeMaterials = normalizeRecipeMaterials(recipe);

          for (const recipeMaterial of recipeMaterials) {''')
end_marker = '''          if (selectedMaterials.length === 0) {
            return alert("Pilih minimal satu bahan untuk proses Rebagging.");
          }
        } else {'''
end = s.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit("Patch target not found: recipe loop boundaries")
end += len('''          if (selectedMaterials.length === 0) {
            return alert("Pilih minimal satu bahan untuk proses Rebagging.");
          }
''')

multi_loop = r'''        if (recipe) {
          const recipeMaterials = normalizeRecipeMaterials(recipe);

          for (let materialIndex = 0; materialIndex < recipeMaterials.length; materialIndex += 1) {
            const recipeMaterial = recipeMaterials[materialIndex];
            const materialSkuId = recipeMaterial.skuId;
            const sourceSku = skus.find((item) => item.id === materialSkuId);
            const allocations = normalizeRebagAllocations(
              rebagMaterialSelections[materialSkuId]
            ).filter(
              (allocation) =>
                allocation.batchId ||
                Number(allocation.qty || 0) > 0 ||
                Number(allocation.damageQty || 0) > 0
            );

            if (!recipeMaterial.required && allocations.length === 0) {
              continue;
            }
            if (allocations.length === 0) {
              return alert(`Pilih minimal satu batch untuk bahan ${materialSkuId}.`);
            }

            const selectedBatchIds = allocations.map((allocation) => allocation.batchId).filter(Boolean);
            if (new Set(selectedBatchIds).size !== selectedBatchIds.length) {
              return alert(`Batch sumber untuk bahan ${materialSkuId} tidak boleh dipilih lebih dari satu kali.`);
            }

            const calculatedQty = getCalculatedMaterialQty(recipeMaterial, qty);
            let materialUsedTotal = 0;
            let materialDamageTotal = 0;
            const materialLines = [];

            for (let allocationIndex = 0; allocationIndex < allocations.length; allocationIndex += 1) {
              const allocation = allocations[allocationIndex];
              const sourceBatch = inventoryBatches.find(
                (batch) => batch.batchId === allocation.batchId
              );
              const usedQty = Number(allocation.qty || 0);
              const materialDamageQty = Number(allocation.damageQty || 0);
              const totalMaterialQty = usedQty + materialDamageQty;

              if (!sourceBatch) {
                return alert(
                  `Pilih batch yang valid untuk bahan ${materialSkuId} sumber ${allocationIndex + 1}.`
                );
              }
              if (!sourceBatch.moNumber) {
                return alert(`Batch bahan ${materialSkuId} belum memiliki No. MO.`);
              }
              if (!sourceBatch.tmNumber) {
                return alert(`Batch bahan ${materialSkuId} belum memiliki No. TM.`);
              }
              if (!Number.isFinite(usedQty) || usedQty < 0) {
                return alert(`Qty dipakai bahan ${materialSkuId} sumber ${allocationIndex + 1} tidak valid.`);
              }
              if (!Number.isFinite(materialDamageQty) || materialDamageQty < 0) {
                return alert(`Qty rusak bahan ${materialSkuId} sumber ${allocationIndex + 1} tidak valid.`);
              }
              if (!Number.isFinite(totalMaterialQty) || totalMaterialQty <= 0) {
                return alert(
                  `Isi Qty Dipakai atau Qty Rusak untuk bahan ${materialSkuId} sumber ${allocationIndex + 1}.`
                );
              }
              if (
                sourceBatch.date &&
                new Date(date).getTime() < new Date(sourceBatch.date).getTime()
              ) {
                return alert(
                  `Tanggal rebagging tidak boleh lebih awal dari tanggal masuk batch ${sourceBatch.batchId}.`
                );
              }

              const expiryInfo = getBatchExpiryInfo(sourceBatch, new Date(date));
              if (expiryInfo.isExpired && !isVerifiedSuperAdmin) {
                return alert(
                  `Batch ${sourceBatch.batchId} sudah EXPIRED dan tidak dapat digunakan untuk Rebagging.`
                );
              }
              if (expiryInfo.isExpired && isVerifiedSuperAdmin) {
                const allowExpired = window.confirm(
                  `PERINGATAN: Batch ${sourceBatch.batchId} sudah EXPIRED.\n\nLanjutkan sebagai override Super Admin?`
                );
                if (!allowExpired) return;
              }

              materialUsedTotal += usedQty;
              materialDamageTotal += materialDamageQty;
              materialLines.push({
                skuId: materialSkuId,
                skuName: sourceSku?.name || materialSkuId,
                required: recipeMaterial.required,
                isPrimaryMaterial: materialIndex === 0,
                allocationIndex: allocationIndex + 1,
                calculationMode: recipeMaterial.calculationMode || "manual",
                outputPerUnit: recipeMaterial.outputPerUnit || "",
                standardQty:
                  recipeMaterial.calculationMode === "per_output"
                    ? Number(calculatedQty || 0)
                    : null,
                usedQty,
                damageQty: materialDamageQty,
                totalQty: totalMaterialQty,
                batchId: sourceBatch.batchId,
                moNumber: sourceBatch.moNumber,
                tmNumber: sourceBatch.tmNumber,
                qty: totalMaterialQty,
                unit: sourceSku?.unit || "",
                sourceWarehouse: sourceBatch.sourceWarehouse || "",
                expiryDate: sourceBatch.expiryDate || "",
                expiredOverride: expiryInfo.isExpired,
                expiredOverrideBy: expiryInfo.isExpired ? currentUser.username : "",
              });
            }

            if (
              recipeMaterial.calculationMode === "per_output" &&
              (!Number.isFinite(Number(recipeMaterial.outputPerUnit)) ||
                Number(recipeMaterial.outputPerUnit) <= 0)
            ) {
              return alert(
                `Standar isi kemasan bahan ${materialSkuId} belum valid di Master Komposisi.`
              );
            }

            if (
              recipeMaterial.calculationMode === "per_output" &&
              Math.abs(materialUsedTotal - Number(calculatedQty || 0)) > 0.0001
            ) {
              return alert(
                `Total Qty Dipakai ${materialSkuId} harus sama dengan kebutuhan standar ${calculatedQty}. Saat ini: ${materialUsedTotal}.`
              );
            }

            if (recipeMaterial.calculationMode !== "per_output" && materialUsedTotal <= 0) {
              return alert(`Total Qty Dipakai bahan ${materialSkuId} harus lebih dari 0.`);
            }

            if (materialIndex === 0) {
              const primaryMos = [
                ...new Set(materialLines.map((line) => line.moNumber).filter(Boolean)),
              ];
              if (primaryMos.length !== 1) {
                return alert(
                  `Bahan utama boleh memakai beberapa batch, tetapi seluruh batch harus berasal dari MO Utama yang sama. MO terpilih: ${primaryMos.join(", ")}.`
                );
              }
            }

            materialLines.forEach((line) => {
              selectedMaterials.push({
                ...line,
                materialUsedTotal,
                materialDamageTotal,
              });
            });
          }

          if (selectedMaterials.length === 0) {
            return alert("Pilih minimal satu bahan untuk proses Rebagging.");
          }
'''
s = s[:start] + multi_loop + s[end:]

# Primary material should explicitly use the line marked as primary.
rep(
'''        const primaryMaterial = selectedMaterials[0];
        const mainMoNumber = String(primaryMaterial?.moNumber || "").trim();''',
'''        const primaryMaterial =
          selectedMaterials.find((material) => material.isPrimaryMaterial) ||
          selectedMaterials[0];
        const mainMoNumber = String(primaryMaterial?.moNumber || "").trim();''',
"primary material selection")

# Outbound expiry authorization before Firestore transaction.
old = '''        for (const item of selections) {
          if (!item.localBatch || item.localBatch.skuId !== sku.id) {
            return alert(`Batch ${item.batchId} tidak valid untuk SKU yang dipilih.`);
          }
          if (isFinishedGoods && item.localBatch.resultTmNumber !== outboundTm) {
            return alert(`Batch ${item.batchId} tidak sesuai dengan TM Hasil ${outboundTm}.`);
          }
          if (
            item.localBatch.date &&
            new Date(date).getTime() < new Date(item.localBatch.date).getTime()
          ) {
            return alert(`Tanggal outbound tidak boleh lebih awal dari tanggal masuk batch ${item.batchId}.`);
          }
        }

        await runTransaction'''
new = '''        const expiredOutboundItems = [];

        for (const item of selections) {
          if (!item.localBatch || item.localBatch.skuId !== sku.id) {
            return alert(`Batch ${item.batchId} tidak valid untuk SKU yang dipilih.`);
          }
          if (isFinishedGoods && item.localBatch.resultTmNumber !== outboundTm) {
            return alert(`Batch ${item.batchId} tidak sesuai dengan TM Hasil ${outboundTm}.`);
          }
          if (
            item.localBatch.date &&
            new Date(date).getTime() < new Date(item.localBatch.date).getTime()
          ) {
            return alert(`Tanggal outbound tidak boleh lebih awal dari tanggal masuk batch ${item.batchId}.`);
          }

          const expiryInfo = getBatchExpiryInfo(item.localBatch, new Date(date));
          if (expiryInfo.isExpired) expiredOutboundItems.push(item);
        }

        if (expiredOutboundItems.length > 0 && !isVerifiedSuperAdmin) {
          return alert(
            `Outbound diblokir karena ${expiredOutboundItems.length} batch sudah EXPIRED. Hubungi Super Admin.`
          );
        }
        if (expiredOutboundItems.length > 0 && isVerifiedSuperAdmin) {
          const allowExpiredOutbound = window.confirm(
            `PERINGATAN: ${expiredOutboundItems.length} batch yang dipilih sudah EXPIRED.\n\nLanjutkan sebagai override Super Admin?`
          );
          if (!allowExpiredOutbound) return;
        }

        const expiredOutboundIds = new Set(
          expiredOutboundItems.map((item) => item.batchId)
        );

        await runTransaction'''
rep(old, new, "outbound expiry precheck")

rep(
'''                resultTmNumber: isFinishedGoods ? outboundTm : (liveBatch.resultTmNumber || ""),
                soNumber: formData.outSoNumber?.trim() || "",''',
'''                resultTmNumber: isFinishedGoods ? outboundTm : (liveBatch.resultTmNumber || ""),
                expiryDate: liveBatch.expiryDate || "",
                expiredOverride: expiredOutboundIds.has(item.batchId),
                expiredOverrideBy: expiredOutboundIds.has(item.batchId)
                  ? currentUser.username
                  : "",
                soNumber: formData.outSoNumber?.trim() || "",''',
"outbound expiry audit")

# Replace destructive history-only reset with archive + full transactional test reset.
start = s.find('''  const handleResetTransactionHistory = async () => {''')
end = s.find('''

  if (dbError) return (''', start)
if start < 0 or end < 0:
    raise SystemExit("Patch target not found: reset handler")

reset_block = r'''  const getOperationalArchiveSnapshot = async () => {
    const collectionNames = [
      "transactions",
      "batches",
      "tm_mo_bindings",
      "batch_sequences",
      "result_tms",
    ];

    const snapshots = {};
    for (const name of collectionNames) {
      const snap = await getDocs(
        collection(db, "artifacts", appId, "public", "data", name)
      );
      snapshots[name] = snap.docs.map((item) => ({
        _docId: item.id,
        ...item.data(),
      }));
    }
    return snapshots;
  };

  const downloadOperationalArchive = (snapshots) => {
    const wb = XLSX.utils.book_new();
    const sheetMap = [
      ["transactions", "Transactions"],
      ["batches", "Batches"],
      ["tm_mo_bindings", "TM-MO"],
      ["batch_sequences", "Batch Sequence"],
      ["result_tms", "Legacy TM"],
    ];

    sheetMap.forEach(([key, sheetName]) => {
      const rows = snapshots[key] || [];
      const sheet = XLSX.utils.json_to_sheet(
        rows.length > 0 ? rows : [{ Keterangan: "Tidak ada data" }]
      );
      XLSX.utils.book_append_sheet(wb, sheet, sheetName);
    });

    const stamp = new Date()
      .toISOString()
      .replace(/[:.]/g, "-")
      .replace("T", "_")
      .slice(0, 19);
    XLSX.writeFile(wb, `Arsip_Data_Operasional_${stamp}.xlsx`);
  };

  const handleArchiveOperationalData = async () => {
    if (!isVerifiedSuperAdmin) {
      return alert("Akses arsip data hanya tersedia untuk Super Admin yang terverifikasi.");
    }
    if (!db) return alert("Database belum siap.");

    try {
      setResetHistoryLoading(true);
      const snapshots = await getOperationalArchiveSnapshot();
      downloadOperationalArchive(snapshots);
      showNotif("Arsip data operasional berhasil dibuat");
    } catch (error) {
      console.error("Archive Operational Data Error:", error);
      alert(`Gagal membuat arsip data: ${error.message || "Terjadi kesalahan tidak diketahui."}`);
    } finally {
      setResetHistoryLoading(false);
    }
  };

  const handleResetTransactionHistory = async () => {
    if (!isVerifiedSuperAdmin) {
      return alert("Akses reset data uji hanya tersedia untuk Super Admin yang terverifikasi.");
    }
    if (!db) {
      return alert("Database belum siap. Silakan muat ulang aplikasi.");
    }

    const firstConfirm = window.confirm(
      "RESET DATA UJI akan menghapus SELURUH transaksi, stok/batch, mapping TM-MO, dan sequence batch.\n\nMaster SKU, Komposisi, Pengguna, dan Konfigurasi tetap dipertahankan.\n\nSebelum penghapusan, sistem akan mengunduh arsip Excel otomatis.\n\nLanjutkan?"
    );
    if (!firstConfirm) return;

    const verification = window.prompt(
      'Ketik tepat "RESET DATA UJI" untuk melanjutkan.'
    );
    if (verification !== "RESET DATA UJI") {
      return alert("Konfirmasi tidak sesuai. Reset dibatalkan.");
    }

    try {
      setResetHistoryLoading(true);
      const snapshots = await getOperationalArchiveSnapshot();
      const totalDocs = Object.values(snapshots).reduce(
        (sum, rows) => sum + rows.length,
        0
      );

      if (totalDocs === 0) {
        return alert("Data operasional sudah kosong.");
      }

      downloadOperationalArchive(snapshots);

      const collectionNames = [
        "transactions",
        "batches",
        "tm_mo_bindings",
        "batch_sequences",
        "result_tms",
      ];
      const chunkSize = 450;

      for (const collectionName of collectionNames) {
        const targetCollection = collection(
          db,
          "artifacts",
          appId,
          "public",
          "data",
          collectionName
        );
        const snapshot = await getDocs(targetCollection);

        for (let i = 0; i < snapshot.docs.length; i += chunkSize) {
          const batch = writeBatch(db);
          snapshot.docs.slice(i, i + chunkSize).forEach((item) => {
            batch.delete(item.ref);
          });
          await batch.commit();
        }
      }

      setFormData(initialFormData);
      setOutboundSelections({});
      setRebagMaterialSelections({});
      showNotif("Data uji berhasil direset dan arsip sudah diunduh");
      alert(
        "Reset Data Uji selesai.\n\nTransaksi, stok/batch, mapping TM-MO, dan sequence batch sudah dikosongkan secara konsisten. Arsip Excel telah diunduh sebelum penghapusan."
      );
    } catch (error) {
      console.error("Reset Test Data Error:", error);
      alert(`Gagal mereset data uji: ${error.message || "Terjadi kesalahan tidak diketahui."}`);
    } finally {
      setResetHistoryLoading(false);
    }
  };
'''
s = s[:start] + reset_block + s[end:]

path.write_text(s, encoding="utf-8")
print("Core multibatch/FEFO/reset patch applied.")
