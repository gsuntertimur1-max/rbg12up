from pathlib import Path

path = Path("src/App.jsx")
s = path.read_text(encoding="utf-8")

start = s.find("async function generateRebaggingBatchPdf")
end = s.find("\nfunction formatStockNumber", start)
if start < 0 or end < 0:
    raise SystemExit("generateRebaggingBatchPdf boundaries not found")

new_function = r'''async function generateRebaggingBatchPdf(tx, systemConfig = {}) {
  const pdf = new jsPDF({ orientation: "portrait", unit: "pt", format: "a4" });
  const totalPages = 3;
  const margin = 18;
  const lineColor = 45;
  const fillGray = 229;
  const lightGray = 247;

  let logo = null;
  try {
    logo = await loadPdfLogo();
  } catch (error) {
    console.warn("Logo PDF tidak dapat dimuat:", error);
  }

  const productName = String(tx.skuName || "PRODUK REBAGGING").toUpperCase();
  const fallbackStandards = getRebagStandards(productName);
  const storedControl = tx.documentControl || {};
  const docControl = {
    code: storedControl.code || systemConfig.rebagDocumentCode || "",
    revision: storedControl.revision || systemConfig.rebagDocumentRevision || "",
    effectiveDate:
      storedControl.effectiveDate || systemConfig.rebagDocumentEffectiveDate || "",
    sopRef: storedControl.sopRef || systemConfig.rebagSopRef || "",
    ssopRef: storedControl.ssopRef || systemConfig.rebagSsopRef || "",
    haccpRef: storedControl.haccpRef || systemConfig.rebagHaccpRef || "",
    scaleId: storedControl.scaleId || systemConfig.rebagScaleId || "",
    scaleCalibrationDue:
      storedControl.scaleCalibrationDue ||
      systemConfig.rebagScaleCalibrationDue ||
      "",
    approverName:
      storedControl.approverName ||
      systemConfig.rebagApproverName ||
      "IRSA MAULIAN NUGRAHA",
    standards: {
      ...fallbackStandards,
      ...(storedControl.standards || {}),
    },
  };

  const qualityControl = tx.qualityControl || {};
  const outputQty = Number(tx.outputQty ?? tx.processedQty ?? 0);
  const goodQty = Number(tx.goodQty ?? tx.finishedQty ?? tx.qtyChange ?? 0);
  const processQty = Number(tx.processQty ?? 0);
  const damageQty = Number(tx.damageQty ?? 0);
  const reconciledQty = goodQty + processQty + damageQty;
  const netWeightKg = Number(
    tx.netWeightKg ?? outputQty * Number(tx.weightPerPackKg || 0)
  );
  const supervisor = tx.supervisor || tx.operator || "";
  const executor = tx.executor || "KOPEL JAYA";
  const materials = Array.isArray(tx.materials) ? tx.materials : [];

  const line = (x1, y1, x2, y2, width = 0.45) => {
    pdf.setDrawColor(lineColor);
    pdf.setLineWidth(width);
    pdf.line(x1, y1, x2, y2);
  };

  const box = (x, y, w, h, fill = null) => {
    pdf.setDrawColor(lineColor);
    pdf.setLineWidth(0.45);
    if (fill !== null) {
      pdf.setFillColor(fill);
      pdf.rect(x, y, w, h, "FD");
    } else {
      pdf.rect(x, y, w, h);
    }
  };

  const txt = (value, x, y, opts = {}) => {
    const {
      size = 6.2,
      bold = false,
      align = "left",
      maxWidth = null,
      color = 0,
      maxLines = null,
    } = opts;

    pdf.setFont("helvetica", bold ? "bold" : "normal");
    pdf.setFontSize(size);
    pdf.setTextColor(color);
    const str = String(value ?? "");

    if (maxWidth) {
      let lines = pdf.splitTextToSize(str, maxWidth);
      if (maxLines && lines.length > maxLines) {
        lines = lines.slice(0, maxLines);
        const last = lines.length - 1;
        lines[last] = String(lines[last]).replace(/\s*$/, "") + "...";
      }
      pdf.text(lines, x, y, { align });
    } else {
      pdf.text(str, x, y, { align });
    }
  };

  const section = (label, y, pageWidth, height = 16) => {
    box(margin, y, pageWidth - margin * 2, height, fillGray);
    txt(label, margin + 3, y + 11, { size: 6.4, bold: true });
    return y + height;
  };

  const cell = (
    x,
    y,
    w,
    h,
    value,
    opts = {}
  ) => {
    box(x, y, w, h, opts.fill ?? null);
    txt(value, opts.align === "center" ? x + w / 2 : x + 3, y + 9, {
      size: opts.size || 5.4,
      bold: Boolean(opts.bold),
      align: opts.align || "left",
      maxWidth: opts.align === "center" ? w - 6 : w - 6,
      maxLines: opts.maxLines || 2,
      color: opts.color || 0,
    });
  };

  const drawHeader = (pageNo) => {
    const pageWidth = pdf.internal.pageSize.getWidth();
    const headerY = 18;
    const headerH = 76;
    const contentW = pageWidth - margin * 2;
    const logoW = pageWidth > 700 ? 150 : 132;
    const controlW = pageWidth > 700 ? 172 : 154;
    const centerW = contentW - logoW - controlW;

    box(margin, headerY, contentW, headerH);
    box(margin, headerY, logoW, headerH);
    box(margin + logoW, headerY, centerW, headerH);
    box(margin + logoW + centerW, headerY, controlW, headerH);

    if (logo) {
      try {
        pdf.addImage(
          logo,
          "PNG",
          margin + 12,
          headerY + 17,
          Math.min(118, logoW - 24),
          31
        );
      } catch (error) {
        txt("BULOG", margin + logoW / 2, headerY + 43, {
          size: 22,
          bold: true,
          align: "center",
        });
      }
    } else {
      txt("BULOG", margin + logoW / 2, headerY + 43, {
        size: 22,
        bold: true,
        align: "center",
      });
    }

    const centerX = margin + logoW + centerW / 2;
    txt("PERUM BULOG", centerX, headerY + 16, {
      size: 7.5,
      bold: true,
      align: "center",
    });
    txt("GBB SUNTER TIMUR I & II", centerX, headerY + 28, {
      size: 6.1,
      bold: true,
      align: "center",
    });
    txt("CATATAN PROSES REBAGGING BATCH", centerX, headerY + 44, {
      size: 8,
      bold: true,
      align: "center",
    });
    txt(productName, centerX, headerY + 59, {
      size: 6.8,
      bold: true,
      align: "center",
      maxWidth: centerW - 20,
      maxLines: 2,
    });

    const controlX = margin + logoW + centerW;
    const rowH = headerH / 4;
    const controlRows = [
      ["Kode Dokumen", docControl.code || "DRAFT - BELUM DITETAPKAN"],
      ["Revisi", docControl.revision || "DRAFT"],
      ["Tgl Berlaku", formatPdfDate(docControl.effectiveDate) || "-"],
      ["Halaman", pageNo + " dari " + totalPages],
    ];

    controlRows.forEach((row, index) => {
      const y = headerY + index * rowH;
      if (index > 0) line(controlX, y, controlX + controlW, y);
      txt(row[0], controlX + 4, y + 12, {
        size: 5.5,
        bold: true,
      });
      txt(": " + row[1], controlX + 55, y + 12, {
        size: 5.4,
        bold: index < 2,
        maxWidth: controlW - 60,
        maxLines: 2,
      });
    });

    return headerY + headerH + 8;
  };

  const drawFooter = (message) => {
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    line(margin, pageHeight - 18, pageWidth - margin, pageHeight - 18, 0.35);
    txt(message, margin, pageHeight - 9, {
      size: 4.6,
      color: 90,
      maxWidth: pageWidth - margin * 2,
      maxLines: 1,
    });
  };

  // PAGE 1 - proses produksi
  let pageWidth = pdf.internal.pageSize.getWidth();
  let y = drawHeader(1);

  const systemReferenceText =
    "Acuan sistem/PRP: " +
    docControl.standards.fsms +
    "; " +
    docControl.standards.prpManufacturing +
    "; " +
    docControl.standards.prpCommon +
    "; " +
    docControl.standards.cppob +
    ". Acuan mutu produk: " +
    docControl.standards.productQuality +
    ".";

  box(margin, y, pageWidth - margin * 2, 26, lightGray);
  txt(systemReferenceText, margin + 4, y + 10, {
    size: 5,
    bold: true,
    maxWidth: pageWidth - margin * 2 - 8,
    maxLines: 2,
  });
  y += 31;

  const metaRows = [
    ["No. Batch", tx.batchId || "", "Tanggal Produksi", formatPdfDate(tx.productionDate || tx.date)],
    ["MO Utama", tx.mainMoNumber || getPrimaryMoNumber(tx) || "", "TM Hasil", tx.resultTmNumber || ""],
    ["Pelaksana", executor, "Pengawas", supervisor],
    ["Tgl Kedaluwarsa", formatPdfDate(tx.expiryDate), "Komposisi", "v" + (tx.recipeVersion || 1)],
  ];

  metaRows.forEach((row) => {
    const rowH = 18;
    box(margin, y, pageWidth - margin * 2, rowH);
    txt(row[0], margin + 4, y + 12, { size: 5.7, bold: true });
    txt(": " + row[1], margin + 89, y + 12, {
      size: 5.7,
      maxWidth: 184,
      maxLines: 1,
    });
    txt(row[2], margin + 290, y + 12, { size: 5.7, bold: true });
    txt(": " + row[3], margin + 380, y + 12, {
      size: 5.7,
      maxWidth: pageWidth - margin - (margin + 380) - 4,
      maxLines: 1,
    });
    y += rowH;
  });

  y += 3;
  y = section("1. KESIAPAN / PRP", y, pageWidth);

  const prpRows = [
    "Kondisi ruangan produksi bersih",
    "Peralatan produksi bersih dan siap digunakan",
    "Higiene personel sesuai ketentuan",
    "Area produksi bebas potensi kontaminasi silang",
    "Alat timbang diverifikasi sebelum digunakan",
  ];

  prpRows.forEach((label) => {
    const h = 18;
    box(margin, y, pageWidth - margin * 2, h);
    txt(label, margin + 4, y + 12, { size: 5.7 });
    txt("Ya [ ]   Tidak [ ]", margin + 355, y + 12, {
      size: 5.7,
      bold: true,
    });
    txt("Paraf: __________", margin + 455, y + 12, { size: 5.7 });
    y += h;
  });

  box(margin, y, pageWidth - margin * 2, 22, lightGray);
  txt("ID Timbangan: " + (docControl.scaleId || "________________"), margin + 4, y + 14, {
    size: 5.6,
    bold: true,
  });
  txt(
    "Kalibrasi berlaku s.d.: " +
      (formatPdfDate(docControl.scaleCalibrationDue) || "________________"),
    margin + 190,
    y + 14,
    { size: 5.6, bold: true }
  );
  txt("Status: SESUAI [ ]  TIDAK [ ]", margin + 410, y + 14, {
    size: 5.6,
    bold: true,
  });
  y += 26;

  y = section("2. TAHAP PERSIAPAN", y, pageWidth);
  box(margin, y, pageWidth - margin * 2, 32);
  txt("2.1 Sortasi bahan baku / pemeriksaan bahan kemasan", margin + 4, y + 10, {
    size: 5.8,
    bold: true,
  });
  txt(
    "Mulai: ______   Selesai: ______   Pemeriksaan sesuai SOP/WI: Ya [ ] Tidak [ ]   Paraf: __________",
    margin + 4,
    y + 24,
    { size: 5.4, maxWidth: pageWidth - margin * 2 - 8, maxLines: 1 }
  );
  y += 36;

  y = section("3. PROSES REBAGGING", y, pageWidth);
  const processSteps = [
    "Naik bahan baku ke conveyor",
    "Penurunan bahan baku dari conveyor ke hopper",
    "Proses pengisian produk ke mesin packing",
    "Penimbangan otomatis dan sealing kemasan",
    "Packing kemasan primer ke dalam karton",
    "Pelabelan / pencetakan Exp Date dan kode produksi",
  ];

  processSteps.forEach((label, index) => {
    const h = 27;
    box(margin, y, pageWidth - margin * 2, h);
    txt("3." + (index + 1) + " " + label, margin + 4, y + 9, {
      size: 5.5,
      bold: true,
      maxWidth: 300,
      maxLines: 1,
    });
    txt(
      "Mulai: ____  Selesai: ____  Sesuai: Ya [ ] Tidak [ ]  Paraf: ______",
      margin + 4,
      y + 21,
      { size: 5.1 }
    );
    y += h;
  });

  y += 3;
  y = section("4. IN PROCESS CONTROL", y, pageWidth);
  const ipcRows = [
    "Berat netto sesuai spesifikasi produk",
    "Seal kemasan rapat",
    "Tidak ada kebocoran kemasan",
    "Exp Date / kode produksi jelas dan terbaca",
    "Karton dalam kondisi baik",
    "Line clearance / kebersihan area terjaga",
  ];

  ipcRows.forEach((label) => {
    const h = 18;
    box(margin, y, pageWidth - margin * 2, h);
    txt(label, margin + 4, y + 12, { size: 5.4 });
    txt("Sesuai [ ]  Tidak [ ]", margin + 355, y + 12, {
      size: 5.4,
      bold: true,
    });
    txt("Paraf: ______", margin + 472, y + 12, { size: 5.4 });
    y += h;
  });

  y += 3;
  y = section("5. REKONSILIASI HASIL PRODUKSI", y, pageWidth);
  box(margin, y, pageWidth - margin * 2, 50);
  txt("Output: " + formatStockNumber(outputQty) + " Pack", margin + 5, y + 15, {
    size: 7,
    bold: true,
  });
  txt("Berat netto: " + formatStockNumber(netWeightKg) + " Kg", margin + 126, y + 15, {
    size: 7,
    bold: true,
  });
  txt("GOOD: " + formatStockNumber(goodQty), margin + 280, y + 15, {
    size: 7,
    bold: true,
  });
  txt("PROCESS: " + formatStockNumber(processQty), margin + 377, y + 15, {
    size: 7,
    bold: true,
  });
  txt("DAMAGE: " + formatStockNumber(damageQty), margin + 475, y + 15, {
    size: 7,
    bold: true,
  });

  txt(
    "Status rekonsiliasi: " +
      (Math.abs(reconciledQty - outputQty) <= 0.0001
        ? "SEIMBANG"
        : "TIDAK SESUAI"),
    margin + 5,
    y + 35,
    { size: 5.8, bold: true }
  );
  txt(
    "Penyimpanan/Tumpukan: " + (tx.targetStack || ""),
    margin + 255,
    y + 35,
    { size: 5.8, bold: true, maxWidth: 280, maxLines: 1 }
  );

  drawFooter(
    "Dokumen rekaman produksi. Pengendalian, distribusi dan retensi mengikuti prosedur informasi terdokumentasi internal."
  );

  // PAGE 2 - landscape traceability
  pdf.addPage("a4", "landscape");
  pageWidth = pdf.internal.pageSize.getWidth();
  y = drawHeader(2);
  y = section("6. TRACEABILITY BAHAN / KEMASAN MULTI-BATCH", y, pageWidth);

  const traceHeaders = [
    "No",
    "SKU / Nama Bahan",
    "Batch Sumber",
    "MO",
    "TM Bahan",
    "Gudang",
    "Expiry",
    "FEFO/FIFO",
    "Pakai",
    "Rusak",
    "Sat",
  ];
  const widths = [22, 150, 95, 90, 90, 70, 55, 62, 52, 42, 40];
  let x = margin;
  traceHeaders.forEach((header, index) => {
    cell(x, y, widths[index], 24, header, {
      fill: fillGray,
      bold: true,
      align: "center",
      size: 5.2,
    });
    x += widths[index];
  });
  y += 24;

  const printableMaterials = materials.slice(0, 11);
  printableMaterials.forEach((material, index) => {
    const h = 24;
    const fefoLabel = material.expiredOverride
      ? "EXP OVERRIDE"
      : material.fefoOverride
      ? "OVERRIDE"
      : material.expiryDate
      ? "FEFO"
      : "FIFO";
    const row = [
      index + 1,
      ((material.skuId || "") + " " + (material.skuName || "")).trim(),
      material.batchId || "",
      material.moNumber || "",
      material.tmNumber || "",
      material.sourceWarehouse || "",
      formatPdfDate(material.expiryDate) || "-",
      fefoLabel,
      formatStockNumber(material.usedQty ?? material.qty ?? 0),
      formatStockNumber(material.damageQty || 0),
      material.unit || "",
    ];

    x = margin;
    row.forEach((value, colIndex) => {
      cell(x, y, widths[colIndex], h, value, {
        align: [0, 8, 9, 10].includes(colIndex) ? "center" : "left",
        size: colIndex === 1 ? 4.9 : 5.1,
        maxLines: 2,
      });
      x += widths[colIndex];
    });
    y += h;
  });

  if (materials.length > printableMaterials.length) {
    box(margin, y, pageWidth - margin * 2, 20, lightGray);
    txt(
      "+ " +
        (materials.length - printableMaterials.length) +
        " baris sumber tambahan tersimpan lengkap pada transaksi sistem dan laporan traceability.",
      margin + 4,
      y + 13,
      { size: 5.2, bold: true }
    );
    y += 24;
  }

  const overrideReasons = [
    ...new Set(
      materials
        .flatMap((material) => [
          material.fefoOverrideReason || "",
          material.expiredOverrideReason || "",
        ])
        .filter(Boolean)
    ),
  ];

  box(margin, y, pageWidth - margin * 2, 32, lightGray);
  txt(
    "Aturan traceability: seluruh batch bahan utama wajib berasal dari MO Utama yang sama. Bahan pendukung dapat berasal dari MO/TM/gudang berbeda.",
    margin + 4,
    y + 10,
    {
      size: 5.3,
      bold: true,
      maxWidth: pageWidth - margin * 2 - 8,
      maxLines: 1,
    }
  );
  txt(
    "Override FEFO/Expired: " +
      (overrideReasons.length > 0 ? overrideReasons.join(" | ") : "Tidak ada"),
    margin + 4,
    y + 23,
    {
      size: 5.1,
      maxWidth: pageWidth - margin * 2 - 8,
      maxLines: 1,
    }
  );
  y += 37;

  y = section("7. RINGKASAN PEMAKAIAN DAN WASTE BAHAN", y, pageWidth);

  const groupedMaterials = {};
  materials.forEach((material) => {
    const key = (material.skuId || "UNKNOWN") + "|" + (material.unit || "");
    if (!groupedMaterials[key]) {
      groupedMaterials[key] = {
        skuId: material.skuId || "",
        name: material.skuName || material.skuId || "",
        unit: material.unit || "",
        used: 0,
        damage: 0,
      };
    }
    const damage = Number(material.damageQty || 0);
    const total = Number(material.totalQty ?? material.qty ?? 0);
    const used = Number(material.usedQty ?? Math.max(0, total - damage));
    groupedMaterials[key].used += used;
    groupedMaterials[key].damage += damage;
  });

  const summaryRows = Object.values(groupedMaterials).slice(0, 7);
  const summaryHeaders = ["SKU", "Bahan", "Dipakai Baik", "Rusak/Waste", "Total Keluar", "Satuan"];
  const summaryWidths = [90, 280, 110, 110, 110, 80];
  x = margin;
  summaryHeaders.forEach((header, index) => {
    cell(x, y, summaryWidths[index], 22, header, {
      fill: fillGray,
      bold: true,
      align: "center",
      size: 5.3,
    });
    x += summaryWidths[index];
  });
  y += 22;

  summaryRows.forEach((row) => {
    const values = [
      row.skuId,
      row.name,
      formatStockNumber(row.used),
      formatStockNumber(row.damage),
      formatStockNumber(row.used + row.damage),
      row.unit,
    ];
    x = margin;
    values.forEach((value, index) => {
      cell(x, y, summaryWidths[index], 22, value, {
        align: index >= 2 ? "center" : "left",
        size: 5.2,
      });
      x += summaryWidths[index];
    });
    y += 22;
  });

  drawFooter(
    "Traceability digital pada sistem tetap menjadi sumber data lengkap apabila jumlah sumber material melebihi ruang cetak."
  );

  // PAGE 3 - quality, nonconformity, release
  pdf.addPage("a4", "portrait");
  pageWidth = pdf.internal.pageSize.getWidth();
  y = drawHeader(3);

  y = section("8. VERIFIKASI MUTU PRODUK / SNI", y, pageWidth);
  box(margin, y, pageWidth - margin * 2, 108);
  txt("Acuan mutu produk:", margin + 4, y + 13, {
    size: 5.8,
    bold: true,
  });
  txt(docControl.standards.productQuality, margin + 98, y + 13, {
    size: 5.8,
    bold: true,
    maxWidth: pageWidth - margin - (margin + 98) - 5,
    maxLines: 2,
  });
  txt(
    "No. COA / Hasil Uji: " +
      (qualityControl.coaNumber || "________________________________________"),
    margin + 4,
    y + 36,
    { size: 5.8 }
  );
  txt(
    "Status mutu: " +
      (qualityControl.qualityStatus || "SESUAI [ ]  TIDAK SESUAI [ ]  MENUNGGU [ ]"),
    margin + 300,
    y + 36,
    { size: 5.8, bold: true }
  );
  txt(
    "Pemenuhan parameter SNI dibuktikan melalui COA/hasil uji atau bukti verifikasi mutu yang berlaku. Form ini tidak menggantikan pengujian laboratorium.",
    margin + 4,
    y + 58,
    {
      size: 5.3,
      maxWidth: pageWidth - margin * 2 - 8,
      maxLines: 2,
    }
  );
  txt(
    "ID Timbangan: " +
      (docControl.scaleId || "________________") +
      "   |   Kalibrasi berlaku s.d.: " +
      (formatPdfDate(docControl.scaleCalibrationDue) || "________________"),
    margin + 4,
    y + 87,
    { size: 5.7, bold: true }
  );
  y += 113;

  y = section("9. PENYIMPANGAN / PRODUK TIDAK SESUAI DAN TINDAKAN KOREKSI", y, pageWidth);
  box(margin, y, pageWidth - margin * 2, 142);
  txt("Penyimpangan / ketidaksesuaian:", margin + 4, y + 14, {
    size: 5.8,
    bold: true,
  });
  txt(
    qualityControl.deviation ||
      "______________________________________________________________________________________________",
    margin + 4,
    y + 32,
    {
      size: 5.5,
      maxWidth: pageWidth - margin * 2 - 8,
      maxLines: 3,
    }
  );
  txt("Tindakan koreksi / disposisi:", margin + 4, y + 68, {
    size: 5.8,
    bold: true,
  });
  txt(
    qualityControl.correctiveAction ||
      "______________________________________________________________________________________________",
    margin + 4,
    y + 86,
    {
      size: 5.5,
      maxWidth: pageWidth - margin * 2 - 8,
      maxLines: 3,
    }
  );
  txt("Verifikasi efektivitas tindakan:", margin + 4, y + 120, {
    size: 5.8,
    bold: true,
  });
  txt(
    qualityControl.effectiveness ||
      "______________________________________________________________________________________________",
    margin + 4,
    y + 136,
    {
      size: 5.5,
      maxWidth: pageWidth - margin * 2 - 8,
      maxLines: 1,
    }
  );
  y += 147;

  y = section("10. STATUS RELEASE PRODUK JADI", y, pageWidth);
  box(margin, y, pageWidth - margin * 2, 86);
  txt(
    "Keputusan: " +
      (qualityControl.releaseStatus ||
        "RELEASE [ ]   HOLD [ ]   REJECT [ ]"),
    margin + 4,
    y + 18,
    { size: 6.5, bold: true }
  );
  txt(
    "Diverifikasi oleh: " +
      (qualityControl.releaseBy || "________________________") +
      "   Jabatan: " +
      (qualityControl.releaseRole || "________________") +
      "   Tanggal: " +
      (formatPdfDate(qualityControl.releaseDate) || "__________"),
    margin + 4,
    y + 43,
    { size: 5.6 }
  );
  txt(
    "Keterangan / alasan: " +
      (qualityControl.releaseNote ||
        "__________________________________________________________________________"),
    margin + 4,
    y + 67,
    {
      size: 5.6,
      maxWidth: pageWidth - margin * 2 - 8,
      maxLines: 1,
    }
  );
  y += 91;

  y = section("11. REFERENSI DOKUMEN INTERNAL DAN PENGENDALIAN REKAMAN", y, pageWidth);
  box(margin, y, pageWidth - margin * 2, 88);
  txt("SOP / WI Rebagging:", margin + 4, y + 16, { size: 5.6, bold: true });
  txt(docControl.sopRef || "______________________________", margin + 102, y + 16, {
    size: 5.6,
  });
  txt("SSOP / PRP:", margin + 302, y + 16, { size: 5.6, bold: true });
  txt(docControl.ssopRef || "______________________________", margin + 365, y + 16, {
    size: 5.6,
  });
  txt("HACCP / Analisis Bahaya:", margin + 4, y + 39, {
    size: 5.6,
    bold: true,
  });
  txt(docControl.haccpRef || "______________________________", margin + 128, y + 39, {
    size: 5.6,
  });
  txt(
    "Retensi rekaman: mengikuti prosedur pengendalian informasi terdokumentasi internal yang berlaku.",
    margin + 4,
    y + 64,
    {
      size: 5.4,
      bold: true,
      maxWidth: pageWidth - margin * 2 - 8,
      maxLines: 2,
    }
  );
  y += 93;

  y = section("12. VERIFIKASI DAN PERSETUJUAN", y, pageWidth);
  box(margin, y, pageWidth - margin * 2, 112);

  const sigW = (pageWidth - margin * 2) / 3;
  line(margin + sigW, y, margin + sigW, y + 112);
  line(margin + sigW * 2, y, margin + sigW * 2, y + 112);

  txt("Pelaksana", margin + sigW / 2, y + 15, {
    size: 6,
    bold: true,
    align: "center",
  });
  txt("Pengawas / QC", margin + sigW * 1.5, y + 15, {
    size: 6,
    bold: true,
    align: "center",
  });
  txt("Persetujuan / Kepala GBB", margin + sigW * 2.5, y + 15, {
    size: 6,
    bold: true,
    align: "center",
  });

  txt("(" + executor + ")", margin + sigW / 2, y + 96, {
    size: 5.8,
    bold: true,
    align: "center",
    maxWidth: sigW - 10,
    maxLines: 1,
  });
  txt(
    "(" + (supervisor || "____________________") + ")",
    margin + sigW * 1.5,
    y + 96,
    {
      size: 5.8,
      bold: true,
      align: "center",
      maxWidth: sigW - 10,
      maxLines: 1,
    }
  );
  txt(
    "(" + (docControl.approverName || "____________________") + ")",
    margin + sigW * 2.5,
    y + 96,
    {
      size: 5.8,
      bold: true,
      align: "center",
      maxWidth: sigW - 10,
      maxLines: 1,
    }
  );

  drawFooter(
    "Dokumen ini mendukung rekaman produksi, PRP, traceability dan pengendalian ketidaksesuaian. Kesesuaian sertifikasi tetap bergantung pada implementasi sistem dan audit."
  );

  const safeBatch = String(tx.batchId || "batch").replace(/[^a-z0-9-_]/gi, "_");
  pdf.save("Catatan_Proses_Rebagging_ISO_SNI_" + safeBatch + ".pdf");
}
'''

s = s[:start] + new_function + s[end:]
path.write_text(s, encoding="utf-8")
print("ISO/SNI/CPPOB 3-page PDF patch applied.")
