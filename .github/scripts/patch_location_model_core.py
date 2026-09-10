from pathlib import Path

path = Path('src/App.jsx')
s = path.read_text(encoding='utf-8')

def rep(old, new, label, count=1):
    global s
    if old not in s:
        raise SystemExit(f'Patch target not found: {label}')
    for _ in range(count):
        s = s.replace(old, new, 1)

# 1) Master lokasi defaults + helpers. Only known locations are seeded.
marker = '''const MATERIAL_SUPPORT_KEYWORDS = ['''
insert = r'''const DEFAULT_LOCATIONS = [
  {
    id: "UP17",
    code: "UP 17",
    name: "Unit Gudang 17 (UP 17)",
    type: "UP",
    functions: ["STORAGE", "REBAG_GULA"],
    active: true,
  },
  {
    id: "UP20",
    code: "UP 20",
    name: "Unit Gudang 20 (UP 20)",
    type: "UP",
    functions: ["STORAGE", "REBAG_BERAS"],
    active: true,
  },
  {
    id: "RTR60",
    code: "RTR 60",
    name: "RTR (60)",
    type: "RTR",
    functions: ["STORAGE", "REBAG_GULA", "REBAG_BERAS"],
    active: true,
  },
  {
    id: "MULTIPURPOSE",
    code: "MULTI PURPOSE",
    name: "Gudang Multi Purpose",
    type: "MULTI_PURPOSE",
    functions: ["STORAGE", "REBAG_GULA", "REBAG_BERAS"],
    active: true,
  },
];

const getLocationDisplayName = (location) =>
  String(location?.name || location?.code || location?.id || "").trim();

const locationSupportsRebag = (location, targetSku) => {
  if (!location || location.active === false) return false;
  const functions = Array.isArray(location.functions) ? location.functions : [];
  const name = String(targetSku?.name || "").toUpperCase();
  if (name.includes("GULA")) return functions.includes("REBAG_GULA");
  if (name.includes("BERAS") || name.includes("FORTIVIT")) {
    return functions.includes("REBAG_BERAS");
  }
  return functions.includes("REBAG_GULA") || functions.includes("REBAG_BERAS");
};

const locationSupportsStorage = (location) =>
  Boolean(location && location.active !== false && (location.functions || []).includes("STORAGE"));

'''
rep(marker, insert + marker, 'location defaults and helpers')

# 2) Physical-location fallback remains compatible with legacy data.
rep(
'''const getBatchPhysicalLocation = (batch, config = {}) =>
  String(batch?.physicalLocation || getProcessingLocation(config)).trim() ||
  getProcessingLocation(config);''',
'''const getBatchPhysicalLocation = (batch, config = {}) =>
  String(
    batch?.physicalLocationName ||
    batch?.physicalLocation ||
    batch?.sourceWarehouse ||
    getProcessingLocation(config)
  ).trim() || getProcessingLocation(config);''',
'batch physical location fallback'
)

# 3) App state/forms.
rep(
'''  const [qcRecords, setQcRecords] = useState([]);
  const [rebagRecipes, setRebagRecipes] = useState(DEFAULT_REBAG_RECIPES);''',
'''  const [qcRecords, setQcRecords] = useState([]);
  const [locations, setLocations] = useState(DEFAULT_LOCATIONS);
  const [rebagRecipes, setRebagRecipes] = useState(DEFAULT_REBAG_RECIPES);''',
'locations state'
)
rep(
'''  const initialFormData = {
    rebagTargetSkuId: "", rebagTargetStack: "", bulkSkuId: "", bulkBatchId: "", qtyToProcess: "",''',
'''  const initialFormData = {
    rebagTargetSkuId: "", rebagProcessingLocationId: "", rebagFinishedLocationId: "", rebagTargetStack: "", bulkSkuId: "", bulkBatchId: "", qtyToProcess: "",''',
'rebag location form fields'
)
rep(
'''  const [inboundLines, setInboundLines] = useState([
    { rowId: "IN-1", skuId: "", qty: "", moNumber: "", tmNumber: "", sourceWarehouse: "" }
  ]);''',
'''  const [inboundLines, setInboundLines] = useState([
    { rowId: "IN-1", skuId: "", qty: "", moNumber: "", tmNumber: "", sourceWarehouse: "", physicalLocationId: "" }
  ]);''',
'inbound physical location field'
)
rep(
'''  const [newUserForm, setNewUserForm] = useState({ username: "", password: "", role: "Operator" });''',
'''  const [newUserForm, setNewUserForm] = useState({ username: "", password: "", role: "Operator" });
  const [locationForm, setLocationForm] = useState({
    id: "",
    code: "",
    name: "",
    type: "GBB",
    functions: ["STORAGE"],
    active: true,
  });
  const [internalMoveForm, setInternalMoveForm] = useState({
    batchId: "",
    qty: "",
    destinationLocationId: "",
    reason: "",
  });''',
'location and move form state'
)

