from pathlib import Path

path = Path("src/App.jsx")
s = path.read_text(encoding="utf-8")

old = '''    box(L, y, W, groupH + headerH2 + 452);
    xs.slice(1, -1).forEach((x) => line(x, y, x, y + groupH + headerH2 + 452));
    line(L, y + groupH, R, y + groupH);
    line(L, y + groupH + headerH2, R, y + groupH + headerH2);'''
new = '''    const rawTableBottom = y + groupH + headerH2 + 452;
    box(L, y, W, groupH + headerH2 + 452);
    [xs[3], xs[6]].forEach((x) => line(x, y, x, rawTableBottom));
    [xs[1], xs[2], xs[4], xs[5]].forEach((x) =>
      line(x, y + groupH, x, rawTableBottom)
    );
    line(L, y + groupH, R, y + groupH);
    line(L, y + groupH + headerH2, R, y + groupH + headerH2);'''
if old not in s:
    raise SystemExit("Raw merged header target not found")
s = s.replace(old, new, 1)

old = '''    box(L, y, W, groupH + headerH2 + 276);
    xs.slice(1, -1).forEach((x) => line(x, y, x, y + groupH + headerH2 + 276));
    line(L, y + groupH, R, y + groupH);
    line(L, y + groupH + headerH2, R, y + groupH + headerH2);'''
new = '''    const fgTableBottom = y + groupH + headerH2 + 276;
    box(L, y, W, groupH + headerH2 + 276);
    [xs[4], xs[9]].forEach((x) => line(x, y, x, fgTableBottom));
    [xs[1], xs[2], xs[3], xs[5], xs[6], xs[7], xs[8]].forEach((x) =>
      line(x, y + groupH, x, fgTableBottom)
    );
    line(L, y + groupH, R, y + groupH);
    line(L, y + groupH + headerH2, R, y + groupH + headerH2);'''
if old not in s:
    raise SystemExit("FG merged header target not found")
s = s.replace(old, new, 1)

old = '''    const footerY = pageH - 34;
    txt("Kepala GBB Sunter Timur I & II", R - 105, footerY, {
      size: 6.8,
      align: "center",
    });
    txt(approver, R - 105, footerY + 34, {'''
new = '''    const footerY = pageH - 58;
    txt("Kepala GBB Sunter Timur I & II", R - 105, footerY, {
      size: 6.8,
      align: "center",
    });
    txt(approver, R - 105, footerY + 34, {'''
if old not in s:
    raise SystemExit("FG footer target not found")
s = s.replace(old, new, 1)

path.write_text(s, encoding="utf-8")
print("Stock card final polish applied.")
