from pathlib import Path

path = Path('src/App.jsx')
s = path.read_text(encoding='utf-8')

def rep(old, new, label, count=1):
    global s
    if old not in s:
        raise SystemExit(f'Patch target not found: {label}')
    for _ in range(count):
        s = s.replace(old, new, 1)

# 1) Config + warehouse classification helpers.
rep(
'''  rebagApproverName: "IRSA MAULIAN NUGRAHA",
};''',
'''  rebagApproverName: "IRSA MAULIAN NUGRAHA",
  processingLocation: "Unit Pengolahan 20",
};''',
'processing location config'
)

marker = '''const getRebagStandards = (productName = "") => {'''
helpers = r'''const MATERIAL_SUPPORT_KEYWORDS = [
  "KEMASAN",
  "KARDUS",
  "KARTON",
  "PLASTIK",
  "PACKAGING",
  "LABEL",
  "BENANG",
  "ROLL",
  "SHEET",
];

const isPackagingMaterialSku = (sku) => {
  const name = String(sku?.name || "").toUpperCase();
  return MATERIAL_SUPPORT_KEYWORDS.some((keyword) => name.includes(keyword));
};

const isPrimaryAdministrativeRawSku = (sku) => {
  if (!sku || sku.type !== "bulk") return false;
  const name = String(sku.name || "").toUpperCase();
  const isMainCommodity = name.includes("BERAS") || name.includes("GULA");
  return isMainCommodity && !isPackagingMaterialSku(sku);
};

const getProcessingLocation = (config = {}) =>
  String(config.processingLocation || "Unit Pengolahan 20").trim() ||
  "Unit Pengolahan 20";

const getBatchAdministrativeWarehouse = (batch, sku, config = {}) => {
  if (batch?.administrativeWarehouse) {
    return String(batch.administrativeWarehouse).trim();
  }
  if (isPackagingMaterialSku(sku)) return getProcessingLocation(config);
  return String(batch?.sourceWarehouse || getProcessingLocation(config)).trim();
};

const getBatchPhysicalLocation = (batch, config = {}) =>
  String(batch?.physicalLocation || getProcessingLocation(config)).trim() ||
  getProcessingLocation(config);

'''
rep(marker, helpers + marker, 'warehouse helpers')

# 2) QC form owns TM Hasil.
rep(
'''    coaNumber: "",
    inspectionNote: "",''',
'''    resultTmNumber: "",
    coaNumber: "",
    inspectionNote: "",''',
'qc result TM field'
)

# 3) Inbound: keep sourceWarehouse for legacy traceability, add admin + physical semantics.
old = '''        normalizedLines.forEach((line, index) => {
          const batchId = `INB-${timestamp}-${index + 1}`;
          const txId = `TRX-${timestamp}-IN-${index + 1}`;

          batch.set('''
new = '''        normalizedLines.forEach((line, index) => {
          const batchId = `INB-${timestamp}-${index + 1}`;
          const txId = `TRX-${timestamp}-IN-${index + 1}`;
          const physicalLocation = getProcessingLocation(systemConfig);
          const administrativeWarehouse = isPackagingMaterialSku(line.sku)
            ? physicalLocation
            : line.sourceWarehouse;
          const materialClass = isPackagingMaterialSku(line.sku)
            ? "SUPPORT"
            : isPrimaryAdministrativeRawSku(line.sku)
            ? "PRIMARY_RAW"
            : "OTHER_RAW";

          batch.set('''
rep(old, new, 'inbound derived warehouse fields')

rep(
'''              currentQty: line.qtyValue,
              sourceWarehouse: line.sourceWarehouse,
              moNumber: line.moNumber,''',
'''              currentQty: line.qtyValue,
              sourceWarehouse: line.sourceWarehouse,
              administrativeWarehouse,
              physicalLocation,
              materialClass,
              moNumber: line.moNumber,''',
'inbound batch warehouse fields'
)
rep(
'''              operator: currentUser.username,
              sourceWarehouse: line.sourceWarehouse,
              moNumber: line.moNumber,''',
'''              operator: currentUser.username,
              sourceWarehouse: line.sourceWarehouse,
              administrativeWarehouse,
              physicalLocation,
              materialClass,
              moNumber: line.moNumber,''',
'inbound tx warehouse fields'
)

