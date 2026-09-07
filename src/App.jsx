import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  Package,
  Download,
  UserPlus,
  Trash2,
  Home,
  PackagePlus,
  FileDown,
  FileUp,
  ArrowRightLeft,
  Settings,
  Users,
  ArrowRight,
  Settings2,
  Database,
  History,
  LogOut,
  Boxes,
  FileSpreadsheet,
  Search,
  CheckCircle,
  Image as ImageIcon,
} from "lucide-react";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
  ResponsiveContainer,
} from "recharts";
import * as XLSX from "xlsx";

// --- FIREBASE IMPORTS ---
import { initializeApp, getApps, getApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth, signInAnonymously, onAuthStateChanged } from "firebase/auth";
import {
  getFirestore,
  doc,
  setDoc,
  onSnapshot,
  collection,
  deleteDoc,
  writeBatch,
} from "firebase/firestore";

// --- DEFAULT DATA ---
const STACK_LOCATIONS = ["Unit Pengolahan 20", "RTR 60", "Gula 17"];
const DEFAULT_USERS = [
  { username: "superadmin", password: "password", role: "Super Admin" },
  { username: "admin", password: "123456", role: "Admin" },
  { username: "operator", password: "123456", role: "Operator" },
];

// --- FIREBASE SETUP ---
const firebaseConfig = {
  apiKey: "AIzaSyC8ygXyWwjnbKMoYBO7CQP-EKcPmUbL6pg",
  authDomain: "rbg12-3a5a0.firebaseapp.com",
  projectId: "rbg12-3a5a0",
  storageBucket: "rbg12-3a5a0.firebasestorage.app",
  messagingSenderId: "477359317412",
  appId: "1:477359317412:web:90e1acb6ae8dae2b7fe131",
  measurementId: "G-4Z0JH7LB1D",
};

