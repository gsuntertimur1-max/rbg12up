from pathlib import Path

path = Path("src/App.jsx")
s = path.read_text(encoding="utf-8")

def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"Patch target not found: {label}")
    s = s.replace(old, new, 1)

rep(
'''const getResultTmLockId = (value) =>
  encodeURIComponent(String(value || "").trim().toUpperCase()).replace(/%/g, "_");''',
'''const getStableDocId = (value) =>
  encodeURIComponent(String(value || "").trim().toUpperCase()).replace(/%/g, "_");

const getProductionDateCode = (value) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const yy = String(date.getFullYear()).slice(-2);
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${yy}${mm}${dd}`;
};

const getBatchSequenceKey = (skuId, dateCode) =>
  getStableDocId(`${skuId}-${dateCode}`);

const getPrimaryMoNumber = (record) => {
  if (!record) return "";
  if (record.mainMoNumber) return String(record.mainMoNumber).trim();
  if (Array.isArray(record.sourceMoNumbers) && record.sourceMoNumbers.length > 0) {
    return String(record.sourceMoNumbers[0] || "").trim();
  }
  const moNumber = String(record.moNumber || "").trim();
  return moNumber.includes(",") ? moNumber.split(",")[0].trim() : moNumber;
};''',
"helpers")

rep(
'''          transaction.set(resultTmRef, {
            resultTmNumber,
            skuId: targetSku.id,
            skuName: targetSku.name,
            batchId: newBatchId,
            transactionId: txId,
            date,
            createdBy: currentUser.username,
          });

          selectedMaterials.forEach((material, index) => {
            const materialDamageQty = Number(material.damageQty || 0);
            if (materialDamageQty <= 0) return;

            const damageTxId = `TRX-MAT-DMG-${timestamp}-${index + 1}`;
            transaction.set(
              doc(db, "artifacts", appId, "public", "data", "transactions", damageTxId),
              {
                id: damageTxId,
                parentTransactionId: txId,
                date,
                type: "MATERIAL_DAMAGE",
                skuId: material.skuId,
                skuName: material.skuName,
                batchId: material.batchId,
                qtyChange: materialDamageQty,
                damageQty: materialDamageQty,
                unit: material.unit,
                moNumber: material.moNumber,
                tmNumber: material.tmNumber,
                resultTmNumber,
                sourceWarehouse: material.sourceWarehouse,
                cause: "Kerusakan saat proses Rebagging",
                operator: currentUser.username,
                stockAlreadyApplied: true,
                ...auditMeta,
              }
            );
          });
''',
'',
"remove misplaced inbound rebag writes")

rep(
'''        const normalizedResultTm = resultTmNumber.toUpperCase();
        const duplicateTm =
          inventoryBatches.some(
            (b) =>
              String(b.resultTmNumber || "").trim().toUpperCase() === normalizedResultTm
          ) ||
          transactions.some(
            (t) =>
              t.type === "REBAGGING" &&
              String(t.resultTmNumber || "").trim().toUpperCase() === normalizedResultTm
          );
        if (duplicateTm) {
          return alert(
            `TM Hasil ${resultTmNumber} sudah pernah digunakan. Gunakan TM Hasil yang unik untuk produksi baru.`
          );
        }
''',
'''        const normalizedResultTm = resultTmNumber.toUpperCase();
''',
"remove global TM uniqueness")

