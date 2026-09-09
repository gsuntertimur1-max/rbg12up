from pathlib import Path

path = Path("src/App.jsx")
s = path.read_text(encoding="utf-8")

def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"Patch target not found: {label}")
    s = s.replace(old, new, 1)

# Expired always last; FEFO/FIFO applies to usable stock first.
rep(
'''const sortBatchesFefoFifo = (batches, referenceDate = new Date()) =>
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
  });''',
'''const sortBatchesFefoFifo = (batches, referenceDate = new Date()) =>
  [...batches].sort((a, b) => {
    const aExpiry = getBatchExpiryInfo(a, referenceDate);
    const bExpiry = getBatchExpiryInfo(b, referenceDate);

    if (aExpiry.isExpired !== bExpiry.isExpired) {
      return aExpiry.isExpired ? 1 : -1;
    }

    if (aExpiry.hasExpiry && bExpiry.hasExpiry) {
      if (aExpiry.priority !== bExpiry.priority) return aExpiry.priority - bExpiry.priority;
    } else if (aExpiry.hasExpiry !== bExpiry.hasExpiry) {
      return aExpiry.hasExpiry ? -1 : 1;
    }

    const aDate = new Date(a.date || a.productionDate || 0).getTime() || 0;
    const bDate = new Date(b.date || b.productionDate || 0).getTime() || 0;
    return aDate - bDate;
  });''',
"expired sorting")

# Rebag: determine FEFO/FIFO prefix and require reason if skipped.
rep(
'''            const calculatedQty = getCalculatedMaterialQty(recipeMaterial, qty);
            let materialUsedTotal = 0;
            let materialDamageTotal = 0;
            const materialLines = [];

            for (let allocationIndex = 0; allocationIndex < allocations.length; allocationIndex += 1) {''',
'''            const calculatedQty = getCalculatedMaterialQty(recipeMaterial, qty);
            let materialUsedTotal = 0;
            let materialDamageTotal = 0;
            const materialLines = [];

            const referenceDate = new Date(date);
            const candidateBatches = sortBatchesFefoFifo(
              inventoryBatches.filter(
                (batch) =>
                  batch.skuId === materialSkuId &&
                  Number(batch.currentQty || 0) > 0
              ),
              referenceDate
            );
            const usableCandidates = candidateBatches.filter(
              (batch) => !getBatchExpiryInfo(batch, referenceDate).isExpired
            );
            const selectedNonExpiredIds = allocations
              .map((allocation) =>
                inventoryBatches.find((batch) => batch.batchId === allocation.batchId)
              )
              .filter(
                (batch) =>
                  batch && !getBatchExpiryInfo(batch, referenceDate).isExpired
              )
              .map((batch) => batch.batchId);
            const expectedFefoIds = new Set(
              usableCandidates
                .slice(0, selectedNonExpiredIds.length)
                .map((batch) => batch.batchId)
            );
            const fefoSkippedIds = selectedNonExpiredIds.filter(
              (batchId) => !expectedFefoIds.has(batchId)
            );
            let materialFefoOverrideReason = "";

            if (fefoSkippedIds.length > 0) {
              const recommendedText = usableCandidates
                .slice(0, selectedNonExpiredIds.length)
                .map((batch) => batch.batchId)
                .join(", ");
              const reason = window.prompt(
                `Pilihan batch ${materialSkuId} melewati urutan FEFO/FIFO.\n\nRekomendasi: ${recommendedText || "-"}\nDipilih di luar urutan: ${fefoSkippedIds.join(", ")}\n\nMasukkan alasan override:`
              );
              if (!reason || reason.trim().length < 5) {
                return alert("Alasan override FEFO/FIFO wajib diisi minimal 5 karakter.");
              }
              materialFefoOverrideReason = reason.trim();
            }

            for (let allocationIndex = 0; allocationIndex < allocations.length; allocationIndex += 1) {''',
"rebag FEFO reason setup")

# Replace expired confirmation with reason.
rep(
'''              const expiryInfo = getBatchExpiryInfo(sourceBatch, new Date(date));
              if (expiryInfo.isExpired && !isVerifiedSuperAdmin) {
                return alert(
                  `Batch ${sourceBatch.batchId} sudah EXPIRED dan tidak dapat digunakan untuk Rebagging.`
                );
              }
              if (expiryInfo.isExpired && isVerifiedSuperAdmin) {
                const allowExpired = window.confirm(
                  `PERINGATAN: Batch ${sourceBatch.batchId} sudah EXPIRED.\\n\\nLanjutkan sebagai override Super Admin?`
                );
                if (!allowExpired) return;
              }

              materialUsedTotal += usedQty;''',
'''              const expiryInfo = getBatchExpiryInfo(sourceBatch, referenceDate);
              let expiredOverrideReason = "";
              if (expiryInfo.isExpired && !isVerifiedSuperAdmin) {
                return alert(
                  `Batch ${sourceBatch.batchId} sudah EXPIRED dan tidak dapat digunakan untuk Rebagging.`
                );
              }
              if (expiryInfo.isExpired && isVerifiedSuperAdmin) {
                const reason = window.prompt(
                  `PERINGATAN: Batch ${sourceBatch.batchId} sudah EXPIRED.\n\nMasukkan alasan override Super Admin:`
                );
                if (!reason || reason.trim().length < 5) {
                  return alert("Alasan override batch expired wajib diisi minimal 5 karakter.");
                }
                expiredOverrideReason = reason.trim();
              }

              materialUsedTotal += usedQty;''',
"rebag expired reason")

