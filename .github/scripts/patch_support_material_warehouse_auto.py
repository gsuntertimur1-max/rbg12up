from pathlib import Path

path = Path('src/App.jsx')
s = path.read_text(encoding='utf-8')

def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f'Patch target not found: {label}')
    s = s.replace(old, new, 1)

rep(
'''        const normalizedLines = inboundLines.map((line) => ({
          ...line,
          sku: skus.find((s) => s.id === line.skuId),
          qtyValue: Number(line.qty),
          moNumber: String(line.moNumber || "").trim(),
          tmNumber: String(line.tmNumber || "").trim(),
          sourceWarehouse: String(line.sourceWarehouse || "").trim(),
        }));''',
'''        const normalizedLines = inboundLines.map((line) => {
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
        });''',
'normalize support material warehouse'
)

rep(
'''                                  <input
                                    type="text"
                                    className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-blue-500"
                                    value={line.sourceWarehouse}
                                    onChange={e=>updateInboundLine(line.rowId,'sourceWarehouse',e.target.value)}
                                    placeholder="Contoh: GST I / Unit 18"
                                    required
                                  />
                                  <p className="mt-1.5 text-[10px] leading-4 text-slate-400">
                                    Untuk Beras/Gula, gudang ini tetap menjadi pemilik stok secara administrasi. Lokasi fisik setelah diterima: {getProcessingLocation(systemConfig)}.
                                  </p>''',
'''                                  {(() => {
                                    const selectedSku = skus.find((s) => s.id === line.skuId);
                                    const supportMaterial = isPackagingMaterialSku(selectedSku);
                                    return (
                                      <>
                                        <input
                                          type="text"
                                          className={`w-full p-3 border rounded-lg outline-none ${supportMaterial ? "border-cyan-200 bg-cyan-50 font-bold text-cyan-800" : "border-slate-300 focus:border-blue-500"}`}
                                          value={supportMaterial ? getProcessingLocation(systemConfig) : line.sourceWarehouse}
                                          onChange={e=>!supportMaterial && updateInboundLine(line.rowId,'sourceWarehouse',e.target.value)}
                                          placeholder="Contoh: GST I / Unit 18"
                                          readOnly={supportMaterial}
                                          required={!supportMaterial}
                                        />
                                        <p className="mt-1.5 text-[10px] leading-4 text-slate-400">
                                          {supportMaterial
                                            ? `Kemasan/kardus otomatis menjadi stok administrasi dan fisik ${getProcessingLocation(systemConfig)}.`
                                            : `Untuk Beras/Gula, gudang ini tetap menjadi pemilik stok administrasi. Lokasi fisik setelah diterima: ${getProcessingLocation(systemConfig)}.`}
                                        </p>
                                      </>
                                    );
                                  })()}''',
'inbound support material auto warehouse UI'
)

path.write_text(s, encoding='utf-8')
print('Support material warehouse automation applied.')
