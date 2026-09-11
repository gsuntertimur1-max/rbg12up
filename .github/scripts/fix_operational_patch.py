from pathlib import Path

path = Path('.github/scripts/operational_hardening_patch.py')
text = path.read_text(encoding='utf-8')
old = '''replace_once(\n    '              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-x-auto w-full">',\n    inventory_priority,\n    "inventory priority and mobile cards",\n)'''
new = '''replace_once(\n    '              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-x-auto w-full">\\n                <table className="w-full text-sm text-left min-w-[920px]">',\n    inventory_priority + '\\n                <table className="w-full text-sm text-left min-w-[920px]">',\n    "inventory priority and mobile cards",\n)'''
if text.count(old) != 1:
    raise SystemExit(f'Expected one ambiguous inventory patch block, found {text.count(old)}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
