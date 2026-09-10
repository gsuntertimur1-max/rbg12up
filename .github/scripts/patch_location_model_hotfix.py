from pathlib import Path

path = Path('src/App.jsx')
s = path.read_text(encoding='utf-8')

def rep(old, new, label, count=1):
    global s
    if old not in s:
        raise SystemExit(f'Patch target not found: {label}')
    for _ in range(count):
        s = s.replace(old, new, 1)

# FEFO candidate scope must match selected process location and QC eligibility.
rep(
'''              inventoryBatches.filter(
                (batch) =>
                  batch.skuId === materialSkuId &&
                  Number(batch.currentQty || 0) > 0
              ),''',
'''              inventoryBatches.filter((batch) => {
                if (!(batch.skuId === materialSkuId && Number(batch.currentQty || 0) > 0 && isRawBatchQcUsable(batch))) {
                  return false;
                }
                if (!formData.rebagProcessingLocationId) return true;
                if (batch.physicalLocationId) {
                  return batch.physicalLocationId === formData.rebagProcessingLocationId;
                }
                return getBatchPhysicalLocation(batch, systemConfig).toUpperCase() ===
                  getLocationDisplayName(processingLocation).toUpperCase();
              }),''',
'FEFO candidate physical scope'
)

# Support materials are the exception: their administrative warehouse follows physical location on internal move.
rep(
'''          if (isFullActiveMove) {
            transaction.update(sourceRef, {
              physicalLocationId: destination.id,''',
'''          const supportMaterialMove = isPackagingMaterialSku(sourceSku);
          const sourceAdministrativeWarehouse =
            liveBatch.administrativeWarehouse ||
            (Array.isArray(liveBatch.administrativeWarehouses)
              ? liveBatch.administrativeWarehouses.join(", ")
              : liveBatch.sourceWarehouse || "");
          const destinationAdministrativeWarehouse = supportMaterialMove
            ? destinationName
            : sourceAdministrativeWarehouse;

          if (isFullActiveMove) {
            transaction.update(sourceRef, {
              ...(supportMaterialMove ? { administrativeWarehouse: destinationAdministrativeWarehouse } : {}),
              physicalLocationId: destination.id,''',
'support admin on full move'
)
rep(
'''              physicalLocationId: destination.id,
              physicalLocation: destinationName,
              physicalLocationName: destinationName,
              locationMoveSplit: true,''',
'''              administrativeWarehouse: destinationAdministrativeWarehouse,
              physicalLocationId: destination.id,
              physicalLocation: destinationName,
              physicalLocationName: destinationName,
              locationMoveSplit: true,''',
'support admin on split move'
)
rep(
'''              administrativeWarehouse:
                liveBatch.administrativeWarehouse ||
                (Array.isArray(liveBatch.administrativeWarehouses)
                  ? liveBatch.administrativeWarehouses.join(", ")
                  : ""),
              administrativeWarehouses: liveBatch.administrativeWarehouses || [],''',
'''              administrativeWarehouse: destinationAdministrativeWarehouse,
              administrativeWarehouseBefore: sourceAdministrativeWarehouse,
              administrativeWarehouseAfter: destinationAdministrativeWarehouse,
              administrativeWarehouses: liveBatch.administrativeWarehouses || [],
              supportMaterialMove,''',
'internal move admin audit'
)

rep(
'''Memindahkan posisi fisik stok tanpa mengubah Gudang Administrasi, MO, TM, atau identitas asal. Mutasi parsial otomatis membentuk batch lokasi turunan agar saldo per lokasi tetap akurat.''',
'''Memindahkan posisi fisik stok tanpa mengubah MO, TM, atau identitas asal. Untuk Beras/Gula Gudang Administrasi tetap; khusus kemasan/kardus Gudang Administrasi mengikuti lokasi fisik tujuan. Mutasi parsial otomatis membentuk batch lokasi turunan.''',
'internal move UI note'
)

path.write_text(s, encoding='utf-8')
print('Location model hotfix applied.')