rep(
'''        const newBatchId = `RBG-${timestamp}`;
        const txId = `TRX-${timestamp}`;
        const sourceMoNumbers = [...new Set(selectedMaterials.map((m) => m.moNumber).filter(Boolean))];
        const sourceTmNumbers = [...new Set(selectedMaterials.map((m) => m.tmNumber).filter(Boolean))];
        const materialDamageLineCount = selectedMaterials.filter(
          (material) => Number(material.damageQty || 0) > 0
        ).length;

        await runTransaction(db, async (transaction) => {
          const resultTmRef = doc(
            db,
            "artifacts",
            appId,
            "public",
            "data",
            "result_tms",
            getResultTmLockId(resultTmNumber)
          );
          const resultTmSnap = await transaction.get(resultTmRef);
          if (resultTmSnap.exists()) {
            throw new Error(`TM Hasil ${resultTmNumber} sudah digunakan oleh produksi lain.`);
          }

          const materialRefs = selectedMaterials.map((material) =>
            doc(db, "artifacts", appId, "public", "data", "batches", material.batchId)
          );
          const materialSnaps = await Promise.all(materialRefs.map((ref) => transaction.get(ref)));''',
'''        let newBatchId = "";
        const txId = `TRX-${timestamp}`;
        const sourceMoNumbers = [...new Set(selectedMaterials.map((m) => m.moNumber).filter(Boolean))];
        const sourceTmNumbers = [...new Set(selectedMaterials.map((m) => m.tmNumber).filter(Boolean))];
        const primaryMaterial = selectedMaterials[0];
        const mainMoNumber = String(primaryMaterial?.moNumber || "").trim();

        if (!mainMoNumber) {
          return alert("MO Utama/pengikat TM Hasil belum tersedia pada bahan utama.");
        }

        const priorTmRecords = [
          ...transactions.filter((t) => t.type === "REBAGGING"),
          ...inventoryBatches.filter((b) => b.resultTmNumber),
        ];
        const conflictingTmRecord = priorTmRecords.find(
          (record) =>
            String(record.resultTmNumber || "").trim().toUpperCase() === normalizedResultTm &&
            getPrimaryMoNumber(record) &&
            getPrimaryMoNumber(record).toUpperCase() !== mainMoNumber.toUpperCase()
        );
        if (conflictingTmRecord) {
          return alert(
            `TM Hasil ${resultTmNumber} sudah terikat ke MO Utama ${getPrimaryMoNumber(conflictingTmRecord)}. Gunakan TM Hasil yang sesuai dengan MO ${mainMoNumber}.`
          );
        }

        const productionDateCode = getProductionDateCode(date);
        if (!productionDateCode) {
          return alert("Tanggal produksi tidak valid untuk pembuatan nomor batch.");
        }

        const batchPrefix = `${targetSku.id}-${productionDateCode}-`;
        const existingSequenceMax = inventoryBatches.reduce((max, batch) => {
          const batchId = String(batch.batchId || "");
          if (!batchId.startsWith(batchPrefix)) return max;
          const suffix = Number(batchId.slice(batchPrefix.length));
          return Number.isFinite(suffix) ? Math.max(max, suffix) : max;
        }, 0);

        const materialDamageLineCount = selectedMaterials.filter(
          (material) => Number(material.damageQty || 0) > 0
        ).length;

        await runTransaction(db, async (transaction) => {
          const tmBindingRef = doc(
            db,
            "artifacts",
            appId,
            "public",
            "data",
            "tm_mo_bindings",
            getStableDocId(resultTmNumber)
          );
          const batchSequenceRef = doc(
            db,
            "artifacts",
            appId,
            "public",
            "data",
            "batch_sequences",
            getBatchSequenceKey(targetSku.id, productionDateCode)
          );
          const materialRefs = selectedMaterials.map((material) =>
            doc(db, "artifacts", appId, "public", "data", "batches", material.batchId)
          );

          const [tmBindingSnap, batchSequenceSnap, ...materialSnaps] = await Promise.all([
            transaction.get(tmBindingRef),
            transaction.get(batchSequenceRef),
            ...materialRefs.map((ref) => transaction.get(ref)),
          ]);

          if (tmBindingSnap.exists()) {
            const binding = tmBindingSnap.data();
            const boundMo = String(binding.mainMoNumber || "").trim();
            if (boundMo && boundMo.toUpperCase() !== mainMoNumber.toUpperCase()) {
              throw new Error(
                `TM Hasil ${resultTmNumber} sudah terikat ke MO Utama ${boundMo}, bukan ${mainMoNumber}.`
              );
            }
          }

          const storedSequence = batchSequenceSnap.exists()
            ? Number(batchSequenceSnap.data()?.lastNumber || 0)
            : 0;
          const nextSequence = Math.max(storedSequence, existingSequenceMax) + 1;
          newBatchId = `${targetSku.id}-${productionDateCode}-${String(nextSequence).padStart(2, "0")}`;''',
"TM binding and batch sequence")

rep(
'''          const primaryMaterial = selectedMaterials[0];
          const sourceWarehouses = [''',
'''          const sourceWarehouses = [''',
"remove duplicate primary material")

rep(
'''            sourceMoNumbers,
            sourceTmNumbers,
            resultTmNumber,
            expiryDate: formData.rebagExpiryDate,''',
'''            sourceMoNumbers,
            sourceTmNumbers,
            mainMoNumber,
            resultTmNumber,
            batchDateCode: productionDateCode,
            expiryDate: formData.rebagExpiryDate,''',
"finished batch MO metadata")

rep(
'''              sourceMoNumbers,
              sourceTmNumbers,
              resultTmNumber,
              targetStack: formData.rebagTargetStack,''',
'''              sourceMoNumbers,
              sourceTmNumbers,
              mainMoNumber,
              resultTmNumber,
              batchDateCode: productionDateCode,
              targetStack: formData.rebagTargetStack,''',
"transaction MO metadata")

rep(
'''              ...auditMeta,
            }
          );
        });
      } else if (activeOpTab === "outbound") {''',
'''              ...auditMeta,
            }
          );

          const existingBinding = tmBindingSnap.exists() ? tmBindingSnap.data() : {};
          transaction.set(tmBindingRef, {
            resultTmNumber,
            mainMoNumber,
            firstProductionAt: existingBinding.firstProductionAt || date,
            firstTransactionId: existingBinding.firstTransactionId || txId,
            firstBatchId: existingBinding.firstBatchId || newBatchId,
            lastProductionAt: date,
            lastTransactionId: txId,
            lastBatchId: newBatchId,
            productionCount: Number(existingBinding.productionCount || 0) + 1,
            updatedBy: currentUser.username,
          });

          transaction.set(batchSequenceRef, {
            skuId: targetSku.id,
            productionDateCode,
            lastNumber: Number(newBatchId.split("-").pop() || 0),
            lastBatchId: newBatchId,
            updatedAt: date,
          });

          selectedMaterials.forEach((material, index) => {
            const materialDamageQty = Number(material.damageQty || 0);
            if (materialDamageQty <= 0) return;

            const damageTxId = `TRX-MAT-DMG-${timestamp}-${index + 1}`;
            transaction.set(
              doc(db, "artifacts", appId, "public", "data", "transactions", damageTxId),
              {
                id: damageTxId,
                parentTransactionId: txId,
                date,
                type: "MATERIAL_DAMAGE",
                skuId: material.skuId,
                skuName: material.skuName,
                batchId: material.batchId,
                qtyChange: materialDamageQty,
                damageQty: materialDamageQty,
                unit: material.unit,
                moNumber: material.moNumber,
                tmNumber: material.tmNumber,
                resultTmNumber,
                mainMoNumber,
                sourceWarehouse: material.sourceWarehouse,
                cause: "Kerusakan saat proses Rebagging",
                operator: currentUser.username,
                stockAlreadyApplied: true,
                ...auditMeta,
              }
            );
          });
        });
      } else if (activeOpTab === "outbound") {''',
"correct rebag tail")

path.write_text(s, encoding="utf-8")
print("Core TM/MO/batch patch applied.")
