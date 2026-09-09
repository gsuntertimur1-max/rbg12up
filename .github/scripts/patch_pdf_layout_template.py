from pathlib import Path

path = Path("src/App.jsx")
s = path.read_text(encoding="utf-8")

def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"Patch target not found: {label}")
    s = s.replace(old, new, 1)

# Use template-like margins.
rep(
'''  const margin = 18;''',
'''  const margin = 30;''',
"PDF margin")

# Add reusable material summary after materials definition.
rep(
'''  const supervisor = tx.supervisor || tx.operator || "";
  const executor = tx.executor || "KOPEL JAYA";
  const materials = Array.isArray(tx.materials) ? tx.materials : [];

  const line =''',
'''  const supervisor = tx.supervisor || tx.operator || "";
  const executor = tx.executor || "KOPEL JAYA";
  const materials = Array.isArray(tx.materials) ? tx.materials : [];

  const materialSummaryMap = {};
  materials.forEach((material) => {
    const key = `${material.skuId || "UNKNOWN"}|${material.unit || ""}`;
    if (!materialSummaryMap[key]) {
      materialSummaryMap[key] = {
        skuId: material.skuId || "",
        skuName: material.skuName || material.skuId || "",
        unit: material.unit || "",
        usedQty: 0,
        damageQty: 0,
        standardQty:
          material.standardQty !== null &&
          material.standardQty !== undefined &&
          Number.isFinite(Number(material.standardQty))
            ? Number(material.standardQty)
            : null,
      };
    }

    const damage = Number(material.damageQty || 0);
    const total = Number(material.totalQty ?? material.qty ?? 0);
    const used = Number(material.usedQty ?? Math.max(0, total - damage));

    materialSummaryMap[key].usedQty += used;
    materialSummaryMap[key].damageQty += damage;

    if (
      materialSummaryMap[key].standardQty === null &&
      material.standardQty !== null &&
      material.standardQty !== undefined &&
      Number.isFinite(Number(material.standardQty))
    ) {
      materialSummaryMap[key].standardQty = Number(material.standardQty);
    }
  });
  const materialSummaryRows = Object.values(materialSummaryMap);

  const line =''',
"material summary")

# Replace header with Excel-inspired header + ratio-safe logo.
start = s.find('''  const drawHeader = (pageNo) => {''')
end = s.find('''

  const drawFooter = (message) => {''', start)
if start < 0 or end < 0:
    raise SystemExit("drawHeader block not found")

new_header = r'''  const drawImageFit = (img, x, y, w, h) => {
    const naturalWidth = Number(img?.naturalWidth || img?.width || 1);
    const naturalHeight = Number(img?.naturalHeight || img?.height || 1);
    if (!naturalWidth || !naturalHeight) return;

    const scale = Math.min(w / naturalWidth, h / naturalHeight);
    const renderW = naturalWidth * scale;
    const renderH = naturalHeight * scale;

    pdf.addImage(
      img,
      "PNG",
      x + (w - renderW) / 2,
      y + (h - renderH) / 2,
      renderW,
      renderH
    );
  };

  const drawHeader = (pageNo) => {
    const pageWidth = pdf.internal.pageSize.getWidth();
    const controlY = 16;
    const mainY = 28;
    const headerH = 62;
    const contentW = pageWidth - margin * 2;
    const logoW = pageWidth > 700 ? 300 : 245;
    const titleW = contentW - logoW;

    txt(
      `Kode: ${docControl.code || "DRAFT"} | Rev: ${docControl.revision || "DRAFT"} | Berlaku: ${formatPdfDate(docControl.effectiveDate) || "-"} | Halaman ${pageNo} dari ${totalPages}`,
      pageWidth - margin,
      controlY + 1,
      { size: 4.8, align: "right", color: 55 }
    );

    box(margin, mainY, logoW, headerH);
    box(margin + logoW, mainY, titleW, headerH);

    if (logo) {
      try {
        drawImageFit(
          logo,
          margin + 22,
          mainY + 13,
          logoW - 44,
          headerH - 26
        );
      } catch (error) {
        txt("BULOG", margin + logoW / 2, mainY + 39, {
          size: 20,
          bold: true,
          align: "center",
        });
      }
    } else {
      txt("BULOG", margin + logoW / 2, mainY + 39, {
        size: 20,
        bold: true,
        align: "center",
      });
    }

    const headerRows = [
      { text: "PERUM BULOG", size: 7.8, bold: true },
      {
        text:
          pageWidth > 700
            ? "GBB SUNTER TIMUR I & II"
            : "Jl. Pelepah Raya, RW.5, Klp. Gading Barat, Kec. Klp. Gading, Jakarta Utara",
        size: pageWidth > 700 ? 6.1 : 4.8,
        bold: pageWidth > 700,
      },
      { text: "CATATAN PROSES REBAGGING BATCH", size: 7.2, bold: true },
      { text: "NAMA PRODUK : " + productName, size: 6.5, bold: true },
    ];

    const rowH = headerH / headerRows.length;
    headerRows.forEach((row, index) => {
      const rowY = mainY + index * rowH;
      if (index > 0) {
        line(margin + logoW, rowY, margin + logoW + titleW, rowY);
      }
      txt(
        row.text,
        margin + logoW + titleW / 2,
        rowY + rowH - 5,
        {
          size: row.size,
          bold: row.bold,
          align: "center",
          maxWidth: titleW - 10,
          maxLines: 1,
        }
      );
    });

    return mainY + headerH;
  };'''

