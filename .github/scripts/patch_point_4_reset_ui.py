from pathlib import Path

path = Path("src/App.jsx")
s = path.read_text(encoding="utf-8")

start = s.find('''              {activeTabSettings === 'reset-data' && isVerifiedSuperAdmin && (''')
end = s.find('''

              {activeTabSettings === 'users' && (''', start)

if start < 0 or end < 0:
    raise SystemExit("Reset UI block not found")

new_ui = r'''              {activeTabSettings === 'reset-data' && isVerifiedSuperAdmin && (
                <div className="max-w-3xl">
                  <div className="overflow-hidden rounded-2xl border border-red-200 bg-white shadow-sm">
                    <div className="border-b border-red-100 bg-gradient-to-r from-red-50 to-white p-5 sm:p-6">
                      <div className="flex items-start gap-4">
                        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-red-100 text-red-600">
                          <Trash2 size={22}/>
                        </div>
                        <div>
                          <div className="text-xs font-black uppercase tracking-[0.16em] text-red-500">Data Operasional</div>
                          <h3 className="mt-1 text-xl font-black text-slate-900">Arsip & Reset Data Uji</h3>
                          <p className="mt-2 text-sm leading-6 text-slate-600">
                            Reset riwayat saja sudah dinonaktifkan karena dapat membuat stok tidak mempunyai jejak transaksi. Reset Data Uji sekarang membersihkan seluruh data operasional yang saling terkait secara bersamaan.
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="p-5 sm:p-6 space-y-5">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
                          <p className="text-xs font-bold uppercase tracking-wider text-blue-500">Arsip Saja</p>
                          <p className="mt-2 text-sm font-black text-blue-900">Download Excel Tanpa Menghapus</p>
                          <p className="mt-1 text-xs leading-5 text-blue-700">
                            Menyimpan snapshot Transactions, Batches, TM-MO, Batch Sequence, dan data TM legacy.
                          </p>
                        </div>
                        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
                          <p className="text-xs font-bold uppercase tracking-wider text-red-500">Reset Data Uji</p>
                          <p className="mt-2 text-sm font-black text-red-900">Kosongkan Data Operasional</p>
                          <p className="mt-1 text-xs leading-5 text-red-700">
                            Transaksi, stok/batch, mapping TM-MO, dan sequence batch akan dihapus bersama. Master SKU, Komposisi, Pengguna, dan Konfigurasi tetap ada.
                          </p>
                        </div>
                      </div>

                      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
                        <strong>Kenapa tidak ada reset per periode?</strong> Menghapus sebagian transaksi sementara saldo batch tetap berjalan dapat memutus traceability dan membuat kartu stok tidak konsisten. Untuk menyimpan data lama tanpa menghapus, gunakan Arsip Data Operasional.
                      </div>

                      <div className="rounded-xl border border-green-200 bg-green-50 p-4 text-sm leading-6 text-green-800">
                        <strong>Backup otomatis:</strong> saat Reset Data Uji dijalankan, sistem membuat dan mengunduh file Excel arsip sebelum penghapusan dimulai.
                      </div>

                      <div className="flex flex-col sm:flex-row gap-3">
                        <button
                          type="button"
                          onClick={handleArchiveOperationalData}
                          disabled={resetHistoryLoading}
                          className="inline-flex items-center justify-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-5 py-3 text-sm font-black text-blue-700 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <Download size={18}/> Arsip Data Operasional
                        </button>

                        <button
                          type="button"
                          onClick={handleResetTransactionHistory}
                          disabled={resetHistoryLoading}
                          className="inline-flex items-center justify-center gap-2 rounded-xl bg-red-600 px-5 py-3 text-sm font-black text-white shadow-lg shadow-red-100 transition-all hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:shadow-none"
                        >
                          <Trash2 size={18}/>
                          {resetHistoryLoading ? "Memproses..." : "Reset Data Uji"}
                        </button>
                      </div>

                      <p className="text-xs leading-5 text-slate-400">
                        Reset memerlukan konfirmasi dua tahap dan pengetikan tepat "RESET DATA UJI".
                      </p>
                    </div>
                  </div>
                </div>
              )}'''

s = s[:start] + new_ui + s[end:]

s = s.replace(
'''                      <Trash2 size={17}/> Reset Data''',
'''                      <Trash2 size={17}/> Arsip / Reset Data''',
1
)

path.write_text(s, encoding="utf-8")
print("Safe reset UI patch applied.")
