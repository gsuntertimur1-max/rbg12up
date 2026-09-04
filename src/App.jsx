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
  Import,
  ArrowRightLeft,
  Settings,
  Users,
  ArrowRight,
  Settings2,
  Database,
  History,
  LogOut,
  PackageOpen,
  Boxes,
  FileSpreadsheet,
  Search,
  CheckCircle,
} from "lucide-react";

// --- FIREBASE IMPORTS ---
import { initializeApp, getApps, getApp } from "firebase/app";
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
const DEFAULT_SKUS = [
  {
    type: "bulk",
    id: "B0010053Z",
    name: "BERAS MEDIUM HASIL REPROSES POLOS 50 KG PSO DN",
    unit: "KG",
  },
  {
    type: "bulk",
    id: "B0010193Z",
    name: "BERAS MEDIUM HASIL GILING 25% POLOS 50 KG PSO DN",
    unit: "KG",
  },
  {
    type: "rebagged",
    id: "B0010201Z",
    name: "BERAS MEDIUM HASIL GILING 25% LOGO SPHP 5 KG PSO DN",
    unit: "KG",
    conversionRate: 5,
  },
  {
    type: "rebagged",
    id: "B0030028X",
    name: "BERAS KHUSUS BERAS MERAH CAPING EMAS 1 KG KOM DN",
    unit: "Pack",
    conversionRate: 1,
  },
];

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
  // measurementId dihapus agar aman di CodeSandbox
};

let app,
  auth,
  db,
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
  }
} catch (e) {
  console.error("Firebase Init Error:", e);
}