# 4) Firestore Master Lokasi listener with defaults.
marker = '''    const unsubRecipes = onSnapshot('''
listener = r'''    const unsubLocations = onSnapshot(
      collection(db, "artifacts", appId, "public", "data", "locations"),
      (snap) => {
        if (snap.empty) {
          setLocations(DEFAULT_LOCATIONS);
          Promise.all(
            DEFAULT_LOCATIONS.map((location) =>
              setDoc(
                doc(db, "artifacts", appId, "public", "data", "locations", location.id),
                location
              )
            )
          ).catch(handleDbError("inisialisasi master lokasi"));
        } else {
          setLocations(
            snap.docs
              .map((d) => ({ id: d.id, ...d.data() }))
              .sort((a, b) =>
                getLocationDisplayName(a).localeCompare(getLocationDisplayName(b), undefined, {
                  numeric: true,
                  sensitivity: "base",
                })
              )
          );
        }
      },
      handleDbError("master lokasi")
    );

'''
rep(marker, listener + marker, 'locations listener')
rep(
'''      unsubBatches();
      unsubRecipes();''',
'''      unsubBatches();
      unsubLocations();
      unsubRecipes();''',
'locations unsubscribe'
)

# 5) Add/remove inbound lines keep physical-location field.
rep(
'''        tmNumber: "",
        sourceWarehouse: "",
      },''',
'''        tmNumber: "",
        sourceWarehouse: "",
        physicalLocationId: "",
      },''',
'add inbound physical field'
)
rep(
'''        : [{ rowId: `IN-${Date.now()}`, skuId: "", qty: "", moNumber: "", tmNumber: "", sourceWarehouse: "" }];''',
'''        : [{ rowId: `IN-${Date.now()}`, skuId: "", qty: "", moNumber: "", tmNumber: "", sourceWarehouse: "", physicalLocationId: "" }];''',
'remove inbound fallback physical field'
)

# 6) Rebag target reset also resets selected locations.
rep(
'''      rebagTargetSkuId: value,
      bulkSkuId: "",''',
'''      rebagTargetSkuId: value,
      rebagProcessingLocationId: "",
      rebagFinishedLocationId: "",
      bulkSkuId: "",''',
'rebag target location reset'
)