rep(
'''                expiryDate: sourceBatch.expiryDate || "",
                expiredOverride: expiryInfo.isExpired,
                expiredOverrideBy: expiryInfo.isExpired ? currentUser.username : "",
              });''',
'''                expiryDate: sourceBatch.expiryDate || "",
                fefoOverride: fefoSkippedIds.includes(sourceBatch.batchId),
                fefoOverrideReason: fefoSkippedIds.includes(sourceBatch.batchId)
                  ? materialFefoOverrideReason
                  : "",
                fefoOverrideBy: fefoSkippedIds.includes(sourceBatch.batchId)
                  ? currentUser.username
                  : "",
                expiredOverride: expiryInfo.isExpired,
                expiredOverrideReason,
                expiredOverrideBy: expiryInfo.isExpired ? currentUser.username : "",
              });''',
"rebag audit fields")

# Outbound: capture FEFO/FIFO override reason and expired reason.
rep(
'''        const expiredOutboundItems = [];

        for (const item of selections) {''',
'''        const expiredOutboundItems = [];
        const outboundReferenceDate = new Date(date);
        const outboundCandidates = sortBatchesFefoFifo(
          inventoryBatches.filter(
            (batch) =>
              batch.skuId === sku.id &&
              Number(batch.currentQty || 0) > 0 &&
              (!isFinishedGoods || batch.resultTmNumber === outboundTm)
          ),
          outboundReferenceDate
        );
        const usableOutboundCandidates = outboundCandidates.filter(
          (batch) => !getBatchExpiryInfo(batch, outboundReferenceDate).isExpired
        );
        const selectedNonExpiredOutboundIds = selections
          .filter(
            (item) =>
              item.localBatch &&
              !getBatchExpiryInfo(item.localBatch, outboundReferenceDate).isExpired
          )
          .map((item) => item.batchId);
        const expectedOutboundIds = new Set(
          usableOutboundCandidates
            .slice(0, selectedNonExpiredOutboundIds.length)
            .map((batch) => batch.batchId)
        );
        const outboundFefoSkippedIds = selectedNonExpiredOutboundIds.filter(
          (batchId) => !expectedOutboundIds.has(batchId)
        );
        let outboundFefoOverrideReason = "";

        if (outboundFefoSkippedIds.length > 0) {
          const recommendedText = usableOutboundCandidates
            .slice(0, selectedNonExpiredOutboundIds.length)
            .map((batch) => batch.batchId)
            .join(", ");
          const reason = window.prompt(
            `Pilihan Outbound melewati urutan FEFO/FIFO.\n\nRekomendasi: ${recommendedText || "-"}\nDipilih di luar urutan: ${outboundFefoSkippedIds.join(", ")}\n\nMasukkan alasan override:`
          );
          if (!reason || reason.trim().length < 5) {
            return alert("Alasan override FEFO/FIFO wajib diisi minimal 5 karakter.");
          }
          outboundFefoOverrideReason = reason.trim();
        }

        for (const item of selections) {''',
"outbound FEFO reason setup")

rep(
'''        if (expiredOutboundItems.length > 0 && isVerifiedSuperAdmin) {
          const allowExpiredOutbound = window.confirm(
            `PERINGATAN: ${expiredOutboundItems.length} batch yang dipilih sudah EXPIRED.

Lanjutkan sebagai override Super Admin?`
          );
          if (!allowExpiredOutbound) return;
        }

        const expiredOutboundIds = new Set(
          expiredOutboundItems.map((item) => item.batchId)
        );''',
'''        let expiredOutboundOverrideReason = "";
        if (expiredOutboundItems.length > 0 && isVerifiedSuperAdmin) {
          const reason = window.prompt(
            `PERINGATAN: ${expiredOutboundItems.length} batch yang dipilih sudah EXPIRED.\n\nMasukkan alasan override Super Admin:`
          );
          if (!reason || reason.trim().length < 5) {
            return alert("Alasan override batch expired wajib diisi minimal 5 karakter.");
          }
          expiredOutboundOverrideReason = reason.trim();
        }

        const expiredOutboundIds = new Set(
          expiredOutboundItems.map((item) => item.batchId)
        );''',
"outbound expired reason")

rep(
'''                expiryDate: liveBatch.expiryDate || "",
                expiredOverride: expiredOutboundIds.has(item.batchId),
                expiredOverrideBy: expiredOutboundIds.has(item.batchId)
                  ? currentUser.username
                  : "",
                soNumber: formData.outSoNumber?.trim() || "",''',
'''                expiryDate: liveBatch.expiryDate || "",
                fefoOverride: outboundFefoSkippedIds.includes(item.batchId),
                fefoOverrideReason: outboundFefoSkippedIds.includes(item.batchId)
                  ? outboundFefoOverrideReason
                  : "",
                fefoOverrideBy: outboundFefoSkippedIds.includes(item.batchId)
                  ? currentUser.username
                  : "",
                expiredOverride: expiredOutboundIds.has(item.batchId),
                expiredOverrideReason: expiredOutboundIds.has(item.batchId)
                  ? expiredOutboundOverrideReason
                  : "",
                expiredOverrideBy: expiredOutboundIds.has(item.batchId)
                  ? currentUser.username
                  : "",
                soNumber: formData.outSoNumber?.trim() || "",''',
"outbound audit fields")

path.write_text(s, encoding="utf-8")
print("FEFO override audit patch applied.")
