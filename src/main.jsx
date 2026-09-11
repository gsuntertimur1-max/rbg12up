import React from "react";
import ReactDOM from "react-dom/client";
import * as XLSX from "xlsx";
import App from "./App.jsx";
import "./index.css";

// Compatibility fix for legacy Outbound/Outbond import templates.
// App.jsx reads legacy sheets with range: 4 (Excel row 5). Some historical
// Outbound templates have their header on Excel row 4 and dates as dd/mm/yyyy.
// Keep the existing importer unchanged for all other sheets, but transparently
// adapt this specific legacy Outbound layout before App.jsx processes it.
const originalSheetToJson = XLSX.utils.sheet_to_json;

const normalizeLegacyOutboundDate = (value) => {
  if (typeof value !== "string") return value;
  const text = value.trim();
  const match = text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!match) return value;
  const [, dd, mm, yyyy] = match;
  return `${yyyy}-${mm.padStart(2, "0")}-${dd.padStart(2, "0")}`;
};

XLSX.utils.sheet_to_json = (worksheet, options = {}) => {
  const outboundDateHeaders = ["Tanggal Outbound", "Tanggal Outbond", "Tanggal Keluar"];
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

  if (!isLegacyOutboundRow4 || !Array.isArray(rows)) return rows;

  return rows.map((row) => {
    const dateKey = outboundDateHeaders.find((header) =>
      Object.prototype.hasOwnProperty.call(row, header)
    );
    if (!dateKey) return row;
    return {
      ...row,
      [dateKey]: normalizeLegacyOutboundDate(row[dateKey]),
    };
  });
};

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