# 7) Master Lokasi CRUD handlers before transaction handler.
marker = '''  const handleTransactionSubmit = async (e) => {'''
handlers = r'''  const resetLocationForm = () => {
    setLocationForm({
      id: "",
      code: "",
      name: "",
      type: "GBB",
      functions: ["STORAGE"],
      active: true,
    });
  };

  const handleLocationFunctionToggle = (functionId) => {
    setLocationForm((prev) => {
      const current = Array.isArray(prev.functions) ? prev.functions : [];
      const next = current.includes(functionId)
        ? current.filter((item) => item !== functionId)
        : [...current, functionId];
      return { ...prev, functions: next };
    });
  };

  const handleSaveLocation = async (e) => {
    e.preventDefault();
    if (!isVerifiedSuperAdmin) return alert("Master Lokasi hanya dapat diubah oleh Super Admin.");
    const code = String(locationForm.code || "").trim();
    const name = String(locationForm.name || "").trim();
    if (!code || !name) return alert("Kode dan Nama Lokasi wajib diisi.");
    if (!Array.isArray(locationForm.functions) || locationForm.functions.length === 0) {
      return alert("Pilih minimal satu fungsi lokasi.");
    }

    const id = locationForm.id || getStableDocId(code);
    await setDoc(
      doc(db, "artifacts", appId, "public", "data", "locations", id),
      {
        id,
        code,
        name,
        type: locationForm.type || "GBB",
        functions: locationForm.functions,
        active: locationForm.active !== false,
        updatedAt: new Date().toISOString(),
        updatedBy: currentUser.username,
      },
      { merge: true }
    );
    showNotif(locationForm.id ? "Master Lokasi diperbarui" : "Master Lokasi ditambahkan");
    resetLocationForm();
  };

  const handleEditLocation = (location) => {
    setLocationForm({
      id: location.id,
      code: location.code || "",
      name: location.name || "",
      type: location.type || "GBB",
      functions: Array.isArray(location.functions) ? location.functions : ["STORAGE"],
      active: location.active !== false,
    });
  };

  const handleDeleteLocation = async (location) => {
    if (!isVerifiedSuperAdmin) return;
    const used = inventoryBatches.some(
      (batch) =>
        batch.physicalLocationId === location.id ||
        batch.processingLocationId === location.id ||
        batch.finishedLocationId === location.id
    );
    if (used) {
      return alert("Lokasi sudah dipakai pada stok/transaksi. Nonaktifkan lokasi daripada menghapusnya.");
    }
    if (!window.confirm(`Hapus lokasi ${getLocationDisplayName(location)}?`)) return;
    await deleteDoc(doc(db, "artifacts", appId, "public", "data", "locations", location.id));
    showNotif("Master Lokasi dihapus");
    if (locationForm.id === location.id) resetLocationForm();
  };

'''
rep(marker, handlers + marker, 'location CRUD handlers')

# 8) Inbound normalization now requires a chosen physical location.
old = '''        const normalizedLines = inboundLines.map((line) => {
          const sku = skus.find((s) => s.id === line.skuId);
          const supportMaterial = isPackagingMaterialSku(sku);
          return {
            ...line,
            sku,
            qtyValue: Number(line.qty),
            moNumber: String(line.moNumber || "").trim(),
            tmNumber: String(line.tmNumber || "").trim(),
            sourceWarehouse: supportMaterial
              ? getProcessingLocation(systemConfig)
              : String(line.sourceWarehouse || "").trim(),
          };
        });'''
new = '''        const normalizedLines = inboundLines.map((line) => {
          const sku = skus.find((s) => s.id === line.skuId);
          const supportMaterial = isPackagingMaterialSku(sku);
          const physicalLocation = locations.find(
            (location) => location.id === line.physicalLocationId && location.active !== false
          );
          const physicalLocationName = getLocationDisplayName(physicalLocation);
          return {
            ...line,
            sku,
            supportMaterial,
            physicalLocation,
            physicalLocationName,
            qtyValue: Number(line.qty),
            moNumber: String(line.moNumber || "").trim(),
            tmNumber: String(line.tmNumber || "").trim(),
            sourceWarehouse: supportMaterial
              ? physicalLocationName
              : String(line.sourceWarehouse || "").trim(),
          };
        });'''
rep(old, new, 'inbound normalize location master')
rep(
'''          if (!line.tmNumber) return alert(`${rowLabel}: No. TM bahan wajib diisi.`);
          if (!line.sourceWarehouse) return alert(`${rowLabel}: gudang asal wajib diisi.`);''',
'''          if (!line.tmNumber) return alert(`${rowLabel}: No. TM bahan wajib diisi.`);
          if (!line.physicalLocation) return alert(`${rowLabel}: Lokasi Fisik wajib dipilih dari Master Lokasi.`);
          if (!line.sourceWarehouse) return alert(`${rowLabel}: Gudang Administrasi wajib diisi.`);''',
'inbound location validation'
)

