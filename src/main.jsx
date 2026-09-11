import React from "react";
import ReactDOM from "react-dom/client";
import * as XLSX from "xlsx";
import App from "./App.jsx";
import "./index.css";

// Compatibility fix for legacy Outbound/Outbond import templates.
// App.jsx reads legacy sheets with range: 4 (Excel row 5). Some historical
// Outbound templates have their header on Excel row 4, dates as dd/mm/yyyy,
// and line-level TM suffixes that must resolve to the TM Hasil recorded in QC.
const originalSheetToJson = XLSX.utils.sheet_to_json;
const legacyQcTmByBase = new Map();

const normalizeLegacyOutboundDate = (value) => {
  if (typeof value !== "string") return value;
  const text = value.trim();
  const match = text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!match) return value;
  const [, dd, mm, yyyy] = match;
  return `${yyyy}-${mm.padStart(2, "0")}-${dd.padStart(2, "0")}`;
};

const getLegacyTmBase = (value) => {
  const text = String(value ?? "").trim();
  const parts = text.split("/");
  if (parts.length < 2) return "";
  return parts.slice(0, -1).join("/");
};

const captureLegacyQcTm = (rows) => {
  const grouped = new Map();

  rows.forEach((row) => {
    const tm = String(
      row?.["TM Hasil"] ?? row?.["No TM Hasil"] ?? row?.["TM Hasil Produk Jadi"] ?? ""
    ).trim();
    const base = getLegacyTmBase(tm);
    if (!tm || !base) return;
    if (!grouped.has(base)) grouped.set(base, new Set());
    grouped.get(base).add(tm);
  });

  grouped.forEach((values, base) => {
    if (values.size === 1) legacyQcTmByBase.set(base, [...values][0]);
  });
};

XLSX.utils.sheet_to_json = (worksheet, options = {}) => {
  const outboundDateHeaders = ["Tanggal Outbound", "Tanggal Outbond", "Tanggal Keluar"];
  const outboundTmHeaders = ["TM Hasil", "No TM Hasil", "TM Hasil Produk Jadi"];
  let isLegacyOutboundRow4 = false;

  if (worksheet && options?.range === 4) {
    isLegacyOutboundRow4 = Object.keys(worksheet).some((address) => {
      if (address.startsWith("!")) return false;
      const cell = XLSX.utils.decode_cell(address);
      if (cell.r !== 3) return false; // Excel row 4
      const value = String(worksheet[address]?.v ?? "").trim();
      return outboundDateHeaders.includes(value);
    });
  }

  const rows = originalSheetToJson(
    worksheet,
    isLegacyOutboundRow4 ? { ...options, range: 3 } : options
  );

  if (!Array.isArray(rows) || rows.length === 0) return rows;

  const firstRow = rows[0] || {};
  const isQcRows =
    Object.prototype.hasOwnProperty.call(firstRow, "Tanggal QC") &&
    outboundTmHeaders.some((header) => Object.prototype.hasOwnProperty.call(firstRow, header));

  if (isQcRows) {
    captureLegacyQcTm(rows);
    return rows;
  }

  const outboundDateKey = outboundDateHeaders.find((header) =>
    Object.prototype.hasOwnProperty.call(firstRow, header)
  );
  if (!outboundDateKey) return rows;

  return rows.map((row) => {
    const dateKey = outboundDateHeaders.find((header) =>
      Object.prototype.hasOwnProperty.call(row, header)
    );
    const tmKey = outboundTmHeaders.find((header) =>
      Object.prototype.hasOwnProperty.call(row, header)
    );

    const currentTm = tmKey ? String(row[tmKey] ?? "").trim() : "";
    const canonicalTm = currentTm
      ? legacyQcTmByBase.get(getLegacyTmBase(currentTm)) || currentTm
      : currentTm;

    return {
      ...row,
      ...(dateKey ? { [dateKey]: normalizeLegacyOutboundDate(row[dateKey]) } : {}),
      ...(tmKey ? { [tmKey]: canonicalTm } : {}),
    };
  });
};

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