# 4) Rebag operator no longer enters TM Hasil.
rep(
'''        const totalResultQty = goodQty + processQty + damageQty;
        const resultTmNumber = String(formData.rebagResultTmNumber || "").trim();

        if (!targetSku) return alert("Pilih SKU hasil rebagging.");
        if (!resultTmNumber) return alert("TM Hasil wajib diisi pada proses Rebagging.");

        const normalizedResultTm = resultTmNumber.toUpperCase();''',
'''        const totalResultQty = goodQty + processQty + damageQty;
        // TM Hasil adalah data administrasi dan diisi pada QC Produk Jadi.
        const resultTmNumber = "";

        if (!targetSku) return alert("Pilih SKU hasil rebagging.");''',
'remove rebag TM requirement'
)

rep(
'''        if (!mainMoNumber) {
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

        const productionDateCode = getProductionDateCode(date);''',
'''        if (!mainMoNumber) {
          return alert("MO Utama belum tersedia pada bahan utama.");
        }

        const primaryAdministrativeWarehouses = [
          ...new Set(
            selectedMaterials
              .filter((material) => material.isPrimaryMaterial || material === primaryMaterial)
              .map((material) => material.administrativeWarehouse || material.sourceWarehouse)
              .filter(Boolean)
          ),
        ];
        const administrativeWarehouse = primaryAdministrativeWarehouses.join(", ");
        const physicalLocation = getProcessingLocation(systemConfig);

        const productionDateCode = getProductionDateCode(date);''',
'remove rebag TM conflict and derive finished locations'
)

# 5) Every material line carries both administrative and physical location.
rep(
'''                unit: sourceSku?.unit || "",
                sourceWarehouse: sourceBatch.sourceWarehouse || "",
                expiryDate: sourceBatch.expiryDate || "",''',
'''                unit: sourceSku?.unit || "",
                sourceWarehouse: sourceBatch.sourceWarehouse || "",
                administrativeWarehouse: getBatchAdministrativeWarehouse(
                  sourceBatch,
                  sourceSku,
                  systemConfig
                ),
                physicalLocation: getBatchPhysicalLocation(sourceBatch, systemConfig),
                materialClass: isPackagingMaterialSku(sourceSku)
                  ? "SUPPORT"
                  : isPrimaryAdministrativeRawSku(sourceSku)
                  ? "PRIMARY_RAW"
                  : "OTHER_RAW",
                expiryDate: sourceBatch.expiryDate || "",''',
'recipe material admin/physical'
)
rep(
'''              unit: sourceSku?.unit || "",
              sourceWarehouse: selectedBatch.sourceWarehouse || "",
            },''',
'''              unit: sourceSku?.unit || "",
              sourceWarehouse: selectedBatch.sourceWarehouse || "",
              administrativeWarehouse: getBatchAdministrativeWarehouse(
                selectedBatch,
                sourceSku,
                systemConfig
              ),
              physicalLocation: getBatchPhysicalLocation(selectedBatch, systemConfig),
              materialClass: isPackagingMaterialSku(sourceSku)
                ? "SUPPORT"
                : isPrimaryAdministrativeRawSku(sourceSku)
                ? "PRIMARY_RAW"
                : "OTHER_RAW",
              isPrimaryMaterial: true,
            },''',
'manual material admin/physical'
)

# 6) Keep Firestore transaction read ordering valid while TM binding is pending.
rep(
'''          const tmBindingRef = doc(
            db,
            "artifacts",
            appId,
            "public",
            "data",
            "tm_mo_bindings",
            getStableDocId(resultTmNumber)
          );
          const batchSequenceRef = doc(''',
'''          // TM Hasil belum dibuat pada tahap operator; binding dilakukan saat QC Produk Jadi.
          const batchSequenceRef = doc(''',
'remove tm binding ref from rebag'
)
rep(
'''          const [tmBindingSnap, batchSequenceSnap, ...materialSnaps] = await Promise.all([
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

          const storedSequence = batchSequenceSnap.exists()''',
'''          const [batchSequenceSnap, ...materialSnaps] = await Promise.all([
            transaction.get(batchSequenceRef),
            ...materialRefs.map((ref) => transaction.get(ref)),
          ]);

          const storedSequence = batchSequenceSnap.exists()''',
'remove tm binding read from rebag'
)