# 9) Inbound records use chosen physical location. Support admin follows physical location.
rep(
'''          const physicalLocation = getProcessingLocation(systemConfig);
          const administrativeWarehouse = isPackagingMaterialSku(line.sku)
            ? physicalLocation
            : line.sourceWarehouse;''',
'''          const physicalLocation = line.physicalLocationName;
          const physicalLocationId = line.physicalLocation.id;
          const administrativeWarehouse = line.supportMaterial
            ? physicalLocation
            : line.sourceWarehouse;''',
'inbound derived locations'
)
rep(
'''              administrativeWarehouse,
              physicalLocation,
              materialClass,''',
'''              administrativeWarehouse,
              physicalLocationId,
              physicalLocation,
              physicalLocationName: physicalLocation,
              materialClass,''',
'inbound batch physical ID',
1
)
rep(
'''              administrativeWarehouse,
              physicalLocation,
              materialClass,''',
'''              administrativeWarehouse,
              physicalLocationId,
              physicalLocation,
              physicalLocationName: physicalLocation,
              materialClass,''',
'inbound tx physical ID',
1
)

# 10) Rebag requires process + finished locations.
rep(
'''        if (!targetSku) return alert("Pilih SKU hasil rebagging.");
        if (!Number.isFinite(qty) || qty <= 0) return alert("Kuantitas hasil yang diproses harus lebih dari 0.");''',
'''        if (!targetSku) return alert("Pilih SKU hasil rebagging.");
        const processingLocation = locations.find(
          (location) => location.id === formData.rebagProcessingLocationId && location.active !== false
        );
        const finishedLocation = locations.find(
          (location) => location.id === formData.rebagFinishedLocationId && location.active !== false
        );
        if (!processingLocation) return alert("Pilih Lokasi Proses Rebagging.");
        if (!locationSupportsRebag(processingLocation, targetSku)) {
          return alert(`Lokasi ${getLocationDisplayName(processingLocation)} belum diizinkan untuk proses produk ${targetSku.name}. Atur fungsi lokasi di Master Lokasi.`);
        }
        if (!finishedLocation || !locationSupportsStorage(finishedLocation)) {
          return alert("Pilih Lokasi Produk Jadi yang aktif dan memiliki fungsi Penyimpanan.");
        }
        if (!Number.isFinite(qty) || qty <= 0) return alert("Kuantitas hasil yang diproses harus lebih dari 0.");''',
'rebag location validation'
)

# Each selected material carries physical location id.
rep(
'''                physicalLocation: getBatchPhysicalLocation(sourceBatch, systemConfig),
                materialClass:''',
'''                physicalLocationId: sourceBatch.physicalLocationId || "",
                physicalLocation: getBatchPhysicalLocation(sourceBatch, systemConfig),
                materialClass:''',
'recipe material physical location id'
)
rep(
'''              physicalLocation: getBatchPhysicalLocation(selectedBatch, systemConfig),
              materialClass:''',
'''              physicalLocationId: selectedBatch.physicalLocationId || "",
              physicalLocation: getBatchPhysicalLocation(selectedBatch, systemConfig),
              materialClass:''',
'manual material physical location id'
)

# Before producing, all selected material must physically be at the chosen process location.
rep(
'''        let newBatchId = "";
        const txId = `TRX-${timestamp}`;''',
'''        const processingLocationName = getLocationDisplayName(processingLocation);
        const finishedLocationName = getLocationDisplayName(finishedLocation);
        const locationMismatch = selectedMaterials.find((material) => {
          if (material.physicalLocationId) {
            return material.physicalLocationId !== processingLocation.id;
          }
          return String(material.physicalLocation || "").trim().toUpperCase() !==
            processingLocationName.toUpperCase();
        });
        if (locationMismatch) {
          return alert(
            `Batch ${locationMismatch.batchId} secara fisik berada di ${locationMismatch.physicalLocation || "lokasi lain"}. Pindahkan dulu melalui Mutasi Internal ke ${processingLocationName}.`
          );
        }

        let newBatchId = "";
        const txId = `TRX-${timestamp}`;''',
'rebag physical co-location validation'
)

