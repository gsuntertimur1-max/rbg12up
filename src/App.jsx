import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  Package, Download, UserPlus, Trash2, Home, PackagePlus,
  FileDown, FileUp, ArrowRightLeft, Settings, Users,
  ArrowRight, Settings2, Database, History, LogOut,
  Boxes, FileSpreadsheet, Search, CheckCircle, Image as ImageIcon
} from "lucide-react";
import {
  BarChart, Bar, PieChart, Pie, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, Cell, ResponsiveContainer
} from 'recharts';
import * as XLSX from 'xlsx';

// --- FIREBASE IMPORTS ---
import { initializeApp, getApps, getApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth, signInAnonymously, onAuthStateChanged } from "firebase/auth";
import { getFirestore, doc, setDoc, onSnapshot, collection, deleteDoc, writeBatch } from "firebase/firestore";

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
        className="w-full border border-slate-300 rounded-lg p-2.5 text-sm cursor-pointer bg-white flex justify-between items-center"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className={`truncate ${!value ? "text-slate-400" : "text-slate-800"}`}>
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <span className="text-slate-400 text-xs ml-2">▼</span>
      </div>
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 flex flex-col">
          <div className="p-2 border-b sticky top-0 bg-white">
            <input type="text" className="w-full px-2 py-1.5 text-sm border rounded-md outline-none" placeholder="Cari..." value={search} onChange={(e) => setSearch(e.target.value)} autoFocus />
          </div>
          <div className="overflow-y-auto">
            {filteredOptions.length === 0 ? (
              <div className="p-3 text-sm text-slate-500 text-center">Tidak ada hasil</div>
            ) : (
              filteredOptions.map(opt => (
                <div key={opt.value} className="p-2.5 text-sm cursor-pointer hover:bg-slate-50 border-b last:border-0" onClick={() => { onChange(opt.value); setIsOpen(false); setSearch(""); }}>
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
  const [systemConfig, setSystemConfig] = useState({ name: "Sistem Rebagging Terpadu", logo: null });
  
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [loginError, setLoginError] = useState("");
  const [activeMenu, setActiveMenu] = useState("dashboard");
  const [activeTabSettings, setActiveTabSettings] = useState("users");
  const [activeInvTab, setActiveInvTab] = useState("bulk");
  const [notification, setNotification] = useState(null);
  
  const [newUserForm, setNewUserForm] = useState({ username: "", password: "", role: "Operator" });
  const [fbUser, setFbUser] = useState(null);
  const [dbLoading, setDbLoading] = useState(true);
  const [activeOpTab, setActiveOpTab] = useState("inbound");
  const [historyStartDate, setHistoryStartDate] = useState("");
  const [historyEndDate, setHistoryEndDate] = useState("");

  const initialFormData = {
    inSkuId: "", inQty: "", inMoNumber: "", inTmNumber: "", inSourceWarehouse: "",
    rebagTargetSkuId: "", rebagTargetStack: "", bulkSkuId: "", bulkBatchId: "", qtyToProcess: "", bulkBatchId2: "", qtyToProcess2: "", outSkuId: ""
  };
  const [formData, setFormData] = useState(initialFormData);
  const [outboundSelections, setOutboundSelections] = useState({});

  useEffect(() => {
    if (!auth) return setDbLoading(false);
    const initAuth = async () => { try { await signInAnonymously(auth); } catch(e){} };
    initAuth();
    return onAuthStateChanged(auth, setFbUser);
  }, []);

  useEffect(() => {
    if (!fbUser || !db) return;
    const unsubUsers = onSnapshot(collection(db, "artifacts", appId, "public", "data", "users"), snap => {
      if (snap.empty) DEFAULT_USERS.forEach(u => setDoc(doc(db, "artifacts", appId, "public", "data", "users", u.username), u));
      else setUsers(snap.docs.map(d => d.data()));
    });
    const unsubSkus = onSnapshot(collection(db, "artifacts", appId, "public", "data", "skus"), snap => {
      setSkus(snap.docs.map(d => d.data()));
      setDbLoading(false);
    });
    const unsubBatches = onSnapshot(collection(db, "artifacts", appId, "public", "data", "batches"), snap => {
      setInventoryBatches(snap.docs.map(d => d.data()));
    });
    const unsubTx = onSnapshot(collection(db, "artifacts", appId, "public", "data", "transactions"), snap => {
      setTransactions(snap.docs.map(d => d.data()).sort((a,b) => new Date(b.date) - new Date(a.date)));
    });
    const unsubConfig = onSnapshot(doc(db, "artifacts", appId, "public", "data", "config", "system"), snap => {
      if (snap.exists()) setSystemConfig(snap.data());
    });
    return () => { unsubUsers(); unsubSkus(); unsubBatches(); unsubTx(); unsubConfig(); };
  }, [fbUser]);

  const showNotif = (msg) => { setNotification(msg); setTimeout(() => setNotification(null), 3000); };
  const hasAccess = (roles) => currentUser && roles.includes(currentUser.role);

  const handleLogin = (e) => {
    e.preventDefault();
    const user = users.find(u => u.username === loginForm.username && u.password === loginForm.password);
    if (user) { setCurrentUser(user); localStorage.setItem("rebagging_session", JSON.stringify(user)); setLoginError(""); }
    else setLoginError("Username/password salah!");
  };

  const handleLogout = () => { setCurrentUser(null); localStorage.removeItem("rebagging_session"); setActiveMenu("dashboard"); };

  const handleTransactionSubmit = async (e) => {
    e.preventDefault();
    const date = new Date().toISOString();
    let txData, batchData, batchUpdates = [];

    if (activeOpTab === "inbound") {
      const sku = skus.find(s => s.id === formData.inSkuId);
      const qty = parseFloat(formData.inQty);
      const batchId = `INB-${Date.now()}`;
      batchData = { batchId, skuId: sku.id, initialQty: qty, currentQty: qty, sourceWarehouse: formData.inSourceWarehouse, date };
      txData = { id: `TRX-${Date.now()}`, date, type: "INBOUND", skuId: sku.id, skuName: sku.name, qtyChange: qty, unit: sku.unit, operator: currentUser.username, sourceWarehouse: formData.inSourceWarehouse };
      batchUpdates.push({ type: 'set', id: batchId, data: batchData });

    } else if (activeOpTab === "rebagging") {
      const b1 = inventoryBatches.find(b => b.batchId === formData.bulkBatchId);
      const targetSku = skus.find(s => s.id === formData.rebagTargetSkuId);
      const qty = parseFloat(formData.qtyToProcess) || 0;
      if (qty > b1.currentQty) return alert("Qty melebihi stok!");
      const resultQty = Math.floor(qty / (targetSku.conversionRate || 1));
      const newBatchId = `RBG-${Date.now()}`;
      batchData = { batchId: newBatchId, skuId: targetSku.id, currentQty: resultQty, sourceWarehouse: b1.sourceWarehouse, targetStack: formData.rebagTargetStack, date };
      txData = { id: `TRX-${Date.now()}`, date, type: "REBAGGING", skuId: targetSku.id, skuName: targetSku.name, qtyChange: resultQty, unit: targetSku.unit, operator: currentUser.username, targetStack: formData.rebagTargetStack };
      batchUpdates.push({ type: 'update', id: b1.batchId, data: { ...b1, currentQty: b1.currentQty - qty } });
      batchUpdates.push({ type: 'set', id: newBatchId, data: batchData });

    } else if (activeOpTab === "outbound") {
      let hasOutbound = false;
      Object.entries(outboundSelections).forEach(([bId, qtyStr]) => {
        const q = parseFloat(qtyStr);
        if (q > 0) {
          hasOutbound = true;
          const b = inventoryBatches.find(x => x.batchId === bId);
          batchUpdates.push({ type: 'update', id: bId, data: { ...b, currentQty: b.currentQty - q } });
          txData = { id: `TRX-${Date.now()}-${bId}`, date, type: "OUTBOUND", skuId: formData.outSkuId, skuName: skus.find(s=>s.id===formData.outSkuId).name, qtyChange: q, operator: currentUser.username };
        }
      });
      if (!hasOutbound) return alert("Isi qty untuk outbound!");
    }

    if (db) {
      for (const update of batchUpdates) await setDoc(doc(db, "artifacts", appId, "public", "data", "batches", update.id), update.data);
      if (txData) await setDoc(doc(db, "artifacts", appId, "public", "data", "transactions", txData.id), txData);
    }
    showNotif("Transaksi Berhasil");
    setFormData(initialFormData); setOutboundSelections({});
  };

  // RECHARTS DATA
  const stockByWarehouseData = useMemo(() => {
    const data = {};
    inventoryBatches.filter(b => b.currentQty > 0).forEach(b => {
      const sw = b.sourceWarehouse || "Unknown";
      if(!data[sw]) data[sw] = { name: sw, kg: 0, pack: 0 };
      const sku = skus.find(s => s.id === b.skuId);
      if (sku && sku.unit?.toUpperCase() === 'KG') data[sw].kg += b.currentQty;
      else data[sw].pack += b.currentQty;
    });
    return Object.values(data);
  }, [inventoryBatches, skus]);

  const compositionData = [
    { name: 'Bahan Baku', value: skus.filter(s=>s.type==='bulk').length },
    { name: 'Barang Jadi', value: skus.filter(s=>s.type==='rebagged').length }
  ];

  // IMPORT/EXPORT EXCEL
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
        showNotif(`${data.length} SKU Diimpor`);
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
      Tanggal: new Date(t.date).toLocaleString(), Tipe: t.type, SKU: t.skuName, Qty: t.qtyChange, Operator: t.operator
    })));
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Riwayat");
    XLSX.writeFile(wb, "Riwayat_Rebagging.xlsx");
  };

  const handleUpdateConfig = async (e) => {
    e.preventDefault();
    if (db) await setDoc(doc(db, "artifacts", appId, "public", "data", "config", "system"), systemConfig);
    showNotif("Sistem Diperbarui");
  };

  if (dbLoading) return <div className="min-h-screen flex items-center justify-center"><Package className="animate-pulse w-12 h-12 text-red-600"/></div>;
  if (!currentUser) return (
    <div className="min-h-screen flex items-center justify-center bg-red-600 p-4">
      <div className="bg-white p-8 rounded-2xl shadow-2xl w-full max-w-sm">
        <h1 className="text-2xl font-black text-center mb-6 text-slate-800">{systemConfig.name}</h1>
        {loginError && <p className="text-red-500 text-sm mb-4 font-semibold text-center">{loginError}</p>}
        <form onSubmit={handleLogin} className="space-y-4">
          <input className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-red-500 transition-colors" placeholder="Username" value={loginForm.username} onChange={e=>setLoginForm({...loginForm, username: e.target.value})} />
          <input className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-red-500 transition-colors" type="password" placeholder="Password" value={loginForm.password} onChange={e=>setLoginForm({...loginForm, password: e.target.value})} />
          <button className="w-full bg-red-600 text-white font-bold py-3 rounded-lg hover:bg-red-700 transition-colors shadow-lg">Login ke Sistem</button>
        </form>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {notification && <div className="fixed top-4 right-4 bg-green-600 text-white px-4 py-2 rounded shadow-lg z-50 animate-bounce">{notification}</div>}
      
      {/* SIDEBAR */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="p-4 border-b border-slate-700 font-bold flex items-center gap-2">
          {systemConfig.logo ? <img src={systemConfig.logo} alt="logo" className="w-8 h-8 rounded bg-white" /> : <Package />}
          <span className="truncate">{systemConfig.name}</span>
        </div>
        <nav className="p-4 flex-1 space-y-2 text-sm">
          <button onClick={()=>setActiveMenu("dashboard")} className={`w-full flex items-center gap-2 p-3 rounded-lg transition-colors ${activeMenu==="dashboard"?"bg-red-600 shadow-md":"hover:bg-slate-800"}`}><Home size={18}/> Dashboard</button>
          <button onClick={()=>setActiveMenu("inventory")} className={`w-full flex items-center gap-2 p-3 rounded-lg transition-colors ${activeMenu==="inventory"?"bg-red-600 shadow-md":"hover:bg-slate-800"}`}><Boxes size={18}/> Inventori</button>
          {hasAccess(["Super Admin", "Admin", "Operator"]) && <button onClick={()=>setActiveMenu("operations")} className={`w-full flex items-center gap-2 p-3 rounded-lg transition-colors ${activeMenu==="operations"?"bg-red-600 shadow-md":"hover:bg-slate-800"}`}><PackagePlus size={18}/> Operasi</button>}
          <button onClick={()=>setActiveMenu("history")} className={`w-full flex items-center gap-2 p-3 rounded-lg transition-colors ${activeMenu==="history"?"bg-red-600 shadow-md":"hover:bg-slate-800"}`}><History size={18}/> Riwayat</button>
          {hasAccess(["Super Admin"]) && <button onClick={()=>setActiveMenu("settings")} className={`w-full flex items-center gap-2 p-3 rounded-lg transition-colors ${activeMenu==="settings"?"bg-slate-700 shadow-md":"hover:bg-slate-800"}`}><Settings size={18}/> Pengaturan</button>}
        </nav>
        <button onClick={handleLogout} className="m-4 p-3 bg-slate-800 hover:bg-red-600 transition-colors rounded-lg flex justify-center"><LogOut size={18}/></button>
      </aside>

      {/* CONTENT */}
      <main className="flex-1 p-8 overflow-y-auto">
        
        {/* DASHBOARD */}
        {activeMenu === "dashboard" && (
          <div className="space-y-6">
            <h1 className="text-3xl font-black text-slate-800 tracking-tight">Dashboard Statistik</h1>
            <div className="grid grid-cols-2 gap-6 h-96">
              <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                <h3 className="font-bold mb-4 text-slate-700">Stok Berdasarkan Gudang Asal</h3>
                <ResponsiveContainer width="100%" height="85%">
                  <BarChart data={stockByWarehouseData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false}/>
                    <XAxis dataKey="name" axisLine={false} tickLine={false}/>
                    <YAxis axisLine={false} tickLine={false}/>
                    <Tooltip cursor={{fill: 'transparent'}} contentStyle={{borderRadius: '8px'}}/>
                    <Legend iconType="circle"/>
                    <Bar dataKey="kg" fill="#ef4444" name="Kilogram (KG)" maxBarSize={60} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="pack" fill="#3b82f6" name="Pack" maxBarSize={60} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                <h3 className="font-bold mb-4 text-slate-700">Komposisi SKU</h3>
                <ResponsiveContainer width="100%" height="85%">
                  <PieChart>
                    <Pie data={compositionData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} fill="#8884d8" dataKey="value" label paddingAngle={5}>
                      <Cell fill="#ef4444"/><Cell fill="#3b82f6"/>
                    </Pie>
                    <Tooltip contentStyle={{borderRadius: '8px'}}/>
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
            <h1 className="text-3xl font-black text-slate-800 tracking-tight">Inventori Gudang</h1>
            <div className="flex gap-6 border-b border-slate-200">
              <button onClick={()=>setActiveInvTab('bulk')} className={`pb-3 text-sm font-semibold transition-all ${activeInvTab==='bulk'?'border-b-2 border-red-600 text-red-600':'text-slate-500 hover:text-slate-800'}`}>Bahan Baku (Curah)</button>
              <button onClick={()=>setActiveInvTab('rebagged')} className={`pb-3 text-sm font-semibold transition-all ${activeInvTab==='rebagged'?'border-b-2 border-red-600 text-red-600':'text-slate-500 hover:text-slate-800'}`}>Barang Jadi (Kemasan)</button>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
              <table className="w-full text-sm text-left">
                <thead className="bg-slate-50 text-slate-600">
                  <tr><th className="p-4 font-semibold">ID SKU</th><th className="p-4 font-semibold">Nama Barang</th><th className="p-4 font-semibold">Gudang Asal</th><th className="p-4 font-semibold text-right">Total Stok</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {skus.filter(s=>s.type===activeInvTab).map(sku => {
                    const batches = inventoryBatches.filter(b=>b.skuId===sku.id && b.currentQty>0);
                    const total = batches.reduce((acc, b) => acc+b.currentQty, 0);
                    const sources = [...new Set(batches.map(b=>b.sourceWarehouse))].join(", ") || "-";
                    return (
                      <tr key={sku.id} className="hover:bg-slate-50 transition-colors">
                        <td className="p-4 text-slate-500 font-mono">{sku.id}</td>
                        <td className="p-4 font-medium text-slate-800">{sku.name}</td>
                        <td className="p-4 text-slate-600">{sources}</td>
                        <td className="p-4 text-right font-bold text-slate-800">{total} <span className="font-normal text-slate-500">{sku.unit}</span></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* OPERATIONS */}
        {activeMenu === "operations" && (
          <div className="space-y-6">
             <h1 className="text-3xl font-black text-slate-800 tracking-tight">Operasi Gudang</h1>
             <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200">
                <div className="flex gap-6 mb-8 border-b border-slate-200">
                  <button onClick={()=>setActiveOpTab('inbound')} className={`pb-3 text-sm font-semibold transition-all ${activeOpTab==='inbound'?'text-red-600 border-b-2 border-red-600':'text-slate-500 hover:text-slate-800'}`}>Inbound Masuk</button>
                  <button onClick={()=>setActiveOpTab('rebagging')} className={`pb-3 text-sm font-semibold transition-all ${activeOpTab==='rebagging'?'text-red-600 border-b-2 border-red-600':'text-slate-500 hover:text-slate-800'}`}>Proses Rebagging</button>
                  <button onClick={()=>setActiveOpTab('outbound')} className={`pb-3 text-sm font-semibold transition-all ${activeOpTab==='outbound'?'text-red-600 border-b-2 border-red-600':'text-slate-500 hover:text-slate-800'}`}>Outbound Keluar</button>
                </div>
                <form onSubmit={handleTransactionSubmit} className="space-y-5 max-w-xl">
                  {/* INBOUND UI */}
                  {activeOpTab === 'inbound' && (
                    <>
                      <div><label className="block text-sm font-semibold text-slate-700 mb-2">Pilih Bahan Baku</label><SearchableSelect options={skus.filter(s=>s.type==='bulk').map(s=>({value:s.id, label:s.name}))} value={formData.inSkuId} onChange={v=>setFormData({...formData, inSkuId:v})} placeholder="Ketik atau pilih SKU..." /></div>
                      <div><label className="block text-sm font-semibold text-slate-700 mb-2">Jumlah (Qty)</label><input type="number" className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-red-500" value={formData.inQty} onChange={e=>setFormData({...formData, inQty:e.target.value})} required/></div>
                      <div><label className="block text-sm font-semibold text-slate-700 mb-2">Asal Gudang</label><input type="text" className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-red-500" value={formData.inSourceWarehouse} onChange={e=>setFormData({...formData, inSourceWarehouse:e.target.value})} required/></div>
                    </>
                  )}
                  {/* REBAGGING UI */}
                  {activeOpTab === 'rebagging' && (
                    <>
                      <div><label className="block text-sm font-semibold text-slate-700 mb-2">Bahan Baku Asal</label><SearchableSelect options={skus.filter(s=>s.type==='bulk').map(s=>({value:s.id, label:s.name}))} value={formData.bulkSkuId} onChange={v=>setFormData({...formData, bulkSkuId:v})} placeholder="Pilih Sumber SKU..." /></div>
                      {formData.bulkSkuId && <div><label className="block text-sm font-semibold text-slate-700 mb-2">Pilih Batch Spesifik</label><SearchableSelect options={inventoryBatches.filter(b=>b.skuId===formData.bulkSkuId && b.currentQty>0).map(b=>({value:b.batchId, label:`${b.sourceWarehouse} (Sisa: ${b.currentQty})`}))} value={formData.bulkBatchId} onChange={v=>setFormData({...formData, bulkBatchId:v})} placeholder="Pilih Batch yang akan direbagging..." /></div>}
                      <div><label className="block text-sm font-semibold text-slate-700 mb-2">Kuantitas Diproses</label><input type="number" className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-red-500" value={formData.qtyToProcess} onChange={e=>setFormData({...formData, qtyToProcess:e.target.value})} /></div>
                      <div><label className="block text-sm font-semibold text-slate-700 mb-2">Target Barang Jadi</label><SearchableSelect options={skus.filter(s=>s.type==='rebagged').map(s=>({value:s.id, label:s.name}))} value={formData.rebagTargetSkuId} onChange={v=>setFormData({...formData, rebagTargetSkuId:v})} placeholder="Pilih SKU Hasil Rebagging..." /></div>
                      <div><label className="block text-sm font-semibold text-slate-700 mb-2">Lokasi Tumpukan Baru</label><select className="w-full p-3 border border-slate-300 rounded-lg outline-none focus:border-red-500 bg-white" value={formData.rebagTargetStack} onChange={e=>setFormData({...formData, rebagTargetStack:e.target.value})}><option value="">-- Pilih Tumpukan --</option>{STACK_LOCATIONS.map(l=><option key={l} value={l}>{l}</option>)}</select></div>
                    </>
                  )}
                  {/* OUTBOUND UI (RESTORED!) */}
                  {activeOpTab === 'outbound' && (
                    <>
                      <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">Pilih SKU Untuk Dikeluarkan</label>
                        <SearchableSelect options={skus.map(s=>({value:s.id, label:s.name}))} value={formData.outSkuId} onChange={v=>setFormData({...formData, outSkuId:v})} placeholder="Cari SKU..." />
                      </div>
                      {formData.outSkuId && (
                        <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 mt-4 space-y-3">
                          <h4 className="font-bold text-sm text-slate-700 mb-3">Tentukan Kuantitas Keluar per Batch:</h4>
                          {inventoryBatches.filter(b => b.skuId === formData.outSkuId && b.currentQty > 0).map(b => (
                            <div key={b.batchId} className="flex justify-between items-center bg-white p-3 rounded border shadow-sm">
                              <div>
                                <p className="font-semibold text-slate-800 text-sm">{b.sourceWarehouse}</p>
                                <p className="text-xs text-slate-500 font-mono">Sisa: {b.currentQty} unit</p>
                              </div>
                              <input type="number" min="0" max={b.currentQty} className="border border-slate-300 p-2 w-28 rounded-md text-center outline-none focus:border-red-500" placeholder="0" value={outboundSelections[b.batchId] || ""} onChange={e => setOutboundSelections({...outboundSelections, [b.batchId]: e.target.value})} />
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                  <button className="w-full bg-red-600 text-white font-bold py-3 mt-4 rounded-lg hover:bg-red-700 transition-colors shadow-lg">Simpan Transaksi</button>
                </form>
             </div>
          </div>
        )}

        {/* HISTORY (RESTORED BEAUTIFUL TABLE!) */}
        {activeMenu === "history" && (
          <div className="space-y-6">
            <div className="flex justify-between items-end border-b border-slate-200 pb-4">
              <h1 className="text-3xl font-black text-slate-800 tracking-tight">Riwayat Transaksi</h1>
              <div className="flex gap-3 items-center">
                <input type="date" className="border border-slate-300 p-2.5 rounded-lg text-sm outline-none focus:border-red-500 text-slate-600" value={historyStartDate} onChange={e=>setHistoryStartDate(e.target.value)} />
                <span className="text-slate-400">s/d</span>
                <input type="date" className="border border-slate-300 p-2.5 rounded-lg text-sm outline-none focus:border-red-500 text-slate-600" value={historyEndDate} onChange={e=>setHistoryEndDate(e.target.value)} />
                <button onClick={handleDownloadHistory} className="bg-green-600 hover:bg-green-700 transition-colors text-white px-5 py-2.5 rounded-lg flex items-center gap-2 font-semibold shadow-md"><Download size={18}/> Ekspor Excel</button>
              </div>
            </div>
            
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
              <table className="w-full text-sm text-left">
                <thead className="bg-slate-50 text-slate-600">
                  <tr>
                    <th className="p-4 font-semibold">Tanggal & Waktu</th>
                    <th className="p-4 font-semibold">Tipe Operasi</th>
                    <th className="p-4 font-semibold">Nama SKU / Barang</th>
                    <th className="p-4 font-semibold text-center">Mutasi (Qty)</th>
                    <th className="p-4 font-semibold">Operator</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {transactions.map(t => (
                    <tr key={t.id} className="hover:bg-slate-50 transition-colors">
                      <td className="p-4 text-slate-600">{new Date(t.date).toLocaleString('id-ID')}</td>
                      <td className="p-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-bold tracking-wider ${t.type === 'INBOUND' ? 'bg-blue-100 text-blue-700' : t.type === 'OUTBOUND' ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'}`}>
                          {t.type}
                        </span>
                      </td>
                      <td className="p-4 font-medium text-slate-800">{t.skuName}</td>
                      <td className={`p-4 text-center font-bold text-base ${t.type==='OUTBOUND' ? 'text-red-600' : 'text-green-600'}`}>
                        {t.type === 'OUTBOUND' ? '-' : '+'}{t.qtyChange}
                      </td>
                      <td className="p-4 text-slate-600 capitalize">{t.operator}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {transactions.length === 0 && <div className="text-center text-slate-400 p-8 italic">Belum ada riwayat transaksi.</div>}
            </div>
          </div>
        )}

        {/* SETTINGS */}
        {activeMenu === "settings" && hasAccess(["Super Admin"]) && (
          <div className="space-y-6">
            <h1 className="text-3xl font-black text-slate-800 tracking-tight">Pengaturan Super Admin</h1>
            <div className="flex gap-6 border-b border-slate-200">
              <button onClick={()=>setActiveTabSettings('system')} className={`pb-3 text-sm font-semibold transition-all ${activeTabSettings==='system'?'text-red-600 border-b-2 border-red-600':'text-slate-500 hover:text-slate-800'}`}>Profil Sistem</button>
              <button onClick={()=>setActiveTabSettings('sku')} className={`pb-3 text-sm font-semibold transition-all ${activeTabSettings==='sku'?'text-red-600 border-b-2 border-red-600':'text-slate-500 hover:text-slate-800'}`}>Database SKU</button>
            </div>
            
            {activeTabSettings === 'system' && (
              <form onSubmit={handleUpdateConfig} className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200 max-w-xl space-y-6">
                <div><label className="block font-bold text-slate-700 mb-2">Nama Aplikasi</label><input className="w-full border border-slate-300 p-3 rounded-lg outline-none focus:border-red-500" value={systemConfig.name} onChange={e=>setSystemConfig({...systemConfig, name: e.target.value})} /></div>
                <div>
                  <label className="block font-bold text-slate-700 mb-2">URL Logo (Opsional)</label>
                  <p className="text-xs text-slate-500 mb-2">Kosongkan jika ingin menggunakan logo kotak default.</p>
                  <input className="w-full border border-slate-300 p-3 rounded-lg outline-none focus:border-red-500" value={systemConfig.logo || ""} onChange={e=>setSystemConfig({...systemConfig, logo: e.target.value})} placeholder="https://..." />
                </div>
                <button className="bg-slate-800 text-white font-bold px-6 py-3 rounded-lg hover:bg-slate-900 shadow-md">Simpan Konfigurasi</button>
              </form>
            )}
            
            {activeTabSettings === 'sku' && (
              <div className="bg-white p-12 rounded-2xl shadow-sm text-center border-dashed border-2 border-slate-300 max-w-2xl mx-auto hover:border-red-500 transition-colors">
                <FileSpreadsheet className="mx-auto w-16 h-16 text-green-600 mb-4" />
                <h3 className="font-bold text-lg mb-2 text-slate-800">Upload Master Data SKU</h3>
                <p className="text-slate-500 mb-6 text-sm">Pastikan format file Anda adalah .xlsx atau .xls</p>
                <input type="file" accept=".xlsx, .xls" onChange={handleImportExcel} className="mx-auto block text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-red-50 file:text-red-700 hover:file:bg-red-100 cursor-pointer" />
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