# 7) Finished batch + transaction storage semantics.
rep(
'''            sourceWarehouse: sourceWarehouses,
            targetStack: formData.rebagTargetStack,
            sourceBatchId: primaryMaterial?.batchId || "",''',
'''            sourceWarehouse: sourceWarehouses,
            administrativeWarehouse,
            administrativeWarehouses: primaryAdministrativeWarehouses,
            administrativeAllocationStatus:
              primaryAdministrativeWarehouses.length > 1 ? "MULTI_ADMIN_UNALLOCATED" : "SINGLE_ADMIN",
            physicalLocation,
            targetStack: formData.rebagTargetStack,
            sourceBatchId: primaryMaterial?.batchId || "",''',
'finished batch admin physical fields'
)
rep(
'''            mainMoNumber,
            resultTmNumber,
            batchDateCode: productionDateCode,''',
'''            mainMoNumber,
            resultTmNumber,
            tmResultStatus: "PENDING_ADMIN",
            batchDateCode: productionDateCode,''',
'finished batch pending TM status'
)
rep(
'''              targetStack: formData.rebagTargetStack,
              sourceWarehouse: sourceWarehouses,
              sourceBatchId: primaryMaterial?.batchId || "",''',
'''              targetStack: formData.rebagTargetStack,
              sourceWarehouse: sourceWarehouses,
              administrativeWarehouse,
              administrativeWarehouses: primaryAdministrativeWarehouses,
              administrativeAllocationStatus:
                primaryAdministrativeWarehouses.length > 1 ? "MULTI_ADMIN_UNALLOCATED" : "SINGLE_ADMIN",
              physicalLocation,
              sourceBatchId: primaryMaterial?.batchId || "",''',
'rebag tx admin physical fields'
)
# second occurrence of mainMo/result TM is transaction
rep(
'''              mainMoNumber,
              resultTmNumber,
              batchDateCode: productionDateCode,''',
'''              mainMoNumber,
              resultTmNumber,
              tmResultStatus: "PENDING_ADMIN",
              batchDateCode: productionDateCode,''',
'rebag tx pending TM status'
)

# 8) Remove binding write from Rebag transaction.
old = '''          const existingBinding = tmBindingSnap.exists() ? tmBindingSnap.data() : {};
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

'''
rep(old, '', 'remove rebag TM binding write')

# Material damage is created before TM assignment; leave explicit pending status and location semantics.
rep(
'''                tmNumber: material.tmNumber,
                resultTmNumber,
                mainMoNumber,
                sourceWarehouse: material.sourceWarehouse,''',
'''                tmNumber: material.tmNumber,
                resultTmNumber: "",
                tmResultStatus: "PENDING_ADMIN",
                mainMoNumber,
                sourceWarehouse: material.sourceWarehouse,
                administrativeWarehouse: material.administrativeWarehouse || "",
                physicalLocation: material.physicalLocation || physicalLocation,''',
'material damage pending TM'
)

# 9) QC finished: derive/require TM Hasil before RELEASE and store location semantics in QC record.
rep(
'''    const batchStatus = isIncoming
      ? qcForm.decision === "ACCEPT" ? "ACCEPTED" : qcForm.decision === "HOLD" ? "HOLD" : "REJECTED"
      : qcForm.decision === "RELEASE" ? "RELEASED" : qcForm.decision === "HOLD" ? "HOLD" : "REJECTED";
    const record = {''',
'''    const batchStatus = isIncoming
      ? qcForm.decision === "ACCEPT" ? "ACCEPTED" : qcForm.decision === "HOLD" ? "HOLD" : "REJECTED"
      : qcForm.decision === "RELEASE" ? "RELEASED" : qcForm.decision === "HOLD" ? "HOLD" : "REJECTED";
    const resultTmNumber = !isIncoming
      ? String(qcForm.resultTmNumber || batch.resultTmNumber || "").trim()
      : String(batch.resultTmNumber || "").trim();
    const mainMoNumber = batch.mainMoNumber || getPrimaryMoNumber(batch) || "";

    if (!isIncoming && qcForm.decision === "RELEASE" && !resultTmNumber) {
      return alert("TM Hasil wajib diisi oleh QC/Admin sebelum produk jadi di-RELEASE.");
    }
    if (!isIncoming && resultTmNumber && !mainMoNumber) {
      return alert("MO Utama batch produk jadi belum tersedia untuk pengikatan TM Hasil.");
    }

    const record = {''',
'QC result TM validation'
)
rep(
'''      mainMoNumber: batch.mainMoNumber || getPrimaryMoNumber(batch) || "",
      tmNumber: batch.tmNumber || "",
      resultTmNumber: batch.resultTmNumber || "",
      sourceWarehouse: batch.sourceWarehouse || "",
      targetStack: batch.targetStack || "",''',
'''      mainMoNumber,
      tmNumber: batch.tmNumber || "",
      resultTmNumber,
      sourceWarehouse: batch.sourceWarehouse || "",
      administrativeWarehouse:
        batch.administrativeWarehouse ||
        (Array.isArray(batch.administrativeWarehouses)
          ? batch.administrativeWarehouses.join(", ")
          : ""),
      administrativeWarehouses: batch.administrativeWarehouses || [],
      physicalLocation: getBatchPhysicalLocation(batch, systemConfig),
      targetStack: batch.targetStack || "",''',
'QC record admin physical TM'
)