# Replace old global physical location assignment for finished goods.
rep(
'''        const administrativeWarehouse = primaryAdministrativeWarehouses.join(", ");
        const physicalLocation = getProcessingLocation(systemConfig);''',
'''        const administrativeWarehouse = primaryAdministrativeWarehouses.join(", ");
        const physicalLocation = finishedLocationName;''',
'rebag final physical location'
)

# Store process and finished location IDs/names in batch/tx.
rep(
'''            physicalLocation,
            targetStack: formData.rebagTargetStack,''',
'''            processingLocationId: processingLocation.id,
            processingLocation: processingLocationName,
            finishedLocationId: finishedLocation.id,
            physicalLocationId: finishedLocation.id,
            physicalLocation,
            physicalLocationName: physicalLocation,
            targetStack: formData.rebagTargetStack,''',
'finished batch process/final locations',
1
)
rep(
'''              physicalLocation,
              sourceBatchId: primaryMaterial?.batchId || "",''',
'''              processingLocationId: processingLocation.id,
              processingLocation: processingLocationName,
              finishedLocationId: finishedLocation.id,
              physicalLocationId: finishedLocation.id,
              physicalLocation,
              physicalLocationName: physicalLocation,
              sourceBatchId: primaryMaterial?.batchId || "",''',
'rebag tx process/final locations',
1
)

