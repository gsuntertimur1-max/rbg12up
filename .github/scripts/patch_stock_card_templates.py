from pathlib import Path

path = Path("src/App.jsx")
s = path.read_text(encoding="utf-8")

raw_start = s.find("async function generateRawMaterialStockCardPdf")
fg_start = s.find("async function generateFinishedGoodsStockCardPdf", raw_start)
app_start = s.find("// --- APLIKASI UTAMA ---", fg_start)

if raw_start < 0 or fg_start < 0 or app_start < 0:
    raise SystemExit("Stock card function boundaries not found")

new_raw = r'''async function generateRawMaterialStockCardPdf({
  sku,
  batches,
  transactions,
  systemConfig = {},
}) {
  const pdf = new jsPDF({ orientation: "portrait", unit: "pt", format: "a4" });
  const pageW = pdf.internal.pageSize.getWidth();
  const pageH = pdf.internal.pageSize.getHeight();
  const L = 40;
  const R = pageW - 40;
  const W = R - L;
  const approver =
    systemConfig.rebagApproverName || "IRSA MAULIAN NUGRAHA";
  const unitLabel = String(sku.unit || "UNIT").toUpperCase();

  const inbound = transactions
    .filter((t) => t.type === "INBOUND" && t.skuId === sku.id)
    .map((t) => ({
      kind: "IN",
      date: t.date,
      qty: Number(t.qtyChange) || 0,
      moNumber: t.moNumber || "",
      batchId: t.batchId || "",
      stack: t.stackNumber || t.sourceWarehouse || "",
    }));

  const rebagOut = transactions
    .filter((t) => t.type === "REBAGGING")
    .flatMap((t) => {
      if (Array.isArray(t.materials) && t.materials.length > 0) {
        return t.materials
          .filter((m) => m.skuId === sku.id)
          .map((m) => ({
            kind: "OUT",
            date: t.date,
            qty: Number(m.qty ?? m.totalQty) || 0,
            moNumber: m.moNumber || "",
            batchId: m.batchId || "",
            stack: m.sourceWarehouse || "",
          }));
      }

      if (t.sourceSkuId === sku.id) {
        return [{
          kind: "OUT",
          date: t.date,
          qty: Number(t.sourceQty ?? t.qtyChange) || 0,
          moNumber: t.mainMoNumber || t.moNumber || "",
          batchId: t.sourceBatchId || "",
          stack: t.sourceWarehouse || "",
        }];
      }

      return [];
    });

  const allMoNumbers = [
    ...new Set(
      [...inbound, ...rebagOut]
        .map((item) => String(item.moNumber || "").trim())
        .filter(Boolean)
    ),
  ];

  if (allMoNumbers.length === 0) {
    allMoNumbers.push("TANPA-MO");
  }

  const drawLogoFit = async (x, y, w, h) => {
    try {
      const logo = await loadPdfLogo();
      const naturalW = Number(logo?.naturalWidth || logo?.width || 1);
      const naturalH = Number(logo?.naturalHeight || logo?.height || 1);
      const scale = Math.min(w / naturalW, h / naturalH);
      const renderW = naturalW * scale;
      const renderH = naturalH * scale;
      pdf.addImage(
        logo,
        "PNG",
        x + (w - renderW) / 2,
        y + (h - renderH) / 2,
        renderW,
        renderH
      );
    } catch (error) {
      console.warn("Logo kartu bahan baku gagal dimuat:", error);
      pdf.setFont("helvetica", "bold");
      pdf.setFontSize(20);
      pdf.text("BULOG", x + w / 2, y + h / 2 + 7, { align: "center" });
    }
  };

  const line = (x1, y1, x2, y2, width = 0.55) => {
    pdf.setDrawColor(25);
    pdf.setLineWidth(width);
    pdf.line(x1, y1, x2, y2);
  };

  const box = (x, y, w, h) => {
    pdf.setDrawColor(25);
    pdf.setLineWidth(0.55);
    pdf.rect(x, y, w, h);
  };

  const txt = (value, x, y, opts = {}) => {
    const {
      size = 8,
      bold = false,
      align = "left",
      maxWidth = null,
      maxLines = null,
    } = opts;
    pdf.setFont("helvetica", bold ? "bold" : "normal");
    pdf.setFontSize(size);
    pdf.setTextColor(0);
    let text = String(value ?? "");
    if (maxWidth) {
      let lines = pdf.splitTextToSize(text, maxWidth);
      if (maxLines && lines.length > maxLines) {
        lines = lines.slice(0, maxLines);
        lines[lines.length - 1] =
          String(lines[lines.length - 1]).replace(/\s*$/, "") + "...";
      }
      pdf.text(lines, x, y, { align });
    } else {
      pdf.text(text, x, y, { align });
    }
  };

  const renderCardPage = async ({
    moNumber,
    cardEvents,
    pageIndex,
    pageCount,
    totalReceived,
    firstInbound,
    locations,
  }) => {
    if (pdf.getNumberOfPages() > 1 || pageIndex > 0 || moNumber !== allMoNumbers[0]) {
      pdf.addPage("a4", "portrait");
    }

    const headerY = 28;
    const headerH = 48;
    const logoW = 122;

    box(L, headerY, W, headerH);
    box(L, headerY, logoW, headerH);
    await drawLogoFit(L + 10, headerY + 6, logoW - 20, headerH - 12);
    txt(
      "KARTU PERSEDIAAN BAHAN BAKU",
      L + logoW + (W - logoW) / 2,
      headerY + 31,
      { size: 16, bold: true, align: "center" }
    );

    let y = headerY + headerH + 2;
    const metaRows = [
      ["Nama Produk", sku.name || ""],
      ["Nomor MO", moNumber === "TANPA-MO" ? "" : moNumber],
      ["Tanggal Masuk Gudang", firstInbound ? formatPdfDate(firstInbound.date) : ""],
      ["Jumlah Karung/Karton", totalReceived ? `${formatStockNumber(totalReceived)} ${unitLabel}` : ""],
      ["Lokasi Tumpukan", locations],
    ];

    metaRows.forEach(([label, value]) => {
      const rowH = 17;
      box(L, y, W, rowH);
      txt(label, L + 2, y + 12, { size: 7.4 });
      txt(":", L + 121, y + 12, { size: 7.4 });
      txt(value, L + 130, y + 12, {
        size: 7.4,
        bold: label === "Nama Produk",
        maxWidth: W - 136,
        maxLines: 1,
      });
      y += rowH;
    });

    y += 8;
    const groupH = 24;
    const headerH2 = 42;
    const cols = [105, 70, 92, 83, 61, 57, 48];
    const xs = [L];
    cols.forEach((w) => xs.push(xs[xs.length - 1] + w));

    box(L, y, W, groupH + headerH2 + 452);
    xs.slice(1, -1).forEach((x) => line(x, y, x, y + groupH + headerH2 + 452));
    line(L, y + groupH, R, y + groupH);
    line(L, y + groupH + headerH2, R, y + groupH + headerH2);

    txt("MASUK", (xs[0] + xs[3]) / 2, y + 17, {
      size: 12.5,
      bold: true,
      align: "center",
    });
    txt("KELUAR", (xs[3] + xs[6]) / 2, y + 17, {
      size: 12.5,
      bold: true,
      align: "center",
    });
    txt("Paraf", (xs[6] + xs[7]) / 2, y + 39, {
      size: 10,
      bold: true,
      align: "center",
    });

    const headers = [
      "Tanggal Masuk",
      `Jumlah (${unitLabel})`,
      "No. Tumpukan",
      "Tanggal Keluar",
      `Jumlah (${unitLabel})`,
      "Sisa",
    ];

    headers.forEach((label, i) => {
      txt(label, (xs[i] + xs[i + 1]) / 2, y + groupH + 16, {
        size: 8,
        bold: true,
        align: "center",
        maxWidth: cols[i] - 6,
        maxLines: 2,
      });
    });

    const bodyTop = y + groupH + headerH2;
    const rowH = 20;
    cardEvents.forEach((event, i) => {
      const rowTop = bodyTop + i * rowH;
      if (i > 0) line(L, rowTop, R, rowTop, 0.25);
      const textY = rowTop + 13;

      if (event.kind === "IN") {
        txt(formatPdfDate(event.date), (xs[0] + xs[1]) / 2, textY, {
          size: 7.4,
          align: "center",
        });
        txt(formatStockNumber(event.qty), (xs[1] + xs[2]) / 2, textY, {
          size: 7.4,
          align: "center",
        });
        txt(event.stack || "", (xs[2] + xs[3]) / 2, textY, {
          size: 7.0,
          align: "center",
          maxWidth: cols[2] - 6,
          maxLines: 1,
        });
      } else {
        txt(formatPdfDate(event.date), (xs[3] + xs[4]) / 2, textY, {
          size: 7.4,
          align: "center",
        });
        txt(formatStockNumber(event.qty), (xs[4] + xs[5]) / 2, textY, {
          size: 7.4,
          align: "center",
        });
      }

      txt(formatStockNumber(event.balance), (xs[5] + xs[6]) / 2, textY, {
        size: 7.4,
        align: "center",
      });
    });

    const footerY = pageH - 74;
    txt("Kepala GBB Sunter Timur I & II", R - 92, footerY, {
      size: 7.2,
      align: "center",
    });
    txt(approver, R - 92, footerY + 52, {
      size: 7.2,
      bold: true,
      align: "center",
    });

    if (pageCount > 1) {
      txt(
        `MO ${moNumber === "TANPA-MO" ? "-" : moNumber} - halaman ${pageIndex + 1} dari ${pageCount}`,
        L,
        pageH - 18,
        { size: 5.5 }
      );
    }
  };

  let firstRendered = false;

  for (const moNumber of allMoNumbers) {
    const moInbound = inbound.filter(
      (item) =>
        (moNumber === "TANPA-MO" && !item.moNumber) ||
        item.moNumber === moNumber
    );
    const moOutbound = rebagOut.filter(
      (item) =>
        (moNumber === "TANPA-MO" && !item.moNumber) ||
        item.moNumber === moNumber
    );

    const events = [...moInbound, ...moOutbound].sort(
      (a, b) => new Date(a.date) - new Date(b.date)
    );

    let balance = 0;
    events.forEach((event) => {
      balance += event.kind === "IN" ? event.qty : -event.qty;
      event.balance = balance;
    });

    const totalReceived = moInbound.reduce((sum, item) => sum + item.qty, 0);
    const firstInbound = [...moInbound].sort(
      (a, b) => new Date(a.date) - new Date(b.date)
    )[0];

    const locations = [
      ...new Set(
        [
          ...batches
            .filter((batch) =>
              moNumber === "TANPA-MO"
                ? !batch.moNumber
                : batch.moNumber === moNumber
            )
            .map((batch) =>
              batch.stackNumber ||
              batch.targetStack ||
              batch.sourceWarehouse
            ),
          ...moInbound.map((item) => item.stack),
        ].filter(Boolean)
      ),
    ].join(", ");

    const maxRows = 22;
    const chunks = [];
    if (events.length === 0) {
      chunks.push([]);
    } else {
      for (let i = 0; i < events.length; i += maxRows) {
        chunks.push(events.slice(i, i + maxRows));
      }
    }

    for (let pageIndex = 0; pageIndex < chunks.length; pageIndex += 1) {
      if (!firstRendered) {
        firstRendered = true;
      }
      await renderCardPage({
        moNumber,
        cardEvents: chunks[pageIndex],
        pageIndex,
        pageCount: chunks.length,
        totalReceived,
        firstInbound,
        locations,
      });
    }
  }

  const safeSku = String(sku.id || sku.name || "bahan-baku").replace(
    /[^a-z0-9-_]/gi,
    "_"
  );
  pdf.save("Kartu_Persediaan_Bahan_Baku_" + safeSku + ".pdf");
}

'''