s = s[:start] + new_header + s[end:]

# Replace page 1 with Excel-template-inspired operational page.
start = s.find('''  // PAGE 1 - proses produksi''')
end = s.find('''

  // PAGE 2 - landscape traceability''', start)
if start < 0 or end < 0:
    raise SystemExit("Page 1 boundaries not found")

page1 = r'''  // PAGE 1 - operational form based on Excel template
  let pageWidth = pdf.internal.pageSize.getWidth();
  let y = drawHeader(1);

  const contentWidth = pageWidth - margin * 2;
  const leftMetaWidth = contentWidth * 0.58;
  const rightMetaWidth = contentWidth - leftMetaWidth;

  const drawMetaRow = (leftLabel, leftValue, rightLabel, rightValue) => {
    const rowH = 14;
    box(margin, y, contentWidth, rowH);
    line(
      margin + leftMetaWidth,
      y,
      margin + leftMetaWidth,
      y + rowH
    );

    txt(leftLabel, margin + 2, y + 10, {
      size: 5.35,
      bold: true,
    });
    txt(": " + String(leftValue || ""), margin + 73, y + 10, {
      size: 5.35,
      maxWidth: leftMetaWidth - 78,
      maxLines: 1,
    });

    txt(rightLabel, margin + leftMetaWidth + 2, y + 10, {
      size: 5.35,
      bold: true,
    });
    txt(
      ": " + String(rightValue || ""),
      margin + leftMetaWidth + 87,
      y + 10,
      {
        size: 5.35,
        maxWidth: rightMetaWidth - 92,
        maxLines: 1,
      }
    );
    y += rowH;
  };

  drawMetaRow(
    "No. Batch",
    tx.batchId || "",
    "Tanggal Kedaluwarsa",
    formatPdfDate(tx.expiryDate)
  );
  drawMetaRow(
    "Tanggal Produksi",
    formatPdfDate(tx.productionDate || tx.date),
    "Pengawas",
    supervisor
  );
  drawMetaRow(
    "Pelaksana",
    executor,
    "Komposisi",
    "v" + (tx.recipeVersion || 1)
  );
  drawMetaRow(
    "MO Utama",
    tx.mainMoNumber || getPrimaryMoNumber(tx) || "",
    "TM Hasil",
    tx.resultTmNumber || ""
  );

  y = section("1. KESIAPAN", y, pageWidth, 14);

  [
    "Kondisi ruangan produksi dalam keadaan bersih",
    "Peralatan produksi dalam keadaan bersih",
    "Higiene karyawan sudah baik",
  ].forEach((label) => {
    const rowH = 16;
    box(margin, y, contentWidth, rowH);
    txt(label, margin + 2, y + 11, { size: 5.35 });
    txt("Ya", margin + contentWidth - 292, y + 11, { size: 5.1 });
    txt("Tidak", margin + contentWidth - 253, y + 11, { size: 5.1 });
    txt("Paraf pelaksana:", margin + contentWidth - 177, y + 11, {
      size: 5.1,
    });
    y += rowH;
  });

  y = section("2. TAHAP PERSIAPAN", y, pageWidth, 14);

  box(margin, y, contentWidth, 14, lightGray);
  txt("2.1 Sortasi Bahan Baku / Pemeriksaan Kemasan", margin + 2, y + 10, {
    size: 5.45,
    bold: true,
  });
  y += 14;

  box(margin, y, contentWidth, 14);
  txt("Mulai jam : ______", margin + 2, y + 10, { size: 5.15 });
  txt("Selesai jam : ______", margin + 275, y + 10, { size: 5.15 });
  txt("Paraf pelaksana: ______", margin + 420, y + 10, {
    size: 5.15,
  });
  y += 14;

  box(margin, y, contentWidth, 14);
  txt("Pemeriksaan sesuai standar : Ya / Tidak", margin + 2, y + 10, {
    size: 5.15,
  });
  y += 14;

  y = section("3. PENIMBANGAN", y, pageWidth, 14);

  const weighingWidths = [210, 100, 70, 70, 85];
  const weighingHeaders = [
    "Bahan",
    "Jumlah Standar",
    "Aktual",
    "Pelaksana",
    "Pengawas",
  ];

  let wx = margin;
  weighingHeaders.forEach((header, index) => {
    cell(wx, y, weighingWidths[index], 17, header, {
      fill: lightGray,
      bold: true,
      align: "center",
      size: 5.35,
      maxLines: 1,
    });
    wx += weighingWidths[index];
  });
  y += 17;

  const visibleSummaryRows = materialSummaryRows.slice(0, 5);
  visibleSummaryRows.forEach((material) => {
    const materialText =
      (material.skuId ? material.skuId + " " : "") +
      (material.skuName || "");
    const actualText =
      formatStockNumber(material.usedQty) +
      (material.unit ? " " + material.unit : "") +
      (material.damageQty > 0
        ? " + rusak " + formatStockNumber(material.damageQty)
        : "");
    const standardText =
      material.standardQty !== null &&
      Number.isFinite(Number(material.standardQty))
        ? formatStockNumber(material.standardQty) +
          (material.unit ? " " + material.unit : "")
        : "-";

    const materialLines = pdf.splitTextToSize(
      materialText,
      weighingWidths[0] - 6
    );
    const standardLines = pdf.splitTextToSize(
      standardText,
      weighingWidths[1] - 6
    );
    const actualLines = pdf.splitTextToSize(
      actualText,
      weighingWidths[2] - 6
    );
    const executorLines = pdf.splitTextToSize(
      executor,
      weighingWidths[3] - 6
    );
    const supervisorLines = pdf.splitTextToSize(
      supervisor,
      weighingWidths[4] - 6
    );

    const maxLineCount = Math.max(
      materialLines.length,
      standardLines.length,
      actualLines.length,
      executorLines.length,
      supervisorLines.length
    );
    const rowH = Math.max(16, Math.min(30, 6 + maxLineCount * 6));

    const rowValues = [
      materialText,
      standardText,
      actualText,
      executor,
      supervisor,
    ];

    wx = margin;
    rowValues.forEach((value, index) => {
      cell(wx, y, weighingWidths[index], rowH, value, {
        align: index === 0 ? "left" : "center",
        size: index === 0 ? 5.0 : 5.05,
        maxLines: 3,
      });
      wx += weighingWidths[index];
    });
    y += rowH;
  });

  if (materialSummaryRows.length > visibleSummaryRows.length) {
    const rowH = 16;
    cell(
      margin,
      y,
      contentWidth,
      rowH,
      "+ " +
        (materialSummaryRows.length - visibleSummaryRows.length) +
        " bahan lain - lihat Traceability Halaman 2",
      {
        fill: lightGray,
        bold: true,
        size: 5.1,
      }
    );
    y += rowH;
  }

  y = section("4. PROSES REBAGGING", y, pageWidth, 14);

  const processSteps = [
    "4.1 Naik bahan baku ke Conveyor",
    "4.2 Penurunan bahan baku dari Conveyor ke Hopper",
    "4.3 Proses pengisian produk ke dalam Mesin Packing",
    "4.4 Penimbangan otomatis dan sealing kemasan",
    "4.5 Packing kemasan primer ke dalam Karton",
    "4.6 Pelabelan / Pencetakan Exp Date",
  ];

  processSteps.forEach((label) => {
    const rowH = 22;
    box(margin, y, contentWidth, rowH);
    txt(label, margin + 2, y + 8, {
      size: 5.3,
      bold: true,
      maxWidth: contentWidth - 4,
      maxLines: 1,
    });
    txt(
      "Mulai: ____   Selesai: ____   Pemeriksaan: Ya / Tidak   Paraf: ______",
      margin + 2,
      y + 18,
      { size: 4.85 }
    );
    y += rowH;
  });

  y = section(
    "5. PENGAWASAN SELAMA PROSES (IN PROCESS CONTROL)",
    y,
    pageWidth,
    14
  );

  [
    "Berat netto sesuai standar",
    "Seal kemasan rapat",
    "Kemasan bocor",
    "Cetakan Exp Date jelas dan terbaca",
    "Karton dalam kondisi baik",
  ].forEach((label) => {
    const rowH = 15;
    box(margin, y, contentWidth, rowH);
    txt(label, margin + 2, y + 10, { size: 5.05 });
    txt("Hasil: __________", margin + 318, y + 10, { size: 5.05 });
    txt("Paraf: ______", margin + 452, y + 10, { size: 5.05 });
    y += rowH;
  });

  y = section("6. REKONSILIASI HASIL PRODUKSI", y, pageWidth, 14);

  const reconciliationWidths = [130, 130, 160, 115];
  const reconciliationCells = [
    ["Output", formatStockNumber(outputQty) + " Pack"],
    ["Berat Netto", formatStockNumber(netWeightKg) + " Kg"],
    [
      "GOOD / PROCESS / DAMAGE",
      "G:" +
        formatStockNumber(goodQty) +
        " / P:" +
        formatStockNumber(processQty) +
        " / D:" +
        formatStockNumber(damageQty),
    ],
    [
      "Status",
      Math.abs(reconciledQty - outputQty) <= 0.0001
        ? "SEIMBANG"
        : "TIDAK SESUAI",
    ],
  ];

  wx = margin;
  reconciliationCells.forEach((entry, index) => {
    box(wx, y, reconciliationWidths[index], 30);
    txt(entry[0], wx + 3, y + 9, { size: 4.8, bold: true });
    txt(entry[1], wx + 3, y + 22, {
      size: 5.35,
      bold: true,
      maxWidth: reconciliationWidths[index] - 6,
      maxLines: 1,
    });
    wx += reconciliationWidths[index];
  });
  y += 30;

  y = section("7. PENYIMPANAN PRODUK JADI", y, pageWidth, 14);
  box(margin, y, contentWidth, 23);
  txt(
    "Penyimpanan : " + (tx.targetStack || ""),
    margin + 2,
    y + 14,
    { size: 5.35 }
  );
  y += 23;

  y = section("8. VERIFIKASI", y, pageWidth, 14);
  box(margin, y, contentWidth, 28);
  txt("Diperiksa oleh : " + supervisor, margin + 2, y + 10, {
    size: 5.15,
  });
  txt(
    "Tanggal : " + formatPdfDate(tx.productionDate || tx.date),
    margin + 2,
    y + 22,
    { size: 5.15 }
  );
  y += 28;

  const signatureH = 55;
  const signatureMid = margin + contentWidth / 2;
  box(margin, y, contentWidth, signatureH);
  line(signatureMid, y, signatureMid, y + signatureH);

  txt(
    "(.................................)",
    margin + contentWidth / 4,
    y + signatureH - 17,
    { size: 5.0, align: "center" }
  );
  txt("Operator", margin + contentWidth / 4, y + signatureH - 6, {
    size: 5.1,
    bold: true,
    align: "center",
  });

  txt(
    "PERUM BULOG",
    signatureMid + contentWidth / 4,
    y + 12,
    { size: 5.1, bold: true, align: "center" }
  );
  txt(
    "(" + (docControl.approverName || "____________________") + ")",
    signatureMid + contentWidth / 4,
    y + signatureH - 17,
    {
      size: 5.0,
      bold: true,
      align: "center",
      maxWidth: contentWidth / 2 - 10,
      maxLines: 1,
    }
  );
  txt(
    "Kepala Gudang Sunter Timur I & II",
    signatureMid + contentWidth / 4,
    y + signatureH - 6,
    {
      size: 5.0,
      bold: true,
      align: "center",
      maxWidth: contentWidth / 2 - 10,
      maxLines: 1,
    }
  );

  drawFooter(
    "Halaman operasional mengikuti template Catatan Proses Rebagging Perbatch; detail traceability dan verifikasi mutu tersedia pada halaman berikutnya."
  );'''

s = s[:start] + page1 + s[end:]

path.write_text(s, encoding="utf-8")
print("PDF layout template patch applied.")