# 11) Internal Move branch before outbound. Supports full relocation or partial split.
marker = '''      } else if (activeOpTab === "outbound") {'''
move_branch = r'''      } else if (activeOpTab === "internal_move") {
        const sourceBatch = inventoryBatches.find(
          (batch) => batch.batchId === internalMoveForm.batchId
        );
        const moveQty = Number(internalMoveForm.qty || 0);
        const destination = locations.find(
          (location) =>
            location.id === internalMoveForm.destinationLocationId &&
            location.active !== false &&
            locationSupportsStorage(location)
        );
        const reason = String(internalMoveForm.reason || "").trim();

        if (!sourceBatch) return alert("Pilih batch sumber mutasi internal.");
        if (!destination) return alert("Pilih lokasi tujuan dari Master Lokasi.");
        if (!Number.isFinite(moveQty) || moveQty <= 0) return alert("Qty mutasi harus lebih dari 0.");
        if (moveQty > Number(sourceBatch.currentQty || 0)) {
          return alert(`Qty mutasi melebihi stok aktif batch (${sourceBatch.currentQty || 0}).`);
        }
        if (reason.length < 3) return alert("Alasan mutasi wajib diisi minimal 3 karakter.");

        const sourceLocationName = getBatchPhysicalLocation(sourceBatch, systemConfig);
        const destinationName = getLocationDisplayName(destination);
        if (
          sourceBatch.physicalLocationId === destination.id ||
          (!sourceBatch.physicalLocationId && sourceLocationName.toUpperCase() === destinationName.toUpperCase())
        ) {
          return alert("Lokasi tujuan sama dengan lokasi fisik saat ini.");
        }

        const sourceSku = skus.find((sku) => sku.id === sourceBatch.skuId);
        const sourceRef = doc(
          db,
          "artifacts",
          appId,
          "public",
          "data",
          "batches",
          sourceBatch.batchId
        );
        const moveTxId = `TRX-MOVE-${timestamp}`;

        await runTransaction(db, async (transaction) => {
          const sourceSnap = await transaction.get(sourceRef);
          if (!sourceSnap.exists()) throw new Error("Batch sumber sudah tidak ditemukan.");
          const liveBatch = sourceSnap.data();
          const liveQty = Number(liveBatch.currentQty || 0);
          if (moveQty > liveQty) {
            throw new Error(`Qty mutasi melebihi stok terbaru (${liveQty}).`);
          }

          const hasOtherQualityQty =
            Number(liveBatch.processQty || 0) > 0 || Number(liveBatch.damageQty || 0) > 0;
          const isFullActiveMove = Math.abs(moveQty - liveQty) <= 0.0001 && !hasOtherQualityQty;
          let destinationBatchId = liveBatch.batchId;

          if (isFullActiveMove) {
            transaction.update(sourceRef, {
              physicalLocationId: destination.id,
              physicalLocation: destinationName,
              physicalLocationName: destinationName,
              lastInternalMoveAt: date,
              lastInternalMoveBy: currentUser.username,
            });
          } else {
            destinationBatchId = `${liveBatch.batchId}-MV-${String(timestamp).slice(-6)}`;
            const destinationRef = doc(
              db,
              "artifacts",
              appId,
              "public",
              "data",
              "batches",
              destinationBatchId
            );

            transaction.update(sourceRef, {
              currentQty: liveQty - moveQty,
              ...(sourceSku?.type === "rebagged"
                ? {
                    goodQty: Math.max(0, Number(liveBatch.goodQty ?? liveQty) - moveQty),
                    goodKg: Math.max(
                      0,
                      Number(liveBatch.goodKg || 0) -
                        moveQty * (Number(liveBatch.weightPerPackKg) || inferWeightPerPackKg(sourceSku) || 0)
                    ),
                  }
                : {}),
            });

            const movedWeight =
              sourceSku?.type === "rebagged"
                ? moveQty * (Number(liveBatch.weightPerPackKg) || inferWeightPerPackKg(sourceSku) || 0)
                : 0;

            transaction.set(destinationRef, {
              ...liveBatch,
              batchId: destinationBatchId,
              parentBatchId: liveBatch.parentBatchId || liveBatch.batchId,
              productionBatchId: liveBatch.productionBatchId || liveBatch.batchId,
              splitFromBatchId: liveBatch.batchId,
              initialQty: moveQty,
              currentQty: moveQty,
              ...(sourceSku?.type === "rebagged"
                ? {
                    goodQty: moveQty,
                    goodKg: movedWeight,
                    processQty: 0,
                    processKg: 0,
                    damageQty: 0,
                    damageKg: 0,
                  }
                : {}),
              physicalLocationId: destination.id,
              physicalLocation: destinationName,
              physicalLocationName: destinationName,
              locationMoveSplit: true,
              movedAt: date,
              movedBy: currentUser.username,
            });
          }

          transaction.set(
            doc(db, "artifacts", appId, "public", "data", "transactions", moveTxId),
            {
              id: moveTxId,
              date,
              type: "INTERNAL_MOVE",
              skuId: liveBatch.skuId,
              skuName: sourceSku?.name || liveBatch.skuId,
              qtyChange: moveQty,
              unit: sourceSku?.unit || "",
              sourceBatchId: liveBatch.batchId,
              destinationBatchId,
              batchId: destinationBatchId,
              moNumber: liveBatch.moNumber || "",
              mainMoNumber: liveBatch.mainMoNumber || getPrimaryMoNumber(liveBatch) || "",
              tmNumber: liveBatch.tmNumber || "",
              resultTmNumber: liveBatch.resultTmNumber || "",
              administrativeWarehouse:
                liveBatch.administrativeWarehouse ||
                (Array.isArray(liveBatch.administrativeWarehouses)
                  ? liveBatch.administrativeWarehouses.join(", ")
                  : ""),
              administrativeWarehouses: liveBatch.administrativeWarehouses || [],
              fromPhysicalLocationId: liveBatch.physicalLocationId || "",
              fromPhysicalLocation: sourceLocationName,
              toPhysicalLocationId: destination.id,
              toPhysicalLocation: destinationName,
              reason,
              operator: currentUser.username,
              ...auditMeta,
            }
          );
        });

        setInternalMoveForm({
          batchId: "",
          qty: "",
          destinationLocationId: "",
          reason: "",
        });
''' + marker
rep(marker, move_branch, 'internal move transaction branch')

# 12) Transaction success reset retains physical field.
rep(
'''        { rowId: `IN-${Date.now()}`, skuId: "", qty: "", moNumber: "", tmNumber: "", sourceWarehouse: "" }
      ]);''',
'''        { rowId: `IN-${Date.now()}`, skuId: "", qty: "", moNumber: "", tmNumber: "", sourceWarehouse: "", physicalLocationId: "" }
      ]);''',
'transaction reset inbound physical field'
)

path.write_text(s, encoding='utf-8')
print('Location model core patch applied.')