// --- KOMPONEN SEARCHABLE SELECT ---
const SearchableSelect = ({
  options,
  value,
  onChange,
  placeholder,
  renderLabel,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const wrapperRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target))
        setIsOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredOptions = options.filter((opt) => {
    const safeLabel = (opt.label || "").toString().toLowerCase();
    const safeSearch = (search || "").toString().toLowerCase();
    return safeLabel.includes(safeSearch);
  });

  const selectedOption = options.find((opt) => opt.value === value);
  const displayValue = selectedOption
    ? renderLabel
      ? renderLabel(selectedOption)
      : selectedOption.label
    : "";

  return (
    <div ref={wrapperRef} className="relative w-full">
      <div
        className="w-full border border-slate-300 rounded-lg p-2.5 text-sm cursor-pointer bg-white flex justify-between items-center"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span
          className={`truncate ${!value ? "text-slate-400" : "text-slate-800"}`}
        >
          {value ? displayValue : placeholder}
        </span>
        <span className="text-slate-400 text-xs ml-2">▼</span>
      </div>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-60 flex flex-col">
          <div className="p-2 border-b border-slate-100 sticky top-0 bg-white">
            <div className="relative">
              <Search
                size={14}
                className="absolute left-2.5 top-2 text-slate-400"
              />
              <input
                type="text"
                className="w-full pl-8 pr-2 py-1.5 text-sm border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-red-500"
                placeholder="Cari..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                autoFocus
              />
            </div>
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
                  className={`p-2.5 text-sm cursor-pointer hover:bg-slate-50 transition-colors border-b border-slate-50 last:border-0 ${
                    value === opt.value
                      ? "bg-red-50 text-red-700 font-medium"
                      : "text-slate-700"
                  }`}
                  onClick={() => {
                    onChange(opt.value);
                    setIsOpen(false);
                    setSearch("");
                  }}
                >
                  {renderLabel ? renderLabel(opt) : opt.label}
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
    const savedUser = localStorage.getItem("rebagging_session");
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const [users, setUsers] = useState([]);
  const [skus, setSkus] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [inventoryBatches, setInventoryBatches] = useState([]);

  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [loginError, setLoginError] = useState("");
  const [activeMenu, setActiveMenu] = useState("dashboard");
  const [systemName, setSystemName] = useState("Sistem Rebagging Terpadu");
  const [activeTabSettings, setActiveTabSettings] = useState("users");
  const [notification, setNotification] = useState(null);

  const [isAddingUser, setIsAddingUser] = useState(false);
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
    if (!auth) {
      setUsers(DEFAULT_USERS);
      setSkus(DEFAULT_SKUS);
      setDbLoading(false);
      return;
    }
    const initAuth = async () => {
      try {
        await signInAnonymously(auth);
      } catch (e) {
        console.error("Auth Error:", e);
      }
    };
    initAuth();
    const unsubscribe = onAuthStateChanged(auth, setFbUser);
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    if (!fbUser || !db) return;

    const unsubUsers = onSnapshot(
      collection(db, "artifacts", appId, "public", "data", "users"),
      (snap) => {
        if (snap.empty) {
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
        } else {
          setUsers(snap.docs.map((d) => d.data()));
        }
      }
    );

    const unsubSkus = onSnapshot(
      collection(db, "artifacts", appId, "public", "data", "skus"),
      (snap) => {
        if (snap.empty) {
          DEFAULT_SKUS.forEach((s) =>
            setDoc(
              doc(db, "artifacts", appId, "public", "data", "skus", s.id),
              s
            )
          );
        } else {
          setSkus(snap.docs.map((d) => d.data()));
        }
        setDbLoading(false);
      },
      (error) => {
        console.error(error);
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

    return () => {
      unsubUsers();
      unsubSkus();
      unsubBatches();
      unsubTx();
    };
  }, [fbUser]);

  const showNotification = (message) => {
    setNotification(message);
    setTimeout(() => setNotification(null), 3000);
  };

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
    } else {
      setLoginError("Username atau password salah!");
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    localStorage.removeItem("rebagging_session");
    setLoginForm({ username: "", password: "" });
    setActiveMenu("dashboard");
  };

  const hasAccess = (allowedRoles) =>
    currentUser && allowedRoles.includes(currentUser.role);

  const handleAddUser = async (e) => {
    e.preventDefault();
    if (users.some((u) => u.username === newUserForm.username)) return;
    if (db)
      await setDoc(
        doc(
          db,
          "artifacts",
          appId,
          "public",
          "data",
          "users",
          newUserForm.username
        ),
        newUserForm
      );
    else setUsers([...users, newUserForm]);
    setIsAddingUser(false);
    setNewUserForm({ username: "", password: "", role: "Operator" });
    showNotification("User Baru Ditambahkan");
  };

  const handleDeleteUser = async (username) => {
    if (username === currentUser.username) return;
    if (db)
      await deleteDoc(
        doc(db, "artifacts", appId, "public", "data", "users", username)
      );
    else setUsers(users.filter((u) => u.username !== username));
    showNotification("User Berhasil Dihapus");
  };

  const handleTransactionSubmit = async (e) => {
    e.preventDefault();
    const date = new Date().toISOString();

    if (activeOpTab === "inbound") {
      const sku = skus.find((s) => s.id === formData.inSkuId);
      const qty = parseFloat(formData.inQty);
      const batchId = `INB-${Date.now()}`;

      const batchData = {
        batchId,
        skuId: formData.inSkuId,
        initialQty: qty,
        currentQty: qty,
        moNumber: formData.inMoNumber,
        tmNumber: formData.inTmNumber,
        sourceWarehouse: formData.inSourceWarehouse,
        date,
      };
      const txData = {
        id: `TRX-${Date.now()}`,
        date,
        type: "INBOUND",
        skuId: formData.inSkuId,
        skuName: sku.name,
        qtyChange: qty,
        unit: sku.unit,
        operator: currentUser.username,
        details: `Pemasukan Curah. Batch: ${batchId}`,
        moNumber: formData.inMoNumber,
        tmNumber: formData.inTmNumber,
        sourceWarehouse: formData.inSourceWarehouse,
      };

      if (db) {
        await setDoc(
          doc(db, "artifacts", appId, "public", "data", "batches", batchId),
          batchData
        );
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
      } else {
        setInventoryBatches([...inventoryBatches, batchData]);
        setTransactions([...transactions, txData]);
      }
      showNotification("Pemasukan (Inbound)");
    } else if (activeOpTab === "rebagging") {
      const bulkBatch1 = inventoryBatches.find(
        (b) => b.batchId === formData.bulkBatchId
      );
      const bulkBatch2 = inventoryBatches.find(
        (b) => b.batchId === formData.bulkBatchId2
      );
      const qty1 = parseFloat(formData.qtyToProcess) || 0;
      const qty2 = parseFloat(formData.qtyToProcess2) || 0;
      const totalQtyProcess = qty1 + qty2;

      if (
        qty1 > bulkBatch1.currentQty ||
        (bulkBatch2 && qty2 > bulkBatch2.currentQty)
      ) {
        alert("Kuantitas proses melebihi sisa batch yang dipilih!");
        return;
      }

      const targetSku = skus.find((s) => s.id === formData.rebagTargetSkuId);
      const convRate = targetSku.conversionRate || 1;
      const resultQty = Math.floor(totalQtyProcess / convRate);
      const combinedMo = bulkBatch2
        ? `${bulkBatch1.moNumber}, ${bulkBatch2.moNumber}`
        : bulkBatch1.moNumber;
      const combinedTm = bulkBatch2
        ? `${bulkBatch1.tmNumber}, ${bulkBatch2.tmNumber}`
        : bulkBatch1.tmNumber;
      const combinedSource = bulkBatch2
        ? `${bulkBatch1.sourceWarehouse}, ${bulkBatch2.sourceWarehouse}`
        : bulkBatch1.sourceWarehouse;
      const newBatchId = `RBG-${Date.now()}`;

      const rebagBatchData = {
        batchId: newBatchId,
        skuId: formData.rebagTargetSkuId,
        initialQty: resultQty,
        currentQty: resultQty,
        moNumber: combinedMo,
        tmNumber: combinedTm,
        sourceWarehouse: combinedSource,
        targetStack: formData.rebagTargetStack,
        date,
      };
      const sourceDetails = bulkBatch2
        ? `${qty1}${bulkBatch1.unit} dari Batch 1 & ${qty2}${bulkBatch2.unit} dari Batch 2`
        : `${qty1}${bulkBatch1.unit} dari Batch ${bulkBatch1.batchId}`;
      const txData = {
        id: `TRX-${Date.now()}`,
        date,
        type: "REBAGGING",
        skuId: formData.rebagTargetSkuId,
        skuName: targetSku.name,
        qtyChange: resultQty,
        unit: targetSku.unit,
        operator: currentUser.username,
        details: `Rebagging: Konversi ${sourceDetails} ➔ ${resultQty}${targetSku.unit}. Tumpukan: ${formData.rebagTargetStack}`,
        moNumber: combinedMo,
        tmNumber: combinedTm,
        sourceWarehouse: combinedSource,
        targetStack: formData.rebagTargetStack,
      };

      if (db) {
        await setDoc(
          doc(
            db,
            "artifacts",
            appId,
            "public",
            "data",
            "batches",
            bulkBatch1.batchId
          ),
          { ...bulkBatch1, currentQty: bulkBatch1.currentQty - qty1 }
        );
        if (bulkBatch2)
          await setDoc(
            doc(
              db,
              "artifacts",
              appId,
              "public",
              "data",
              "batches",
              bulkBatch2.batchId
            ),
            { ...bulkBatch2, currentQty: bulkBatch2.currentQty - qty2 }
          );
        await setDoc(
          doc(db, "artifacts", appId, "public", "data", "batches", newBatchId),
          rebagBatchData
        );
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
      } else {
        const updatedBatches = inventoryBatches.map((b) => {
          if (b.batchId === formData.bulkBatchId)
            return { ...b, currentQty: b.currentQty - qty1 };
          if (b.batchId === formData.bulkBatchId2)
            return { ...b, currentQty: b.currentQty - qty2 };
          return b;
        });
        setInventoryBatches([...updatedBatches, rebagBatchData]);
        setTransactions([...transactions, txData]);
      }
      showNotification("Proses Rebagging");
    } else if (activeOpTab === "outbound") {
      const targetSku = skus.find((s) => s.id === formData.outSkuId);
      const newTransactions = [];
      const updatedBatches = [];

      Object.entries(outboundSelections).forEach(([batchId, outQtyStr]) => {
        const outQty = parseFloat(outQtyStr);
        if (outQty > 0) {
          const batch = inventoryBatches.find((b) => b.batchId === batchId);
          if (batch && batch.currentQty >= outQty) {
            updatedBatches.push({
              ...batch,
              currentQty: batch.currentQty - outQty,
            });
            newTransactions.push({
              id: `TRX-${Date.now()}-${batchId}`,
              date,
              type: "OUTBOUND",
              skuId: formData.outSkuId,
              skuName: targetSku.name,
              qtyChange: -outQty,
              unit: targetSku.unit,
              operator: currentUser.username,
              details: `Pengeluaran dari Batch ${batchId}`,
              moNumber: batch.moNumber,
              tmNumber: batch.tmNumber,
              targetStack: batch.targetStack,
            });
          }
        }
      });

      if (newTransactions.length === 0) {
        alert("Tidak ada kuantitas pengeluaran valid.");
        return;
      }

      if (db) {
        for (const b of updatedBatches)
          await setDoc(
            doc(db, "artifacts", appId, "public", "data", "batches", b.batchId),
            b
          );
        for (const tx of newTransactions)
          await setDoc(
            doc(
              db,
              "artifacts",
              appId,
              "public",
              "data",
              "transactions",
              tx.id
            ),
            tx
          );
      } else {
        let nextBatches = [...inventoryBatches];
        updatedBatches.forEach((ub) => {
          const idx = nextBatches.findIndex((b) => b.batchId === ub.batchId);
          if (idx > -1) nextBatches[idx] = ub;
        });
        setInventoryBatches(nextBatches);
        setTransactions([...transactions, ...newTransactions]);
      }
      showNotification("Pengeluaran (Outbound)");
    }
    setFormData(initialFormData);
    setOutboundSelections({});
  };

  const inventorySummary = useMemo(() => {
    const summary = {};
    skus.forEach((sku) => (summary[sku.id] = { ...sku, currentStock: 0 }));
    inventoryBatches.forEach((batch) => {
      if (summary[batch.skuId])
        summary[batch.skuId].currentStock += batch.currentQty;
    });
    return Object.values(summary);
  }, [skus, inventoryBatches]);

  const getAvailableBatches = (skuId) =>
    inventoryBatches.filter((b) => b.skuId === skuId && b.currentQty > 0);

  const handleImportCSV = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (event) => {
      const csvText = event.target.result;
      const rows = csvText.split("\n");
      const newSkus = [];
      for (let i = 1; i < rows.length; i++) {
        if (!rows[i].trim()) continue;
        const cols = rows[i]
          .split(",")
          .map((c) => c.trim().replace(/^"|"$/g, ""));
        if (cols.length >= 4) {
          const type = cols[0].toLowerCase().includes("bulk")
            ? "bulk"
            : "rebagged";
          const conv = cols[4] ? parseFloat(cols[4]) : null;
          if (cols[1] && cols[2]) {
            newSkus.push({
              type,
              id: cols[1],
              name: cols[2],
              unit: cols[3],
              ...(type === "rebagged" && conv ? { conversionRate: conv } : {}),
            });
          }
        }
      }
      if (newSkus.length > 0) {
        if (db) {
          const batch = writeBatch(db);
          for (const sku of newSkus) {
            batch.set(
              doc(db, "artifacts", appId, "public", "data", "skus", sku.id),
              sku
            );
          }
          await batch.commit();
        } else {
          const mergedSkus = [...skus];
          newSkus.forEach((newSku) => {
            const existingIdx = mergedSkus.findIndex((s) => s.id === newSku.id);
            if (existingIdx >= 0) mergedSkus[existingIdx] = newSku;
            else mergedSkus.push(newSku);
          });
          setSkus(mergedSkus);
        }
        alert(`${newSkus.length} SKU berhasil diimpor!`);
      }
    };
    reader.readAsText(file);
  };

  const handleDeleteSKU = async (skuId) => {
    if (db)
      await deleteDoc(
        doc(db, "artifacts", appId, "public", "data", "skus", skuId)
      );
    else setSkus(skus.filter((s) => s.id !== skuId));
    showNotification("SKU Dihapus");
  };

  const handleDownloadRiwayat = () => {
    let filteredData = transactions.filter((t) => t.type === "REBAGGING");
    if (historyStartDate && historyEndDate) {
      const start = new Date(historyStartDate);
      const end = new Date(historyEndDate);
      end.setHours(23, 59, 59, 999);
      filteredData = filteredData.filter((t) => {
        const d = new Date(t.date);
        return d >= start && d <= end;
      });
    }
    const headers = [
      "No",
      "Tanggal",
      "ID Transaksi",
      "SKU Hasil",
      "ID SKU",
      "Jml",
      "Satuan",
      "No MO",
      "No TM",
      "Tumpukan",
      "Detail",
      "Operator",
    ];
    let csvContent = headers.join(",") + "\n";
    filteredData.forEach((trx, index) => {
      csvContent +=
        [
          index + 1,
          `"${new Date(trx.date).toLocaleString()}"`,
          `"${trx.id}"`,
          `"${trx.skuName}"`,
          `"${trx.skuId}"`,
          trx.qtyChange,
          `"${trx.unit}"`,
          `"${trx.moNumber || "-"}"`,
          `"${trx.tmNumber || "-"}"`,
          `"${trx.targetStack || "-"}"`,
          `"${trx.details}"`,
          `"${trx.operator}"`,
        ].join(",") + "\n";
    });
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `Riwayat_Rebagging.csv`;
    link.click();
  };

  if (dbLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col justify-center items-center p-4">
        <Package className="w-16 h-16 text-red-600 animate-pulse mb-4" />
        <p className="text-slate-500 font-medium">
          Menghubungkan ke Cloud Database...
        </p>
      </div>
    );
  }

  if (!currentUser) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col justify-center items-center p-4">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden">
          <div className="bg-red-600 p-8 text-center">
            <Package className="w-16 h-16 text-white mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-white mb-2">{systemName}</h1>
            <p className="text-red-100 text-sm">Masuk untuk melanjutkan</p>
          </div>
          <div className="p-8">
            {loginError && (
              <div className="mb-4 p-3 bg-red-50 border-l-4 border-red-500 text-red-700 text-sm">
                {loginError}
              </div>
            )}
            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">
                  Username
                </label>
                <input
                  type="text"
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-red-500 outline-none"
                  value={loginForm.username}
                  onChange={(e) =>
                    setLoginForm({ ...loginForm, username: e.target.value })
                  }
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">
                  Password
                </label>
                <input
                  type="password"
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-red-500 outline-none"
                  value={loginForm.password}
                  onChange={(e) =>
                    setLoginForm({ ...loginForm, password: e.target.value })
                  }
                  required
                />
              </div>
              <button
                type="submit"
                className="w-full bg-red-600 text-white font-bold py-2.5 rounded-lg hover:bg-red-700"
              >
                Masuk
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col md:flex-row font-sans">
      {notification && (
        <div className="fixed top-4 right-4 z-50 animate-bounce">
          <div className="bg-green-600 text-white px-6 py-3 rounded-xl shadow-lg flex items-center gap-3">
            <CheckCircle size={20} className="text-green-200" />
            <div>
              <p className="font-bold text-sm">Berhasil!</p>
              <p className="text-xs text-green-100">
                Data {notification} tersimpan.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Sidebar */}
      <aside className="w-full md:w-64 bg-slate-900 text-slate-300 flex flex-col flex-shrink-0">
        <div className="p-5 bg-slate-950 border-b border-slate-800 flex items-center gap-3">
          <Package className="text-red-500 w-8 h-8 flex-shrink-0" />
          <div>
            <h2 className="font-bold text-white text-sm">{systemName}</h2>
            <span className="text-xs text-slate-500">v2.5 (Stable)</span>
          </div>
        </div>
        <div className="p-4 flex items-center gap-3 border-b border-slate-800">
          <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center font-bold text-slate-300">
            {currentUser.username.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="text-sm font-semibold text-white">
              {currentUser.username}
            </p>
            <p className="text-xs text-red-400 font-medium">
              {currentUser.role}
            </p>
          </div>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          <button
            onClick={() => setActiveMenu("dashboard")}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium ${
              activeMenu === "dashboard"
                ? "bg-red-600 text-white"
                : "hover:bg-slate-800 hover:text-white"
            }`}
          >
            <Home size={18} /> Dashboard
          </button>
          <button
            onClick={() => setActiveMenu("inventory")}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium ${
              activeMenu === "inventory"
                ? "bg-red-600 text-white"
                : "hover:bg-slate-800 hover:text-white"
            }`}
          >
            <Boxes size={18} /> Inventori
          </button>
          {hasAccess(["Super Admin", "Admin", "Operator"]) && (
            <button
              onClick={() => setActiveMenu("operations")}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium ${
                activeMenu === "operations"
                  ? "bg-red-600 text-white"
                  : "hover:bg-slate-800 hover:text-white"
              }`}
            >
              <PackagePlus size={18} /> Operasi Gudang
            </button>
          )}
          <button
            onClick={() => setActiveMenu("history")}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium ${
              activeMenu === "history"
                ? "bg-red-600 text-white"
                : "hover:bg-slate-800 hover:text-white"
            }`}
          >
            <History size={18} /> Riwayat Rebagging
          </button>
        </nav>
        {hasAccess(["Super Admin"]) && (
          <div className="p-4 border-t border-slate-800">
            <button
              onClick={() => setActiveMenu("settings")}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium ${
                activeMenu === "settings"
                  ? "bg-slate-700 text-white"
                  : "hover:bg-slate-800 hover:text-white"
              }`}
            >
              <Settings2 size={18} /> Pengaturan
            </button>
          </div>
        )}
        <div className="p-4">
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-slate-400 border border-slate-700 hover:bg-slate-800"
          >
            <LogOut size={16} /> Keluar
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-6 md:p-8 max-w-6xl mx-auto">
          {activeMenu === "dashboard" && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div>
                <h1 className="text-2xl font-bold text-slate-800">Dashboard</h1>
                <p className="text-slate-500 text-sm mt-1">
                  Ringkasan aktivitas dan status gudang.
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center gap-4">
                  <div className="p-4 bg-blue-50 text-blue-600 rounded-xl">
                    <Database size={24} />
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Total Jenis SKU</p>
                    <p className="text-2xl font-bold">{skus.length}</p>
                  </div>
                </div>
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center gap-4">
                  <div className="p-4 bg-orange-50 text-orange-600 rounded-xl">
                    <History size={24} />
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Total Transaksi</p>
                    <p className="text-2xl font-bold">{transactions.length}</p>
                  </div>
                </div>
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center gap-4">
                  <div className="p-4 bg-green-50 text-green-600 rounded-xl">
                    <Boxes size={24} />
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Batch Aktif</p>
                    <p className="text-2xl font-bold">
                      {inventoryBatches.filter((b) => b.currentQty > 0).length}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeMenu === "inventory" && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h1 className="text-2xl font-bold text-slate-800">
                Inventori Saat Ini
              </h1>
              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                <table className="w-full text-sm text-left">
                  <thead className="bg-slate-50 uppercase text-xs text-slate-600 border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-4">ID Barang</th>
                      <th className="px-6 py-4">Nama</th>
                      <th className="px-6 py-4">Kategori</th>
                      <th className="px-6 py-4 text-right">Stok</th>
                    </tr>
                  </thead>
                  <tbody>
                    {inventorySummary.map((item, idx) => (
                      <tr
                        key={idx}
                        className="border-b border-slate-100 hover:bg-slate-50"
                      >
                        <td className="px-6 py-4 font-medium">{item.id}</td>
                        <td className="px-6 py-4">{item.name}</td>
                        <td className="px-6 py-4">
                          <span
                            className={`px-2 py-1 rounded-md text-xs font-medium ${
                              item.type === "bulk"
                                ? "bg-slate-100 text-slate-700"
                                : "bg-red-50 text-red-700"
                            }`}
                          >
                            {item.type === "bulk" ? "Curah" : "Rebagged"}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right font-bold">
                          {item.currentStock.toLocaleString()} {item.unit}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeMenu === "operations" && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h1 className="text-2xl font-bold text-slate-800">
                Operasi Gudang
              </h1>
              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                <div className="flex border-b border-slate-200">
                  <button
                    onClick={() => setActiveOpTab("inbound")}
                    className={`flex-1 py-4 text-sm font-semibold flex items-center justify-center gap-2 ${
                      activeOpTab === "inbound"
                        ? "bg-red-50 text-red-700 border-b-2 border-red-600"
                        : "text-slate-500"
                    }`}
                  >
                    <FileDown size={18} /> Inbound
                  </button>
                  <button
                    onClick={() => setActiveOpTab("rebagging")}
                    className={`flex-1 py-4 text-sm font-semibold flex items-center justify-center gap-2 ${
                      activeOpTab === "rebagging"
                        ? "bg-red-50 text-red-700 border-b-2 border-red-600"
                        : "text-slate-500"
                    }`}
                  >
                    <ArrowRightLeft size={18} /> Rebagging
                  </button>
                  <button
                    onClick={() => setActiveOpTab("outbound")}
                    className={`flex-1 py-4 text-sm font-semibold flex items-center justify-center gap-2 ${
                      activeOpTab === "outbound"
                        ? "bg-red-50 text-red-700 border-b-2 border-red-600"
                        : "text-slate-500"
                    }`}
                  >
                    <FileUp size={18} /> Outbound
                  </button>
                </div>
                <div className="p-6 md:p-8">
                  <form
                    onSubmit={handleTransactionSubmit}
                    className="max-w-3xl mx-auto space-y-6"
                  >
                    {activeOpTab === "inbound" && (
                      <>
                        <label className="block text-sm font-semibold text-slate-700">
                          Pilih Barang Curah
                        </label>
                        <SearchableSelect
                          options={skus
                            .filter((s) => s.type === "bulk")
                            .map((s) => ({
                              value: s.id,
                              label: `${s.id} - ${s.name} (${s.unit})`,
                            }))}
                          value={formData.inSkuId}
                          onChange={(val) =>
                            setFormData({ ...formData, inSkuId: val })
                          }
                          placeholder="Pilih SKU Curah..."
                        />
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-semibold text-slate-700">
                              Kuantitas Masuk
                            </label>
                            <input
                              type="number"
                              step="0.01"
                              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-red-500"
                              value={formData.inQty}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  inQty: e.target.value,
                                })
                              }
                              required
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-semibold text-slate-700">
                              Gudang Asal
                            </label>
                            <input
                              type="text"
                              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-red-500"
                              value={formData.inSourceWarehouse}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  inSourceWarehouse: e.target.value,
                                })
                              }
                              required
                            />
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-semibold text-slate-700">
                              No. MO
                            </label>
                            <input
                              type="text"
                              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-red-500"
                              value={formData.inMoNumber}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  inMoNumber: e.target.value,
                                })
                              }
                              required
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-semibold text-slate-700">
                              No. TM
                            </label>
                            <input
                              type="text"
                              className="w-full px-4 py-2.5 border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-red-500"
                              value={formData.inTmNumber}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  inTmNumber: e.target.value,
                                })
                              }
                              required
                            />
                          </div>
                        </div>
                      </>
                    )}

                    {activeOpTab === "rebagging" && (
                      <>
                        <div className="grid grid-cols-2 gap-6 p-4 border rounded-xl bg-slate-50">
                          <div>
                            <h4 className="text-sm font-bold text-slate-700 mb-4 border-b pb-2">
                              Sumber 1
                            </h4>
                            <label className="block text-xs font-semibold text-slate-700 mb-1">
                              SKU Bahan
                            </label>
                            <SearchableSelect
                              options={skus
                                .filter((s) => s.type === "bulk")
                                .map((s) => ({ value: s.id, label: s.name }))}
                              value={formData.bulkSkuId}
                              onChange={(val) =>
                                setFormData({
                                  ...formData,
                                  bulkSkuId: val,
                                  bulkBatchId: "",
                                })
                              }
                              placeholder="Cari SKU..."
                            />
                            {formData.bulkSkuId && (
                              <>
                                <label className="block text-xs font-semibold mt-3 mb-1">
                                  Pilih Batch (Inbound)
                                </label>
                                <SearchableSelect
                                  options={getAvailableBatches(
                                    formData.bulkSkuId
                                  ).map((b) => ({
                                    value: b.batchId,
                                    label: `MO: ${b.moNumber} | Sisa: ${b.currentQty}`,
                                    data: b,
                                  }))}
                                  value={formData.bulkBatchId}
                                  onChange={(val) =>
                                    setFormData({
                                      ...formData,
                                      bulkBatchId: val,
                                    })
                                  }
                                  placeholder="Pilih Batch..."
                                />
                                <label className="block text-xs font-semibold mt-3 mb-1">
                                  Kuantitas Diproses
                                </label>
                                <input
                                  type="number"
                                  step="0.01"
                                  className="w-full px-3 py-2 border rounded-lg"
                                  value={formData.qtyToProcess}
                                  onChange={(e) =>
                                    setFormData({
                                      ...formData,
                                      qtyToProcess: e.target.value,
                                    })
                                  }
                                  required
                                />
                              </>
                            )}
                          </div>
                          <div className="border-l pl-6 border-dashed">
                            <h4 className="text-sm font-bold text-slate-500 mb-4 border-b pb-2">
                              Sumber 2 (Opsional)
                            </h4>
                            <label className="block text-xs font-semibold text-slate-500 mb-1">
                              Batch Lain
                            </label>
                            <SearchableSelect
                              options={
                                formData.bulkSkuId
                                  ? getAvailableBatches(formData.bulkSkuId)
                                      .filter(
                                        (b) =>
                                          b.batchId !== formData.bulkBatchId
                                      )
                                      .map((b) => ({
                                        value: b.batchId,
                                        label: `MO: ${b.moNumber} | Sisa: ${b.currentQty}`,
                                      }))
                                  : []
                              }
                              value={formData.bulkBatchId2}
                              onChange={(val) =>
                                setFormData({ ...formData, bulkBatchId2: val })
                              }
                              placeholder="Pilih Batch Tambahan..."
                            />
                            {formData.bulkBatchId2 && (
                              <>
                                <label className="block text-xs font-semibold mt-3 mb-1">
                                  Kuantitas Tambahan
                                </label>
                                <input
                                  type="number"
                                  step="0.01"
                                  className="w-full px-3 py-2 border rounded-lg"
                                  value={formData.qtyToProcess2}
                                  onChange={(e) =>
                                    setFormData({
                                      ...formData,
                                      qtyToProcess2: e.target.value,
                                    })
                                  }
                                />
                              </>
                            )}
                          </div>
                        </div>

                        <label className="block text-sm font-semibold text-slate-700 mt-4">
                          Jadikan Produk (SKU)
                        </label>
                        <SearchableSelect
                          options={skus
                            .filter((s) => s.type === "rebagged")
                            .map((s) => ({ value: s.id, label: s.name }))}
                          value={formData.rebagTargetSkuId}
                          onChange={(val) =>
                            setFormData({ ...formData, rebagTargetSkuId: val })
                          }
                          placeholder="Cari Produk Jadi..."
                        />

                        <label className="block text-sm font-semibold text-slate-700 mt-4">
                          Tumpukan Penerimaan
                        </label>
                        <select
                          className="w-full px-4 py-2 border rounded-lg"
                          value={formData.rebagTargetStack}
                          onChange={(e) =>
                            setFormData({
                              ...formData,
                              rebagTargetStack: e.target.value,
                            })
                          }
                          required
                        >
                          <option value="" disabled>
                            -- Pilih Tumpukan --
                          </option>
                          {STACK_LOCATIONS.map((loc) => (
                            <option key={loc} value={loc}>
                              {loc}
                            </option>
                          ))}
                        </select>
                      </>
                    )}

                    {activeOpTab === "outbound" && (
                      <>
                        <label className="block text-sm font-semibold text-slate-700">
                          Pilih Barang Jadi Dikeluarkan
                        </label>
                        <SearchableSelect
                          options={skus
                            .filter((s) => s.type === "rebagged")
                            .map((s) => ({ value: s.id, label: s.name }))}
                          value={formData.outSkuId}
                          onChange={(val) => {
                            setFormData({ ...formData, outSkuId: val });
                            setOutboundSelections({});
                          }}
                          placeholder="Cari Produk Jadi..."
                        />

                        {formData.outSkuId && (
                          <div className="mt-4 space-y-3 border-t pt-4">
                            {getAvailableBatches(formData.outSkuId).map(
                              (batch) => (
                                <div
                                  key={batch.batchId}
                                  className="flex justify-between items-center p-4 border rounded-lg"
                                >
                                  <div>
                                    <p className="text-sm font-bold">
                                      MO: {batch.moNumber}
                                    </p>
                                    <p className="text-xs text-slate-500">
                                      Tersedia: {batch.currentQty}
                                    </p>
                                  </div>
                                  <input
                                    type="number"
                                    max={batch.currentQty}
                                    min="0"
                                    className="w-32 px-3 py-2 border rounded-lg text-center"
                                    placeholder="0"
                                    value={
                                      outboundSelections[batch.batchId] || ""
                                    }
                                    onChange={(e) => {
                                      if (
                                        parseFloat(e.target.value) >
                                        batch.currentQty
                                      )
                                        return;
                                      setOutboundSelections({
                                        ...outboundSelections,
                                        [batch.batchId]: e.target.value,
                                      });
                                    }}
                                  />
                                </div>
                              )
                            )}
                          </div>
                        )}
                      </>
                    )}

                    <div className="flex justify-end pt-4 border-t gap-3">
                      <button
                        type="button"
                        onClick={() => {
                          setFormData(initialFormData);
                          setOutboundSelections({});
                        }}
                        className="px-6 py-2 bg-slate-200 text-slate-700 rounded-xl font-bold hover:bg-slate-300"
                      >
                        Batal
                      </button>
                      <button
                        type="submit"
                        className="px-6 py-2 bg-red-600 text-white rounded-xl font-bold hover:bg-red-700 flex items-center gap-2"
                      >
                        Simpan <ArrowRight size={18} />
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            </div>
          )}

          {activeMenu === "history" && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold">Riwayat</h1>
                <button
                  onClick={handleDownloadRiwayat}
                  className="bg-green-600 text-white px-4 py-2 rounded-lg font-bold flex gap-2"
                >
                  <FileSpreadsheet size={16} /> Unduh CSV
                </button>
              </div>
              <div className="bg-white rounded-2xl shadow-sm border p-4">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="p-3">Tgl</th>
                      <th className="p-3">Barang</th>
                      <th className="p-3 text-right">Qty</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions
                      .filter((t) => t.type === "REBAGGING")
                      .map((trx, idx) => (
                        <tr key={idx} className="border-b">
                          <td className="p-3">
                            {new Date(trx.date).toLocaleDateString()}
                          </td>
                          <td className="p-3">{trx.skuName}</td>
                          <td className="p-3 text-right font-bold text-red-600">
                            +{trx.qtyChange}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeMenu === "settings" && hasAccess(["Super Admin"]) && (
            <div className="space-y-6">
              <h1 className="text-2xl font-bold">Pengaturan</h1>
              <div className="bg-white rounded-2xl border flex flex-col md:flex-row">
                <div className="p-4 border-b md:border-b-0 md:border-r w-full md:w-48 space-y-2">
                  <button
                    onClick={() => setActiveTabSettings("users")}
                    className={`w-full text-left p-2 rounded ${
                      activeTabSettings === "users"
                        ? "bg-slate-100 font-bold"
                        : ""
                    }`}
                  >
                    User
                  </button>
                  <button
                    onClick={() => setActiveTabSettings("sku")}
                    className={`w-full text-left p-2 rounded ${
                      activeTabSettings === "sku"
                        ? "bg-slate-100 font-bold"
                        : ""
                    }`}
                  >
                    Master SKU
                  </button>
                  <button
                    onClick={() => setActiveTabSettings("import")}
                    className={`w-full text-left p-2 rounded ${
                      activeTabSettings === "import"
                        ? "bg-slate-100 font-bold"
                        : ""
                    }`}
                  >
                    Import CSV
                  </button>
                </div>
                <div className="p-6 flex-1">
                  {activeTabSettings === "users" && (
                    <div>
                      <button
                        onClick={() => setIsAddingUser(!isAddingUser)}
                        className="mb-4 bg-slate-800 text-white px-4 py-2 rounded"
                      >
                        Tambah User
                      </button>
                      {isAddingUser && (
                        <form
                          onSubmit={handleAddUser}
                          className="flex gap-2 mb-4"
                        >
                          <input
                            required
                            placeholder="Username"
                            className="border p-2 rounded"
                            value={newUserForm.username}
                            onChange={(e) =>
                              setNewUserForm({
                                ...newUserForm,
                                username: e.target.value,
                              })
                            }
                          />
                          <input
                            required
                            type="password"
                            placeholder="Password"
                            className="border p-2 rounded"
                            value={newUserForm.password}
                            onChange={(e) =>
                              setNewUserForm({
                                ...newUserForm,
                                password: e.target.value,
                              })
                            }
                          />
                          <select
                            className="border p-2 rounded"
                            value={newUserForm.role}
                            onChange={(e) =>
                              setNewUserForm({
                                ...newUserForm,
                                role: e.target.value,
                              })
                            }
                          >
                            <option value="Operator">Operator</option>
                            <option value="Admin">Admin</option>
                            <option value="Super Admin">Super Admin</option>
                          </select>
                          <button className="bg-red-600 text-white p-2 rounded">
                            Simpan
                          </button>
                        </form>
                      )}
                      {users.map((u) => (
                        <div
                          key={u.username}
                          className="flex justify-between border p-3 rounded mb-2"
                        >
                          <span>
                            {u.username} ({u.role})
                          </span>
                          <button
                            onClick={() => handleDeleteUser(u.username)}
                            disabled={u.username === currentUser.username}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  {activeTabSettings === "sku" && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="p-2 text-left">ID</th>
                            <th className="p-2 text-left">Nama</th>
                            <th className="p-2">Aksi</th>
                          </tr>
                        </thead>
                        <tbody>
                          {skus.map((s) => (
                            <tr key={s.id} className="border-b">
                              <td className="p-2">{s.id}</td>
                              <td className="p-2">{s.name}</td>
                              <td className="p-2 text-center">
                                <button onClick={() => handleDeleteSKU(s.id)}>
                                  <Trash2 size={16} />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {activeTabSettings === "import" && (
                    <div className="p-8 border-2 border-dashed rounded text-center">
                      <input
                        type="file"
                        accept=".csv"
                        onChange={handleImportCSV}
                      />
                      <p className="mt-2 text-xs text-slate-500">
                        Kolom CSV: Tipe(bulk/rebagged), ID, Nama, Satuan,
                        Konversi
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