new_fg = r'''async function generateFinishedGoodsStockCardPdf({
  sku,
  batches,
  transactions,
  systemConfig = {},
}) {
  const pdf = new jsPDF({ orientation: "landscape", unit: "pt", format: "a4" });
  const pageW = pdf.internal.pageSize.getWidth();
  const pageH = pdf.internal.pageSize.getHeight();
  const L = 34;
  const R = pageW - 34;
  const W = R - L;
  const approver =
    systemConfig.rebagApproverName || "IRSA MAULIAN NUGRAHA";
  const unitLabel = String(sku.unit || "UNIT").toUpperCase();

  const inbound = transactions
    .filter(
      (t) =>
        (t.type === "REBAGGING" || t.type === "PROCESS_TO_GOOD") &&
        t.skuId === sku.id
    )
    .map((t) => ({
      kind: "IN",
      date:
        t.type === "PROCESS_TO_GOOD"
          ? t.date
          : t.productionDate || t.date,
      batchId: t.batchId || "",
      qty:
        t.type === "PROCESS_TO_GOOD"
          ? Number(t.resolutionQty ?? t.qtyChange) || 0
          : Number(t.finishedQty ?? t.goodQty ?? t.qtyChange) || 0,
      stack: t.targetStack || "",
      productionDate: t.productionDate || t.date,
      resultTmNumber: t.resultTmNumber || "",
    }));

  const outbound = transactions
    .filter((t) => t.type === "OUTBOUND" && t.skuId === sku.id)
    .map((t) => ({
      kind: "OUT",
      date: t.date,
      batchId: t.batchId || "",
      qty: Number(t.qtyChange) || 0,
      soNumber: t.soNumber || "",
      customer: t.customer || "",
    }));

  const batchIds = [
    ...new Set(
      [
        ...batches.map((b) => b.batchId),
        ...inbound.map((item) => item.batchId),
        ...outbound.map((item) => item.batchId),
      ].filter(Boolean)
    ),
  ];

  if (batchIds.length === 0) {
    batchIds.push("TANPA-BATCH");
  }

  const drawLogoFit = async (x, y, w, h) => {
    try {
      const logo = await loadPdfLogo();
      const naturalW = Number(logo?.naturalWidth || logo?.width || 1);
      const naturalH = Number(logo?.naturalHeight || logo?.height || 1);
      const scale = Math.min(w / naturalW, h / naturalH);
      const renderW = naturalW * scale;
      const renderH = naturalH * scale;
      pdf.addImage(
        logo,
        "PNG",
        x + (w - renderW) / 2,
        y + (h - renderH) / 2,
        renderW,
        renderH
      );
    } catch (error) {
      console.warn("Logo kartu produk jadi gagal dimuat:", error);
      pdf.setFont("helvetica", "bold");
      pdf.setFontSize(20);
      pdf.text("BULOG", x + w / 2, y + h / 2 + 7, { align: "center" });
    }
  };

  const line = (x1, y1, x2, y2, width = 0.55) => {
    pdf.setDrawColor(25);
    pdf.setLineWidth(width);
    pdf.line(x1, y1, x2, y2);
  };

  const box = (x, y, w, h) => {
    pdf.setDrawColor(25);
    pdf.setLineWidth(0.55);
    pdf.rect(x, y, w, h);
  };

  const txt = (value, x, y, opts = {}) => {
    const {
      size = 7.4,
      bold = false,
      align = "left",
      maxWidth = null,
      maxLines = null,
    } = opts;
    pdf.setFont("helvetica", bold ? "bold" : "normal");
    pdf.setFontSize(size);
    pdf.setTextColor(0);
    let text = String(value ?? "");
    if (maxWidth) {
      let lines = pdf.splitTextToSize(text, maxWidth);
      if (maxLines && lines.length > maxLines) {
        lines = lines.slice(0, maxLines);
        lines[lines.length - 1] =
          String(lines[lines.length - 1]).replace(/\s*$/, "") + "...";
      }
      pdf.text(lines, x, y, { align });
    } else {
      pdf.text(text, x, y, { align });
    }
  };

  const renderCardPage = async ({
    batchId,
    cardEvents,
    pageIndex,
    pageCount,
    batchMeta,
    totalReceived,
  }) => {
    if (pdf.getNumberOfPages() > 1 || pageIndex > 0 || batchId !== batchIds[0]) {
      pdf.addPage("a4", "landscape");
    }

    const headerY = 22;
    const headerH = 42;
    const logoW = 95;
    box(L, headerY, W, headerH);
    box(L, headerY, logoW, headerH);
    await drawLogoFit(L + 8, headerY + 5, logoW - 16, headerH - 10);

    txt(
      "KARTU PERSEDIAAN PRODUK JADI",
      L + logoW + (W - logoW) / 2,
      headerY + 28,
      { size: 17, bold: true, align: "center" }
    );

    let y = headerY + headerH + 2;
    const metaRows = [
      ["Nama Produk", sku.name || ""],
      ["Nomor Batch", batchId === "TANPA-BATCH" ? "" : batchId],
      ["Tanggal Produksi", formatPdfDate(batchMeta.productionDate)],
      ["Tanggal Masuk Gudang", formatPdfDate(batchMeta.firstInboundDate)],
      ["Jumlah Karung/Karton", totalReceived ? `${formatStockNumber(totalReceived)} ${unitLabel}` : ""],
      ["Lokasi Tumpukan", batchMeta.targetStack || ""],
    ];

    metaRows.forEach(([label, value]) => {
      const rowH = 14;
      box(L, y, W, rowH);
      txt(label, L + 2, y + 10, { size: 6.8 });
      txt(":", L + 185, y + 10, { size: 6.8 });
      txt(value, L + 194, y + 10, {
        size: 6.8,
        bold: label === "Nama Produk",
        maxWidth: W - 200,
        maxLines: 1,
      });
      y += rowH;
    });

    y += 7;
    const groupH = 22;
    const headerH2 = 40;
    const cols = [75, 88, 54, 67, 71, 100, 183, 50, 46, 46];
    const xs = [L];
    cols.forEach((w) => xs.push(xs[xs.length - 1] + w));

    box(L, y, W, groupH + headerH2 + 276);
    xs.slice(1, -1).forEach((x) => line(x, y, x, y + groupH + headerH2 + 276));
    line(L, y + groupH, R, y + groupH);
    line(L, y + groupH + headerH2, R, y + groupH + headerH2);

    txt("MASUK", (xs[0] + xs[4]) / 2, y + 16, {
      size: 12,
      bold: true,
      align: "center",
    });
    txt("KELUAR", (xs[4] + xs[9]) / 2, y + 16, {
      size: 12,
      bold: true,
      align: "center",
    });
    txt("Paraf", (xs[9] + xs[10]) / 2, y + 36, {
      size: 9.3,
      bold: true,
      align: "center",
    });

    const headers = [
      "Tanggal Masuk",
      "No.Bets",
      "Jumlah Masuk",
      "No. Tumpukan",
      "Tanggal Keluar",
      "No. SO",
      "Nama Pelanggan",
      "Jumlah Keluar",
      "Sisa",
    ];

    headers.forEach((label, i) => {
      txt(label, (xs[i] + xs[i + 1]) / 2, y + groupH + 15, {
        size: 7.4,
        bold: true,
        align: "center",
        maxWidth: cols[i] - 6,
        maxLines: 2,
      });
    });

    const bodyTop = y + groupH + headerH2;
    const rowH = 20;
    cardEvents.forEach((event, i) => {
      const rowTop = bodyTop + i * rowH;
      if (i > 0) line(L, rowTop, R, rowTop, 0.25);
      const textY = rowTop + 13;

      if (event.kind === "IN") {
        txt(formatPdfDate(event.date), (xs[0] + xs[1]) / 2, textY, {
          size: 7.0,
          align: "center",
        });
        txt(event.batchId || "", (xs[1] + xs[2]) / 2, textY, {
          size: 6.7,
          align: "center",
          maxWidth: cols[1] - 6,
          maxLines: 1,
        });
        txt(formatStockNumber(event.qty), (xs[2] + xs[3]) / 2, textY, {
          size: 7.0,
          align: "center",
        });
        txt(event.stack || "", (xs[3] + xs[4]) / 2, textY, {
          size: 6.7,
          align: "center",
          maxWidth: cols[3] - 6,
          maxLines: 1,
        });
      } else {
        txt(formatPdfDate(event.date), (xs[4] + xs[5]) / 2, textY, {
          size: 7.0,
          align: "center",
        });
        txt(event.soNumber || "", (xs[5] + xs[6]) / 2, textY, {
          size: 6.7,
          align: "center",
          maxWidth: cols[5] - 6,
          maxLines: 1,
        });
        txt(event.customer || "", xs[6] + 3, textY, {
          size: 6.7,
          maxWidth: cols[6] - 6,
          maxLines: 1,
        });
        txt(formatStockNumber(event.qty), (xs[7] + xs[8]) / 2, textY, {
          size: 7.0,
          align: "center",
        });
      }

      txt(formatStockNumber(event.balance), (xs[8] + xs[9]) / 2, textY, {
        size: 7.0,
        align: "center",
      });
    });

    const footerY = pageH - 34;
    txt("Kepala GBB Sunter Timur I & II", R - 105, footerY, {
      size: 6.8,
      align: "center",
    });
    txt(approver, R - 105, footerY + 34, {
      size: 6.8,
      bold: true,
      align: "center",
    });

    if (pageCount > 1) {
      txt(
        `Batch ${batchId === "TANPA-BATCH" ? "-" : batchId} - halaman ${pageIndex + 1} dari ${pageCount}`,
        L,
        pageH - 10,
        { size: 5.3 }
      );
    }
  };

  for (const batchId of batchIds) {
    const batchInbound = inbound.filter(
      (item) =>
        (batchId === "TANPA-BATCH" && !item.batchId) ||
        item.batchId === batchId
    );
    const batchOutbound = outbound.filter(
      (item) =>
        (batchId === "TANPA-BATCH" && !item.batchId) ||
        item.batchId === batchId
    );

    const events = [...batchInbound, ...batchOutbound].sort(
      (a, b) => new Date(a.date) - new Date(b.date)
    );

    let balance = 0;
    events.forEach((event) => {
      balance += event.kind === "IN" ? event.qty : -event.qty;
      event.balance = balance;
    });

    const liveBatch = batches.find((b) => b.batchId === batchId);
    const firstIn = [...batchInbound].sort(
      (a, b) => new Date(a.date) - new Date(b.date)
    )[0];

    const batchMeta = {
      productionDate:
        liveBatch?.productionDate ||
        firstIn?.productionDate ||
        firstIn?.date ||
        "",
      firstInboundDate: firstIn?.date || liveBatch?.date || "",
      targetStack:
        liveBatch?.targetStack ||
        firstIn?.stack ||
        "",
    };

    const totalReceived = batchInbound.reduce(
      (sum, item) => sum + item.qty,
      0
    );

    const maxRows = 13;
    const chunks = [];
    if (events.length === 0) {
      chunks.push([]);
    } else {
      for (let i = 0; i < events.length; i += maxRows) {
        chunks.push(events.slice(i, i + maxRows));
      }
    }

    for (let pageIndex = 0; pageIndex < chunks.length; pageIndex += 1) {
      await renderCardPage({
        batchId,
        cardEvents: chunks[pageIndex],
        pageIndex,
        pageCount: chunks.length,
        batchMeta,
        totalReceived,
      });
    }
  }

  const safeSku = String(sku.id || sku.name || "produk-jadi").replace(
    /[^a-z0-9-_]/gi,
    "_"
  );
  pdf.save("Kartu_Persediaan_Produk_Jadi_" + safeSku + ".pdf");
}

'''

s = s[:raw_start] + new_raw + new_fg + s[app_start:]

# Pass system config into card generators.
old = '''        await generateRawMaterialStockCardPdf({
          sku,
          batches: skuBatches,
          transactions,
        });'''
new = '''        await generateRawMaterialStockCardPdf({
          sku,
          batches: skuBatches,
          transactions,
          systemConfig,
        });'''
if old not in s:
    raise SystemExit("Raw card call not found")
s = s.replace(old, new, 1)

old = '''        await generateFinishedGoodsStockCardPdf({
          sku,
          batches: skuBatches,
          transactions,
        });'''
new = '''        await generateFinishedGoodsStockCardPdf({
          sku,
          batches: skuBatches,
          transactions,
          systemConfig,
        });'''
if old not in s:
    raise SystemExit("FG card call not found")
s = s.replace(old, new, 1)

path.write_text(s, encoding="utf-8")
print("Stock card template patch applied.")
