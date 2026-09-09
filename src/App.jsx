import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  Package, Download, UserPlus, Trash2, Home, PackagePlus,
  FileDown, FileUp, ArrowRightLeft, Settings, Users,
  ArrowRight, Settings2, Database, History, LogOut,
  Boxes, FileSpreadsheet, Search, CheckCircle, Image as ImageIcon, PlusCircle, Eye,
  Menu, X, LogIn, UserRound, LockKeyhole
} from "lucide-react";
import {
  BarChart, Bar, PieChart, Pie, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, Cell, ResponsiveContainer
} from 'recharts';
import * as XLSX from 'xlsx';
import { jsPDF } from "jspdf";

// --- FIREBASE IMPORTS ---
import { initializeApp, getApps, getApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth, signInAnonymously, onAuthStateChanged } from "firebase/auth";
import { getFirestore, doc, setDoc, onSnapshot, collection, deleteDoc, writeBatch, runTransaction, getDocs } from "firebase/firestore";

// --- DEFAULT DATA ---
const STACK_LOCATIONS = ["Unit Pengolahan 20", "RTR 60", "Gula 17"];
const DEFAULT_USERS = [
  { username: "superadmin", password: "password", role: "Super Admin" },
  { username: "admin", password: "123456", role: "Admin" },
  { username: "operator", password: "123456", role: "Operator" },
];

const DEFAULT_REBAG_RECIPES = [
  {
    id: "FORTIVIT_1KG",
    targetSku: "B0030038X",
    label: "Fortivit 1 Kg",
    active: true,
    notes: "",
    materials: [
      { skuId: "A0020003X", required: true, order: 1 },
      { skuId: "A0210001X", required: true, order: 2 },
      { skuId: "D0200129X", required: true, order: 3 },
      { skuId: "D0200111X", required: true, order: 4 },
    ],
  },
  {
    id: "FORTIVIT_5KG",
    targetSku: "B0030039X",
    label: "Fortivit 5 Kg",
    active: true,
    notes: "",
    materials: [
      { skuId: "A0020003X", required: true, order: 1 },
      { skuId: "A0210001X", required: true, order: 2 },
      { skuId: "D0200084X", required: true, order: 3 },
    ],
  },
  {
    id: "GULA",
    targetSku: "",
    matchName: "GULA",
    label: "Rebag Gula",
    active: true,
    notes: "Preset awal. Pilih SKU produk jadi gula pada Master Komposisi agar aturan tidak bergantung pada nama produk.",
    materials: [
      { skuId: "A0060004X", required: true, order: 1 },
      { skuId: "D0200062X", required: true, order: 2 },
      { skuId: "D0200130X", required: true, order: 3, calculationMode: "per_output", outputPerUnit: 24 },
    ],
  },
];

const normalizeRecipeMaterials = (recipe) =>
  (recipe?.materials || [])
    .map((item, index) =>
      typeof item === "string"
        ? { skuId: item, required: true, order: index + 1, calculationMode: "manual", outputPerUnit: "" }
        : {
            skuId: item?.skuId || "",
            required: item?.required !== false,
            order: Number(item?.order) || index + 1,
            calculationMode: item?.calculationMode === "per_output" ? "per_output" : "manual",
            outputPerUnit:
              item?.calculationMode === "per_output" && Number(item?.outputPerUnit) > 0
                ? Number(item.outputPerUnit)
                : "",
          }
    )
    .filter((item) => item.skuId)
    .sort((a, b) => a.order - b.order);

const getCalculatedMaterialQty = (material, outputQty) => {
  if (material?.calculationMode !== "per_output") return null;
  const ratio = Number(material?.outputPerUnit);
  const produced = Number(outputQty);
  if (!Number.isFinite(ratio) || ratio <= 0 || !Number.isFinite(produced) || produced <= 0) {
    return 0;
  }
  return Math.ceil(produced / ratio);
};

const getRebagRecipe = (targetSku, recipes = []) => {
  if (!targetSku) return null;
  const activeRecipes = recipes.filter((recipe) => recipe.active !== false);
  return (
    activeRecipes.find((recipe) => recipe.targetSku === targetSku.id) ||
    activeRecipes.find(
      (recipe) =>
        recipe.matchName &&
        String(targetSku.name || "").toUpperCase().includes(String(recipe.matchName).toUpperCase())
    ) ||
    null
  );
};

// --- FIREBASE SETUP ---
const firebaseConfig = {
  apiKey: "AIzaSyC8ygXyWwjnbKMoYBO7CQP-EKcPmUbL6pg",
  authDomain: "rbg12-3a5a0.firebaseapp.com",
  projectId: "rbg12-3a5a0",
  storageBucket: "rbg12-3a5a0.firebasestorage.app",
  messagingSenderId: "477359317412",
  appId: "1:477359317412:web:90e1acb6ae8dae2b7fe131",
  measurementId: "G-4Z0JH7LB1D"
};

let app, auth, db, analytics, appId = "rbg12-3a5a0";

try {
  if (getApps().length === 0) {
    app = initializeApp(firebaseConfig);
  } else {
    app = getApp();
  }
  if (app) {
    auth = getAuth(app);
    db = getFirestore(app);
    if (typeof window !== "undefined") {
      analytics = getAnalytics(app);
    }
  }
} catch (e) {
  console.error("Firebase Init Error:", e);
}