# 10) QC transaction reads TM binding + child damage records before all writes, validates same MO.
rep(
'''      const relatedOperationalTx = transactions.find((item) =>
        isIncoming
          ? item.type === "INBOUND" && item.batchId === batch.batchId
          : item.type === "REBAGGING" && item.batchId === batch.batchId
      );

      await runTransaction(db, async (transaction) => {''',
'''      const relatedOperationalTx = transactions.find((item) =>
        isIncoming
          ? item.type === "INBOUND" && item.batchId === batch.batchId
          : item.type === "REBAGGING" && item.batchId === batch.batchId
      );
      const relatedDamageTxs = !isIncoming && relatedOperationalTx?.id
        ? transactions.filter(
            (item) =>
              item.type === "MATERIAL_DAMAGE" &&
              item.parentTransactionId === relatedOperationalTx.id
          )
        : [];

      await runTransaction(db, async (transaction) => {''',
'QC related material damage collection'
)

rep(
'''        const relatedTxRef = relatedOperationalTx?.id
          ? doc(db, "artifacts", appId, "public", "data", "transactions", relatedOperationalTx.id)
          : null;

        const batchSnap = await transaction.get(batchRef);
        const relatedTxSnap = relatedTxRef ? await transaction.get(relatedTxRef) : null;
        if (!batchSnap.exists()) throw new Error("Batch sudah tidak ditemukan.");

        const liveBatch = batchSnap.data();''',
'''        const relatedTxRef = relatedOperationalTx?.id
          ? doc(db, "artifacts", appId, "public", "data", "transactions", relatedOperationalTx.id)
          : null;
        const damageTxRefs = relatedDamageTxs.map((item) =>
          doc(db, "artifacts", appId, "public", "data", "transactions", item.id)
        );
        const tmBindingRef = !isIncoming && resultTmNumber
          ? doc(
              db,
              "artifacts",
              appId,
              "public",
              "data",
              "tm_mo_bindings",
              getStableDocId(resultTmNumber)
            )
          : null;

        const [batchSnap, relatedTxSnap, tmBindingSnap, ...damageTxSnaps] = await Promise.all([
          transaction.get(batchRef),
          relatedTxRef ? transaction.get(relatedTxRef) : Promise.resolve(null),
          tmBindingRef ? transaction.get(tmBindingRef) : Promise.resolve(null),
          ...damageTxRefs.map((ref) => transaction.get(ref)),
        ]);
        if (!batchSnap.exists()) throw new Error("Batch sudah tidak ditemukan.");

        if (tmBindingSnap?.exists()) {
          const binding = tmBindingSnap.data();
          const boundMo = String(binding.mainMoNumber || "").trim();
          if (boundMo && boundMo.toUpperCase() !== String(mainMoNumber).toUpperCase()) {
            throw new Error(
              `TM Hasil ${resultTmNumber} sudah terikat ke MO Utama ${boundMo}, bukan ${mainMoNumber}.`
            );
          }
        }

        const liveBatch = batchSnap.data();''',
'QC binding reads and validation'
)