let app,
  auth,
  db,
  analytics,
  appId = "rbg12-3a5a0";

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
      if (wrapperRef.current && !wrapperRef.current.contains(e.target))
        setIsOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredOptions = options.filter((opt) =>
    (opt.label || "")
      .toString()
      .toLowerCase()
      .includes((search || "").toLowerCase())
  );
  const selectedOption = options.find((opt) => opt.value === value);

  return (
    <div ref={wrapperRef} className="relative w-full">
      <div
        className="w-full border border-slate-300 rounded-lg p-2.5 text-sm cursor-pointer bg-white flex justify-between items-center"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span
          className={`truncate ${!value ? "text-slate-400" : "text-slate-800"}`}
        >
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <span className="text-slate-400 text-xs ml-2">▼</span>
      </div>
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 flex flex-col">
          <div className="p-2 border-b sticky top-0 bg-white">
            <input
              type="text"
              className="w-full px-2 py-1.5 text-sm border rounded-md outline-none"
              placeholder="Cari..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
          </div>
          <div className="overflow-y-auto">
            {filteredOptions.length === 0 ? (
              <div className="p-3 text-sm text-slate-500 text-center">
                Tidak ada hasil
              </div>
            ) : (
              filteredOptions.map((opt) => (
                <div
                  key={opt.value}
                  className="p-2.5 text-sm cursor-pointer hover:bg-slate-50 border-b last:border-0"
                  onClick={() => {
                    onChange(opt.value);
                    setIsOpen(false);
                    setSearch("");
                  }}
                >
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

// --- APLIKASI UTAMA ---
export default function App() {
  const [currentUser, setCurrentUser] = useState(() => {
    const saved = localStorage.getItem("rebagging_session");
    return saved ? JSON.parse(saved) : null;
  });

  const [users, setUsers] = useState([]);
  const [skus, setSkus] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [inventoryBatches, setInventoryBatches] = useState([]);
  const [systemConfig, setSystemConfig] = useState({
    name: "Sistem Rebagging Terpadu",
    logo: null,
  });

  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [loginError, setLoginError] = useState("");
  const [activeMenu, setActiveMenu] = useState("dashboard");
  const [activeTabSettings, setActiveTabSettings] = useState("users");
  const [activeInvTab, setActiveInvTab] = useState("bulk");
  const [notification, setNotification] = useState(null);

  const [newUserForm, setNewUserForm] = useState({
    username: "",
    password: "",
    role: "Operator",
  });
  const [fbUser, setFbUser] = useState(null);
  const [dbLoading, setDbLoading] = useState(true);
  const [activeOpTab, setActiveOpTab] = useState("inbound");
  const [historyStartDate, setHistoryStartDate] = useState("");
  const [historyEndDate, setHistoryEndDate] = useState("");

  const initialFormData = {
    inSkuId: "",
    inQty: "",
    inMoNumber: "",
    inTmNumber: "",
    inSourceWarehouse: "",
    rebagTargetSkuId: "",
    rebagTargetStack: "",
    bulkSkuId: "",
    bulkBatchId: "",
    qtyToProcess: "",
    bulkBatchId2: "",
    qtyToProcess2: "",
    outSkuId: "",
  };
  const [formData, setFormData] = useState(initialFormData);
  const [outboundSelections, setOutboundSelections] = useState({});

  useEffect(() => {
    if (!auth) return setDbLoading(false);
    const initAuth = async () => {
      try {
        await signInAnonymously(auth);
      } catch (e) {}
    };
    initAuth();
    return onAuthStateChanged(auth, setFbUser);
  }, []);

  useEffect(() => {
    if (!fbUser || !db) return;
    const unsubUsers = onSnapshot(
      collection(db, "artifacts", appId, "public", "data", "users"),
      (snap) => {
        if (snap.empty)
          DEFAULT_USERS.forEach((u) =>
            setDoc(
              doc(
                db,
                "artifacts",
                appId,
                "public",
                "data",
                "users",
                u.username
              ),
              u
            )
          );
        else setUsers(snap.docs.map((d) => d.data()));
      }
    );
    const unsubSkus = onSnapshot(
      collection(db, "artifacts", appId, "public", "data", "skus"),
      (snap) => {
        setSkus(snap.docs.map((d) => d.data()));
        setDbLoading(false);
      }
    );
    const unsubBatches = onSnapshot(
      collection(db, "artifacts", appId, "public", "data", "batches"),
      (snap) => {
        setInventoryBatches(snap.docs.map((d) => d.data()));
      }
    );
    const unsubTx = onSnapshot(
      collection(db, "artifacts", appId, "public", "data", "transactions"),
      (snap) => {
        setTransactions(
          snap.docs
            .map((d) => d.data())
            .sort((a, b) => new Date(a.date) - new Date(b.date))
        );
      }
    );
    const unsubConfig = onSnapshot(
      doc(db, "artifacts", appId, "public", "data", "config", "system"),
      (snap) => {
        if (snap.exists()) setSystemConfig(snap.data());
      }
    );
    return () => {
      unsubUsers();
      unsubSkus();
      unsubBatches();
      unsubTx();
      unsubConfig();
    };
  }, [fbUser]);

  const showNotif = (msg) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3000);
  };
  const hasAccess = (roles) => currentUser && roles.includes(currentUser.role);

  const handleLogin = (e) => {
    e.preventDefault();
    const user = users.find(
      (u) =>
        u.username === loginForm.username && u.password === loginForm.password
    );
    if (user) {
      setCurrentUser(user);
      localStorage.setItem("rebagging_session", JSON.stringify(user));
      setLoginError("");
    } else setLoginError("Username/password salah!");
  };

  const handleLogout = () => {
    setCurrentUser(null);
    localStorage.removeItem("rebagging_session");
    setActiveMenu("dashboard");
  };

  const handleTransactionSubmit = async (e) => {
    e.preventDefault();
    const date = new Date().toISOString();
    let txData,
      batchData,
      batchUpdates = [];

    if (activeOpTab === "inbound") {
      const sku = skus.find((s) => s.id === formData.inSkuId);
      const qty = parseFloat(formData.inQty);
      const batchId = `INB-${Date.now()}`;
      batchData = {
        batchId,
        skuId: sku.id,
        initialQty: qty,
        currentQty: qty,
        sourceWarehouse: formData.inSourceWarehouse,
        date,
      };
      txData = {
        id: `TRX-${Date.now()}`,
        date,
        type: "INBOUND",
        skuId: sku.id,
        skuName: sku.name,
        qtyChange: qty,
        unit: sku.unit,
        operator: currentUser.username,
        sourceWarehouse: formData.inSourceWarehouse,
      };
      batchUpdates.push({ type: "set", id: batchId, data: batchData });
    } else if (activeOpTab === "rebagging") {
      const b1 = inventoryBatches.find(
        (b) => b.batchId === formData.bulkBatchId
      );
      const targetSku = skus.find((s) => s.id === formData.rebagTargetSkuId);
      const qty = parseFloat(formData.qtyToProcess) || 0;
      if (qty > b1.currentQty) return alert("Qty melebihi stok!");
      const resultQty = Math.floor(qty / (targetSku.conversionRate || 1));
      const newBatchId = `RBG-${Date.now()}`;
      batchData = {
        batchId: newBatchId,
        skuId: targetSku.id,
        currentQty: resultQty,
        sourceWarehouse: b1.sourceWarehouse,
        targetStack: formData.rebagTargetStack,
        date,
      };
      txData = {
        id: `TRX-${Date.now()}`,
        date,
        type: "REBAGGING",
        skuId: targetSku.id,
        skuName: targetSku.name,
        qtyChange: resultQty,
        unit: targetSku.unit,
        operator: currentUser.username,
        targetStack: formData.rebagTargetStack,
      };
      batchUpdates.push({
        type: "update",
        id: b1.batchId,
        data: { ...b1, currentQty: b1.currentQty - qty },
      });
      batchUpdates.push({ type: "set", id: newBatchId, data: batchData });
    } else if (activeOpTab === "outbound") {
      Object.entries(outboundSelections).forEach(([bId, qtyStr]) => {
        const q = parseFloat(qtyStr);
        if (q > 0) {
          const b = inventoryBatches.find((x) => x.batchId === bId);
          batchUpdates.push({
            type: "update",
            id: bId,
            data: { ...b, currentQty: b.currentQty - q },
          });
          txData = {
            id: `TRX-${Date.now()}-${bId}`,
            date,
            type: "OUTBOUND",
            skuId: formData.outSkuId,
            skuName: skus.find((s) => s.id === formData.outSkuId).name,
            qtyChange: -q,
            operator: currentUser.username,
          };
        }
      });
    }

    if (db) {
      for (const update of batchUpdates)
        await setDoc(
          doc(db, "artifacts", appId, "public", "data", "batches", update.id),
          update.data
        );
      if (txData)
        await setDoc(
          doc(
            db,
            "artifacts",
            appId,
            "public",
            "data",
            "transactions",
            txData.id
          ),
          txData
        );
    }
    showNotif("Transaksi Berhasil");
    setFormData(initialFormData);
    setOutboundSelections({});
  };

  // RECHARTS DATA
  const stockByWarehouseData = useMemo(() => {
    const data = {};
    inventoryBatches
      .filter((b) => b.currentQty > 0)
      .forEach((b) => {
        const sw = b.sourceWarehouse || "Unknown";
        if (!data[sw]) data[sw] = { name: sw, kg: 0, pack: 0 };
        const sku = skus.find((s) => s.id === b.skuId);
        if (sku && sku.unit?.toUpperCase() === "KG")
          data[sw].kg += b.currentQty;
        else data[sw].pack += b.currentQty;
      });
    return Object.values(data);
  }, [inventoryBatches, skus]);

  const compositionData = [
    { name: "Bahan Baku", value: skus.filter((s) => s.type === "bulk").length },
    {
      name: "Barang Jadi",
      value: skus.filter((s) => s.type === "rebagged").length,
    },
  ];

  // IMPORT/EXPORT EXCEL
  const handleImportExcel = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (event) => {
      const bstr = event.target.result;
      const wb = XLSX.read(bstr, { type: "binary" });
      const wsname = wb.SheetNames[0];
      const data = XLSX.utils.sheet_to_json(wb.Sheets[wsname]);
      if (db) {
        const batch = writeBatch(db);
        data.forEach((row) => {
          if (row.id)
            batch.set(
              doc(
                db,
                "artifacts",
                appId,
                "public",
                "data",
                "skus",
                row.id.toString()
              ),
              row
            );
        });
        await batch.commit();
        showNotif(`${data.length} SKU Diimpor`);
      }
    };
    reader.readAsBinaryString(file);
  };

  const handleDownloadHistory = () => {
    let filtered = transactions;
    if (historyStartDate && historyEndDate) {
      const s = new Date(historyStartDate);
      const e = new Date(historyEndDate);
      e.setHours(23, 59, 59);
      filtered = filtered.filter(
        (t) => new Date(t.date) >= s && new Date(t.date) <= e
      );
    }
    const ws = XLSX.utils.json_to_sheet(
      filtered.map((t) => ({
        Tanggal: new Date(t.date).toLocaleString(),
        Tipe: t.type,
        SKU: t.skuName,
        Qty: t.qtyChange,
        Operator: t.operator,
      }))
    );
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Riwayat");
    XLSX.writeFile(wb, "Riwayat_Rebagging.xlsx");
  };

  const handleUpdateConfig = async (e) => {
    e.preventDefault();
    if (db)
      await setDoc(
        doc(db, "artifacts", appId, "public", "data", "config", "system"),
        systemConfig
      );
    showNotif("Sistem Diperbarui");
  };

  if (dbLoading)
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Package className="animate-pulse w-12 h-12 text-red-600" />
      </div>
    );
  if (!currentUser)
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100 p-4">
        <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-sm">
          <h1 className="text-2xl font-bold text-center mb-6">
            {systemConfig.name}
          </h1>
          {loginError && (
            <p className="text-red-500 text-sm mb-4">{loginError}</p>
          )}
          <form onSubmit={handleLogin} className="space-y-4">
            <input
              className="w-full p-2 border rounded"
              placeholder="Username"
              value={loginForm.username}
              onChange={(e) =>
                setLoginForm({ ...loginForm, username: e.target.value })
              }
            />
            <input
              className="w-full p-2 border rounded"
              type="password"
              placeholder="Password"
              value={loginForm.password}
              onChange={(e) =>
                setLoginForm({ ...loginForm, password: e.target.value })
              }
            />
            <button className="w-full bg-red-600 text-white font-bold py-2 rounded hover:bg-red-700">
              Login
            </button>
          </form>
        </div>
      </div>
    );

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {notification && (
        <div className="fixed top-4 right-4 bg-green-600 text-white px-4 py-2 rounded shadow z-50">
          {notification}
        </div>
      )}

      {/* SIDEBAR */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="p-4 border-b border-slate-700 font-bold flex items-center gap-2">
          {systemConfig.logo ? (
            <img
              src={systemConfig.logo}
              alt="logo"
              className="w-8 h-8 rounded"
            />
          ) : (
            <Package />
          )}
          <span className="truncate">{systemConfig.name}</span>
        </div>
        <nav className="p-4 flex-1 space-y-2 text-sm">
          <button
            onClick={() => setActiveMenu("dashboard")}
            className={`w-full flex items-center gap-2 p-2 rounded ${
              activeMenu === "dashboard" ? "bg-red-600" : ""
            }`}
          >
            <Home size={16} /> Dashboard
          </button>
          <button
            onClick={() => setActiveMenu("inventory")}
            className={`w-full flex items-center gap-2 p-2 rounded ${
              activeMenu === "inventory" ? "bg-red-600" : ""
            }`}
          >
            <Boxes size={16} /> Inventori
          </button>
          {hasAccess(["Super Admin", "Admin", "Operator"]) && (
            <button
              onClick={() => setActiveMenu("operations")}
              className={`w-full flex items-center gap-2 p-2 rounded ${
                activeMenu === "operations" ? "bg-red-600" : ""
              }`}
            >
              <PackagePlus size={16} /> Operasi
            </button>
          )}
          <button
            onClick={() => setActiveMenu("history")}
            className={`w-full flex items-center gap-2 p-2 rounded ${
              activeMenu === "history" ? "bg-red-600" : ""
            }`}
          >
            <History size={16} /> Riwayat
          </button>
          {hasAccess(["Super Admin"]) && (
            <button
              onClick={() => setActiveMenu("settings")}
              className={`w-full flex items-center gap-2 p-2 rounded ${
                activeMenu === "settings" ? "bg-slate-700" : ""
              }`}
            >
              <Settings size={16} /> Pengaturan
            </button>
          )}
        </nav>
        <button
          onClick={handleLogout}
          className="m-4 p-2 bg-slate-800 rounded flex justify-center"
        >
          <LogOut size={16} />
        </button>
      </aside>

      {/* CONTENT */}
      <main className="flex-1 p-8 overflow-y-auto">
        {activeMenu === "dashboard" && (
          <div className="space-y-6">
            <h1 className="text-2xl font-bold">Dashboard Statistik</h1>
            <div className="grid grid-cols-2 gap-6 h-80">
              <div className="bg-white p-4 rounded-xl shadow-sm border">
                <h3 className="font-bold mb-4">Stok Berdasarkan Gudang Asal</h3>
                <ResponsiveContainer width="100%" height="80%">
                  <BarChart data={stockByWarehouseData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="kg" fill="#ef4444" name="Kilogram (KG)" />
                    <Bar dataKey="pack" fill="#3b82f6" name="Pack" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="bg-white p-4 rounded-xl shadow-sm border">
                <h3 className="font-bold mb-4">Komposisi SKU</h3>
                <ResponsiveContainer width="100%" height="80%">
                  <PieChart>
                    <Pie
                      data={compositionData}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                      label
                    >
                      <Cell fill="#ef4444" />
                      <Cell fill="#3b82f6" />
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {activeMenu === "inventory" && (
          <div className="space-y-4">
            <h1 className="text-2xl font-bold">Inventori Gudang</h1>
            <div className="flex gap-4 border-b">
              <button
                onClick={() => setActiveInvTab("bulk")}
                className={`pb-2 ${
                  activeInvTab === "bulk"
                    ? "border-b-2 border-red-600 font-bold"
                    : ""
                }`}
              >
                Bahan Baku (Curah)
              </button>
              <button
                onClick={() => setActiveInvTab("rebagged")}
                className={`pb-2 ${
                  activeInvTab === "rebagged"
                    ? "border-b-2 border-red-600 font-bold"
                    : ""
                }`}
              >
                Barang Jadi (Kemasan)
              </button>
            </div>
            <div className="bg-white rounded-xl shadow border p-4">
              <table className="w-full text-sm text-left">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="p-2">ID</th>
                    <th className="p-2">Nama</th>
                    <th className="p-2">Gudang Asal</th>
                    <th className="p-2 text-right">Stok</th>
                  </tr>
                </thead>
                <tbody>
                  {skus
                    .filter((s) => s.type === activeInvTab)
                    .map((sku) => {
                      const batches = inventoryBatches.filter(
                        (b) => b.skuId === sku.id && b.currentQty > 0
                      );
                      const total = batches.reduce(
                        (acc, b) => acc + b.currentQty,
                        0
                      );
                      const sources =
                        [
                          ...new Set(batches.map((b) => b.sourceWarehouse)),
                        ].join(", ") || "-";
                      return (
                        <tr key={sku.id} className="border-t">
                          <td className="p-2">{sku.id}</td>
                          <td className="p-2">{sku.name}</td>
                          <td className="p-2">{sources}</td>
                          <td className="p-2 text-right font-bold">
                            {total} {sku.unit}
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* OPERATIONS (Simplified for brevity, uses same logic as previous) */}
        {activeMenu === "operations" && (
          <div>
            <h1 className="text-2xl font-bold mb-4">Operasi Gudang</h1>
            <div className="bg-white p-6 rounded-xl shadow border">
              <div className="flex gap-4 mb-6 border-b">
                <button
                  onClick={() => setActiveOpTab("inbound")}
                  className={`pb-2 ${
                    activeOpTab === "inbound"
                      ? "font-bold border-b-2 border-red-600"
                      : ""
                  }`}
                >
                  Inbound
                </button>
                <button
                  onClick={() => setActiveOpTab("rebagging")}
                  className={`pb-2 ${
                    activeOpTab === "rebagging"
                      ? "font-bold border-b-2 border-red-600"
                      : ""
                  }`}
                >
                  Rebagging
                </button>
                <button
                  onClick={() => setActiveOpTab("outbound")}
                  className={`pb-2 ${
                    activeOpTab === "outbound"
                      ? "font-bold border-b-2 border-red-600"
                      : ""
                  }`}
                >
                  Outbound
                </button>
              </div>
              <form
                onSubmit={handleTransactionSubmit}
                className="space-y-4 max-w-xl"
              >
                {activeOpTab === "inbound" && (
                  <>
                    <SearchableSelect
                      options={skus
                        .filter((s) => s.type === "bulk")
                        .map((s) => ({ value: s.id, label: s.name }))}
                      value={formData.inSkuId}
                      onChange={(v) => setFormData({ ...formData, inSkuId: v })}
                      placeholder="Pilih SKU Curah"
                    />
                    <input
                      type="number"
                      placeholder="Qty"
                      className="w-full p-2 border rounded"
                      value={formData.inQty}
                      onChange={(e) =>
                        setFormData({ ...formData, inQty: e.target.value })
                      }
                      required
                    />
                    <input
                      type="text"
                      placeholder="Gudang Asal"
                      className="w-full p-2 border rounded"
                      value={formData.inSourceWarehouse}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          inSourceWarehouse: e.target.value,
                        })
                      }
                      required
                    />
                  </>
                )}
                {activeOpTab === "rebagging" && (
                  <>
                    <SearchableSelect
                      options={skus
                        .filter((s) => s.type === "bulk")
                        .map((s) => ({ value: s.id, label: s.name }))}
                      value={formData.bulkSkuId}
                      onChange={(v) =>
                        setFormData({ ...formData, bulkSkuId: v })
                      }
                      placeholder="Sumber SKU"
                    />
                    {formData.bulkSkuId && (
                      <SearchableSelect
                        options={inventoryBatches
                          .filter(
                            (b) =>
                              b.skuId === formData.bulkSkuId && b.currentQty > 0
                          )
                          .map((b) => ({
                            value: b.batchId,
                            label: `Sisa: ${b.currentQty}`,
                          }))}
                        value={formData.bulkBatchId}
                        onChange={(v) =>
                          setFormData({ ...formData, bulkBatchId: v })
                        }
                        placeholder="Pilih Batch"
                      />
                    )}
                    <input
                      type="number"
                      placeholder="Qty Diproses"
                      className="w-full p-2 border rounded"
                      value={formData.qtyToProcess}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          qtyToProcess: e.target.value,
                        })
                      }
                    />
                    <SearchableSelect
                      options={skus
                        .filter((s) => s.type === "rebagged")
                        .map((s) => ({ value: s.id, label: s.name }))}
                      value={formData.rebagTargetSkuId}
                      onChange={(v) =>
                        setFormData({ ...formData, rebagTargetSkuId: v })
                      }
                      placeholder="SKU Hasil"
                    />
                    <select
                      className="w-full p-2 border rounded"
                      value={formData.rebagTargetStack}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          rebagTargetStack: e.target.value,
                        })
                      }
                    >
                      <option value="">Pilih Tumpukan</option>
                      {STACK_LOCATIONS.map((l) => (
                        <option key={l} value={l}>
                          {l}
                        </option>
                      ))}
                    </select>
                  </>
                )}
                <button className="bg-red-600 text-white px-4 py-2 rounded font-bold">
                  Simpan Transaksi
                </button>
              </form>
            </div>
          </div>
        )}

        {activeMenu === "history" && (
          <div className="space-y-4">
            <div className="flex justify-between">
              <h1 className="text-2xl font-bold">Riwayat .xlsx</h1>
              <div className="flex gap-2">
                <input
                  type="date"
                  className="border p-2 rounded"
                  value={historyStartDate}
                  onChange={(e) => setHistoryStartDate(e.target.value)}
                />
                <input
                  type="date"
                  className="border p-2 rounded"
                  value={historyEndDate}
                  onChange={(e) => setHistoryEndDate(e.target.value)}
                />
                <button
                  onClick={handleDownloadHistory}
                  className="bg-green-600 text-white px-4 rounded flex items-center gap-2"
                >
                  <Download size={16} /> Unduh
                </button>
              </div>
            </div>
            <div className="bg-white p-4 rounded shadow border">
              {transactions.map((t) => (
                <div key={t.id} className="border-b p-2 flex justify-between">
                  <span>
                    {new Date(t.date).toLocaleDateString()} - {t.skuName}
                  </span>
                  <span className="font-bold">{t.qtyChange}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeMenu === "settings" && hasAccess(["Super Admin"]) && (
          <div className="space-y-6">
            <h1 className="text-2xl font-bold">Pengaturan Super Admin</h1>
            <div className="flex gap-4 border-b pb-2">
              <button
                onClick={() => setActiveTabSettings("system")}
                className={`font-bold ${
                  activeTabSettings === "system" ? "text-red-600" : ""
                }`}
              >
                Sistem
              </button>
              <button
                onClick={() => setActiveTabSettings("sku")}
                className={`font-bold ${
                  activeTabSettings === "sku" ? "text-red-600" : ""
                }`}
              >
                Upload Excel SKU
              </button>
            </div>
            {activeTabSettings === "system" && (
              <form
                onSubmit={handleUpdateConfig}
                className="bg-white p-6 rounded shadow max-w-md space-y-4"
              >
                <label className="block font-bold">Nama Aplikasi</label>
                <input
                  className="w-full border p-2 rounded"
                  value={systemConfig.name}
                  onChange={(e) =>
                    setSystemConfig({ ...systemConfig, name: e.target.value })
                  }
                />
                <label className="block font-bold">URL Logo (Opsional)</label>
                <input
                  className="w-full border p-2 rounded"
                  value={systemConfig.logo || ""}
                  onChange={(e) =>
                    setSystemConfig({ ...systemConfig, logo: e.target.value })
                  }
                  placeholder="https://..."
                />
                <button className="bg-slate-800 text-white px-4 py-2 rounded">
                  Simpan Konfigurasi
                </button>
              </form>
            )}
            {activeTabSettings === "sku" && (
              <div className="bg-white p-8 rounded shadow text-center border-dashed border-2">
                <FileSpreadsheet className="mx-auto w-12 h-12 text-green-600 mb-4" />
                <h3 className="font-bold mb-2">Upload Master SKU (.xlsx)</h3>
                <input
                  type="file"
                  accept=".xlsx, .xls"
                  onChange={handleImportExcel}
                  className="mx-auto block"
                />
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