// --- KOMPONEN SEARCHABLE SELECT ---
const SearchableSelect = ({ options, value, onChange, placeholder }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const wrapperRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) setIsOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredOptions = options.filter(opt =>
    (opt.label || "").toString().toLowerCase().includes((search || "").toLowerCase())
  );
  const selectedOption = options.find(opt => opt.value === value);

  return (
    <div ref={wrapperRef} className="relative w-full">
      <div
        className="w-full border border-slate-300 rounded-lg p-3 text-sm cursor-pointer bg-white flex justify-between items-center"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className={`truncate ${!value ? "text-slate-400" : "text-slate-800"}`}>
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <span className="text-slate-400 text-xs ml-2">▼</span>
      </div>
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-xl max-h-60 flex flex-col">
          <div className="p-2 border-b sticky top-0 bg-white">
            <input type="text" className="w-full px-3 py-2 text-sm border border-slate-200 rounded-md outline-none focus:border-red-500" placeholder="Ketik untuk mencari..." value={search} onChange={(e) => setSearch(e.target.value)} autoFocus />
          </div>
          <div className="overflow-y-auto">
            {filteredOptions.length === 0 ? (
              <div className="p-3 text-sm text-slate-500 text-center">Tidak ada hasil</div>
            ) : (
              filteredOptions.map(opt => (
                <div key={opt.value} className="p-3 text-sm cursor-pointer hover:bg-red-50 hover:text-red-700 border-b border-slate-100 last:border-0 transition-colors" onClick={() => { onChange(opt.value); setIsOpen(false); setSearch(""); }}>
                  {opt.label}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

function getDefaultExpiryDate() {
  const d = new Date();
  d.setFullYear(d.getFullYear() + 1);
  return d.toISOString().slice(0, 10);
}

function getLocalDateTimeInput(date = new Date()) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function getExpiryDateFromLocalDateTime(value) {
  if (!value) return getDefaultExpiryDate();
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return getDefaultExpiryDate();
  d.setFullYear(d.getFullYear() + 1);
  const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function formatPdfDate(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("id-ID");
}

function loadPdfLogo() {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = "/logo.png";
  });
}

async function generateRebaggingBatchPdf(tx) {
  const pdf = new jsPDF({ orientation: "portrait", unit: "pt", format: "a4" });
  const L = 18.5;
  const R = 571.3;
  const W = R - L;
  const lineColor = 35;
  const gray = 225;

  const line = (x1, y1, x2, y2, width = 0.45) => {
    pdf.setDrawColor(lineColor);
    pdf.setLineWidth(width);
    pdf.line(x1, y1, x2, y2);
  };
  const box = (x, y, w, h, fill = false) => {
    pdf.setDrawColor(lineColor);
    pdf.setLineWidth(0.45);
    if (fill) {
      pdf.setFillColor(gray);
      pdf.rect(x, y, w, h, "FD");
    } else {
      pdf.rect(x, y, w, h);
    }
  };
  const txt = (value, x, y, opts = {}) => {
    const { size = 6.4, bold = false, align = "left", maxWidth = null } = opts;
    pdf.setFont("helvetica", bold ? "bold" : "normal");
    pdf.setFontSize(size);
    pdf.setTextColor(0);
    const str = String(value ?? "");
    if (maxWidth) {
      const lines = pdf.splitTextToSize(str, maxWidth);
      pdf.text(lines, x, y, { align });
    } else {
      pdf.text(str, x, y, { align });
    }
  };
  const section = (label, y) => {
    box(L, y, W, 9, true);
    txt(label, L + 2, y + 6.5, { size: 6.6, bold: true });
  };

  box(L, 63.5, W, 656.5);

  line(301.1, 63.5, 301.1, 100);
  [72.7, 81.7, 90.7, 100].forEach((y) => line(301.1, y, R, y));
  try {
    const logo = await loadPdfLogo();
    pdf.addImage(logo, "PNG", 28, 70, 125, 28);
  } catch (error) {
    console.warn("Logo PDF tidak dapat dimuat:", error);
    txt("BULOG", 55, 91, { size: 24, bold: true });
  }
  txt("PERUM BULOG", 436, 70.5, { size: 7.3, bold: true, align: "center" });
  txt("Jl. Pelepah Raya, RW.5, Klp. Gading Barat, Kec. Klp. Gading, Jakarta Utara", 436, 79.2, { size: 5.2, bold: true, align: "center" });
  txt("CATATAN PROSES REBAGGING BATCH", 436, 88.2, { size: 7.2, bold: true, align: "center" });
  const productName = (tx.skuName || "GULA MANISKITA 1 KG KOM DN").toUpperCase();
  txt("NAMA PRODUK : " + productName, 436, 97, { size: 7, bold: true, align: "center", maxWidth: 255 });

  [100, 109, 118, 127, 136].forEach((y) => line(L, y, R, y));
  line(339.7, 100, 339.7, 136);
  txt("No. Batch", 20, 106.5);
  txt(":", 79, 106.5);
  txt(tx.batchId || "", 86, 106.5, { bold: true });
  txt("Tanggal Kadaluwarsa", 341.5, 106.5);
  txt(":", 430, 106.5);
  txt(formatPdfDate(tx.expiryDate), 438, 106.5, { bold: true });

  txt("Tanggal Produksi", 20, 115.5);
  txt(":", 79, 115.5);
  txt(formatPdfDate(tx.productionDate || tx.date), 86, 115.5, { bold: true });
  txt("Pengawas", 341.5, 115.5);
  txt(":", 397, 115.5);
  txt(tx.supervisor || tx.operator || "", 404, 115.5, { bold: true });

  txt("Pelaksana", 20, 124.5);
  txt(":", 79, 124.5);
  txt(tx.executor || "KOPEL JAYA", 86, 124.5, { bold: true });
  txt("No. MO", 20, 133.5);
  txt(":", 79, 133.5);
  txt(tx.moNumber || "", 86, 133.5, { bold: true });
  txt("Tanggal", 341.5, 133.5);
  txt(":", 397, 133.5);
  txt(formatPdfDate(tx.productionDate || tx.date), 404, 133.5, { bold: true });

  section("1. KESIAPAN", 136);
  const readyRows = [
    "Kondisi ruangan produksi dalam keadaan bersih",
    "Peralatan produksi dalam keadaan bersih",
    "Higiene karyawan sudah baik",
  ];
  [145, 160.5, 176, 191].forEach((y) => line(L, y, R, y));
  [301.1, 339.7, 378.2].forEach((x) => line(x, 145, x, 191));
  readyRows.forEach((label, i) => {
    const y = 154.5 + i * 15.5;
    txt(label, 20, y);
    txt("Ya", 320, y, { align: "center" });
    txt("Tidak", 359, y, { align: "center" });
    txt("Paraf pelaksana:", 381, y);
  });

  section("2. TAHAP PERSIAPAN", 191);
  box(L, 200, W, 9, true);
  txt("2.1 Sortasi Bahan Baku Gula Curah 50 Kg", 20, 206.5, { bold: true });
  line(L, 209, R, 209);
  line(L, 218, R, 218);
  line(L, 227, R, 227);
  line(301.1, 209, 301.1, 218);
  line(378.2, 209, 378.2, 218);
  txt("Mulai jam :", 20, 215.5);
  txt("Selesai jam :", 304, 215.5);
  txt("Paraf pelaksana:", 381, 215.5);
  txt("Pemeriksaan sesuai standar : Ya / Tidak", 20, 224.5);

  section("3. PENIMBANGAN", 227);
  [236, 245, 254, 263, 272, 281, 290, 299].forEach((y) => line(L, y, R, y));
  [166.7, 301.1, 339.7, 378.2].forEach((x) => line(x, 236, x, 299));
  txt("Bahan", 92, 242.5, { bold: true, align: "center" });
  txt("Jumlah Standar", 234, 242.5, { bold: true, align: "center" });
  txt("Aktual", 320, 242.5, { bold: true, align: "center" });
  txt("Pelaksana", 359, 242.5, { bold: true, align: "center" });
  txt("Pengawas", 474, 242.5, { bold: true, align: "center" });

  const sourceQty = Number(tx.sourceQty ?? tx.processedQty ?? tx.qtyChange ?? 0);
  const finishedQty = Number(tx.finishedQty ?? tx.goodQty ?? tx.qtyChange ?? 0);
  const goodQty = Number(tx.goodQty ?? finishedQty ?? 0);
  const processQty = Number(tx.processQty ?? 0);
  const damageQty = Number(tx.damageQty ?? 0);
  const reconciledQty = goodQty + processQty + damageQty;
  const sourceUnit = tx.sourceUnit || "KG";
  const finishedUnit = tx.finishedUnit || tx.unit || "Pack";
  const executor = tx.executor || "KOPEL JAYA";
  const supervisor = tx.supervisor || tx.operator || "";
  const materials =
    Array.isArray(tx.materials) && tx.materials.length > 0
      ? tx.materials.slice(0, 5).map((m) => [
          `${m.skuId || ""} ${m.skuName || ""}`.trim(),
          `${m.usedQty ?? m.qty ?? ""} ${m.unit || ""}${Number(m.damageQty || 0) > 0 ? ` + rusak ${m.damageQty}` : ""}`.trim(),
          executor,
          supervisor,
        ])
      : [
          ["Gula Curah", sourceQty ? sourceQty + " " + sourceUnit : "", executor, supervisor],
          ["Plastik PP 1 Kg", finishedQty ? finishedQty + " " + finishedUnit : "", executor, supervisor],
          ["Karton", "", "", ""],
          ["Lakban", "", "", ""],
          ["Tinta Inkjet Exp Date", "", "", ""],
        ];
  materials.forEach((row, i) => {
    const y = 251.5 + i * 9;
    txt(row[0], 20, y);
    txt(row[1], 320, y, { align: "center" });
    txt(row[2], 359, y, { align: "center", size: 5.4 });
    txt(row[3], 474, y, { align: "center", size: 5.4 });
  });

  section("4. PROSES REBAGGING", 299);
  const steps = [
    "4.1 Naik bahan baku ke Conveyor",
    "4.2 Penurunan bahan baku dari Conveyor ke Hopper",
    "4.3 Proses pengisian gula ke dalam Mesin Packing",
    "4.4 Penimbangan otomatis dan sealing kemasan 1 Kg",
    "4.5 Packing kemasan primer ke dalam Karton",
    "4.6 Pelabelan / Pencetakan Exp Date",
  ];
  let sy = 308;
  steps.forEach((label) => {
    box(L, sy, W, 9, true);
    txt(label, 20, sy + 6.5, { bold: true });
    line(L, sy + 9, R, sy + 9);
    line(L, sy + 18, R, sy + 18);
    line(L, sy + 27, R, sy + 27);
    line(301.1, sy + 9, 301.1, sy + 18);
    line(378.2, sy + 9, 378.2, sy + 27);
    txt("Mulai jam :", 20, sy + 15.5);
    txt("Selesai jam :", 304, sy + 15.5);
    txt("Paraf pelaksana:", 381, sy + 15.5);
    txt("Pemeriksaan sesuai standar : Ya / Tidak", 20, sy + 24.5);
    sy += 27;
  });

  section("5. PENGAWASAN SELAMA PROSES (IN PROCESS CONTROL)", 470);
  [479, 488, 497, 506, 515, 524].forEach((y) => line(L, y, R, y));
  [301.1, 378.2].forEach((x) => line(x, 479, x, 524));
  txt("Parameter", 160, 485.5, { bold: true, align: "center" });
  txt("Hasil", 339, 485.5, { bold: true, align: "center" });
  txt("Paraf", 474, 485.5, { bold: true, align: "center" });
  [
    "Berat netto sesuai standar (1.000 gram +/- toleransi)",
    "Seal kemasan rapat",
    "Kemasan bocor",
    "Cetakan Exp Date jelas dan terbaca",
    "Karton dalam kondisi baik",
  ].forEach((label, i) => txt(label, 20, 494.5 + i * 9));

  section("6. REKONSILIASI HASIL PRODUKSI", 524);
  line(L, 533, R, 533);
  line(L, 561, R, 561);
  [166.7, 339.7, 448.2].forEach((x) => line(x, 533, x, 561));
  txt("Besaran Batch", 20, 540.5);
  txt("Jumlah Aktual Produk Jadi", 169, 540.5);
  txt("Selisih", 342, 540.5);
  txt("Paraf", 451, 540.5);
  txt(sourceQty ? sourceQty + " " + sourceUnit : "", 20, 553, { bold: true });
  txt(finishedQty ? finishedQty + " " + finishedUnit : "", 169, 553, { bold: true });
  if (Number.isFinite(sourceQty) && Number.isFinite(reconciledQty)) {
    txt(String(reconciledQty - sourceQty), 342, 553, { bold: true });
  }
  txt(
    "GOOD: " + goodQty + " | PROCESS: " + processQty + " | DAMAGE: " + damageQty,
    169,
    559,
    { size: 5.2, bold: true }
  );

  section("7. PENYIMPANAN PRODUK JADI", 561);
  line(L, 570, R, 570);
  line(L, 604, R, 604);
  txt("Penyimpanan :", 20, 578);
  txt(tx.targetStack || "", 82, 578, { bold: true, maxWidth: 470 });

  section("8. VERIFIKASI", 604);
  line(L, 613, R, 613);
  line(L, 622, R, 622);
  line(L, 631, R, 631);
  line(301.1, 631, 301.1, 720);
  txt("Diperiksa oleh", 20, 619.5);
  txt(":", 76, 619.5);
  txt(supervisor, 84, 619.5, { bold: true });
  txt("Tanggal", 20, 628.5);
  txt(":", 76, 628.5);
  txt(formatPdfDate(tx.productionDate || tx.date), 84, 628.5, { bold: true });
  txt("PERUM BULOG", 436, 638, { bold: true, align: "center" });
  txt("(..............................................)", 159, 714, { align: "center" });
  txt("(IRSA MAULIAN NUGRAHA)", 436, 714, { bold: true, align: "center" });

  const safeBatch = String(tx.batchId || "batch").replace(/[^a-z0-9-_]/gi, "_");
  pdf.save("Catatan_Proses_Rebagging_" + safeBatch + ".pdf");
}

function formatStockNumber(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  return n.toLocaleString("id-ID", { maximumFractionDigits: 2 });
}

async function generateRawMaterialStockCardPdf({ sku, batches, transactions }) {
  const pdf = new jsPDF({ orientation: "portrait", unit: "pt", format: "a4" });
  const L = 12;
  const R = 583;
  const W = R - L;
  const matchingBatchIds = new Set(batches.map((b) => b.batchId));

  const inbound = transactions
    .filter((t) => t.type === "INBOUND" && t.skuId === sku.id)
    .map((t) => ({
      kind: "IN",
      date: t.date,
      qty: Number(t.qtyChange) || 0,
      moNumber: t.moNumber || "",
      stack: t.stackNumber || "",
    }));

  const rebagOut = transactions
    .filter((t) => t.type === "REBAGGING")
    .flatMap((t) => {
      if (Array.isArray(t.materials) && t.materials.length > 0) {
        return t.materials
          .filter(
            (m) =>
              m.skuId === sku.id ||
              matchingBatchIds.has(m.batchId)
          )
          .map((m) => ({
            kind: "OUT",
            date: t.date,
            qty: Number(m.qty) || 0,
            stack: m.sourceStack || "",
          }));
      }

      if (t.sourceSkuId === sku.id || matchingBatchIds.has(t.sourceBatchId)) {
        return [{
          kind: "OUT",
          date: t.date,
          qty: Number(t.sourceQty ?? t.qtyChange) || 0,
          stack: t.sourceStack || "",
        }];
      }

      return [];
    });

  const events = [...inbound, ...rebagOut].sort(
    (a, b) => new Date(a.date) - new Date(b.date)
  );

  let balance = 0;
  events.forEach((e) => {
    balance += e.kind === "IN" ? e.qty : -e.qty;
    e.balance = balance;
  });

  const currentStock = batches.reduce(
    (sum, b) => sum + (Number(b.currentQty) || 0),
    0
  );
  const firstInbound = inbound[0];
  const moNumber =
    inbound.find((x) => x.moNumber)?.moNumber ||
    batches.find((b) => b.moNumber)?.moNumber ||
    transactions.find(
      (t) =>
        t.type === "REBAGGING" &&
        (t.sourceSkuId === sku.id || matchingBatchIds.has(t.sourceBatchId)) &&
        t.moNumber
    )?.moNumber ||
    "";
  const stackLocation =
    [...new Set(batches.map((b) => b.stackNumber || b.targetStack).filter(Boolean))].join(", ");

  const line = (x1, y1, x2, y2, width = 0.55) => {
    pdf.setDrawColor(30);
    pdf.setLineWidth(width);
    pdf.line(x1, y1, x2, y2);
  };
  const box = (x, y, w, h) => {
    pdf.setDrawColor(30);
    pdf.setLineWidth(0.55);
    pdf.rect(x, y, w, h);
  };
  const txt = (value, x, y, opts = {}) => {
    const { size = 7.3, bold = false, align = "left", maxWidth = null } = opts;
    pdf.setFont("helvetica", bold ? "bold" : "normal");
    pdf.setFontSize(size);
    pdf.setTextColor(0);
    const str = String(value ?? "");
    if (maxWidth) {
      pdf.text(pdf.splitTextToSize(str, maxWidth), x, y, { align });
    } else {
      pdf.text(str, x, y, { align });
    }
  };

  try {
    const logo = await loadPdfLogo();
    pdf.addImage(logo, "PNG", 18, 18, 125, 42);
  } catch (error) {
    console.warn("Logo kartu bahan baku gagal dimuat:", error);
    txt("BULOG", 20, 48, { size: 24, bold: true });
  }

  box(L, 68, W, 112);
  txt("KARTU PERSEDIAAN BAHAN BAKU", (L + R) / 2, 93, {
    size: 17,
    bold: true,
    align: "center",
  });
  line(L, 103, R, 103);

  const meta = [
    ["Nama Produk", sku.name || ""],
    ["Nomor MO", moNumber],
    ["Tanggal Masuk Gudang", firstInbound ? formatPdfDate(firstInbound.date) : ""],
    ["Jumlah Karung/Karton", currentStock ? formatStockNumber(currentStock) + " " + (sku.unit || "") : ""],
    ["Lokasi Tumpukan", stackLocation],
  ];
  meta.forEach((row, i) => {
    const y = 117 + i * 13;
    txt(row[0], 18, y, { size: 7.4 });
    txt(":", 130, y, { size: 7.4 });
    txt(row[1], 138, y, { size: 7.4, bold: i === 0, maxWidth: 425 });
  });

  const tableTop = 194;
  const headerMid = 218;
  const headerBottom = 254;
  const tableBottom = 707;
  const xs = [L, 132, 210, 314, 407, 468, 528, R];

  box(L, tableTop, W, tableBottom - tableTop);
  xs.slice(1, -1).forEach((x) => line(x, tableTop, x, tableBottom));
  line(L, headerMid, R, headerMid);
  line(L, headerBottom, R, headerBottom);

  txt("MASUK", (L + 314) / 2, 211, { size: 13, bold: true, align: "center" });
  txt("KELUAR", (314 + 528) / 2, 211, { size: 13, bold: true, align: "center" });

  const headers = [
    ["Tanggal Masuk", (L + 132) / 2],
    ["Jumlah (kg)", (132 + 210) / 2],
    ["No. Tumpukan", (210 + 314) / 2],
    ["Tanggal Keluar", (314 + 407) / 2],
    ["Jumlah (kg)", (407 + 468) / 2],
    ["Sisa", (468 + 528) / 2],
    ["Paraf", (528 + R) / 2],
  ];
  headers.forEach(([label, x]) => txt(label, x, 237, { size: 7.3, bold: true, align: "center" }));

  const maxRows = 19;
  const rowH = 22.5;
  events.slice(0, maxRows).forEach((event, i) => {
    const top = headerBottom + i * rowH;
    const y = top + 14.5;
    if (i > 0) line(L, top, R, top, 0.3);
    if (event.kind === "IN") {
      txt(formatPdfDate(event.date), (L + 132) / 2, y, { align: "center" });
      txt(formatStockNumber(event.qty), (132 + 210) / 2, y, { align: "center" });
      txt(event.stack || "", (210 + 314) / 2, y, { align: "center" });
    } else {
      txt(formatPdfDate(event.date), (314 + 407) / 2, y, { align: "center" });
      txt(formatStockNumber(event.qty), (407 + 468) / 2, y, { align: "center" });
    }
    txt(formatStockNumber(event.balance), (468 + 528) / 2, y, { align: "center" });
  });

  txt("Kepala GBB Sunter Timur I & II", 462, 746, { size: 7, align: "center" });
  txt("IRSA MAULIAN NUGRAHA", 462, 805, { size: 7, bold: true, align: "center" });

  const safeSku = String(sku.id || sku.name || "bahan-baku").replace(/[^a-z0-9-_]/gi, "_");
  pdf.save("Kartu_Persediaan_Bahan_Baku_" + safeSku + ".pdf");
}

async function generateFinishedGoodsStockCardPdf({ sku, batches, transactions }) {
  const pdf = new jsPDF({ orientation: "landscape", unit: "pt", format: "a4" });
  const pageW = 841.89;
  const L = 12;
  const R = pageW - 12;
  const W = R - L;

  const inbound = transactions
    .filter(
      (t) =>
        (t.type === "REBAGGING" || t.type === "PROCESS_TO_GOOD") &&
        t.skuId === sku.id
    )
    .map((t) => ({
      kind: "IN",
      date: t.type === "PROCESS_TO_GOOD" ? t.date : (t.productionDate || t.date),
      batchId: t.batchId || "",
      qty:
        t.type === "PROCESS_TO_GOOD"
          ? Number(t.resolutionQty ?? t.qtyChange) || 0
          : Number(t.finishedQty ?? t.goodQty ?? t.qtyChange) || 0,
      stack: t.targetStack || "",
    }));

  const outbound = transactions
    .filter((t) => t.type === "OUTBOUND" && t.skuId === sku.id)
    .map((t) => ({
      kind: "OUT",
      date: t.date,
      qty: Number(t.qtyChange) || 0,
      soNumber: t.soNumber || "",
      customer: t.customer || "",
    }));

  const events = [...inbound, ...outbound].sort(
    (a, b) => new Date(a.date) - new Date(b.date)
  );

  let balance = 0;
  events.forEach((e) => {
    balance += e.kind === "IN" ? e.qty : -e.qty;
    e.balance = balance;
  });

  const activeBatches = batches.filter((b) => (Number(b.currentQty) || 0) > 0);
  const currentStock = activeBatches.reduce(
    (sum, b) => sum + (Number(b.currentQty) || 0),
    0
  );
  const batchIds = [...new Set(activeBatches.map((b) => b.batchId).filter(Boolean))];
  const productionDates = [...new Set(activeBatches.map((b) => b.productionDate || b.date).filter(Boolean))];
  const targetStacks = [...new Set(activeBatches.map((b) => b.targetStack).filter(Boolean))];

  const line = (x1, y1, x2, y2, width = 0.55) => {
    pdf.setDrawColor(30);
    pdf.setLineWidth(width);
    pdf.line(x1, y1, x2, y2);
  };
  const box = (x, y, w, h) => {
    pdf.setDrawColor(30);
    pdf.setLineWidth(0.55);
    pdf.rect(x, y, w, h);
  };
  const txt = (value, x, y, opts = {}) => {
    const { size = 7.2, bold = false, align = "left", maxWidth = null } = opts;
    pdf.setFont("helvetica", bold ? "bold" : "normal");
    pdf.setFontSize(size);
    pdf.setTextColor(0);
    const str = String(value ?? "");
    if (maxWidth) {
      pdf.text(pdf.splitTextToSize(str, maxWidth), x, y, { align });
    } else {
      pdf.text(str, x, y, { align });
    }
  };

  try {
    const logo = await loadPdfLogo();
    pdf.addImage(logo, "PNG", 18, 13, 125, 38);
  } catch (error) {
    console.warn("Logo kartu produk jadi gagal dimuat:", error);
    txt("BULOG", 20, 42, { size: 23, bold: true });
  }

  box(L, 58, W, 90);
  txt("KARTU PERSEDIAAN PRODUK JADI", pageW / 2, 82, {
    size: 17,
    bold: true,
    align: "center",
  });
  line(L, 91, R, 91);

  const firstInbound = inbound[0];
  const meta = [
    ["Nama Produk", sku.name || ""],
    ["Nomor Batch", batchIds.length === 1 ? batchIds[0] : batchIds.length > 1 ? "Lihat tabel masuk" : ""],
    ["Tanggal Produksi", productionDates.length === 1 ? formatPdfDate(productionDates[0]) : productionDates.length > 1 ? "Lihat tabel masuk" : ""],
    ["Tanggal Masuk Gudang", firstInbound ? formatPdfDate(firstInbound.date) : ""],
    ["Jumlah Karung/Karton", currentStock ? formatStockNumber(currentStock) + " " + (sku.unit || "") : ""],
    ["Lokasi Tumpukan", targetStacks.join(", ")],
  ];
  meta.forEach((row, i) => {
    const y = 103 + i * 7.2;
    txt(row[0], 18, y, { size: 6.1 });
    txt(":", 100, y, { size: 6.1 });
    txt(row[1], 108, y, { size: 6.1, bold: i === 0, maxWidth: 700 });
  });

  const tableTop = 155;
  const headerMid = 178;
  const headerBottom = 211;
  const tableBottom = 500;
  const xs = [L, 100, 205, 250, 323, 392, 505, 720, 766, 812, R];

  box(L, tableTop, W, tableBottom - tableTop);
  xs.slice(1, -1).forEach((x) => line(x, tableTop, x, tableBottom));
  line(L, headerMid, R, headerMid);
  line(L, headerBottom, R, headerBottom);

  txt("MASUK", (L + 323) / 2, 171, { size: 12.5, bold: true, align: "center" });
  txt("KELUAR", (323 + 812) / 2, 171, { size: 12.5, bold: true, align: "center" });

  const headers = [
    ["Tanggal Masuk", (L + 100) / 2],
    ["No.Bets", (100 + 205) / 2],
    ["Jumlah Masuk", (205 + 250) / 2],
    ["No. Tumpukan", (250 + 323) / 2],
    ["Tanggal Keluar", (323 + 392) / 2],
    ["No. SO", (392 + 505) / 2],
    ["Nama Pelanggan", (505 + 720) / 2],
    ["Jumlah Keluar", (720 + 766) / 2],
    ["Sisa", (766 + 812) / 2],
    ["Paraf", (812 + R) / 2],
  ];
  headers.forEach(([label, x]) => txt(label, x, 198, { size: 6.6, bold: true, align: "center" }));

  const maxRows = 13;
  const rowH = 22;
  events.slice(0, maxRows).forEach((event, i) => {
    const top = headerBottom + i * rowH;
    const y = top + 14.5;
    if (i > 0) line(L, top, R, top, 0.3);
    if (event.kind === "IN") {
      txt(formatPdfDate(event.date), (L + 100) / 2, y, { align: "center", size: 6.5 });
      txt(event.batchId, (100 + 205) / 2, y, { align: "center", size: 6.2 });
      txt(formatStockNumber(event.qty), (205 + 250) / 2, y, { align: "center", size: 6.5 });
      txt(event.stack, (250 + 323) / 2, y, { align: "center", size: 6.2 });
    } else {
      txt(formatPdfDate(event.date), (323 + 392) / 2, y, { align: "center", size: 6.5 });
      txt(event.soNumber, (392 + 505) / 2, y, { align: "center", size: 6.2 });
      txt(event.customer, 510, y, { size: 6.2, maxWidth: 205 });
      txt(formatStockNumber(event.qty), (720 + 766) / 2, y, { align: "center", size: 6.5 });
    }
    txt(formatStockNumber(event.balance), (766 + 812) / 2, y, { align: "center", size: 6.5 });
  });

  txt("Kepala GBB Sunter Timur I & II", 770, 526, { size: 6.8, align: "center" });
  txt("IRSA MAULIAN NUGRAHA", 770, 567, { size: 6.8, bold: true, align: "center" });

  const safeSku = String(sku.id || sku.name || "produk-jadi").replace(/[^a-z0-9-_]/gi, "_");
  pdf.save("Kartu_Persediaan_Produk_Jadi_" + safeSku + ".pdf");
}

// --- APLIKASI UTAMA ---
export default function App() {
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = localStorage.getItem("rebagging_session");
      if (!saved) return null;
      const parsed = JSON.parse(saved);
      if (!parsed?.username || !parsed?.role) {
        localStorage.removeItem("rebagging_session");
        return null;
      }
      // Jangan simpan password di session browser.
      return { username: parsed.username, role: parsed.role };
    } catch (error) {
      console.error("Session Parse Error:", error);
      localStorage.removeItem("rebagging_session");
      return null;
    }
  });
  
  const [users, setUsers] = useState([]);
  const [skus, setSkus] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [inventoryBatches, setInventoryBatches] = useState([]);
  const [rebagRecipes, setRebagRecipes] = useState(DEFAULT_REBAG_RECIPES);
  const [systemConfig, setSystemConfig] = useState({ name: "Sistem Rebagging Terpadu", logo: null });
  
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [loginError, setLoginError] = useState("");
  const [activeMenu, setActiveMenu] = useState("dashboard");
  const [activeTabSettings, setActiveTabSettings] = useState("system");
  const [activeInvTab, setActiveInvTab] = useState("bulk");
  const [notification, setNotification] = useState(null);
  
  const [fbUser, setFbUser] = useState(null);
  const [dbLoading, setDbLoading] = useState(true);
  const [dbError, setDbError] = useState("");
  const [activeOpTab, setActiveOpTab] = useState("inbound");
  const [historyStartDate, setHistoryStartDate] = useState("");
  const [historyEndDate, setHistoryEndDate] = useState("");
  const [resetHistoryLoading, setResetHistoryLoading] = useState(false);

  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const initialFormData = {
    rebagTargetSkuId: "", rebagTargetStack: "", bulkSkuId: "", bulkBatchId: "", qtyToProcess: "",
    rebagGoodQty: "", rebagProcessQty: "0", rebagDamageQty: "0",
    rebagResultTmNumber: "", rebagExpiryDate: getDefaultExpiryDate(),
    outSkuId: "", outTmNumber: "", outSoNumber: "", outCustomer: "",
    useBackdate: false, backdateDateTime: ""
  };
  const [formData, setFormData] = useState(initialFormData);
  const [inboundLines, setInboundLines] = useState([
    { rowId: "IN-1", skuId: "", qty: "", moNumber: "", tmNumber: "", sourceWarehouse: "" }
  ]);
  const [outboundSelections, setOutboundSelections] = useState({});
  const [rebagMaterialSelections, setRebagMaterialSelections] = useState({});
  const [processResolution, setProcessResolution] = useState({
    batchId: "",
    qty: "",
    outcome: "GOOD",
  });

  const [newSku, setNewSku] = useState({ id: "", name: "", type: "bulk", unit: "KG" });
  const [newUserForm, setNewUserForm] = useState({ username: "", password: "", role: "Operator" });
  const [editingRecipeId, setEditingRecipeId] = useState("");
  const [recipeForm, setRecipeForm] = useState({
    targetSku: "",
    label: "",
    active: true,
    notes: "",
    materials: [{ rowId: "MAT-1", skuId: "", required: true, calculationMode: "manual", outputPerUnit: "" }],
  });

  useEffect(() => {
    if (!auth) {
      setDbError("Firebase Authentication tidak tersedia.");
      setDbLoading(false);
      return;
    }

    const initAuth = async () => {
      try {
        await signInAnonymously(auth);
      } catch (error) {
        console.error("Firebase Auth Error:", error);
        setDbError(`Gagal terhubung ke Firebase Authentication: ${error.message || "unknown error"}`);
        setDbLoading(false);
      }
    };

    const unsubscribeAuth = onAuthStateChanged(
      auth,
      setFbUser,
      (error) => {
        console.error("Firebase Auth State Error:", error);
        setDbError(`Firebase Authentication bermasalah: ${error.message || "unknown error"}`);
        setDbLoading(false);
      }
    );

    initAuth();
    return unsubscribeAuth;
  }, []);

  useEffect(() => {
    if (!fbUser || !db) return;

    const handleDbError = (source) => (error) => {
      console.error(`Firestore ${source} Error:`, error);
      setDbError(`Gagal membaca database (${source}): ${error.message || "unknown error"}`);
      setDbLoading(false);
    };

    const unsubUsers = onSnapshot(
      collection(db, "artifacts", appId, "public", "data", "users"),
      (snap) => {
        if (snap.empty) {
          setUsers(DEFAULT_USERS);
          Promise.all(
            DEFAULT_USERS.map((u) =>
              setDoc(doc(db, "artifacts", appId, "public", "data", "users", u.username), u)
            )
          ).catch(handleDbError("inisialisasi pengguna"));
        } else {
          setUsers(snap.docs.map((d) => d.data()));
        }
      },
      handleDbError("pengguna")
    );

    const unsubSkus = onSnapshot(
      collection(db, "artifacts", appId, "public", "data", "skus"),
      (snap) => {
        setSkus(snap.docs.map((d) => d.data()));
        setDbLoading(false);
      },
      handleDbError("SKU")
    );

    const unsubBatches = onSnapshot(
      collection(db, "artifacts", appId, "public", "data", "batches"),
      (snap) => setInventoryBatches(snap.docs.map((d) => d.data())),
      handleDbError("stok batch")
    );

    const unsubRecipes = onSnapshot(
      collection(db, "artifacts", appId, "public", "data", "recipes"),
      (snap) => {
        if (snap.empty) {
          setRebagRecipes(DEFAULT_REBAG_RECIPES);
          Promise.all(
            DEFAULT_REBAG_RECIPES.map((recipe) =>
              setDoc(
                doc(db, "artifacts", appId, "public", "data", "recipes", recipe.id),
                recipe
              )
            )
          ).catch(handleDbError("inisialisasi komposisi"));
        } else {
          setRebagRecipes(
            snap.docs
              .map((d) => ({ id: d.id, ...d.data() }))
              .sort((a, b) => String(a.label || "").localeCompare(String(b.label || "")))
          );
        }
      },
      handleDbError("komposisi rebagging")
    );

    const unsubTx = onSnapshot(
      collection(db, "artifacts", appId, "public", "data", "transactions"),
      (snap) => {
        setTransactions(
          snap.docs
            .map((d) => d.data())
            .sort((a, b) => new Date(b.date) - new Date(a.date))
        );
      },
      handleDbError("transaksi")
    );

    const unsubConfig = onSnapshot(
      doc(db, "artifacts", appId, "public", "data", "config", "system"),
      (snap) => {
        if (snap.exists()) setSystemConfig(snap.data());
      },
      handleDbError("konfigurasi")
    );

    return () => {
      unsubUsers();
      unsubSkus();
      unsubBatches();
      unsubRecipes();
      unsubTx();
      unsubConfig();
    };
  }, [fbUser]);

  useEffect(() => {
    if (!fbUser || !db || rebagRecipes.length === 0 || skus.length === 0) return;

    const standardByRecipe = {
      GULA: 24,
      FORTIVIT_1KG: 20,
    };

    rebagRecipes.forEach((recipe) => {
      const standard = standardByRecipe[recipe.id];
      if (!standard || !Array.isArray(recipe.materials)) return;

      let changed = false;
      const updatedMaterials = recipe.materials.map((item) => {
        if (!item || typeof item === "string" || item.calculationMode) return item;
        const sku = skus.find((s) => s.id === item.skuId);
        const name = String(sku?.name || "").toUpperCase();
        const namedAsCarton = name.includes("KARDUS") || name.includes("KARTON");
        const defaultGulaCarton = recipe.id === "GULA" && item.skuId === "D0200130X";
        if (!namedAsCarton && !defaultGulaCarton) return item;

        changed = true;
        return {
          ...item,
          calculationMode: "per_output",
          outputPerUnit: standard,
        };
      });

      if (changed) {
        setDoc(
          doc(db, "artifacts", appId, "public", "data", "recipes", recipe.id),
          {
            ...recipe,
            materials: updatedMaterials,
            updatedAt: new Date().toISOString(),
            updatedBy: "system-migration",
          }
        ).catch((error) =>
          console.error("Gagal memperbarui standar kardus lama:", error)
        );
      }
    });
  }, [fbUser, db, rebagRecipes, skus]);

  const showNotif = (msg) => { setNotification(msg); setTimeout(() => setNotification(null), 3000); };
  const hasAccess = (roles) => currentUser && roles.includes(currentUser.role);
  const isVerifiedSuperAdmin = Boolean(
    currentUser?.role === "Super Admin" &&
    users.some(
      (u) => u.username === currentUser.username && u.role === "Super Admin"
    )
  );

  const selectedRebagTargetSku = skus.find((s) => s.id === formData.rebagTargetSkuId);
  const activeRebagRecipe = getRebagRecipe(selectedRebagTargetSku, rebagRecipes);
  const activeRebagMaterials = normalizeRecipeMaterials(activeRebagRecipe);

  const outboundSelectedSku = skus.find((s) => s.id === formData.outSkuId);
  const outboundIsFinishedGoods = outboundSelectedSku?.type === "rebagged";

  const outboundAvailableResultTms = useMemo(() => {
    if (!formData.outSkuId || !outboundIsFinishedGoods) return [];
    return [
      ...new Set(
        inventoryBatches
          .filter(
            (b) =>
              b.skuId === formData.outSkuId &&
              Number(b.currentQty || 0) > 0 &&
              b.resultTmNumber
          )
          .map((b) => b.resultTmNumber)
      ),
    ].sort();
  }, [formData.outSkuId, outboundIsFinishedGoods, inventoryBatches]);

  const addInboundLine = () => {
    setInboundLines((prev) => [
      ...prev,
      {
        rowId: `IN-${Date.now()}-${prev.length + 1}`,
        skuId: "",
        qty: "",
        moNumber: "",
        tmNumber: "",
        sourceWarehouse: "",
      },
    ]);
  };

  const updateInboundLine = (rowId, field, value) => {
    setInboundLines((prev) =>
      prev.map((line) => (line.rowId === rowId ? { ...line, [field]: value } : line))
    );
  };

  const removeInboundLine = (rowId) => {
    setInboundLines((prev) => {
      const next = prev.filter((line) => line.rowId !== rowId);
      return next.length > 0
        ? next
        : [{ rowId: `IN-${Date.now()}`, skuId: "", qty: "", moNumber: "", tmNumber: "", sourceWarehouse: "" }];
    });
  };

  const handleRebagTargetChange = (value) => {
    setFormData((prev) => ({
      ...prev,
      rebagTargetSkuId: value,
      bulkSkuId: "",
      bulkBatchId: "",
      rebagResultTmNumber: "",
    }));
    setRebagMaterialSelections({});
  };

  const handleOutboundSkuChange = (value) => {
    const sku = skus.find((s) => s.id === value);
    const resultTms =
      sku?.type === "rebagged"
        ? [
            ...new Set(
              inventoryBatches
                .filter(
                  (b) =>
                    b.skuId === value &&
                    Number(b.currentQty || 0) > 0 &&
                    b.resultTmNumber
                )
                .map((b) => b.resultTmNumber)
            ),
          ].sort()
        : [];

    setFormData((prev) => ({
      ...prev,
      outSkuId: value,
      outTmNumber: resultTms.length === 1 ? resultTms[0] : "",
    }));
    setOutboundSelections({});
  };

  const handleOutboundTmChange = (value) => {
    setFormData((prev) => ({ ...prev, outTmNumber: value }));
    setOutboundSelections({});
  };

  const handleBackdateDateTimeChange = (value) => {
    setFormData((prev) => {
      const next = { ...prev, backdateDateTime: value };
      if (activeOpTab === "rebagging" && value) {
        next.rebagExpiryDate = getExpiryDateFromLocalDateTime(value);
      }
      return next;
    });
  };

  const handleLogin = (e) => {
    e.preventDefault();
    const user = users.find(u => u.username === loginForm.username && u.password === loginForm.password);
    if (user) {
      const sessionUser = { username: user.username, role: user.role };
      setCurrentUser(sessionUser);
      localStorage.setItem("rebagging_session", JSON.stringify(sessionUser));
      setLoginError("");
      setLoginForm({ username: "", password: "" });
    }
    else setLoginError("Username/password salah!");
  };

  const handleGuestLogin = () => {
    const guestUser = { username: "Tamu (View Only)", role: "Viewer" };
    setCurrentUser(guestUser);
    localStorage.setItem("rebagging_session", JSON.stringify(guestUser));
    setLoginError("");
  };

  const handleLogout = () => { setCurrentUser(null); localStorage.removeItem("rebagging_session"); setActiveMenu("dashboard"); };

  const handleNavClick = (menuName) => {
    setActiveMenu(menuName);
    setIsSidebarOpen(false);
  };

  const handleTransactionSubmit = async (e) => {
    e.preventDefault();

    if (!db) return alert("Database belum siap. Silakan muat ulang aplikasi.");

    const timestamp = Date.now();
    const recordedAt = new Date(timestamp).toISOString();
    const backdateRequested = Boolean(formData.useBackdate);

    if (backdateRequested && !isVerifiedSuperAdmin) {
      return alert("Akses backdate hanya tersedia untuk Super Admin yang terverifikasi.");
    }

    let date = recordedAt;
    if (backdateRequested) {
      if (!formData.backdateDateTime) {
        return alert("Pilih tanggal dan waktu backdate terlebih dahulu.");
      }

      const selectedDate = new Date(formData.backdateDateTime);
      if (Number.isNaN(selectedDate.getTime())) {
        return alert("Tanggal backdate tidak valid.");
      }
      if (selectedDate.getTime() > timestamp + 60000) {
        return alert("Tanggal backdate tidak boleh melebihi waktu sekarang.");
      }
      date = selectedDate.toISOString();
    }

    const auditMeta = {
      recordedAt,
      isBackdated: backdateRequested,
      backdatedBy: backdateRequested ? currentUser.username : "",
    };

    try {
      if (activeOpTab === "inbound") {
        const normalizedLines = inboundLines.map((line) => ({
          ...line,
          sku: skus.find((s) => s.id === line.skuId),
          qtyValue: Number(line.qty),
          moNumber: String(line.moNumber || "").trim(),
          tmNumber: String(line.tmNumber || "").trim(),
          sourceWarehouse: String(line.sourceWarehouse || "").trim(),
        }));

        if (normalizedLines.length === 0) {
          return alert("Tambahkan minimal satu SKU bahan.");
        }

        for (let i = 0; i < normalizedLines.length; i += 1) {
          const line = normalizedLines[i];
          const rowLabel = `Baris ${i + 1}`;

          if (!line.sku) return alert(`${rowLabel}: pilih SKU bahan.`);
          if (!Number.isFinite(line.qtyValue) || line.qtyValue <= 0) {
            return alert(`${rowLabel}: kuantitas harus lebih dari 0.`);
          }
          if (!line.moNumber) return alert(`${rowLabel}: No. MO wajib diisi.`);
          if (!line.tmNumber) return alert(`${rowLabel}: No. TM bahan wajib diisi.`);
          if (!line.sourceWarehouse) return alert(`${rowLabel}: gudang asal wajib diisi.`);
        }

        const receiptGroupId = `IN-GRP-${timestamp}`;
        const batch = writeBatch(db);

        normalizedLines.forEach((line, index) => {
          const batchId = `INB-${timestamp}-${index + 1}`;
          const txId = `TRX-${timestamp}-IN-${index + 1}`;

          batch.set(
            doc(db, "artifacts", appId, "public", "data", "batches", batchId),
            {
              batchId,
              receiptGroupId,
              skuId: line.sku.id,
              initialQty: line.qtyValue,
              currentQty: line.qtyValue,
              sourceWarehouse: line.sourceWarehouse,
              moNumber: line.moNumber,
              tmNumber: line.tmNumber,
              date,
              ...auditMeta,
            }
          );

          batch.set(
            doc(db, "artifacts", appId, "public", "data", "transactions", txId),
            {
              id: txId,
              receiptGroupId,
              date,
              type: "INBOUND",
              skuId: line.sku.id,
              skuName: line.sku.name,
              qtyChange: line.qtyValue,
              unit: line.sku.unit,
              operator: currentUser.username,
              sourceWarehouse: line.sourceWarehouse,
              moNumber: line.moNumber,
              tmNumber: line.tmNumber,
              batchId,
              ...auditMeta,
            }
          );
        });

        await batch.commit();
      } else if (activeOpTab === "rebagging") {
        const targetSku = skus.find((s) => s.id === formData.rebagTargetSkuId);
        const qty = Number(formData.qtyToProcess);
        const goodQty = Number(formData.rebagGoodQty || 0);
        const processQty = Number(formData.rebagProcessQty || 0);
        const damageQty = Number(formData.rebagDamageQty || 0);
        const totalResultQty = goodQty + processQty + damageQty;
        const resultTmNumber = String(formData.rebagResultTmNumber || "").trim();

        if (!targetSku) return alert("Pilih SKU hasil rebagging.");
        if (!resultTmNumber) return alert("TM Hasil wajib diisi pada proses Rebagging.");
        if (!Number.isFinite(qty) || qty <= 0) return alert("Kuantitas hasil yang diproses harus lebih dari 0.");
        if (
          ![goodQty, processQty, damageQty].every((value) => Number.isFinite(value) && value >= 0)
        ) {
          return alert("Jumlah GOOD, PROCESS, dan DAMAGE harus berupa angka 0 atau lebih.");
        }
        if (Math.abs(totalResultQty - qty) > 0.0001) {
          return alert(
            `Total hasil tidak sesuai. GOOD + PROCESS + DAMAGE harus sama dengan Qty Diproses (${qty}). Saat ini total hasil: ${totalResultQty}.`
          );
        }
        if (!formData.rebagExpiryDate) return alert("Tanggal kedaluwarsa wajib diisi.");
        if (!formData.rebagTargetStack) return alert("Pilih lokasi tumpukan tujuan.");

        const recipe = getRebagRecipe(targetSku, rebagRecipes);
        let selectedMaterials = [];

        if (recipe) {
          const recipeMaterials = normalizeRecipeMaterials(recipe);

          for (const recipeMaterial of recipeMaterials) {
            const materialSkuId = recipeMaterial.skuId;
            const selection = rebagMaterialSelections[materialSkuId] || {};
            const sourceBatch = inventoryBatches.find((b) => b.batchId === selection.batchId);
            const sourceSku = skus.find((s) => s.id === materialSkuId);
            const calculatedQty = getCalculatedMaterialQty(recipeMaterial, qty);
            const usedQty =
              recipeMaterial.calculationMode === "per_output"
                ? Number(calculatedQty || 0)
                : Number(selection.qty);
            const materialDamageQty = Number(selection.damageQty || 0);
            const totalMaterialQty = usedQty + materialDamageQty;
            const hasSelection =
              Boolean(selection.batchId) ||
              Boolean(selection.qty) ||
              materialDamageQty > 0;

            if (!recipeMaterial.required && !hasSelection) {
              continue;
            }
            if (!sourceBatch) {
              return alert(
                `Pilih batch untuk bahan ${materialSkuId}${recipeMaterial.required ? "" : " atau kosongkan bahan opsional ini"}.`
              );
            }
            if (!sourceBatch.moNumber) return alert(`Batch bahan ${materialSkuId} belum memiliki No. MO.`);
            if (!sourceBatch.tmNumber) return alert(`Batch bahan ${materialSkuId} belum memiliki No. TM.`);
            if (!Number.isFinite(materialDamageQty) || materialDamageQty < 0) {
              return alert(`Qty rusak bahan ${materialSkuId} tidak valid.`);
            }
            if (
              recipeMaterial.calculationMode === "per_output" &&
              (!Number.isFinite(Number(recipeMaterial.outputPerUnit)) ||
                Number(recipeMaterial.outputPerUnit) <= 0)
            ) {
              return alert(`Standar isi kemasan bahan ${materialSkuId} belum valid di Master Komposisi.`);
            }
            if (!Number.isFinite(usedQty) || usedQty <= 0) {
              return alert(`Jumlah pemakaian bahan ${materialSkuId} harus lebih dari 0.`);
            }
            if (!Number.isFinite(totalMaterialQty) || totalMaterialQty <= 0) {
              return alert(`Total pemakaian bahan ${materialSkuId} tidak valid.`);
            }
            if (
              sourceBatch.date &&
              new Date(date).getTime() < new Date(sourceBatch.date).getTime()
            ) {
              return alert(
                `Tanggal rebagging tidak boleh lebih awal dari tanggal masuk bahan ${materialSkuId}.`
              );
            }

            selectedMaterials.push({
              skuId: materialSkuId,
              skuName: sourceSku?.name || materialSkuId,
              required: recipeMaterial.required,
              calculationMode: recipeMaterial.calculationMode || "manual",
              outputPerUnit: recipeMaterial.outputPerUnit || "",
              standardQty:
                recipeMaterial.calculationMode === "per_output" ? usedQty : null,
              usedQty,
              damageQty: materialDamageQty,
              totalQty: totalMaterialQty,
              batchId: sourceBatch.batchId,
              moNumber: sourceBatch.moNumber,
              tmNumber: sourceBatch.tmNumber,
              qty: totalMaterialQty,
              unit: sourceSku?.unit || "",
              sourceWarehouse: sourceBatch.sourceWarehouse || "",
            });
          }

          if (selectedMaterials.length === 0) {
            return alert("Pilih minimal satu bahan untuk proses Rebagging.");
          }
        } else {
          const selectedBatch = inventoryBatches.find((b) => b.batchId === formData.bulkBatchId);
          const sourceSku = skus.find((s) => s.id === selectedBatch?.skuId);

          if (!selectedBatch) return alert("Pilih batch bahan baku yang valid.");
          if (!selectedBatch.moNumber) return alert("Batch bahan baku belum memiliki No. MO.");
          if (!selectedBatch.tmNumber) return alert("Batch bahan baku belum memiliki No. TM.");
          if (
            selectedBatch.date &&
            new Date(date).getTime() < new Date(selectedBatch.date).getTime()
          ) {
            return alert("Tanggal rebagging tidak boleh lebih awal dari tanggal batch bahan baku masuk.");
          }

          selectedMaterials = [
            {
              skuId: sourceSku?.id || selectedBatch.skuId || "",
              skuName: sourceSku?.name || selectedBatch.skuId || "Bahan Baku",
              batchId: selectedBatch.batchId,
              moNumber: selectedBatch.moNumber,
              tmNumber: selectedBatch.tmNumber,
              calculationMode: "manual",
              outputPerUnit: "",
              standardQty: null,
              usedQty: qty,
              damageQty: 0,
              totalQty: qty,
              qty,
              unit: sourceSku?.unit || "",
              sourceWarehouse: selectedBatch.sourceWarehouse || "",
            },
          ];
        }

        const newBatchId = `RBG-${timestamp}`;
        const txId = `TRX-${timestamp}`;
        const sourceMoNumbers = [...new Set(selectedMaterials.map((m) => m.moNumber).filter(Boolean))];
        const sourceTmNumbers = [...new Set(selectedMaterials.map((m) => m.tmNumber).filter(Boolean))];
        const materialDamageTotal = selectedMaterials.reduce(
          (sum, material) => sum + Number(material.damageQty || 0),
          0
        );

        await runTransaction(db, async (transaction) => {
          const materialRefs = selectedMaterials.map((material) =>
            doc(db, "artifacts", appId, "public", "data", "batches", material.batchId)
          );
          const materialSnaps = await Promise.all(materialRefs.map((ref) => transaction.get(ref)));

          materialSnaps.forEach((snap, index) => {
            if (!snap.exists()) {
              throw new Error(`Batch bahan ${selectedMaterials[index].batchId} tidak ditemukan.`);
            }
            const liveBatch = snap.data();
            const liveQty = Number(liveBatch.currentQty) || 0;
            const requestedQty = Number(selectedMaterials[index].qty) || 0;

            if (requestedQty > liveQty) {
              throw new Error(
                `Pemakaian ${selectedMaterials[index].skuId} melebihi stok terbaru (${liveQty}).`
              );
            }
          });

          materialSnaps.forEach((snap, index) => {
            const liveBatch = snap.data();
            const liveQty = Number(liveBatch.currentQty) || 0;
            transaction.update(materialRefs[index], {
              currentQty: liveQty - Number(selectedMaterials[index].qty),
            });
          });

          const primaryMaterial = selectedMaterials[0];
          const sourceWarehouses = [
            ...new Set(selectedMaterials.map((m) => m.sourceWarehouse).filter(Boolean)),
          ].join(", ");

          const finishedBatchData = {
            batchId: newBatchId,
            skuId: targetSku.id,
            initialQty: qty,
            currentQty: goodQty,
            goodQty,
            processQty,
            damageQty,
            totalProducedQty: qty,
            sourceWarehouse: sourceWarehouses,
            targetStack: formData.rebagTargetStack,
            sourceBatchId: primaryMaterial?.batchId || "",
            sourceBatchIds: selectedMaterials.map((m) => m.batchId),
            materials: selectedMaterials,
            materialDamageTotal,
            moNumber: sourceMoNumbers.join(", "),
            sourceMoNumbers,
            sourceTmNumbers,
            resultTmNumber,
            expiryDate: formData.rebagExpiryDate,
            productionDate: date,
            executor: "KOPEL JAYA",
            supervisor: currentUser.username,
            date,
            ...auditMeta,
          };

          transaction.set(
            doc(db, "artifacts", appId, "public", "data", "batches", newBatchId),
            finishedBatchData
          );

          transaction.set(
            doc(db, "artifacts", appId, "public", "data", "transactions", txId),
            {
              id: txId,
              date,
              type: "REBAGGING",
              skuId: targetSku.id,
              skuName: targetSku.name,
              qtyChange: goodQty,
              processedQty: qty,
              goodQty,
              processQty,
              damageQty,
              unit: targetSku.unit,
              operator: currentUser.username,
              supervisor: currentUser.username,
              executor: "KOPEL JAYA",
              productionDate: date,
              expiryDate: formData.rebagExpiryDate,
              moNumber: sourceMoNumbers.join(", "),
              sourceMoNumbers,
              sourceTmNumbers,
              resultTmNumber,
              targetStack: formData.rebagTargetStack,
              sourceWarehouse: sourceWarehouses,
              sourceBatchId: primaryMaterial?.batchId || "",
              sourceBatchIds: selectedMaterials.map((m) => m.batchId),
              sourceSkuId: primaryMaterial?.skuId || "",
              sourceSkuName: primaryMaterial?.skuName || "",
              sourceQty: primaryMaterial?.qty || 0,
              sourceUnit: primaryMaterial?.unit || "",
              materials: selectedMaterials,
              materialDamageTotal,
              finishedQty: goodQty,
              finishedUnit: targetSku.unit,
              batchId: newBatchId,
              recipeKey: recipe?.id || "MANUAL",
              ...auditMeta,
            }
          );
        });
      } else if (activeOpTab === "outbound") {
        const sku = skus.find((s) => s.id === formData.outSkuId);
        if (!sku) return alert("Pilih barang yang akan dikeluarkan.");

        const isFinishedGoods = sku.type === "rebagged";
        const outboundTm = formData.outTmNumber?.trim() || "";

        if (isFinishedGoods && !outboundTm) {
          return alert("Pilih TM Hasil untuk outbound produk jadi.");
        }

        const selections = Object.entries(outboundSelections)
          .map(([batchId, qtyValue]) => ({
            batchId,
            qty: Number(qtyValue),
            localBatch: inventoryBatches.find((b) => b.batchId === batchId),
          }))
          .filter(({ qty }) => Number.isFinite(qty) && qty > 0);

        if (selections.length === 0) return alert("Isi qty untuk outbound!");

        for (const item of selections) {
          if (!item.localBatch || item.localBatch.skuId !== sku.id) {
            return alert(`Batch ${item.batchId} tidak valid untuk SKU yang dipilih.`);
          }
          if (isFinishedGoods && item.localBatch.resultTmNumber !== outboundTm) {
            return alert(`Batch ${item.batchId} tidak sesuai dengan TM Hasil ${outboundTm}.`);
          }
          if (
            item.localBatch.date &&
            new Date(date).getTime() < new Date(item.localBatch.date).getTime()
          ) {
            return alert(`Tanggal outbound tidak boleh lebih awal dari tanggal masuk batch ${item.batchId}.`);
          }
        }

        await runTransaction(db, async (transaction) => {
          // Semua pembacaan dilakukan lebih dahulu agar transaksi Firestore tetap valid.
          const refs = selections.map((item) =>
            doc(db, "artifacts", appId, "public", "data", "batches", item.batchId)
          );
          const snapshots = await Promise.all(refs.map((ref) => transaction.get(ref)));

          snapshots.forEach((snap, index) => {
            if (!snap.exists()) throw new Error(`Batch ${selections[index].batchId} tidak ditemukan.`);
            const liveBatch = snap.data();
            const liveQty = Number(liveBatch.currentQty) || 0;
            if (liveBatch.skuId !== sku.id) {
              throw new Error(`Batch ${selections[index].batchId} tidak sesuai SKU yang dipilih.`);
            }
            if (selections[index].qty > liveQty) {
              throw new Error(
                `Qty outbound batch ${selections[index].batchId} melebihi stok terbaru (${liveQty}).`
              );
            }
          });

          snapshots.forEach((snap, index) => {
            const item = selections[index];
            const liveBatch = snap.data();
            const liveQty = Number(liveBatch.currentQty) || 0;
            const txId = `TRX-${timestamp}-${index + 1}`;

            transaction.update(refs[index], { currentQty: liveQty - item.qty });
            transaction.set(
              doc(db, "artifacts", appId, "public", "data", "transactions", txId),
              {
                id: txId,
                date,
                type: "OUTBOUND",
                skuId: sku.id,
                skuName: sku.name,
                qtyChange: item.qty,
                unit: sku.unit,
                operator: currentUser.username,
                batchId: item.batchId,
                sourceWarehouse: liveBatch.sourceWarehouse || "",
                moNumber: liveBatch.moNumber || "",
                sourceMoNumbers: liveBatch.sourceMoNumbers || [],
                sourceTmNumbers: liveBatch.sourceTmNumbers || [],
                tmNumber: isFinishedGoods ? outboundTm : (liveBatch.tmNumber || ""),
                resultTmNumber: isFinishedGoods ? outboundTm : (liveBatch.resultTmNumber || ""),
                soNumber: formData.outSoNumber?.trim() || "",
                customer: formData.outCustomer?.trim() || "",
                ...auditMeta,
              }
            );
          });
        });
      }

      showNotif("Transaksi Berhasil Disimpan");
      setFormData(initialFormData);
      setInboundLines([
        { rowId: `IN-${Date.now()}`, skuId: "", qty: "", moNumber: "", tmNumber: "", sourceWarehouse: "" }
      ]);
      setOutboundSelections({});
      setRebagMaterialSelections({});
    } catch (error) {
      console.error("Transaction Error:", error);
      alert(`Transaksi gagal disimpan: ${error.message || "Terjadi kesalahan tidak diketahui."}`);
    }
  };

  const handleProcessResolutionSubmit = async (e) => {
    e.preventDefault();

    if (!hasAccess(["Super Admin", "Admin", "Operator"])) {
      return alert("Anda tidak memiliki akses untuk menindaklanjuti barang PROCESS.");
    }
    if (!db) return alert("Database belum siap. Silakan muat ulang aplikasi.");

    const batch = inventoryBatches.find((b) => b.batchId === processResolution.batchId);
    const qty = Number(processResolution.qty);
    const outcome = processResolution.outcome;

    if (!batch) return alert("Pilih batch PROCESS yang valid.");
    if (!Number.isFinite(qty) || qty <= 0) return alert("Jumlah tindak lanjut harus lebih dari 0.");
    if (!["GOOD", "DAMAGE"].includes(outcome)) return alert("Pilih hasil tindak lanjut yang valid.");

    const sku = skus.find((s) => s.id === batch.skuId);
    const timestamp = Date.now();
    const date = new Date(timestamp).toISOString();
    const batchRef = doc(db, "artifacts", appId, "public", "data", "batches", batch.batchId);
    const txId = `TRX-PRC-${timestamp}`;

    try {
      await runTransaction(db, async (transaction) => {
        const batchSnap = await transaction.get(batchRef);
        if (!batchSnap.exists()) throw new Error("Batch produk jadi tidak ditemukan.");

        const liveBatch = batchSnap.data();
        const liveProcessQty = Number(liveBatch.processQty || 0);
        const liveCurrentQty = Number(liveBatch.currentQty || 0);
        const liveGoodQty = Number(liveBatch.goodQty ?? liveCurrentQty);
        const liveDamageQty = Number(liveBatch.damageQty || 0);

        if (qty > liveProcessQty) {
          throw new Error(`Jumlah melebihi stok PROCESS terbaru (${liveProcessQty}).`);
        }

        const updates = {
          processQty: liveProcessQty - qty,
        };

        if (outcome === "GOOD") {
          updates.currentQty = liveCurrentQty + qty;
          updates.goodQty = liveGoodQty + qty;
        } else {
          updates.damageQty = liveDamageQty + qty;
        }

        transaction.update(batchRef, updates);
        transaction.set(
          doc(db, "artifacts", appId, "public", "data", "transactions", txId),
          {
            id: txId,
            date,
            recordedAt: date,
            isBackdated: false,
            backdatedBy: "",
            type: outcome === "GOOD" ? "PROCESS_TO_GOOD" : "PROCESS_TO_DAMAGE",
            skuId: liveBatch.skuId,
            skuName: sku?.name || liveBatch.skuId || "",
            qtyChange: outcome === "GOOD" ? qty : 0,
            resolutionQty: qty,
            fromStatus: "PROCESS",
            toStatus: outcome,
            unit: sku?.unit || "",
            operator: currentUser.username,
            batchId: liveBatch.batchId,
            targetStack: liveBatch.targetStack || "",
            productionDate: liveBatch.productionDate || liveBatch.date || date,
          }
        );
      });

      showNotif(`PROCESS berhasil dipindahkan menjadi ${outcome}`);
      setProcessResolution({ batchId: "", qty: "", outcome: "GOOD" });
    } catch (error) {
      console.error("Process Resolution Error:", error);
      alert(`Gagal menindaklanjuti PROCESS: ${error.message || "Terjadi kesalahan tidak diketahui."}`);
    }
  };

  const resetRecipeForm = () => {
    setEditingRecipeId("");
    setRecipeForm({
      targetSku: "",
      label: "",
      active: true,
      notes: "",
      materials: [{ rowId: `MAT-${Date.now()}`, skuId: "", required: true, calculationMode: "manual", outputPerUnit: "" }],
    });
  };

  const addRecipeMaterialLine = () => {
    setRecipeForm((prev) => ({
      ...prev,
      materials: [
        ...prev.materials,
        { rowId: `MAT-${Date.now()}-${prev.materials.length + 1}`, skuId: "", required: true, calculationMode: "manual", outputPerUnit: "" },
      ],
    }));
  };

  const updateRecipeMaterialLine = (rowId, field, value) => {
    setRecipeForm((prev) => ({
      ...prev,
      materials: prev.materials.map((item) =>
        item.rowId === rowId ? { ...item, [field]: value } : item
      ),
    }));
  };

  const removeRecipeMaterialLine = (rowId) => {
    setRecipeForm((prev) => {
      const next = prev.materials.filter((item) => item.rowId !== rowId);
      return {
        ...prev,
        materials:
          next.length > 0
            ? next
            : [{ rowId: `MAT-${Date.now()}`, skuId: "", required: true, calculationMode: "manual", outputPerUnit: "" }],
      };
    });
  };

  const handleEditRecipe = (recipe) => {
    const materials = normalizeRecipeMaterials(recipe).map((item, index) => ({
      rowId: `MAT-EDIT-${index + 1}-${Date.now()}`,
      skuId: item.skuId,
      required: item.required,
      calculationMode: item.calculationMode || "manual",
      outputPerUnit: item.outputPerUnit || "",
    }));
    setEditingRecipeId(recipe.id);
    setRecipeForm({
      targetSku: recipe.targetSku || "",
      label: recipe.label || "",
      active: recipe.active !== false,
      notes: recipe.notes || "",
      materials:
        materials.length > 0
          ? materials
          : [{ rowId: `MAT-${Date.now()}`, skuId: "", required: true, calculationMode: "manual", outputPerUnit: "" }],
    });
    setActiveTabSettings("recipes");
  };

  const handleSaveRecipe = async (e) => {
    e.preventDefault();

    if (!isVerifiedSuperAdmin) {
      return alert("Hanya Super Admin yang dapat mengubah Master Komposisi.");
    }
    if (!db) return alert("Database belum siap.");

    const targetSku = String(recipeForm.targetSku || "").trim();
    const label = String(recipeForm.label || "").trim();
    const materials = recipeForm.materials
      .map((item, index) => ({
        skuId: String(item.skuId || "").trim(),
        required: item.required !== false,
        order: index + 1,
        calculationMode: item.calculationMode === "per_output" ? "per_output" : "manual",
        outputPerUnit:
          item.calculationMode === "per_output" && Number(item.outputPerUnit) > 0
            ? Number(item.outputPerUnit)
            : "",
      }))
      .filter((item) => item.skuId);

    if (!targetSku) return alert("Pilih SKU Produk Jadi.");
    if (!label) return alert("Nama komposisi wajib diisi.");
    if (materials.length === 0) return alert("Tambahkan minimal satu SKU bahan.");

    const invalidAutoMaterial = materials.find(
      (item) =>
        item.calculationMode === "per_output" &&
        (!Number.isFinite(Number(item.outputPerUnit)) || Number(item.outputPerUnit) <= 0)
    );
    if (invalidAutoMaterial) {
      return alert(
        `Isi per kemasan untuk SKU ${invalidAutoMaterial.skuId} harus lebih dari 0.`
      );
    }

    const duplicateMaterial = materials.find(
      (item, index) =>
        materials.findIndex((other) => other.skuId === item.skuId) !== index
    );
    if (duplicateMaterial) {
      return alert(`SKU bahan ${duplicateMaterial.skuId} tercantum lebih dari satu kali.`);
    }

    const duplicateTarget = rebagRecipes.find(
      (recipe) =>
        recipe.id !== editingRecipeId &&
        recipe.targetSku === targetSku &&
        recipe.active !== false &&
        recipeForm.active !== false
    );
    if (duplicateTarget) {
      return alert(
        `Produk jadi ini sudah memiliki komposisi aktif: ${duplicateTarget.label}. Nonaktifkan atau edit komposisi tersebut terlebih dahulu.`
      );
    }

    const recipeId = editingRecipeId || `REC-${targetSku}-${Date.now()}`;
    const existing = rebagRecipes.find((recipe) => recipe.id === editingRecipeId);

    await setDoc(
      doc(db, "artifacts", appId, "public", "data", "recipes", recipeId),
      {
        id: recipeId,
        targetSku,
        label,
        active: recipeForm.active !== false,
        notes: String(recipeForm.notes || "").trim(),
        materials,
        createdAt: existing?.createdAt || new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        updatedBy: currentUser.username,
      }
    );

    showNotif(editingRecipeId ? "Komposisi berhasil diperbarui" : "Komposisi berhasil ditambahkan");
    resetRecipeForm();
  };

  const handleDeleteRecipe = async (recipe) => {
    if (!isVerifiedSuperAdmin) {
      return alert("Hanya Super Admin yang dapat menghapus Master Komposisi.");
    }
    if (!window.confirm(`Hapus komposisi "${recipe.label}"? Data transaksi lama tidak akan ikut terhapus.`)) {
      return;
    }

    await deleteDoc(
      doc(db, "artifacts", appId, "public", "data", "recipes", recipe.id)
    );
    if (editingRecipeId === recipe.id) resetRecipeForm();
    showNotif("Komposisi berhasil dihapus");
  };

  const handleAddManualSku = async (e) => {
    e.preventDefault();
    if (!newSku.id || !newSku.name) return alert("ID dan Nama SKU wajib diisi!");
    if (db) {
      await setDoc(doc(db, "artifacts", appId, "public", "data", "skus", newSku.id.toString()), newSku);
      showNotif(`SKU ${newSku.name} Berhasil Ditambahkan`);
      setNewSku({ id: "", name: "", type: "bulk", unit: "KG" });
    }
  };

  const handleAddUser = async (e) => {
    e.preventDefault();
    if (!newUserForm.username || !newUserForm.password) return alert("Username dan password wajib diisi!");
    if (db) {
      await setDoc(doc(db, "artifacts", appId, "public", "data", "users", newUserForm.username), newUserForm);
      showNotif(`Pengguna ${newUserForm.username} berhasil ditambahkan`);
      setNewUserForm({ username: "", password: "", role: "Operator" });
    }
  };

  const handleDeleteUser = async (username) => {
    if (username === currentUser.username) return alert("Anda tidak bisa menghapus akun Anda sendiri yang sedang aktif!");
    if (window.confirm(`Yakin ingin menghapus pengguna '${username}'?`)) {
      if (db) await deleteDoc(doc(db, "artifacts", appId, "public", "data", "users", username));
      showNotif(`Pengguna ${username} telah dihapus`);
    }
  };

  const stockByWarehouseData = useMemo(() => {
    const data = {};
    let hasData = false;
    inventoryBatches.filter(b => b.currentQty > 0).forEach(b => {
      hasData = true;
      const sw = b.sourceWarehouse || "Unknown";
      if(!data[sw]) data[sw] = { name: sw, kg: 0, pack: 0 };
      const sku = skus.find(s => s.id === b.skuId);
      if (sku && sku.unit?.toUpperCase() === 'KG') data[sw].kg += b.currentQty;
      else data[sw].pack += b.currentQty;
    });
    
    if (!hasData) return [{ name: 'Belum Ada Data', kg: 0, pack: 0 }];
    return Object.values(data);
  }, [inventoryBatches, skus]);

  const compositionData = [
    { name: 'Bahan Baku', value: skus.filter(s=>s.type==='bulk').length },
    { name: 'Barang Jadi', value: skus.filter(s=>s.type==='rebagged').length }
  ];

  const handleImportExcel = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (event) => {
      const bstr = event.target.result;
      const wb = XLSX.read(bstr, { type: 'binary' });
      const wsname = wb.SheetNames[0];
      const data = XLSX.utils.sheet_to_json(wb.Sheets[wsname]);
      if (db) {
        const batch = writeBatch(db);
        data.forEach(row => {
          if(row.id) batch.set(doc(db, "artifacts", appId, "public", "data", "skus", row.id.toString()), row);
        });
        await batch.commit();
        showNotif(`${data.length} SKU Berhasil Diimpor`);
      }
    };
    reader.readAsBinaryString(file);
  };

  const handleDownloadHistory = () => {
    let filtered = transactions;
    if (historyStartDate && historyEndDate) {
      const s = new Date(historyStartDate); const e = new Date(historyEndDate); e.setHours(23,59,59);
      filtered = filtered.filter(t => new Date(t.date) >= s && new Date(t.date) <= e);
    }
    const ws = XLSX.utils.json_to_sheet(filtered.map(t => ({
      Tanggal: new Date(t.date).toLocaleString('id-ID'),
      "Waktu Input": t.recordedAt ? new Date(t.recordedAt).toLocaleString('id-ID') : "",
      Backdate: t.isBackdated ? "YA" : "TIDAK",
      "Backdate Oleh": t.backdatedBy || "",
      Tipe: t.type,
      SKU: t.skuName,
      "No. MO": t.moNumber || "",
      "MO Sumber": Array.isArray(t.sourceMoNumbers) ? t.sourceMoNumbers.join(", ") : "",
      "No. TM": t.tmNumber || "",
      "TM Bahan Sumber": Array.isArray(t.sourceTmNumbers) ? t.sourceTmNumbers.join(", ") : "",
      "TM Hasil": t.resultTmNumber || "",
      Qty: t.qtyChange,
      Operator: t.operator
    })));
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Riwayat Transaksi");
    XLSX.writeFile(wb, "Riwayat_Rebagging.xlsx");
  };

  const handleDownloadRebaggingPdf = async (transaction) => {
    try {
      const sourceBatch = inventoryBatches.find((b) => b.batchId === transaction.sourceBatchId);
      const sourceSku = skus.find((s) => s.id === (transaction.sourceSkuId || sourceBatch?.skuId));
      await generateRebaggingBatchPdf({
        ...transaction,
        sourceWarehouse: transaction.sourceWarehouse || sourceBatch?.sourceWarehouse || "",
        sourceSkuName: transaction.sourceSkuName || sourceSku?.name || "Gula Curah",
        sourceUnit: transaction.sourceUnit || sourceSku?.unit || "KG",
        sourceQty: transaction.sourceQty ?? transaction.qtyChange,
        finishedQty: transaction.finishedQty ?? transaction.qtyChange,
        finishedUnit: transaction.finishedUnit || transaction.unit || "Pack",
      });
    } catch (error) {
      console.error("PDF Rebagging Error:", error);
      alert(`Gagal membuat PDF rebagging: ${error.message || "Terjadi kesalahan tidak diketahui."}`);
    }
  };

  const handleDownloadInventoryCard = async (sku) => {
    try {
      const skuBatches = inventoryBatches.filter((b) => b.skuId === sku.id);
      if (sku.type === "bulk") {
        await generateRawMaterialStockCardPdf({
          sku,
          batches: skuBatches,
          transactions,
        });
      } else {
        await generateFinishedGoodsStockCardPdf({
          sku,
          batches: skuBatches,
          transactions,
        });
      }
    } catch (error) {
      console.error("Inventory Card PDF Error:", error);
      alert(`Gagal membuat kartu persediaan: ${error.message || "Terjadi kesalahan tidak diketahui."}`);
    }
  };

  const handleUpdateConfig = async (e) => {
    e.preventDefault();
    if (db) await setDoc(doc(db, "artifacts", appId, "public", "data", "config", "system"), systemConfig);
    showNotif("Konfigurasi Sistem Diperbarui");
  };

  const handleResetTransactionHistory = async () => {
    if (!isVerifiedSuperAdmin) {
      return alert("Akses reset riwayat hanya tersedia untuk Super Admin yang terverifikasi.");
    }
    if (!db) {
      return alert("Database belum siap. Silakan muat ulang aplikasi.");
    }

    const firstConfirm = window.confirm(
      "PERINGATAN: Semua RIWAYAT TRANSAKSI akan dihapus permanen.\n\nStok, batch inventori, master SKU, pengguna, dan konfigurasi TIDAK akan dihapus.\n\nLanjutkan?"
    );
    if (!firstConfirm) return;

    const verification = window.prompt(
      'Ketik tepat "RESET RIWAYAT" untuk mengonfirmasi penghapusan seluruh riwayat transaksi.'
    );
    if (verification !== "RESET RIWAYAT") {
      return alert("Konfirmasi tidak sesuai. Reset dibatalkan.");
    }

    try {
      setResetHistoryLoading(true);

      const txCollection = collection(db, "artifacts", appId, "public", "data", "transactions");
      const snapshot = await getDocs(txCollection);

      if (snapshot.empty) {
        alert("Riwayat transaksi sudah kosong.");
        return;
      }

      const docsToDelete = snapshot.docs;
      const chunkSize = 450;

      for (let i = 0; i < docsToDelete.length; i += chunkSize) {
        const batch = writeBatch(db);
        docsToDelete.slice(i, i + chunkSize).forEach((txDoc) => {
          batch.delete(txDoc.ref);
        });
        await batch.commit();
      }

      showNotif(`${docsToDelete.length} riwayat transaksi berhasil dihapus`);
      alert(
        `${docsToDelete.length} riwayat transaksi telah dihapus.\n\nStok dan batch inventori tetap dipertahankan.`
      );
    } catch (error) {
      console.error("Reset Transaction History Error:", error);
      alert(`Gagal mereset riwayat transaksi: ${error.message || "Terjadi kesalahan tidak diketahui."}`);
    } finally {
      setResetHistoryLoading(false);
    }
  };

  if (dbError) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <div className="bg-white border border-red-200 rounded-2xl shadow-sm p-6 max-w-lg w-full text-center">
        <div className="text-red-600 font-black text-xl mb-2">Koneksi Database Bermasalah</div>
        <p className="text-slate-600 text-sm mb-5">{dbError}</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="bg-red-600 hover:bg-red-700 text-white font-bold px-5 py-3 rounded-lg"
        >
          Muat Ulang Aplikasi
        </button>
      </div>
    </div>
  );

  if (dbLoading) return <div className="min-h-screen flex items-center justify-center"><Package className="animate-pulse w-12 h-12 text-red-600"/></div>;
  
  if (!currentUser) return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-slate-950 via-slate-900 to-red-950">
      <div className="pointer-events-none absolute -top-28 -left-20 h-80 w-80 rounded-full bg-red-600/20 blur-3xl"></div>
      <div className="pointer-events-none absolute -bottom-36 -right-24 h-96 w-96 rounded-full bg-white/5 blur-3xl"></div>

      <div className="relative z-10 min-h-screen flex items-center justify-center p-4 sm:p-6 lg:p-10">
        <div className="w-full max-w-5xl overflow-hidden rounded-[2rem] border border-white/10 bg-white shadow-2xl shadow-black/30 grid lg:grid-cols-[1.05fr_0.95fr]">

          <div className="hidden lg:flex relative min-h-[650px] flex-col justify-between overflow-hidden bg-slate-950 p-10 xl:p-12 text-white">
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-red-600/20 via-transparent to-blue-500/10"></div>
            <div className="pointer-events-none absolute -right-20 top-24 h-64 w-64 rounded-full border border-white/10"></div>
            <div className="pointer-events-none absolute -right-4 top-40 h-40 w-40 rounded-full border border-white/10"></div>

            <div className="relative z-10">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3.5 py-2 text-xs font-bold tracking-[0.18em] text-slate-300">
                <span className="h-2 w-2 rounded-full bg-red-500"></span>
                SISTEM OPERASIONAL GUDANG
              </div>

              <div className="mt-10">
                {systemConfig.logo ? (
                  <div className="inline-flex rounded-2xl bg-white p-4 shadow-2xl shadow-black/20">
                    <img src={systemConfig.logo} alt="Logo" className="h-14 w-auto object-contain" />
                  </div>
                ) : (
                  <div className="inline-flex h-20 w-20 items-center justify-center rounded-2xl bg-red-600 shadow-xl shadow-red-950/40">
                    <Package size={38} />
                  </div>
                )}

                <h1 className="mt-8 max-w-md text-4xl font-black leading-tight tracking-tight">
                  {systemConfig.name}
                </h1>
                <p className="mt-4 max-w-md text-sm leading-7 text-slate-400">
                  Kelola inbound, proses rebagging, outbound, persediaan batch, serta dokumen operasional dalam satu sistem terintegrasi.
                </p>
              </div>
            </div>

            <div className="relative z-10 grid grid-cols-3 gap-3">
              {[
                ["Inbound", "Penerimaan"],
                ["Rebagging", "Produksi"],
                ["Outbound", "Pengeluaran"],
              ].map(([title, desc]) => (
                <div key={title} className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
                  <p className="text-sm font-black text-white">{title}</p>
                  <p className="mt-1 text-[11px] font-medium text-slate-500">{desc}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="flex min-h-[650px] items-center bg-white p-6 sm:p-10 lg:p-12">
            <div className="mx-auto w-full max-w-md">
              <div className="mb-8 lg:hidden">
                <div className="flex items-center gap-4">
                  {systemConfig.logo ? (
                    <div className="flex h-16 min-w-16 items-center justify-center rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
                      <img src={systemConfig.logo} alt="Logo" className="max-h-11 w-auto object-contain" />
                    </div>
                  ) : (
                    <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-red-600 text-white shadow-lg shadow-red-100">
                      <Package size={30} />
                    </div>
                  )}
                  <div>
                    <p className="text-xs font-black uppercase tracking-[0.18em] text-red-600">Sistem Gudang</p>
                    <h1 className="mt-1 text-xl font-black leading-tight text-slate-900">{systemConfig.name}</h1>
                  </div>
                </div>
              </div>

              <div className="mb-8">
                <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-red-50 text-red-600">
                  <LogIn size={23} />
                </div>
                <h2 className="text-3xl font-black tracking-tight text-slate-900">Selamat datang</h2>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  Masuk menggunakan akun yang telah terdaftar untuk mengakses sistem.
                </p>
              </div>

              {loginError && (
                <div className="mb-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
                  {loginError}
                </div>
              )}

              <form onSubmit={handleLogin} className="space-y-5">
                <div>
                  <label className="mb-2 block text-sm font-bold text-slate-700">Username</label>
                  <div className="group relative">
                    <UserRound className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 transition-colors group-focus-within:text-red-500" size={19} />
                    <input
                      className="w-full rounded-xl border border-slate-200 bg-slate-50 py-3.5 pl-12 pr-4 text-sm font-medium text-slate-800 outline-none transition-all placeholder:text-slate-400 focus:border-red-400 focus:bg-white focus:ring-4 focus:ring-red-50"
                      placeholder="Masukkan username"
                      value={loginForm.username}
                      onChange={e=>setLoginForm({...loginForm, username: e.target.value})}
                      autoComplete="username"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-bold text-slate-700">Password</label>
                  <div className="group relative">
                    <LockKeyhole className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 transition-colors group-focus-within:text-red-500" size={19} />
                    <input
                      className="w-full rounded-xl border border-slate-200 bg-slate-50 py-3.5 pl-12 pr-4 text-sm font-medium text-slate-800 outline-none transition-all placeholder:text-slate-400 focus:border-red-400 focus:bg-white focus:ring-4 focus:ring-red-50"
                      type="password"
                      placeholder="Masukkan password"
                      value={loginForm.password}
                      onChange={e=>setLoginForm({...loginForm, password: e.target.value})}
                      autoComplete="current-password"
                      required
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  className="group flex w-full items-center justify-center gap-2 rounded-xl bg-red-600 px-5 py-3.5 text-sm font-black text-white shadow-lg shadow-red-200 transition-all hover:-translate-y-0.5 hover:bg-red-700 hover:shadow-xl active:translate-y-0"
                >
                  Masuk ke Sistem
                  <LogIn size={18} className="transition-transform group-hover:translate-x-0.5" />
                </button>
              </form>

              <div className="my-7 flex items-center gap-4">
                <div className="h-px flex-1 bg-slate-200"></div>
                <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-400">akses terbatas</span>
                <div className="h-px flex-1 bg-slate-200"></div>
              </div>

              <button
                onClick={handleGuestLogin}
                type="button"
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-3.5 text-sm font-bold text-slate-600 transition-all hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
              >
                <Eye size={18} className="text-slate-400"/>
                Masuk sebagai Tamu (View Only)
              </button>

              <p className="mt-8 text-center text-[11px] leading-5 text-slate-400">
                Akses sistem hanya untuk pengguna yang berwenang. Aktivitas transaksi tercatat pada sistem.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row font-sans">
      {notification && <div className="fixed top-4 right-4 bg-green-600 text-white px-5 py-3 rounded-lg shadow-xl z-50 font-semibold animate-bounce flex items-center gap-2"><CheckCircle size={18}/> {notification}</div>}
      
      {/* HEADER KHUSUS MOBILE (HP) */}
      <div className="md:hidden bg-slate-900 text-white p-4 flex justify-between items-center z-40 sticky top-0 shadow-md">
        <div className="flex items-center gap-3">
          {systemConfig.logo ? (
             <div className="bg-white p-1.5 rounded w-12 h-10 flex items-center justify-center">
                <img src={systemConfig.logo} alt="logo" className="w-full h-full object-contain" />
             </div>
          ) : (
             <Package size={28} />
          )}
          <span className="font-bold text-sm truncate">{systemConfig.name}</span>
        </div>
        <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-2 bg-slate-800 rounded-lg hover:bg-slate-700 transition-colors">
          {isSidebarOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* OVERLAY GELAP UNTUK MOBILE */}
      {isSidebarOpen && (
        <div className="fixed inset-0 bg-black/60 z-40 md:hidden" onClick={() => setIsSidebarOpen(false)}></div>
      )}

      {/* SIDEBAR - PERBAIKAN: Selalu full height dengan min-h-screen */}
      <aside className={`fixed md:static inset-y-0 left-0 z-50 w-64 bg-slate-900 text-white flex flex-col transform transition-transform duration-300 ease-in-out ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"} md:translate-x-0 min-h-screen overflow-y-auto shadow-2xl md:shadow-none`}>
        
        {/* LOGO DI DESKTOP */}
        <div className="p-6 border-b border-slate-800 flex flex-col items-center justify-center gap-5 text-center hidden md:flex mt-2">
          {systemConfig.logo ? (
            <div className="bg-white p-2.5 rounded-2xl w-10/12 flex justify-center shadow-lg hover:scale-105 transition-transform duration-300">
               <img src={systemConfig.logo} alt="logo" className="h-12 w-auto object-contain" />
            </div>
          ) : (
            <Package size={36} />
          )}
          <span className="font-black text-lg leading-tight w-full break-words tracking-wide">{systemConfig.name}</span>
        </div>
        
        {/* LOGO DI MOBILE SIDEBAR */}
        <div className="md:hidden p-4 border-b border-slate-800 flex justify-between items-center">
           <span className="font-black text-lg tracking-wider text-slate-300">MENU UTAMA</span>
           <button onClick={() => setIsSidebarOpen(false)} className="text-slate-400 hover:text-white"><X size={24}/></button>
        </div>

        <nav className="p-4 flex-1 space-y-1.5 text-sm mt-2">
          <button onClick={()=>handleNavClick("dashboard")} className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors ${activeMenu==="dashboard"?"bg-red-600 shadow-md font-semibold text-white":"hover:bg-slate-800 text-slate-300"}`}><Home size={18}/> Dashboard</button>
          <button onClick={()=>handleNavClick("inventory")} className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors ${activeMenu==="inventory"?"bg-red-600 shadow-md font-semibold text-white":"hover:bg-slate-800 text-slate-300"}`}><Boxes size={18}/> Inventori Gudang</button>
          {hasAccess(["Super Admin", "Admin", "Operator"]) && <button onClick={()=>handleNavClick("operations")} className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors ${activeMenu==="operations"?"bg-red-600 shadow-md font-semibold text-white":"hover:bg-slate-800 text-slate-300"}`}><PackagePlus size={18}/> Operasi Logistik</button>}
          <button onClick={()=>handleNavClick("history")} className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors ${activeMenu==="history"?"bg-red-600 shadow-md font-semibold text-white":"hover:bg-slate-800 text-slate-300"}`}><History size={18}/> Riwayat Transaksi</button>
          {hasAccess(["Super Admin"]) && <button onClick={()=>handleNavClick("settings")} className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors ${activeMenu==="settings"?"bg-slate-700 shadow-md font-semibold text-white":"hover:bg-slate-800 text-slate-300"}`}><Settings size={18}/> Pengaturan Sistem</button>}
        </nav>
        
        <div className="px-4 py-3 bg-slate-800 mx-4 rounded-lg mb-2 text-center text-xs border border-slate-700">
          <p className="text-slate-400">Login sebagai:</p>
          <p className="font-bold text-white truncate">{currentUser.username}</p>
        </div>
        <button onClick={handleLogout} className="mx-4 mb-4 p-3 bg-slate-800 hover:bg-red-600 transition-colors rounded-lg flex justify-center items-center gap-2 text-slate-300 hover:text-white font-bold"><LogOut size={16}/> Keluar</button>
      </aside>

      <main className="flex-1 p-4 sm:p-8 overflow-y-auto w-full bg-slate-50">
        <div className="max-w-7xl mx-auto">
          
          {/* DASHBOARD */}
          {activeMenu === "dashboard" && (
            <div className="space-y-6">
              <h1 className="text-2xl sm:text-3xl font-black text-slate-800 tracking-tight">Dashboard Statistik</h1>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                <div className="bg-white p-4 sm:p-6 rounded-3xl shadow-sm border border-slate-200 h-80 sm:h-96">
                  <h3 className="font-bold mb-4 text-slate-700">Stok Berdasarkan Gudang Asal</h3>
                  <ResponsiveContainer width="100%" height="85%">
                    <BarChart data={stockByWarehouseData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false}/>
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}}/>
                      <YAxis axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}}/>
                      <Tooltip cursor={{fill: '#f1f5f9'}} contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'}}/>
                      <Legend iconType="circle"/>
                      <Bar dataKey="kg" fill="#ef4444" name="Kilogram (KG)" maxBarSize={60} radius={[4, 4, 0, 0]} />
                      <Bar dataKey="pack" fill="#3b82f6" name="Pack" maxBarSize={60} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div className="bg-white p-4 sm:p-6 rounded-3xl shadow-sm border border-slate-200 h-80 sm:h-96">
                  <h3 className="font-bold mb-4 text-slate-700">Komposisi Master SKU</h3>
                  <ResponsiveContainer width="100%" height="85%">
                    <PieChart>
                      <Pie 
                        data={compositionData} 
                        cx="50%" cy="50%" 
                        innerRadius={60} outerRadius={100} 
                        dataKey="value" 
                        paddingAngle={5}
                        stroke="none"
                      >
                        <Cell fill="#ef4444"/><Cell fill="#3b82f6"/>
                      </Pie>
                      <Tooltip contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'}}/>
                      <Legend iconType="circle"/>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {/* INVENTORY */}
          {activeMenu === "inventory" && (
            <div className="space-y-6">
              <h1 className="text-2xl sm:text-3xl font-black text-slate-800 tracking-tight">Inventori Gudang</h1>
              <div className="w-full overflow-x-auto pb-1">
                <div className="inline-flex min-w-max items-center gap-1.5 rounded-2xl border border-slate-200 bg-slate-100/80 p-1.5 shadow-inner">
                  <button
                    onClick={()=>setActiveInvTab('bulk')}
                    className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all ${activeInvTab==='bulk'?'bg-white text-red-600 shadow-md ring-1 ring-black/5':'text-slate-500 hover:bg-white/70 hover:text-slate-800'}`}
                  >
                    <Database size={17}/> Bahan Baku
                  </button>
                  <button
                    onClick={()=>setActiveInvTab('rebagged')}
                    className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all ${activeInvTab==='rebagged'?'bg-white text-red-600 shadow-md ring-1 ring-black/5':'text-slate-500 hover:bg-white/70 hover:text-slate-800'}`}
                  >
                    <Boxes size={17}/> Produk Jadi
                  </button>
                </div>
              </div>
              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-x-auto w-full">
                <table className="w-full text-sm text-left min-w-[920px]">
                  <thead className="bg-slate-50 text-slate-600">
                    <tr>
                      <th className="p-4 font-semibold whitespace-nowrap">ID SKU</th>
                      <th className="p-4 font-semibold whitespace-nowrap">Nama Barang</th>
                      <th className="p-4 font-semibold whitespace-nowrap">Gudang Asal</th>
                      {activeInvTab === 'rebagged' ? (
                        <>
                          <th className="p-4 font-semibold text-right whitespace-nowrap text-green-700">GOOD</th>
                          <th className="p-4 font-semibold text-right whitespace-nowrap text-amber-700">PROCESS</th>
                          <th className="p-4 font-semibold text-right whitespace-nowrap text-red-700">DAMAGE</th>
                          <th className="p-4 font-semibold text-right whitespace-nowrap">Total</th>
                        </>
                      ) : (
                        <th className="p-4 font-semibold text-right whitespace-nowrap">Total Stok Aktif</th>
                      )}
                      <th className="p-4 font-semibold text-center whitespace-nowrap">Dokumen</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {skus.filter(s=>s.type===activeInvTab).map(sku => {
                      const allSkuBatches = inventoryBatches.filter(b=>b.skuId===sku.id);
                      const batches = allSkuBatches.filter(b =>
                        activeInvTab === 'rebagged'
                          ? (Number(b.currentQty || 0) > 0 || Number(b.processQty || 0) > 0 || Number(b.damageQty || 0) > 0)
                          : Number(b.currentQty || 0) > 0
                      );
                      const good = batches.reduce((acc, b) => acc + Number(b.currentQty || 0), 0);
                      const process = batches.reduce((acc, b) => acc + Number(b.processQty || 0), 0);
                      const damage = batches.reduce((acc, b) => acc + Number(b.damageQty || 0), 0);
                      const total = activeInvTab === 'rebagged' ? good + process + damage : good;
                      const sources = [...new Set(batches.map(b=>b.sourceWarehouse).filter(Boolean))].join(", ") || "-";
                      return (
                        <tr key={sku.id} className="hover:bg-slate-50 transition-colors">
                          <td className="p-4 text-slate-500 font-mono">{sku.id}</td>
                          <td className="p-4 font-semibold text-slate-800">{sku.name}</td>
                          <td className="p-4 text-slate-600">{sources}</td>
                          {activeInvTab === 'rebagged' ? (
                            <>
                              <td className="p-4 text-right font-black text-green-700 text-base">{good} <span className="font-medium text-slate-400 text-xs">{sku.unit}</span></td>
                              <td className="p-4 text-right font-black text-amber-700 text-base">{process} <span className="font-medium text-slate-400 text-xs">{sku.unit}</span></td>
                              <td className="p-4 text-right font-black text-red-700 text-base">{damage} <span className="font-medium text-slate-400 text-xs">{sku.unit}</span></td>
                              <td className="p-4 text-right font-black text-slate-800 text-base">{total} <span className="font-medium text-slate-500 text-sm">{sku.unit}</span></td>
                            </>
                          ) : (
                            <td className="p-4 text-right font-black text-slate-800 text-base">{total} <span className="font-medium text-slate-500 text-sm">{sku.unit}</span></td>
                          )}
                          <td className="p-4 text-center">
                            <button
                              type="button"
                              onClick={() => handleDownloadInventoryCard(sku)}
                              className="inline-flex items-center justify-center gap-2 bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 px-3 py-2 rounded-lg font-bold text-xs whitespace-nowrap"
                              title={sku.type === "bulk" ? "Download Kartu Persediaan Bahan Baku" : "Download Kartu Persediaan Produk Jadi"}
                            >
                              <FileDown size={16}/>
                              {sku.type === "bulk" ? "Kartu Bahan Baku" : "Kartu Produk Jadi"}
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
                {skus.filter(s=>s.type===activeInvTab).length === 0 && <div className="p-8 text-center text-slate-400 italic">Belum ada data SKU di kategori ini.</div>}
              </div>
            </div>
          )}

          {/* OPERATIONS */}
          {activeMenu === "operations" && hasAccess(["Super Admin", "Admin", "Operator"]) && (
            <div className="space-y-6">
               <h1 className="text-2xl sm:text-3xl font-black text-slate-800 tracking-tight">Operasi Logistik</h1>
               <div className="bg-white p-4 sm:p-8 rounded-2xl shadow-sm border border-slate-200">
                  <div className="mb-8 overflow-x-auto pb-1">
                    <div className="inline-flex min-w-max items-center gap-1.5 rounded-2xl border border-slate-200 bg-slate-100/80 p-1.5 shadow-inner">
                      <button
                        onClick={()=>setActiveOpTab('inbound')}
                        className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all ${activeOpTab==='inbound'?'bg-blue-600 text-white shadow-lg shadow-blue-100':'text-slate-500 hover:bg-white hover:text-slate-800'}`}
                      >
                        <PackagePlus size={17}/> Inbound
                      </button>
                      <button
                        onClick={()=>setActiveOpTab('rebagging')}
                        className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all ${activeOpTab==='rebagging'?'bg-red-600 text-white shadow-lg shadow-red-100':'text-slate-500 hover:bg-white hover:text-slate-800'}`}
                      >
                        <Settings2 size={17}/> Rebagging
                      </button>
                      <button
                        onClick={()=>setActiveOpTab('outbound')}
                        className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all ${activeOpTab==='outbound'?'bg-orange-500 text-white shadow-lg shadow-orange-100':'text-slate-500 hover:bg-white hover:text-slate-800'}`}
                      >
                        <ArrowRightLeft size={17}/> Outbound
                      </button>
                    </div>
                  </div>
                  <form onSubmit={handleTransactionSubmit} className="space-y-5 max-w-3xl">
                    {isVerifiedSuperAdmin && (
                      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-3">
                        <label className="flex items-center gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={Boolean(formData.useBackdate)}
                            onChange={(e) => {
                              const enabled = e.target.checked;
                              setFormData((prev) => ({
                                ...prev,
                                useBackdate: enabled,
                                backdateDateTime: enabled
                                  ? (prev.backdateDateTime || getLocalDateTimeInput())
                                  : "",
                              }));
                            }}
                            className="w-4 h-4 accent-amber-600"
                          />
                          <div>
                            <div className="font-black text-amber-900 text-sm">Mode Backdate — Khusus Super Admin</div>
                            <div className="text-xs text-amber-700">Berlaku untuk Inbound, Rebagging, dan Outbound.</div>
                          </div>
                        </label>
                        {formData.useBackdate && (
                          <div>
                            <label className="block text-sm font-bold text-amber-900 mb-2">Tanggal & Waktu Transaksi</label>
                            <input
                              type="datetime-local"
                              max={getLocalDateTimeInput()}
                              value={formData.backdateDateTime}
                              onChange={(e) => handleBackdateDateTimeChange(e.target.value)}
                              className="w-full p-3 border border-amber-300 rounded-lg outline-none focus:border-amber-600 bg-white"
                              required
                            />
                            <p className="text-xs text-amber-700 mt-2">
                              Tanggal transaksi akan mengikuti backdate. Waktu input sebenarnya tetap disimpan untuk audit.
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                    {activeOpTab === 'inbound' && (
                      <div className="space-y-4">
                        <div className="rounded-2xl border border-blue-200 bg-blue-50/60 p-4">
                          <div className="flex items-start gap-3">
                            <PackagePlus size={20} className="mt-0.5 shrink-0 text-blue-600"/>
                            <div>
                              <h3 className="font-black text-blue-900">Inbound Multi-SKU</h3>
                              <p className="mt-1 text-xs leading-5 text-blue-700">
                                Satu penerimaan dapat berisi beberapa SKU. Setiap SKU menyimpan batch, MO, TM bahan, qty, dan gudang asalnya sendiri.
                              </p>
                            </div>
                          </div>
                        </div>

                        {inboundLines.map((line, index) => (
                          <div key={line.rowId} className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5 shadow-sm">
                            <div className="mb-4 flex items-center justify-between gap-3">
                              <div>
                                <div className="text-xs font-black uppercase tracking-[0.14em] text-blue-500">Bahan {index + 1}</div>
                                <div className="mt-1 text-sm font-bold text-slate-700">Detail bahan masuk</div>
                              </div>
                              {inboundLines.length > 1 && (
                                <button
                                  type="button"
                                  onClick={()=>removeInboundLine(line.rowId)}
                                  className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-bold text-red-600 hover:bg-red-100"
                                >
                                  <Trash2 size={15}/> Hapus
                                </button>
                              )}
                            </div>

                            <div className="space-y-4">
                              <div>
                                <label className="block text-sm font-bold text-slate-700 mb-2">SKU Bahan</label>
                                <SearchableSelect
                                  options={skus.filter(s=>s.type==='bulk').map(s=>({value:s.id,label:`${s.id} - ${s.name}`}))}
                                  value={line.skuId}
                                  onChange={v=>updateInboundLine(line.rowId,'skuId',v)}
                                  placeholder="Pilih SKU bahan..."
                                />
                              </div>

                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                  <label className="block text-sm font-bold text-slate-700 mb-2">Jumlah / Kuantitas</label>
                                  <input
                                    type="number"
                                    min="0"
                                    className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-blue-500"
                                    value={line.qty}
                                    onChange={e=>updateInboundLine(line.rowId,'qty',e.target.value)}
                                    placeholder="0"
                                    required
                                  />
                                </div>
                                <div>
                                  <label className="block text-sm font-bold text-slate-700 mb-2">Gudang Asal</label>
                                  <input
                                    type="text"
                                    className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-blue-500"
                                    value={line.sourceWarehouse}
                                    onChange={e=>updateInboundLine(line.rowId,'sourceWarehouse',e.target.value)}
                                    placeholder="Contoh: GST I / Gudang asal lain"
                                    required
                                  />
                                </div>
                              </div>

                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                  <label className="block text-sm font-bold text-slate-700 mb-2">No. MO Bahan</label>
                                  <input
                                    type="text"
                                    className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-blue-500"
                                    value={line.moNumber}
                                    onChange={e=>updateInboundLine(line.rowId,'moNumber',e.target.value)}
                                    placeholder="Nomor MO bahan ini"
                                    required
                                  />
                                </div>
                                <div>
                                  <label className="block text-sm font-bold text-slate-700 mb-2">No. TM Bahan</label>
                                  <input
                                    type="text"
                                    className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-blue-500"
                                    value={line.tmNumber}
                                    onChange={e=>updateInboundLine(line.rowId,'tmNumber',e.target.value)}
                                    placeholder="Nomor TM bahan ini"
                                    required
                                  />
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}

                        <button
                          type="button"
                          onClick={addInboundLine}
                          className="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-black text-blue-700 hover:bg-blue-100"
                        >
                          <PlusCircle size={18}/> Tambah SKU Bahan
                        </button>
                      </div>
                    )}
                    {activeOpTab === 'rebagging' && (
                      <>
                        <div>
                          <label className="block text-sm font-bold text-slate-700 mb-2">Target Produk Jadi</label>
                          <SearchableSelect
                            options={skus.filter(s=>s.type==='rebagged').map(s=>({value:s.id,label:`${s.id} - ${s.name}`}))}
                            value={formData.rebagTargetSkuId}
                            onChange={handleRebagTargetChange}
                            placeholder="Pilih SKU hasil Rebagging..."
                          />
                        </div>

                        {formData.rebagTargetSkuId && (
                          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                            <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Komposisi Bahan</div>
                            {activeRebagRecipe ? (
                              <div className="mt-2">
                                <div className="font-black text-slate-800">{activeRebagRecipe.label}</div>
                                <p className="mt-1 text-xs text-slate-500">
                                  Setiap bahan boleh berasal dari gudang, MO, dan TM yang berbeda. MO/TM mengikuti batch yang dipilih.
                                </p>
                                <div className="mt-3 flex flex-wrap gap-2">
                                  {activeRebagMaterials.map((item)=>(
                                    <span key={item.skuId} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-mono font-bold text-slate-700">
                                      {item.skuId}
                                      <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-black ${item.required ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'}`}>
                                        {item.required ? 'WAJIB' : 'OPSIONAL'}
                                      </span>
                                      {item.calculationMode === 'per_output' && (
                                        <span className="rounded-full bg-green-50 px-1.5 py-0.5 text-[9px] font-black text-green-700">
                                          AUTO 1/{item.outputPerUnit}
                                        </span>
                                      )}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            ) : (
                              <p className="mt-2 text-sm text-slate-600">Belum ada preset komposisi. Gunakan bahan tunggal/manual.</p>
                            )}
                          </div>
                        )}

                        <div>
                          <label className="block text-sm font-bold text-slate-700 mb-2">Kuantitas Hasil yang Diproses</label>
                          <input type="number" min="0" className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-red-500" value={formData.qtyToProcess} onChange={e=>setFormData({...formData,qtyToProcess:e.target.value})} placeholder="0" required/>
                          <p className="mt-1.5 text-xs text-slate-500">Jumlah ini menjadi dasar perhitungan otomatis bahan kemasan yang memakai standar isi.</p>
                        </div>

                        {activeRebagRecipe && (
                          <div className="space-y-3">
                            <h4 className="font-black text-slate-800">Pilih Batch Bahan</h4>
                            {activeRebagMaterials.map((recipeMaterial)=>{
                              const materialSkuId=recipeMaterial.skuId;
                              const materialSku=skus.find(s=>s.id===materialSkuId);
                              const selection=rebagMaterialSelections[materialSkuId]||{};
                              const batchOptions=inventoryBatches.filter(
                                b=>b.skuId===materialSkuId && Number(b.currentQty||0)>0
                              );
                              const selectedBatch=batchOptions.find(b=>b.batchId===selection.batchId);
                              const calculatedUsage=getCalculatedMaterialQty(recipeMaterial, formData.qtyToProcess);
                              const usedQty=recipeMaterial.calculationMode==='per_output'
                                ? Number(calculatedUsage||0)
                                : Number(selection.qty||0);
                              const materialDamageQty=Number(selection.damageQty||0);
                              const totalMaterialOut=usedQty+materialDamageQty;
                              return (
                                <div key={materialSkuId} className={`rounded-2xl border bg-white p-4 shadow-sm ${recipeMaterial.required ? 'border-slate-200' : 'border-blue-200'}`}>
                                  <div className="mb-3 flex items-start justify-between gap-3">
                                    <div>
                                      <div className="font-mono text-xs font-black text-red-600">{materialSkuId}</div>
                                      <div className="font-bold text-slate-800">{materialSku?.name || 'SKU belum ada di master'}</div>
                                    </div>
                                    <div className="flex flex-wrap justify-end gap-1.5">
                                      {recipeMaterial.calculationMode === 'per_output' && (
                                        <span className="rounded-full bg-green-50 px-2.5 py-1 text-[10px] font-black text-green-700">
                                          AUTO · 1/{recipeMaterial.outputPerUnit}
                                        </span>
                                      )}
                                      <span className={`rounded-full px-2.5 py-1 text-[10px] font-black ${recipeMaterial.required ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'}`}>
                                        {recipeMaterial.required ? 'WAJIB' : 'OPSIONAL'}
                                      </span>
                                    </div>
                                  </div>
                                  <div>
                                    <label className="mb-1.5 block text-xs font-bold text-slate-500">Batch / MO / TM Bahan</label>
                                    <select
                                      className="w-full p-3 border border-slate-300 rounded-lg bg-white outline-none focus:border-red-500 text-sm"
                                      value={selection.batchId||''}
                                      onChange={e=>setRebagMaterialSelections(prev=>({
                                        ...prev,
                                        [materialSkuId]: {...(prev[materialSkuId]||{}),batchId:e.target.value}
                                      }))}
                                      required={recipeMaterial.required}
                                    >
                                      <option value="">-- {recipeMaterial.required ? 'Pilih Batch Bahan' : 'Opsional / tidak digunakan'} --</option>
                                      {batchOptions.map(b=>(
                                        <option key={b.batchId} value={b.batchId}>
                                          {b.sourceWarehouse||'-'} · MO: {b.moNumber||'-'} · TM: {b.tmNumber||'-'} · Stok: {b.currentQty}
                                        </option>
                                      ))}
                                    </select>
                                  </div>

                                  <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div>
                                      <label className="mb-1.5 block text-xs font-bold text-slate-500">
                                        {recipeMaterial.calculationMode === 'per_output' ? 'Kebutuhan Standar' : 'Qty Dipakai Baik'}
                                      </label>
                                      <input
                                        type="number"
                                        min="0"
                                        max={selectedBatch?.currentQty||undefined}
                                        readOnly={recipeMaterial.calculationMode === 'per_output'}
                                        className={`w-full p-3 border rounded-lg outline-none font-bold ${recipeMaterial.calculationMode === 'per_output' ? 'border-green-200 bg-green-50 text-green-800' : 'border-slate-300 bg-white focus:border-red-500'}`}
                                        value={recipeMaterial.calculationMode === 'per_output' ? calculatedUsage : (selection.qty||'')}
                                        onChange={e=>setRebagMaterialSelections(prev=>({
                                          ...prev,
                                          [materialSkuId]: {...(prev[materialSkuId]||{}),qty:e.target.value}
                                        }))}
                                        placeholder="0"
                                        required={recipeMaterial.required}
                                        disabled={!recipeMaterial.required && !selection.batchId}
                                      />
                                      {recipeMaterial.calculationMode === 'per_output' && (
                                        <p className="mt-1 text-[10px] text-green-700">
                                          ceil({Number(formData.qtyToProcess||0)} ÷ {recipeMaterial.outputPerUnit}) = {calculatedUsage}
                                        </p>
                                      )}
                                    </div>

                                    <div>
                                      <label className="mb-1.5 block text-xs font-bold text-red-600">Qty Rusak</label>
                                      <input
                                        type="number"
                                        min="0"
                                        max={selectedBatch ? Math.max(0, Number(selectedBatch.currentQty||0)-usedQty) : undefined}
                                        className="w-full p-3 border border-red-200 rounded-lg bg-red-50/50 outline-none focus:border-red-500 font-bold text-red-700"
                                        value={selection.damageQty||''}
                                        onChange={e=>setRebagMaterialSelections(prev=>({
                                          ...prev,
                                          [materialSkuId]: {...(prev[materialSkuId]||{}),damageQty:e.target.value}
                                        }))}
                                        placeholder="0"
                                        disabled={!selection.batchId}
                                      />
                                      <p className="mt-1 text-[10px] text-slate-400">Kerusakan bahan saat proses.</p>
                                    </div>

                                    <div>
                                      <label className="mb-1.5 block text-xs font-bold text-slate-500">Total Stok Berkurang</label>
                                      <div className="flex min-h-[46px] items-center justify-between rounded-lg border border-slate-200 bg-slate-100 px-3">
                                        <span className="text-sm font-black text-slate-800">{totalMaterialOut}</span>
                                        <span className="text-xs font-bold text-slate-400">{materialSku?.unit || ''}</span>
                                      </div>
                                      <p className="mt-1 text-[10px] text-slate-400">Dipakai + rusak.</p>
                                    </div>
                                  </div>
                                  {selectedBatch && (
                                    <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                                      <div className="rounded-lg bg-blue-50 px-3 py-2 text-blue-800"><span className="font-bold">MO:</span> {selectedBatch.moNumber||'-'}</div>
                                      <div className="rounded-lg bg-violet-50 px-3 py-2 text-violet-800"><span className="font-bold">TM:</span> {selectedBatch.tmNumber||'-'}</div>
                                      <div className="rounded-lg bg-slate-100 px-3 py-2 text-slate-700"><span className="font-bold">Gudang:</span> {selectedBatch.sourceWarehouse||'-'}</div>
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}

                        {!activeRebagRecipe && (
                          <>
                            <div>
                              <label className="block text-sm font-bold text-slate-700 mb-2">Bahan Baku Utama</label>
                              <SearchableSelect
                                options={skus.filter(s=>s.type==='bulk').map(s=>({value:s.id,label:`${s.id} - ${s.name}`}))}
                                value={formData.bulkSkuId}
                                onChange={v=>{
                                  setFormData({...formData,bulkSkuId:v,bulkBatchId:''});
                                  setRebagMaterialSelections({});
                                }}
                                placeholder="Pilih bahan baku..."
                              />
                            </div>
                            {formData.bulkSkuId && (
                              <div>
                                <label className="block text-sm font-bold text-slate-700 mb-2">Batch Bahan Baku</label>
                                <SearchableSelect
                                  options={inventoryBatches
                                    .filter(b=>b.skuId===formData.bulkSkuId && Number(b.currentQty||0)>0)
                                    .map(b=>({value:b.batchId,label:`${b.sourceWarehouse||'-'} · MO: ${b.moNumber||'-'} · TM: ${b.tmNumber||'-'} · Stok: ${b.currentQty}`}))}
                                  value={formData.bulkBatchId}
                                  onChange={v=>setFormData({...formData,bulkBatchId:v})}
                                  placeholder="Pilih batch bahan..."
                                />
                              </div>
                            )}
                          </>
                        )}

                        <div className="rounded-2xl border border-green-200 bg-green-50/60 p-4">
                          <label className="block text-sm font-black text-green-900 mb-2">TM Hasil</label>
                          <input
                            type="text"
                            className="w-full p-3 border border-green-300 rounded-lg bg-white outline-none focus:border-green-600 font-bold text-green-900"
                            value={formData.rebagResultTmNumber}
                            onChange={e=>setFormData({...formData,rebagResultTmNumber:e.target.value})}
                            placeholder="Masukkan TM hasil produksi"
                            required
                          />
                          <p className="mt-2 text-xs text-green-700">TM Hasil dibuat pada proses Rebagging dan menjadi referensi utama produk jadi saat Outbound.</p>
                        </div>

                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:p-5">
                          <div className="mb-4">
                            <h4 className="font-black text-slate-800">Hasil Pemeriksaan Rebagging</h4>
                            <p className="text-xs text-slate-500 mt-1">GOOD siap outbound, PROCESS menunggu rework, DAMAGE dipisahkan.</p>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <div><label className="block text-xs font-black text-green-700 mb-2">GOOD</label><input type="number" min="0" className="w-full p-3 border border-green-200 bg-white rounded-lg outline-none focus:border-green-500 font-bold text-green-700" value={formData.rebagGoodQty} onChange={e=>setFormData({...formData,rebagGoodQty:e.target.value})} placeholder="0" required/></div>
                            <div><label className="block text-xs font-black text-amber-700 mb-2">PROCESS / REWORK</label><input type="number" min="0" className="w-full p-3 border border-amber-200 bg-white rounded-lg outline-none focus:border-amber-500 font-bold text-amber-700" value={formData.rebagProcessQty} onChange={e=>setFormData({...formData,rebagProcessQty:e.target.value})} placeholder="0" required/></div>
                            <div><label className="block text-xs font-black text-red-700 mb-2">DAMAGE</label><input type="number" min="0" className="w-full p-3 border border-red-200 bg-white rounded-lg outline-none focus:border-red-500 font-bold text-red-700" value={formData.rebagDamageQty} onChange={e=>setFormData({...formData,rebagDamageQty:e.target.value})} placeholder="0" required/></div>
                          </div>
                          <div className="mt-4 flex items-center justify-between rounded-xl bg-white border border-slate-200 px-4 py-3 text-xs">
                            <span className="font-bold text-slate-500">Total hasil</span>
                            <span className={`font-black ${Math.abs((Number(formData.rebagGoodQty||0)+Number(formData.rebagProcessQty||0)+Number(formData.rebagDamageQty||0))-Number(formData.qtyToProcess||0))<0.0001 && Number(formData.qtyToProcess||0)>0?'text-green-600':'text-red-600'}`}>
                              {Number(formData.rebagGoodQty||0)+Number(formData.rebagProcessQty||0)+Number(formData.rebagDamageQty||0)} / {Number(formData.qtyToProcess||0)}
                            </span>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-bold text-slate-700 mb-2">Tanggal Kadaluwarsa</label>
                            <input type="date" className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-red-500" value={formData.rebagExpiryDate} onChange={e=>setFormData({...formData,rebagExpiryDate:e.target.value})} required/>
                          </div>
                          <div>
                            <label className="block text-sm font-bold text-slate-700 mb-2">Tumpukan Tujuan</label>
                            <select className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-red-500 bg-white" value={formData.rebagTargetStack} onChange={e=>setFormData({...formData,rebagTargetStack:e.target.value})} required>
                              <option value="">-- Pilih Lokasi Tumpukan --</option>
                              {STACK_LOCATIONS.map(l=><option key={l} value={l}>{l}</option>)}
                            </select>
                          </div>
                        </div>
                      </>
                    )}
                    {activeOpTab === 'outbound' && (
                      <>
                        <div>
                          <label className="block text-sm font-bold text-slate-700 mb-2">Pilih Barang yang akan Dikeluarkan</label>
                          <SearchableSelect
                            options={skus.map(s=>({value:s.id,label:`${s.id} - ${s.name}`}))}
                            value={formData.outSkuId}
                            onChange={handleOutboundSkuChange}
                            placeholder="Cari SKU..."
                          />
                        </div>

                        {formData.outSkuId && outboundIsFinishedGoods && (
                          <div className="rounded-2xl border border-green-200 bg-green-50/60 p-4">
                            <label className="block text-sm font-black text-green-900 mb-2">TM Hasil Produk Jadi</label>
                            <select
                              className="w-full p-3 border border-green-300 rounded-lg bg-white outline-none focus:border-green-600 font-bold text-green-900"
                              value={formData.outTmNumber}
                              onChange={e=>handleOutboundTmChange(e.target.value)}
                              required
                            >
                              <option value="">-- Pilih TM Hasil --</option>
                              {outboundAvailableResultTms.map(tm=><option key={tm} value={tm}>{tm}</option>)}
                            </select>
                            {outboundAvailableResultTms.length===0 && (
                              <p className="mt-2 text-xs text-red-600">Belum ada stok GOOD produk jadi dengan TM Hasil.</p>
                            )}
                          </div>
                        )}

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-bold text-slate-700 mb-2">No. SO <span className="font-normal text-slate-400">(opsional)</span></label>
                            <input type="text" className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-orange-500" value={formData.outSoNumber} onChange={e=>setFormData({...formData,outSoNumber:e.target.value})} placeholder="Nomor SO"/>
                          </div>
                          <div>
                            <label className="block text-sm font-bold text-slate-700 mb-2">Nama Pelanggan <span className="font-normal text-slate-400">(opsional)</span></label>
                            <input type="text" className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-orange-500" value={formData.outCustomer} onChange={e=>setFormData({...formData,outCustomer:e.target.value})} placeholder="Nama pelanggan / tujuan"/>
                          </div>
                        </div>

                        {formData.outSkuId && (!outboundIsFinishedGoods || formData.outTmNumber) && (
                          <div className="bg-slate-50 p-4 sm:p-5 rounded-xl border border-slate-200 mt-4 space-y-4">
                            <h4 className="font-bold text-sm text-slate-700 border-b pb-2">Pilih stok GOOD yang akan dikeluarkan:</h4>
                            {inventoryBatches
                              .filter(b=>
                                b.skuId===formData.outSkuId &&
                                Number(b.currentQty||0)>0 &&
                                (!outboundIsFinishedGoods || b.resultTmNumber===formData.outTmNumber)
                              )
                              .map(b=>(
                                <div key={b.batchId} className="flex flex-col sm:flex-row justify-between sm:items-center bg-white p-3 rounded-lg border shadow-sm gap-3">
                                  <div>
                                    <p className="font-bold text-slate-800 text-sm">{b.targetStack||b.sourceWarehouse||'-'}</p>
                                    <p className="text-xs text-slate-500 font-mono mt-1">Batch: {b.batchId}</p>
                                    {outboundIsFinishedGoods ? (
                                      <>
                                        <p className="text-xs text-green-700 font-bold mt-1">TM Hasil: {b.resultTmNumber||'-'}</p>
                                        <p className="text-xs text-slate-500 mt-1">MO Sumber: {(b.sourceMoNumbers||[]).join(', ') || b.moNumber || '-'}</p>
                                        <p className="text-xs text-slate-500 mt-1">TM Bahan: {(b.sourceTmNumbers||[]).join(', ') || '-'}</p>
                                      </>
                                    ) : (
                                      <p className="text-xs text-slate-500 mt-1">MO: {b.moNumber||'-'} · TM: {b.tmNumber||'-'}</p>
                                    )}
                                    <p className="text-xs text-slate-500 mt-1">Stok GOOD: <span className="font-bold text-blue-600">{b.currentQty}</span></p>
                                  </div>
                                  <input
                                    type="number"
                                    min="0"
                                    max={b.currentQty}
                                    className="border border-slate-300 p-2.5 w-full sm:w-28 rounded-md text-center font-bold outline-none focus:border-orange-500"
                                    placeholder="0"
                                    value={outboundSelections[b.batchId]||''}
                                    onChange={e=>setOutboundSelections({...outboundSelections,[b.batchId]:e.target.value})}
                                  />
                                </div>
                              ))}
                            {inventoryBatches.filter(b=>
                              b.skuId===formData.outSkuId &&
                              Number(b.currentQty||0)>0 &&
                              (!outboundIsFinishedGoods || b.resultTmNumber===formData.outTmNumber)
                            ).length===0 && (
                              <p className="text-sm text-red-500 italic">Stok GOOD untuk pilihan ini kosong.</p>
                            )}
                          </div>
                        )}
                      </>
                    )}
                    <button className="w-full bg-red-600 text-white font-bold py-3.5 mt-6 rounded-lg hover:bg-red-700 transition-colors shadow-lg flex justify-center items-center gap-2"><CheckCircle size={20}/> Konfirmasi & Simpan Transaksi</button>
                  </form>

                  {activeOpTab === 'rebagging' && (
                    <div className="mt-10 max-w-3xl border-t border-slate-200 pt-8">
                      <div className="flex items-start gap-3 mb-5">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-700 shrink-0">
                          <Settings2 size={20}/>
                        </div>
                        <div>
                          <h3 className="font-black text-lg text-slate-800">Tindak Lanjut Barang PROCESS</h3>
                          <p className="text-sm text-slate-500 mt-1">Setelah rework dan pemeriksaan ulang, pindahkan PROCESS menjadi GOOD. Jika tidak layak, pindahkan menjadi DAMAGE.</p>
                        </div>
                      </div>

                      <form onSubmit={handleProcessResolutionSubmit} className="rounded-2xl border border-amber-200 bg-amber-50/50 p-4 sm:p-5 space-y-4">
                        {inventoryBatches.filter(b => Number(b.processQty || 0) > 0).length > 0 ? (
                          <>
                            <div>
                              <label className="block text-sm font-bold text-slate-700 mb-2">Batch dengan stok PROCESS</label>
                              <select
                                className="w-full p-3 border border-amber-200 rounded-lg bg-white outline-none focus:border-amber-500"
                                value={processResolution.batchId}
                                onChange={e=>setProcessResolution({...processResolution, batchId:e.target.value, qty:""})}
                                required
                              >
                                <option value="">-- Pilih Batch PROCESS --</option>
                                {inventoryBatches
                                  .filter(b => Number(b.processQty || 0) > 0)
                                  .map(b => {
                                    const sku = skus.find(s => s.id === b.skuId);
                                    return (
                                      <option key={b.batchId} value={b.batchId}>
                                        {b.batchId} - {sku?.name || b.skuId} (PROCESS: {b.processQty})
                                      </option>
                                    );
                                  })}
                              </select>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                              <div>
                                <label className="block text-sm font-bold text-slate-700 mb-2">Jumlah Diproses Ulang</label>
                                <input
                                  type="number"
                                  min="0"
                                  max={inventoryBatches.find(b=>b.batchId===processResolution.batchId)?.processQty || undefined}
                                  className="w-full p-3 border border-amber-200 rounded-lg bg-white outline-none focus:border-amber-500"
                                  value={processResolution.qty}
                                  onChange={e=>setProcessResolution({...processResolution, qty:e.target.value})}
                                  placeholder="0"
                                  required
                                />
                              </div>
                              <div>
                                <label className="block text-sm font-bold text-slate-700 mb-2">Hasil Pemeriksaan Ulang</label>
                                <select
                                  className="w-full p-3 border border-amber-200 rounded-lg bg-white outline-none focus:border-amber-500 font-bold"
                                  value={processResolution.outcome}
                                  onChange={e=>setProcessResolution({...processResolution, outcome:e.target.value})}
                                >
                                  <option value="GOOD">GOOD — Lolos, masuk stok siap outbound</option>
                                  <option value="DAMAGE">DAMAGE — Tidak layak, pisahkan dari stok normal</option>
                                </select>
                              </div>
                            </div>

                            <button type="submit" className="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-black px-5 py-3 shadow-md">
                              <CheckCircle size={18}/> Simpan Tindak Lanjut PROCESS
                            </button>
                          </>
                        ) : (
                          <div className="rounded-xl border border-green-200 bg-green-50 p-4 text-sm font-semibold text-green-700">
                            Tidak ada stok PROCESS yang menunggu tindak lanjut.
                          </div>
                        )}
                      </form>
                    </div>
                  )}
               </div>
            </div>
          )}

          {/* HISTORY */}
          {activeMenu === "history" && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end border-b border-slate-200 pb-4 gap-4">
                <h1 className="text-2xl sm:text-3xl font-black text-slate-800 tracking-tight">Riwayat Transaksi</h1>
                <div className="flex flex-wrap gap-2 sm:gap-3 items-center w-full sm:w-auto">
                  <input type="date" className="border border-slate-300 p-2 rounded-lg text-xs sm:text-sm outline-none focus:border-red-500 text-slate-600 font-medium flex-1 sm:flex-none" value={historyStartDate} onChange={e=>setHistoryStartDate(e.target.value)} />
                  <span className="text-slate-400 font-medium text-xs sm:text-sm">s.d</span>
                  <input type="date" className="border border-slate-300 p-2 rounded-lg text-xs sm:text-sm outline-none focus:border-red-500 text-slate-600 font-medium flex-1 sm:flex-none" value={historyEndDate} onChange={e=>setHistoryEndDate(e.target.value)} />
                  <button onClick={handleDownloadHistory} className="bg-green-600 hover:bg-green-700 transition-colors text-white px-3 sm:px-5 py-2 sm:py-2.5 rounded-lg flex items-center justify-center gap-2 font-bold shadow-md w-full sm:w-auto text-sm"><Download size={18}/> Export .xlsx</button>
                </div>
              </div>
              
              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-x-auto w-full">
                <table className="w-full text-sm text-left min-w-[820px]">
                  <thead className="bg-slate-50 text-slate-600">
                    <tr>
                      <th className="p-4 font-bold whitespace-nowrap">Tanggal & Waktu</th>
                      <th className="p-4 font-bold text-center whitespace-nowrap">Jenis Operasi</th>
                      <th className="p-4 font-bold whitespace-nowrap">Nama Barang Terlibat</th>
                      <th className="p-4 font-bold text-center whitespace-nowrap">Mutasi (Qty)</th>
                      <th className="p-4 font-bold whitespace-nowrap">Petugas</th>
                      <th className="p-4 font-bold text-center whitespace-nowrap">Dokumen</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {transactions.map(t => (
                      <tr key={t.id} className="hover:bg-slate-50 transition-colors">
                        <td className="p-4 text-slate-600 font-medium whitespace-nowrap">
                          <div>{new Date(t.date).toLocaleString('id-ID')}</div>
                          {t.isBackdated && (
                            <div
                              className="inline-flex mt-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-[10px] font-black tracking-wide"
                              title={t.recordedAt ? `Diinput: ${new Date(t.recordedAt).toLocaleString('id-ID')} oleh ${t.backdatedBy || t.operator}` : "Transaksi backdate"}
                            >
                              BACKDATE
                            </div>
                          )}
                        </td>
                        <td className="p-4 text-center">
                          <span className={`px-4 py-1.5 rounded-full text-xs font-black tracking-widest whitespace-nowrap ${t.type === 'INBOUND' ? 'bg-blue-100 text-blue-700' : t.type === 'OUTBOUND' ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'}`}>
                            {t.type}
                          </span>
                        </td>
                        <td className="p-4 font-bold text-slate-800 min-w-[200px]">{t.skuName} <br/><span className="text-xs font-normal text-slate-500">{t.skuId}</span></td>
                        <td className="p-4 text-center font-black whitespace-nowrap">
                          {t.type === 'PROCESS_TO_DAMAGE' ? (
                            <div>
                              <div className="text-red-600">PROCESS → DAMAGE</div>
                              <div className="text-xs text-slate-500 mt-1">{t.resolutionQty} {t.unit}</div>
                            </div>
                          ) : t.type === 'PROCESS_TO_GOOD' ? (
                            <div>
                              <div className="text-green-600">PROCESS → GOOD</div>
                              <div className="text-xs text-slate-500 mt-1">+{t.resolutionQty} {t.unit}</div>
                            </div>
                          ) : t.type === 'REBAGGING' ? (
                            <div>
                              <div className="text-green-600 text-lg">+{t.goodQty ?? t.qtyChange}</div>
                              <div className="text-[10px] text-slate-500 mt-1">
                                G:{t.goodQty ?? t.qtyChange} · P:{t.processQty ?? 0} · D:{t.damageQty ?? 0}
                              </div>
                              {Number(t.materialDamageTotal || 0) > 0 && (
                                <div className="mt-1 text-[10px] font-bold text-red-500">
                                  Bahan rusak: {t.materialDamageTotal}
                                </div>
                              )}
                            </div>
                          ) : (
                            <span className={`text-lg ${t.type==='OUTBOUND' ? 'text-red-600' : 'text-green-600'}`}>
                              {t.type === 'OUTBOUND' ? '-' : '+'}{t.qtyChange}
                            </span>
                          )}
                        </td>
                        <td className="p-4 text-slate-600 capitalize font-medium whitespace-nowrap">{t.operator}</td>
                        <td className="p-4 text-center whitespace-nowrap">
                          {t.type === "REBAGGING" ? (
                            <button
                              type="button"
                              onClick={() => handleDownloadRebaggingPdf(t)}
                              className="inline-flex items-center gap-2 bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 px-3 py-2 rounded-lg font-bold text-xs"
                              title="Download Catatan Proses Rebagging Batch"
                            >
                              <FileDown size={16}/> PDF Batch
                            </button>
                          ) : (
                            <span className="text-slate-300">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {transactions.length === 0 && <div className="text-center text-slate-400 p-8 italic">Belum ada riwayat transaksi yang tercatat.</div>}
              </div>
            </div>
          )}

          {/* SETTINGS */}
          {activeMenu === "settings" && hasAccess(["Super Admin"]) && (
            <div className="space-y-6">
              <h1 className="text-2xl sm:text-3xl font-black text-slate-800 tracking-tight">Pengaturan Super Admin</h1>
              
              <div className="overflow-x-auto pb-1">
                <div className="inline-flex min-w-max items-center gap-1.5 rounded-2xl border border-slate-200 bg-slate-100/80 p-1.5 shadow-inner">
                  <button
                    onClick={()=>setActiveTabSettings('system')}
                    className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all ${activeTabSettings==='system'?'bg-slate-900 text-white shadow-lg':'text-slate-500 hover:bg-white hover:text-slate-800'}`}
                  >
                    <Settings2 size={17}/> Profil Sistem
                  </button>
                  <button
                    onClick={()=>setActiveTabSettings('sku')}
                    className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all ${activeTabSettings==='sku'?'bg-slate-900 text-white shadow-lg':'text-slate-500 hover:bg-white hover:text-slate-800'}`}
                  >
                    <Database size={17}/> Database SKU
                  </button>
                  <button
                    onClick={()=>setActiveTabSettings('recipes')}
                    className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all ${activeTabSettings==='recipes'?'bg-slate-900 text-white shadow-lg':'text-slate-500 hover:bg-white hover:text-slate-800'}`}
                  >
                    <Boxes size={17}/> Komposisi Rebagging
                  </button>
                  <button
                    onClick={()=>setActiveTabSettings('users')}
                    className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all ${activeTabSettings==='users'?'bg-slate-900 text-white shadow-lg':'text-slate-500 hover:bg-white hover:text-slate-800'}`}
                  >
                    <Users size={17}/> Pengguna
                  </button>
                  {isVerifiedSuperAdmin && (
                    <button
                      onClick={()=>setActiveTabSettings('reset-data')}
                      className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-all ${activeTabSettings==='reset-data'?'bg-red-600 text-white shadow-lg shadow-red-100':'text-red-600 hover:bg-red-50'}`}
                    >
                      <Trash2 size={17}/> Reset Data
                    </button>
                  )}
                </div>
              </div>
              
              {activeTabSettings === 'system' && (
                <form onSubmit={handleUpdateConfig} className="bg-white p-4 sm:p-8 rounded-2xl shadow-sm border border-slate-200 max-w-xl space-y-6">
                  <div><label className="block font-bold text-slate-700 mb-2">Nama Aplikasi</label><input className="w-full border border-slate-300 p-3 rounded-lg outline-none focus:border-red-500" value={systemConfig.name} onChange={e=>setSystemConfig({...systemConfig, name: e.target.value})} /></div>
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">URL Logo (Opsional)</label>
                    <p className="text-xs text-slate-500 mb-3">Biarkan kosong jika ingin menggunakan ikon kotak default.</p>
                    <input className="w-full border border-slate-300 p-3 rounded-lg outline-none focus:border-red-500" value={systemConfig.logo || ""} onChange={e=>setSystemConfig({...systemConfig, logo: e.target.value})} placeholder="Contoh: /logo.png" />
                  </div>
                  <button className="w-full sm:w-auto bg-slate-800 text-white font-bold px-6 py-3 rounded-lg hover:bg-slate-900 shadow-md">Simpan Perubahan Sistem</button>
                </form>
              )}
              
              {activeTabSettings === 'sku' && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8 items-start">
                  <form onSubmit={handleAddManualSku} className="bg-white p-4 sm:p-6 rounded-2xl shadow-sm border border-slate-200 space-y-5">
                    <div className="border-b border-slate-100 pb-3 mb-2 flex items-center gap-2 text-slate-800">
                      <PlusCircle size={20} className="text-red-600"/>
                      <h3 className="font-black text-lg">Tambah SKU Manual</h3>
                    </div>
                    <div><label className="block text-sm font-bold mb-2 text-slate-700">Kode / ID Barang</label><input className="w-full border border-slate-300 p-2.5 rounded-lg outline-none focus:border-red-500" value={newSku.id} onChange={e=>setNewSku({...newSku, id: e.target.value})} required placeholder="Contoh: B-001" /></div>
                    <div><label className="block text-sm font-bold mb-2 text-slate-700">Nama Lengkap Barang</label><input className="w-full border border-slate-300 p-2.5 rounded-lg outline-none focus:border-red-500" value={newSku.name} onChange={e=>setNewSku({...newSku, name: e.target.value})} required placeholder="Contoh: Beras Medium..." /></div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-bold mb-2 text-slate-700">Tipe Kategori</label>
                        <select className="w-full border border-slate-300 p-2.5 rounded-lg outline-none focus:border-red-500 bg-white" value={newSku.type} onChange={e=>setNewSku({...newSku, type: e.target.value})}>
                          <option value="bulk">Bahan Baku (Curah)</option>
                          <option value="rebagged">Barang Jadi (Kemasan)</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-bold mb-2 text-slate-700">Satuan Hitung</label>
                        <select className="w-full border border-slate-300 p-2.5 rounded-lg outline-none focus:border-red-500 bg-white" value={newSku.unit} onChange={e=>setNewSku({...newSku, unit: e.target.value})}>
                          <option value="KG">Kilogram (KG)</option>
                          <option value="Pack">Kemasan (Pack)</option>
                        </select>
                      </div>
                    </div>
                    <button type="submit" className="w-full bg-slate-800 text-white font-bold py-3 rounded-lg hover:bg-slate-900 transition-colors shadow-md mt-2">Simpan SKU Baru</button>
                  </form>

                  <div className="bg-white p-6 sm:p-8 h-full rounded-2xl shadow-sm text-center border-dashed border-2 border-slate-300 hover:border-green-500 transition-colors flex flex-col justify-center items-center">
                    <FileSpreadsheet className="w-16 h-16 text-green-600 mb-4" />
                    <h3 className="font-black text-xl mb-2 text-slate-800">Upload Massal (.xlsx)</h3>
                    <p className="text-slate-500 mb-8 text-sm">Gunakan fitur ini jika ingin memasukkan puluhan atau ratusan data SKU sekaligus via Excel.</p>
                    <label className="cursor-pointer w-full sm:w-auto bg-green-50 text-green-700 hover:bg-green-100 font-bold py-3 px-6 rounded-xl sm:rounded-full transition-colors border border-green-200">
                      Pilih File Excel Anda
                      <input type="file" accept=".xlsx, .xls" onChange={handleImportExcel} className="hidden" />
                    </label>
                  </div>
                </div>
              )}

              {activeTabSettings === 'recipes' && isVerifiedSuperAdmin && (
                <div className="grid grid-cols-1 xl:grid-cols-[0.95fr_1.35fr] gap-6 items-start">
                  <form onSubmit={handleSaveRecipe} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 sm:p-6 space-y-5">
                    <div className="flex items-start justify-between gap-3 border-b border-slate-100 pb-4">
                      <div>
                        <div className="text-xs font-black uppercase tracking-[0.14em] text-red-500">Master Produksi</div>
                        <h3 className="mt-1 text-xl font-black text-slate-900">
                          {editingRecipeId ? "Edit Komposisi" : "Tambah Komposisi"}
                        </h3>
                        <p className="mt-1 text-xs leading-5 text-slate-500">
                          Operator akan membaca komposisi aktif ini secara otomatis pada proses Rebagging.
                        </p>
                      </div>
                      {editingRecipeId && (
                        <button
                          type="button"
                          onClick={resetRecipeForm}
                          className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-500 hover:bg-slate-50"
                        >
                          Batal Edit
                        </button>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-bold text-slate-700 mb-2">SKU Produk Jadi</label>
                      <SearchableSelect
                        options={skus.filter(s=>s.type==='rebagged').map(s=>({value:s.id,label:`${s.id} - ${s.name}`}))}
                        value={recipeForm.targetSku}
                        onChange={v=>{
                          const product=skus.find(s=>s.id===v);
                          setRecipeForm(prev=>({
                            ...prev,
                            targetSku:v,
                            label:prev.label || product?.name || ""
                          }));
                        }}
                        placeholder="Pilih produk jadi..."
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-bold text-slate-700 mb-2">Nama Komposisi</label>
                      <input
                        type="text"
                        className="w-full border border-slate-300 p-3 rounded-lg outline-none focus:border-red-500"
                        value={recipeForm.label}
                        onChange={e=>setRecipeForm({...recipeForm,label:e.target.value})}
                        placeholder="Contoh: Fortivit 1 Kg"
                        required
                      />
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <label className="block text-sm font-black text-slate-800">Daftar Bahan</label>
                          <p className="text-xs text-slate-500 mt-1">Urutan di bawah ini menjadi urutan bahan pada form operator.</p>
                        </div>
                        <button
                          type="button"
                          onClick={addRecipeMaterialLine}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-xs font-bold text-white hover:bg-black"
                        >
                          <PlusCircle size={15}/> Tambah
                        </button>
                      </div>

                      {recipeForm.materials.map((item,index)=>(
                        <div key={item.rowId} className="rounded-xl border border-slate-200 bg-slate-50 p-3 space-y-3">
                          <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto_auto] gap-3 items-end">
                            <div>
                              <label className="block text-xs font-bold text-slate-500 mb-1.5">Bahan {index+1}</label>
                              <SearchableSelect
                                options={skus.filter(s=>s.type==='bulk').map(s=>({value:s.id,label:`${s.id} - ${s.name}`}))}
                                value={item.skuId}
                                onChange={v=>updateRecipeMaterialLine(item.rowId,'skuId',v)}
                                placeholder="Pilih SKU bahan..."
                              />
                            </div>
                            <label className="flex h-[46px] items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={item.required !== false}
                                onChange={e=>updateRecipeMaterialLine(item.rowId,'required',e.target.checked)}
                                className="h-4 w-4 accent-red-600"
                              />
                              Wajib
                            </label>
                            <button
                              type="button"
                              onClick={()=>removeRecipeMaterialLine(item.rowId)}
                              className="flex h-[46px] items-center justify-center rounded-lg border border-red-200 bg-red-50 px-3 text-red-600 hover:bg-red-100"
                              title="Hapus bahan"
                            >
                              <Trash2 size={17}/>
                            </button>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <div>
                              <label className="block text-xs font-bold text-slate-500 mb-1.5">Perhitungan Pemakaian</label>
                              <select
                                className="w-full border border-slate-300 bg-white p-2.5 rounded-lg outline-none focus:border-red-500 text-sm"
                                value={item.calculationMode || 'manual'}
                                onChange={e=>{
                                  updateRecipeMaterialLine(item.rowId,'calculationMode',e.target.value);
                                  if(e.target.value==='manual') updateRecipeMaterialLine(item.rowId,'outputPerUnit','');
                                }}
                              >
                                <option value="manual">Manual — Operator isi Qty</option>
                                <option value="per_output">Otomatis — Berdasarkan Qty Hasil</option>
                              </select>
                            </div>

                            {item.calculationMode === 'per_output' ? (
                              <div>
                                <label className="block text-xs font-bold text-green-700 mb-1.5">Isi Produk per 1 Bahan</label>
                                <input
                                  type="number"
                                  min="1"
                                  className="w-full border border-green-300 bg-green-50 p-2.5 rounded-lg outline-none focus:border-green-600 font-bold text-green-800"
                                  value={item.outputPerUnit || ''}
                                  onChange={e=>updateRecipeMaterialLine(item.rowId,'outputPerUnit',e.target.value)}
                                  placeholder="Contoh: 24"
                                  required
                                />
                                <div className="mt-2 flex flex-wrap gap-1.5">
                                  <button type="button" onClick={()=>updateRecipeMaterialLine(item.rowId,'outputPerUnit','24')} className="rounded-md bg-white border border-green-200 px-2 py-1 text-[10px] font-bold text-green-700">24 · Gula 1 kg</button>
                                  <button type="button" onClick={()=>updateRecipeMaterialLine(item.rowId,'outputPerUnit','20')} className="rounded-md bg-white border border-green-200 px-2 py-1 text-[10px] font-bold text-green-700">20 · Fortivit 1 kg</button>
                                </div>
                              </div>
                            ) : (
                              <div className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-xs leading-5 text-slate-500">
                                Operator mengisi pemakaian aktual. Qty rusak tetap dicatat terpisah saat Rebagging.
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    <div>
                      <label className="block text-sm font-bold text-slate-700 mb-2">Catatan <span className="font-normal text-slate-400">(opsional)</span></label>
                      <textarea
                        className="w-full min-h-24 border border-slate-300 p-3 rounded-lg outline-none focus:border-red-500 resize-y"
                        value={recipeForm.notes}
                        onChange={e=>setRecipeForm({...recipeForm,notes:e.target.value})}
                        placeholder="Catatan penggunaan komposisi..."
                      />
                    </div>

                    <label className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4 cursor-pointer">
                      <div>
                        <div className="text-sm font-black text-slate-800">Status Komposisi</div>
                        <div className="text-xs text-slate-500 mt-1">Hanya komposisi aktif yang digunakan Operator.</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={recipeForm.active !== false}
                          onChange={e=>setRecipeForm({...recipeForm,active:e.target.checked})}
                          className="h-5 w-5 accent-green-600"
                        />
                        <span className={`text-xs font-black ${recipeForm.active !== false ? 'text-green-600' : 'text-slate-400'}`}>
                          {recipeForm.active !== false ? "AKTIF" : "NONAKTIF"}
                        </span>
                      </div>
                    </label>

                    <button
                      type="submit"
                      className="w-full rounded-xl bg-red-600 py-3.5 text-sm font-black text-white shadow-lg shadow-red-100 hover:bg-red-700"
                    >
                      {editingRecipeId ? "Simpan Perubahan Komposisi" : "Simpan Komposisi Baru"}
                    </button>
                  </form>

                  <div className="space-y-4">
                    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div>
                          <h3 className="text-xl font-black text-slate-900">Daftar Komposisi</h3>
                          <p className="mt-1 text-sm text-slate-500">{rebagRecipes.length} komposisi tersimpan di Firestore.</p>
                        </div>
                        <div className="rounded-xl bg-green-50 px-4 py-2 text-xs font-black text-green-700">
                          {rebagRecipes.filter(r=>r.active!==false).length} AKTIF
                        </div>
                      </div>
                    </div>

                    {rebagRecipes.map(recipe=>{
                      const product=skus.find(s=>s.id===recipe.targetSku);
                      const materials=normalizeRecipeMaterials(recipe);
                      return (
                        <div key={recipe.id} className={`rounded-2xl border bg-white p-5 shadow-sm ${recipe.active!==false?'border-slate-200':'border-slate-200 opacity-70'}`}>
                          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <h4 className="text-lg font-black text-slate-900">{recipe.label}</h4>
                                <span className={`rounded-full px-2.5 py-1 text-[10px] font-black ${recipe.active!==false?'bg-green-50 text-green-700':'bg-slate-100 text-slate-500'}`}>
                                  {recipe.active!==false?'AKTIF':'NONAKTIF'}
                                </span>
                              </div>
                              <p className="mt-1 text-sm font-mono text-slate-500">
                                {recipe.targetSku || (recipe.matchName ? `Deteksi nama: ${recipe.matchName}` : "Belum memilih produk jadi")}
                              </p>
                              <p className="mt-1 text-sm text-slate-600">{product?.name || (recipe.targetSku ? "SKU produk jadi belum ada di master" : "")}</p>
                            </div>
                            <div className="flex gap-2">
                              <button
                                type="button"
                                onClick={()=>handleEditRecipe(recipe)}
                                className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-bold text-blue-700 hover:bg-blue-100"
                              >
                                Edit
                              </button>
                              <button
                                type="button"
                                onClick={()=>handleDeleteRecipe(recipe)}
                                className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-bold text-red-600 hover:bg-red-100"
                              >
                                Hapus
                              </button>
                            </div>
                          </div>

                          <div className="mt-4 flex flex-wrap gap-2">
                            {materials.map(item=>{
                              const materialSku=skus.find(s=>s.id===item.skuId);
                              return (
                                <div key={item.skuId} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
                                  <div className="flex items-center gap-2">
                                    <span className="font-mono text-xs font-black text-slate-700">{item.skuId}</span>
                                    <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-black ${item.required?'bg-red-100 text-red-600':'bg-blue-100 text-blue-600'}`}>
                                      {item.required?'WAJIB':'OPSIONAL'}
                                    </span>
                                    {item.calculationMode === 'per_output' && (
                                      <span className="rounded-full bg-green-100 px-1.5 py-0.5 text-[9px] font-black text-green-700">
                                        AUTO 1/{item.outputPerUnit}
                                      </span>
                                    )}
                                  </div>
                                  <div className="mt-1 max-w-56 truncate text-[11px] text-slate-500">{materialSku?.name || "SKU belum ada di master"}</div>
                                </div>
                              );
                            })}
                          </div>

                          {recipe.notes && (
                            <div className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-800">{recipe.notes}</div>
                          )}
                        </div>
                      );
                    })}

                    {rebagRecipes.length===0 && (
                      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
                        Belum ada Master Komposisi.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeTabSettings === 'reset-data' && isVerifiedSuperAdmin && (
                <div className="max-w-2xl">
                  <div className="overflow-hidden rounded-2xl border border-red-200 bg-white shadow-sm">
                    <div className="border-b border-red-100 bg-gradient-to-r from-red-50 to-white p-5 sm:p-6">
                      <div className="flex items-start gap-4">
                        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-red-100 text-red-600">
                          <Trash2 size={22}/>
                        </div>
                        <div>
                          <div className="text-xs font-black uppercase tracking-[0.16em] text-red-500">Zona Berbahaya</div>
                          <h3 className="mt-1 text-xl font-black text-slate-900">Reset Riwayat Transaksi</h3>
                          <p className="mt-2 text-sm leading-6 text-slate-600">
                            Fitur ini hanya menghapus data pada riwayat transaksi Inbound, Rebagging, dan Outbound.
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="p-5 sm:p-6 space-y-5">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Akan Dihapus</p>
                          <p className="mt-2 text-lg font-black text-red-600">{transactions.length} transaksi</p>
                          <p className="mt-1 text-xs text-slate-500">Seluruh riwayat transaksi yang tersimpan.</p>
                        </div>
                        <div className="rounded-xl border border-green-200 bg-green-50 p-4">
                          <p className="text-xs font-bold uppercase tracking-wider text-green-600">Tetap Dipertahankan</p>
                          <p className="mt-2 text-sm font-black text-green-800">Stok & Batch Inventori</p>
                          <p className="mt-1 text-xs text-green-700">Master SKU, pengguna, dan konfigurasi juga tidak dihapus.</p>
                        </div>
                      </div>

                      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
                        <strong>Perhatian:</strong> setelah riwayat dihapus, kartu persediaan masih dapat dibuat dari stok aktif, tetapi detail pergerakan transaksi lama tidak lagi tersedia.
                      </div>

                      <button
                        type="button"
                        onClick={handleResetTransactionHistory}
                        disabled={resetHistoryLoading || transactions.length === 0}
                        className="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-xl bg-red-600 px-5 py-3 text-sm font-black text-white shadow-lg shadow-red-100 transition-all hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:shadow-none"
                      >
                        <Trash2 size={18}/>
                        {resetHistoryLoading ? "Menghapus Riwayat..." : transactions.length === 0 ? "Riwayat Sudah Kosong" : "Reset Seluruh Riwayat Transaksi"}
                      </button>

                      <p className="text-xs leading-5 text-slate-400">
                        Sistem akan meminta konfirmasi dua tahap sebelum proses penghapusan dijalankan.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {activeTabSettings === 'users' && (
                <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 xl:gap-8 items-start">
                  <form onSubmit={handleAddUser} className="bg-white p-4 sm:p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4 xl:col-span-1">
                    <div className="border-b border-slate-100 pb-3 mb-2 flex items-center gap-2 text-slate-800">
                      <UserPlus size={20} className="text-blue-600"/>
                      <h3 className="font-black text-lg">Tambah Pengguna</h3>
                    </div>
                    <div><label className="block text-sm font-bold mb-2 text-slate-700">Username</label><input className="w-full border border-slate-300 p-2.5 rounded-lg outline-none focus:border-blue-500" value={newUserForm.username} onChange={e=>setNewUserForm({...newUserForm, username: e.target.value})} required placeholder="Contoh: operator1" /></div>
                    <div><label className="block text-sm font-bold mb-2 text-slate-700">Password</label><input type="password" className="w-full border border-slate-300 p-2.5 rounded-lg outline-none focus:border-blue-500" value={newUserForm.password} onChange={e=>setNewUserForm({...newUserForm, password: e.target.value})} required placeholder="***" /></div>
                    <div>
                      <label className="block text-sm font-bold mb-2 text-slate-700">Hak Akses (Role)</label>
                      <select className="w-full border border-slate-300 p-2.5 rounded-lg outline-none focus:border-blue-500 bg-white" value={newUserForm.role} onChange={e=>setNewUserForm({...newUserForm, role: e.target.value})}>
                        <option value="Super Admin">Super Admin</option>
                        <option value="Admin">Admin</option>
                        <option value="Operator">Operator</option>
                        <option value="Viewer">View Only (Tamu)</option>
                      </select>
                    </div>
                    <button type="submit" className="w-full bg-blue-600 text-white font-bold py-3 rounded-lg hover:bg-blue-700 transition-colors shadow-md mt-2">Daftarkan Akun</button>
                  </form>

                  <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-x-auto w-full xl:col-span-2">
                    <table className="w-full text-sm text-left min-w-[500px]">
                      <thead className="bg-slate-50 text-slate-600">
                        <tr><th className="p-4 font-bold whitespace-nowrap">Username</th><th className="p-4 font-bold whitespace-nowrap">Role Akses</th><th className="p-4 font-bold text-center whitespace-nowrap">Aksi</th></tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {users.map(user => (
                          <tr key={user.username} className="hover:bg-slate-50 transition-colors">
                            <td className="p-4 font-bold text-slate-800">{user.username}</td>
                            <td className="p-4">
                              <span className={`px-3 py-1 rounded-full text-xs font-bold border whitespace-nowrap ${user.role === 'Viewer' ? 'bg-purple-100 text-purple-700 border-purple-200' : 'bg-slate-100 text-slate-600 border-slate-200'}`}>
                                {user.role}
                              </span>
                            </td>
                            <td className="p-4 text-center">
                              <button onClick={()=>handleDeleteUser(user.username)} className="text-red-500 hover:bg-red-50 p-2 rounded-lg transition-colors" title="Hapus User">
                                <Trash2 size={18} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