# 11) QC updates batch and originating REBAG tx with TM and warehouse/location semantics.
rep(
'''          qcDecision: qcForm.decision,
          ...releaseMeta,
        });''',
'''          qcDecision: qcForm.decision,
          ...(!isIncoming
            ? {
                resultTmNumber,
                tmResultStatus: resultTmNumber ? "ASSIGNED" : "PENDING_ADMIN",
                resultTmAssignedAt: resultTmNumber ? inspectedAt : "",
                resultTmAssignedBy: resultTmNumber ? currentUser.username : "",
              }
            : {}),
          ...releaseMeta,
        });''',
'QC batch TM assignment'
)
rep(
'''            qcUpdatedBy: currentUser.username,
            ...(!isIncoming
              ? {
                  qualityControl: {''',
'''            qcUpdatedBy: currentUser.username,
            ...(!isIncoming
              ? {
                  resultTmNumber,
                  tmResultStatus: resultTmNumber ? "ASSIGNED" : "PENDING_ADMIN",
                  resultTmAssignedAt: resultTmNumber ? inspectedAt : "",
                  resultTmAssignedBy: resultTmNumber ? currentUser.username : "",
                  administrativeWarehouse:
                    liveBatch.administrativeWarehouse ||
                    (Array.isArray(liveBatch.administrativeWarehouses)
                      ? liveBatch.administrativeWarehouses.join(", ")
                      : ""),
                  administrativeWarehouses: liveBatch.administrativeWarehouses || [],
                  physicalLocation: getBatchPhysicalLocation(liveBatch, systemConfig),
                  qualityControl: {''',
'QC rebag transaction TM/location update'
)

# Insert TM binding and MATERIAL_DAMAGE updates before QC record write.
old = '''        transaction.set(doc(db, "artifacts", appId, "public", "data", "qc_records", recordId), record);'''
new = '''        if (!isIncoming && resultTmNumber && tmBindingRef) {
          const existingBinding = tmBindingSnap?.exists() ? tmBindingSnap.data() : {};
          transaction.set(tmBindingRef, {
            resultTmNumber,
            mainMoNumber,
            firstProductionAt:
              existingBinding.firstProductionAt ||
              relatedOperationalTx?.productionDate ||
              relatedOperationalTx?.date ||
              batch.productionDate ||
              inspectedAt,
            firstTransactionId:
              existingBinding.firstTransactionId || relatedOperationalTx?.id || "",
            firstBatchId: existingBinding.firstBatchId || batch.batchId,
            lastProductionAt:
              relatedOperationalTx?.productionDate || relatedOperationalTx?.date || inspectedAt,
            lastTransactionId: relatedOperationalTx?.id || existingBinding.lastTransactionId || "",
            lastBatchId: batch.batchId,
            productionCount: Math.max(1, Number(existingBinding.productionCount || 0)),
            assignedAt: existingBinding.assignedAt || inspectedAt,
            assignedBy: existingBinding.assignedBy || currentUser.username,
            updatedAt: inspectedAt,
            updatedBy: currentUser.username,
          });
        }

        if (!isIncoming && resultTmNumber) {
          damageTxSnaps.forEach((snap, index) => {
            if (!snap?.exists()) return;
            transaction.update(damageTxRefs[index], {
              resultTmNumber,
              tmResultStatus: "ASSIGNED",
              resultTmAssignedAt: inspectedAt,
              resultTmAssignedBy: currentUser.username,
            });
          });
        }

        transaction.set(doc(db, "artifacts", appId, "public", "data", "qc_records", recordId), record);'''
rep(old, new, 'QC TM binding and child damage update')

# 12) Outbound transaction preserves admin + physical location.
rep(
'''                batchId: item.batchId,
                sourceWarehouse: liveBatch.sourceWarehouse || "",
                moNumber: liveBatch.moNumber || "",''',
'''                batchId: item.batchId,
                sourceWarehouse: liveBatch.sourceWarehouse || "",
                administrativeWarehouse:
                  liveBatch.administrativeWarehouse ||
                  (Array.isArray(liveBatch.administrativeWarehouses)
                    ? liveBatch.administrativeWarehouses.join(", ")
                    : ""),
                administrativeWarehouses: liveBatch.administrativeWarehouses || [],
                physicalLocation: getBatchPhysicalLocation(liveBatch, systemConfig),
                targetStack: liveBatch.targetStack || "",
                moNumber: liveBatch.moNumber || "",''',
'outbound admin physical fields'
)

# 13) Fix archive/reset consistency for QC records.
rep(
'''      "result_tms",
      "qc_records",
      "qc_records",
    ];''',
'''      "result_tms",
      "qc_records",
    ];''',
'archive duplicate qc_records'
)
rep(
'''        "batch_sequences",
        "result_tms",
      ];''',
'''        "batch_sequences",
        "result_tms",
        "qc_records",
      ];''',
'reset qc_records too'
)

path.write_text(s, encoding='utf-8')
print('Core administrative/physical warehouse and QC TM patch applied.')
