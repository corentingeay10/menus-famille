import argparse
import json
import os
import re
import threading
import unicodedata
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")

DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MEALS = ["midi", "soir"]

RECIPES = [
    {
        "id": "pates-bolognaise",
        "name": "Pâtes bolognaise",
        "child_friendly": True,
        "ingredients": ["pâtes", "viande hachée", "sauce tomate", "oignon", "huile d'olive"],
        "instructions": "Faire revenir l'oignon, ajouter la viande, puis la sauce tomate. Servir sur les pâtes.",
    },
    {
        "id": "puree-jambon",
        "name": "Purée de pommes de terre au jambon",
        "child_friendly": True,
        "ingredients": ["pommes de terre", "lait", "beurre", "jambon blanc"],
        "instructions": "Cuire les pommes de terre, écraser avec lait et beurre. Ajouter le jambon coupé en petits morceaux.",
    },
    {
        "id": "omelette-fromage",
        "name": "Omelette au fromage",
        "child_friendly": True,
        "ingredients": ["œufs", "fromage râpé", "beurre", "lait"],
        "instructions": "Battre les œufs avec le lait, cuire à feu doux avec le beurre, ajouter le fromage.",
    },
    {
        "id": "saumon-vapeur-legumes",
        "name": "Saumon vapeur et légumes",
        "child_friendly": True,
        "ingredients": ["saumon", "carottes", "courgette", "riz", "citron"],
        "instructions": "Cuire le saumon à la vapeur avec le citron, servir avec le riz et les légumes cuits à l'eau.",
    },
    {
        "id": "gratin-courgettes",
        "name": "Gratin de courgettes",
        "child_friendly": True,
        "ingredients": ["courgettes", "crème fraîche", "œufs", "fromage râpé"],
        "instructions": "Trancher les courgettes, mélanger avec crème, œufs et fromage, enfourner 30 min.",
    },
    {
        "id": "soupe-de-legumes",
        "name": "Soupe de légumes maison",
        "child_friendly": True,
        "ingredients": ["pommes de terre", "carottes", "poireau", "bouillon de légumes"],
        "instructions": "Faire cuire les légumes dans le bouillon, mixer finement. Texture lisse idéale pour bébé.",
    },
    {
        "id": "poulet-riz",
        "name": "Poulet rôti et riz",
        "child_friendly": True,
        "ingredients": ["blanc de poulet", "riz", "carottes", "huile d'olive"],
        "instructions": "Cuire le poulet à la poêle, servir avec du riz et des carottes vapeur coupées en petits dés.",
    },
    {
        "id": "coquillettes-jambon",
        "name": "Coquillettes au jambon et fromage",
        "child_friendly": True,
        "ingredients": ["coquillettes", "jambon blanc", "fromage râpé", "crème fraîche"],
        "instructions": "Cuire les coquillettes, mélanger avec la crème, le jambon en morceaux et le fromage.",
    },
    {
        "id": "lasagnes",
        "name": "Lasagnes bolognaise",
        "child_friendly": False,
        "ingredients": ["pâtes à lasagne", "viande hachée", "sauce tomate", "béchamel", "fromage râpé"],
        "instructions": "Alterner couches de pâtes, bolognaise et béchamel, gratiner au four.",
    },
    {
        "id": "tarte-saumon-epinards",
        "name": "Tarte saumon-épinards",
        "child_friendly": False,
        "ingredients": ["pâte brisée", "saumon", "épinards", "crème fraîche", "œufs"],
        "instructions": "Étaler la pâte, garnir de saumon et épinards, verser le mélange crème-œufs, cuire 35 min.",
    },
    {
        "id": "ratatouille",
        "name": "Ratatouille et semoule",
        "child_friendly": False,
        "ingredients": ["courgettes", "aubergine", "poivron", "sauce tomate", "semoule"],
        "instructions": "Faire mijoter les légumes coupés en dés avec la sauce tomate, servir avec la semoule.",
    },
    {
        "id": "hachis-parmentier",
        "name": "Hachis Parmentier",
        "child_friendly": True,
        "ingredients": ["viande hachée", "pommes de terre", "lait", "beurre", "fromage râpé"],
        "instructions": "Préparer une purée, étaler la viande cuite dans un plat, recouvrir de purée et gratiner.",
    },
]

DEFAULT_DATA = {
    "menu": {
        day: {meal: {"text": "", "persons": 2, "baby": ""} for meal in MEALS}
        for day in DAYS
    },
    "shopping": [],
    "inventory": [],
    "recipes": [],
}

lock = threading.Lock()


def normalize(text):
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


def load_data():
    if not os.path.exists(DATA_FILE):
        return json.loads(json.dumps(DEFAULT_DATA))
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    for key, default in DEFAULT_DATA.items():
        data.setdefault(key, json.loads(json.dumps(default)))
    for day in DAYS:
        data["menu"].setdefault(day, {})
        for meal in MEALS:
            entry = data["menu"][day].get(meal)
            if isinstance(entry, str):
                data["menu"][day][meal] = {"text": entry, "persons": 2, "baby": ""}
            elif not isinstance(entry, dict):
                data["menu"][day][meal] = {"text": "", "persons": 2, "baby": ""}
    return data


def save_data(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


def has_ingredient(inventory_names, ingredient):
    target = normalize(ingredient)
    for item in inventory_names:
        item_n = normalize(item)
        if item_n == target or target in item_n or item_n in target:
            return True
    return False


def all_recipes(data):
    return RECIPES + data.get("recipes", [])


def tokens(text):
    return [t for t in re.split(r"[^a-z0-9]+", normalize(text)) if len(t) >= 3]


def find_recipe(text, recipes):
    t = normalize(text)
    if not t:
        return None
    for r in recipes:
        rn = normalize(r["name"])
        if t == rn or t in rn or rn in t:
            return r
    tt = set(tokens(text))
    if tt:
        for r in recipes:
            if tt.issubset(set(tokens(r["name"]))):
                return r
    return None


def add_missing_to_shopping(data, recipe):
    names = [i["name"] for i in data["inventory"]]
    added = 0
    for ing in recipe["ingredients"]:
        if has_ingredient(names, ing):
            continue
        listed = False
        for s in data["shopping"]:
            a, b = normalize(ing), normalize(s["name"])
            if a == b or a in b or b in a:
                listed = True
                break
        if not listed:
            data["shopping"].append({"id": uuid.uuid4().hex[:8], "name": ing, "checked": False})
            added += 1
    return added


def suggestions(inventory_names, data=None):
    result = []
    for recipe in all_recipes(data or {"recipes": []}):
        missing = [i for i in recipe["ingredients"] if not has_ingredient(inventory_names, i)]
        result.append(
            {
                "id": recipe["id"],
                "name": recipe["name"],
                "child_friendly": recipe["child_friendly"],
                "ingredients": recipe["ingredients"],
                "missing": missing,
                "missing_count": len(missing),
                "instructions": recipe["instructions"],
            }
        )
    result.sort(key=lambda r: (r["missing_count"], not r["child_friendly"], r["name"]))
    return result


PAGE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Menus de la semaine</title>
<style>
:root { --bg:#f6f4ef; --card:#ffffff; --ink:#2b2b2b; --accent:#c2571b; --accent2:#2e7d5b; --line:#e3ded4; }
* { box-sizing:border-box; }
body { margin:0; font-family:-apple-system, "Segoe UI", Roboto, sans-serif; background:var(--bg); color:var(--ink); }
header { background:var(--accent); color:#fff; padding:14px 16px; }
header h1 { margin:0; font-size:1.15rem; }
nav { display:flex; gap:4px; padding:8px 8px 0; background:var(--bg); flex-wrap:wrap; }
nav button { flex:1; min-width:70px; padding:12px 6px; border:1px solid var(--line); background:var(--card); border-radius:10px 10px 0 0; font-size:.95rem; cursor:pointer; }
nav button.active { background:var(--card); border-bottom-color:var(--card); font-weight:700; color:var(--accent); }
main { padding:12px; max-width:760px; margin:0 auto 60px; }
.tab { display:none; background:var(--card); border:1px solid var(--line); border-radius:0 10px 10px 10px; padding:14px; }
.tab.active { display:block; }
h2 { margin:4px 0 12px; font-size:1.05rem; }
.day { border-bottom:1px solid var(--line); padding:8px 0; }
.day b { text-transform:capitalize; display:block; margin-bottom:6px; }
.meal-row { display:flex; align-items:center; gap:8px; margin:4px 0; }
.meal-row label { width:44px; font-size:.9rem; color:#666; }
.meal-row input { flex:1; padding:10px; border:1px solid var(--line); border-radius:8px; font-size:1rem; }
.seg { display:flex; gap:6px; }
.seg button { padding:9px 14px; border:1px solid var(--line); background:#fff; border-radius:8px; font-size:.9rem; cursor:pointer; }
.seg button.on { background:var(--accent); border-color:var(--accent); color:#fff; font-weight:700; }
form.add { display:flex; gap:8px; margin-bottom:12px; }
form.add input { flex:1; padding:10px; border:1px solid var(--line); border-radius:8px; font-size:1rem; }
button.action { padding:10px 14px; border:none; border-radius:8px; background:var(--accent); color:#fff; font-size:1rem; cursor:pointer; white-space:nowrap; }
button.action.secondary { background:var(--accent2); }
ul.items { list-style:none; margin:0; padding:0; }
ul.items li { display:flex; align-items:center; gap:10px; padding:10px 4px; border-bottom:1px solid var(--line); font-size:1rem; }
ul.items li .name { flex:1; }
ul.items li.done .name { text-decoration:line-through; color:#999; }
ul.items input[type=checkbox] { width:22px; height:22px; }
button.del { border:none; background:none; color:#b00; font-size:1.1rem; cursor:pointer; padding:4px 8px; }
.recipe { border:1px solid var(--line); border-radius:10px; padding:10px 12px; margin-bottom:10px; }
.recipe h3 { margin:0 0 4px; font-size:1rem; }
.badge { display:inline-block; font-size:.72rem; background:#e7f3ec; color:var(--accent2); border-radius:20px; padding:2px 8px; margin-left:6px; vertical-align:middle; }
.badge.missing { background:#fdecea; color:#b00; }
.recipe p { margin:6px 0; font-size:.9rem; color:#444; }
.recipe .missing-list { color:#b00; font-size:.9rem; }
.recipe button { margin-top:6px; }
.empty { color:#888; font-style:italic; padding:8px 0; }
footer { text-align:center; color:#999; font-size:.8rem; padding:16px; }
</style>
</head>
<body>
<header><h1>🍽️ Menus de la semaine — Famille</h1></header>
<nav>
<button type="button" data-tab="menu" class="active">Menu</button>
<button type="button" data-tab="courses">Courses</button>
<button type="button" data-tab="inventaire">Chez nous</button>
<button type="button" data-tab="suggestions">Suggestions</button>
</nav>
<main>
<section id="tab-menu" class="tab active"><h2>Menu de la semaine</h2><div id="menu"></div><p id="menu-status" class="empty"></p></section>
<section id="tab-courses" class="tab"><h2>Liste de courses</h2>
<form class="add" id="form-shopping"><input id="input-shopping" placeholder="Ajouter un article…" required><button class="action" type="submit">Ajouter</button></form>
<button type="button" class="action secondary" id="sync-shopping">🔄 Générer depuis le menu</button>
<p id="sync-status" class="empty"></p>
<ul class="items" id="list-shopping"></ul></section>
<section id="tab-inventaire" class="tab"><h2>Ce qu'on a déjà à la maison</h2>
<form class="add" id="form-inventory"><input id="input-inventory" placeholder="Ex : œufs, pâtes, lait…" required><button class="action" type="submit">Ajouter</button></form>
<ul class="items" id="list-inventory"></ul></section>
<section id="tab-suggestions" class="tab"><h2>Idées de repas selon ce qu’on a</h2>
<form class="add" id="form-recipe" style="flex-wrap:wrap">
<input id="recipe-name" placeholder="Nom de la recette" required>
<input id="recipe-ingredients" placeholder="Ingrédients séparés par des virgules" required style="flex:2">
<label style="display:flex;align-items:center;gap:6px;white-space:nowrap"><input type="checkbox" id="recipe-child" style="width:18px;height:18px"> 👶 18 mois</label>
<button class="action" type="submit">Ajouter</button>
</form>
<ul class="items" id="list-recipes"></ul>
<div id="suggestions"></div></section>
</main>
<footer>Application familiale locale — données stockées sur cet appareil.</footer>
<script>
const $ = (s) => document.querySelector(s);
document.querySelectorAll('nav button').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('nav button').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  $('#tab-' + b.dataset.tab).classList.add('active');
  if (b.dataset.tab === 'suggestions') { loadSuggestions(); loadRecipes(); }
}));
async function api(path, method, body) {
  const res = await fetch(path, { method: method || 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined });
  return res.json();
}
function esc(s) { return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); }
async function loadMenu() {
  const [menu, recipes] = await Promise.all([api('/api/menu'), api('/api/recipes/all')]);
  const names = recipes.map(r => r.name);
  $('#menu').innerHTML = Object.keys(menu).map(d => `
    <div class="day"><b>${d}</b>
      ${['midi','soir'].map(m => {
        const e = menu[d][m] || {};
        const persons = e.persons === 3 ? 3 : 2;
        const txt = e.text || '';
        const known = names.includes(txt);
        const selVal = txt === '' ? '' : (known ? txt : '__custom__');
        return `
        <div class="meal-row"><label>${m}</label>
          <select data-day="${d}" data-meal="${m}" style="flex:1;padding:10px;border:1px solid var(--line);border-radius:8px;font-size:1rem">
            <option value="">— Choisir un repas —</option>
            ${recipes.map(r => `<option value="${esc(r.name)}" ${selVal === r.name ? 'selected' : ''}>${esc(r.name)}${r.child_friendly ? ' 👶' : ''}</option>`).join('')}
            <option value="__custom__" ${selVal === '__custom__' ? 'selected' : ''}>✏️ Autre (texte libre)</option>
          </select>
          <input data-day="${d}" data-meal="${m}" data-field="text" value="${esc(txt)}" placeholder="Repas ${m}…" style="${(known || txt === '') ? 'display:none' : 'flex:1'}">
        </div>
        <div class="meal-row"><label></label>
          <div class="seg">
            <button type="button" data-day="${d}" data-meal="${m}" data-persons="2" class="${persons === 2 ? 'on' : ''}">2 pers.</button>
            <button type="button" data-day="${d}" data-meal="${m}" data-persons="3" class="${persons === 3 ? 'on' : ''}">3 (avec bébé)</button>
          </div></div>
        ${persons === 3 ? `<div class="meal-row"><label>bébé</label>
        <input data-day="${d}" data-meal="${m}" data-field="baby" value="${esc(e.baby)}" placeholder="Repas bébé…"></div>` : ''}`;
      }).join('')}
    </div>`).join('');
  document.querySelectorAll('#menu select').forEach(s => s.addEventListener('change', async (e) => {
    const row = e.target.closest('.meal-row');
    const input = row ? row.querySelector('input[data-field="text"]') : null;
    if (e.target.value === '__custom__') {
      if (input) { input.style.display = 'flex'; input.focus(); }
      return;
    }
    if (input) input.style.display = 'none';
    const r = await api('/api/menu', 'POST', { day: e.target.dataset.day, meal: e.target.dataset.meal, field: 'text', value: e.target.value });
    const st = $('#menu-status');
    if (r.matched) {
      st.textContent = r.added > 0
        ? `« ${r.matched} » — ${r.added} ingrédient(s) ajouté(s) aux courses.`
        : `« ${r.matched} » — tout est déjà en stock ou listé.`;
    } else {
      st.textContent = '';
    }
  }));
  document.querySelectorAll('#menu input').forEach(i => i.addEventListener('change', async (e) => {
    const r = await api('/api/menu', 'POST', { day: e.target.dataset.day, meal: e.target.dataset.meal, field: e.target.dataset.field, value: e.target.value });
    const st = $('#menu-status');
    if (r.matched) {
      st.textContent = r.added > 0
        ? `Recette « ${r.matched} » reconnue — ${r.added} ingrédient(s) ajouté(s) aux courses.`
        : `Recette « ${r.matched} » reconnue — tout est déjà en stock ou listé.`;
    } else if (e.target.dataset.field === 'text') {
      st.textContent = '';
    }
  }));
  document.querySelectorAll('#menu .seg button').forEach(b => b.addEventListener('click', async (e) => {
    await api('/api/menu', 'POST', { day: e.target.dataset.day, meal: e.target.dataset.meal, field: 'persons', value: e.target.dataset.persons });
    loadMenu();
  }));
}
async function loadShopping() {
  const items = await api('/api/shopping');
  $('#list-shopping').innerHTML = items.length ? items.map(i => `
    <li class="${i.checked ? 'done' : ''}">
      <input type="checkbox" ${i.checked ? 'checked' : ''} data-id="${i.id}">
      <span class="name">${i.name}</span>
      <button class="del" data-id="${i.id}" title="Supprimer">✕</button>
    </li>`).join('') : '<p class="empty">Liste vide.</p>';
  document.querySelectorAll('#list-shopping input[type=checkbox]').forEach(c => c.addEventListener('change', () => api('/api/shopping/toggle', 'POST', { id: c.dataset.id })));
  document.querySelectorAll('#list-shopping .del').forEach(b => b.addEventListener('click', async () => { await api('/api/shopping/' + b.dataset.id, 'DELETE'); loadShopping(); }));
}
async function loadInventory() {
  const items = await api('/api/inventory');
  $('#list-inventory').innerHTML = items.length ? items.map(i => `
    <li><span class="name">${i.name}</span>
    <button class="del" data-id="${i.id}" title="Supprimer">✕</button></li>`).join('') : '<p class="empty">Rien pour l’instant — ajoutez ce que vous avez.</p>';
  document.querySelectorAll('#list-inventory .del').forEach(b => b.addEventListener('click', async () => { await api('/api/inventory/' + b.dataset.id, 'DELETE'); loadInventory(); }));
}
async function loadSuggestions() {
  const list = await api('/api/suggestions');
  $('#suggestions').innerHTML = list.length ? list.map(r => `
    <div class="recipe">
      <h3>${r.name}${r.child_friendly ? '<span class="badge">👶 adapté 18 mois</span>' : ''}${r.missing_count === 0 ? '<span class="badge">✅ tout en stock</span>' : `<span class="badge missing">il manque ${r.missing_count}</span>`}</h3>
      ${r.missing.length ? `<p class="missing-list">Manque : ${r.missing.join(', ')}</p>` : ''}
      <p>${r.instructions}</p>
      ${r.missing.length ? `<button class="action secondary" data-recipe="${r.id}">Ajouter le manque aux courses</button>` : ''}
    </div>`).join('') : '<p class="empty">Aucune suggestion.</p>';
  document.querySelectorAll('#suggestions button[data-recipe]').forEach(b => b.addEventListener('click', async () => {
    await api('/api/suggestions/' + b.dataset.recipe + '/add-missing', 'POST');
    loadSuggestions(); loadShopping();
  }));
}
$('#form-shopping').addEventListener('submit', async (e) => { e.preventDefault(); await api('/api/shopping', 'POST', { name: $('#input-shopping').value }); $('#input-shopping').value=''; loadShopping(); });
$('#sync-shopping').addEventListener('click', async () => {
  const r = await api('/api/menu/sync-shopping', 'POST', {});
  $('#sync-status').textContent = r.added > 0
    ? `+${r.added} article(s) ajouté(s) depuis le menu (${r.matched.length} recette(s) reconnue(s)).`
    : 'Rien à ajouter : tout est déjà en stock ou listé.';
  loadShopping();
});
$('#form-recipe').addEventListener('submit', async (e) => {
  e.preventDefault();
  await api('/api/recipes', 'POST', {
    name: $('#recipe-name').value,
    ingredients: $('#recipe-ingredients').value,
    child_friendly: $('#recipe-child').checked,
  });
  $('#recipe-name').value = ''; $('#recipe-ingredients').value = ''; $('#recipe-child').checked = false;
  loadRecipes(); loadSuggestions();
});
async function loadRecipes() {
  const items = await api('/api/recipes');
  $('#list-recipes').innerHTML = items.length ? items.map(r => `
    <li><span class="name">${r.name} ${r.child_friendly ? '<span class="badge">👶 adapté 18 mois</span>' : ''}<br><small style="color:#777">${r.ingredients.join(', ')}</small></span>
    <button class="del" data-id="${r.id}" title="Supprimer">✕</button></li>`).join('') : '';
  document.querySelectorAll('#list-recipes .del').forEach(b => b.addEventListener('click', async () => { await api('/api/recipes/' + b.dataset.id, 'DELETE'); loadRecipes(); loadSuggestions(); }));
}
$('#form-inventory').addEventListener('submit', async (e) => { e.preventDefault(); await api('/api/inventory', 'POST', { name: $('#input-inventory').value }); $('#input-inventory').value=''; loadInventory(); });
loadMenu(); loadShopping(); loadInventory();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            self._send(200, PAGE, "text/html; charset=utf-8")
            return
        with lock:
            data = load_data()
        if path == "/api/menu":
            self._json(200, data["menu"])
        elif path == "/api/shopping":
            self._json(200, data["shopping"])
        elif path == "/api/inventory":
            self._json(200, data["inventory"])
        elif path == "/api/suggestions":
            self._json(200, suggestions([i["name"] for i in data["inventory"]], data))
        elif path == "/api/recipes/all":
            self._json(200, all_recipes(data))
        elif path == "/api/recipes":
            self._json(200, data["recipes"])
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._body()
        with lock:
            data = load_data()
            if path == "/api/menu":
                day, meal = body.get("day"), body.get("meal")
                if day in data["menu"] and meal in data["menu"][day]:
                    entry = data["menu"][day][meal]
                    if not isinstance(entry, dict):
                        entry = {"text": "", "persons": 2, "baby": ""}
                        data["menu"][day][meal] = entry
                    field = body.get("field", "text")
                    matched = None
                    added = 0
                    if field == "persons":
                        entry["persons"] = 3 if str(body.get("value")) == "3" else 2
                    elif field in ("text", "baby"):
                        entry[field] = str(body.get("value", ""))
                        recipe = find_recipe(entry[field], all_recipes(data))
                        if recipe:
                            matched = recipe["name"]
                            added = add_missing_to_shopping(data, recipe)
                    save_data(data)
                    self._json(200, {"ok": True, "matched": matched, "added": added})
                else:
                    self._json(400, {"error": "invalid day/meal"})
            elif path == "/api/menu/sync-shopping":
                added = 0
                matched = []
                for day in DAYS:
                    for meal in MEALS:
                        entry = data["menu"].get(day, {}).get(meal)
                        if not isinstance(entry, dict):
                            continue
                        for field in ("text", "baby"):
                            recipe = find_recipe(entry.get(field, ""), all_recipes(data))
                            if recipe:
                                matched.append(recipe["name"])
                                added += add_missing_to_shopping(data, recipe)
                save_data(data)
                self._json(200, {"added": added, "matched": matched})
            elif path == "/api/recipes":
                name = (body.get("name") or "").strip()
                ingredients = body.get("ingredients") or []
                if isinstance(ingredients, str):
                    ingredients = [i.strip() for i in ingredients.split(",") if i.strip()]
                if name and ingredients:
                    data["recipes"].append({
                        "id": uuid.uuid4().hex[:8],
                        "name": name,
                        "ingredients": ingredients,
                        "child_friendly": bool(body.get("child_friendly")),
                        "instructions": (body.get("instructions") or "").strip(),
                    })
                    save_data(data)
                self._json(200, data["recipes"])
            elif path == "/api/shopping":
                name = (body.get("name") or "").strip()
                if name:
                    data["shopping"].append({"id": uuid.uuid4().hex[:8], "name": name, "checked": False})
                    save_data(data)
                self._json(200, data["shopping"])
            elif path == "/api/shopping/toggle":
                for item in data["shopping"]:
                    if item["id"] == body.get("id"):
                        item["checked"] = not item["checked"]
                        save_data(data)
                        self._json(200, {"ok": True})
                        return
                self._json(404, {"error": "not found"})
            elif path == "/api/inventory":
                name = (body.get("name") or "").strip()
                if name:
                    data["inventory"].append({"id": uuid.uuid4().hex[:8], "name": name})
                    save_data(data)
                self._json(200, data["inventory"])
            elif path.startswith("/api/suggestions/") and path.endswith("/add-missing"):
                recipe_id = path[len("/api/suggestions/") : -len("/add-missing")]
                names = [i["name"] for i in data["inventory"]]
                recipe = next((r for r in all_recipes(data) if r["id"] == recipe_id), None)
                if not recipe:
                    self._json(404, {"error": "recipe not found"})
                    return
                added = 0
                for ing in recipe["ingredients"]:
                    if not has_ingredient(names, ing) and not any(
                        normalize(ing) in normalize(s["name"]) or normalize(s["name"]) in normalize(ing)
                        for s in data["shopping"]
                    ):
                        data["shopping"].append({"id": uuid.uuid4().hex[:8], "name": ing, "checked": False})
                        added += 1
                save_data(data)
                self._json(200, {"added": added})
            else:
                self._json(404, {"error": "not found"})

    def do_DELETE(self):
        path = urlparse(self.path).path
        with lock:
            data = load_data()
            if path.startswith("/api/shopping/"):
                item_id = path[len("/api/shopping/") :]
                data["shopping"] = [i for i in data["shopping"] if i["id"] != item_id]
                save_data(data)
                self._json(200, {"ok": True})
            elif path.startswith("/api/inventory/"):
                item_id = path[len("/api/inventory/") :]
                data["inventory"] = [i for i in data["inventory"] if i["id"] != item_id]
                save_data(data)
                self._json(200, {"ok": True})
            elif path.startswith("/api/recipes/"):
                item_id = path[len("/api/recipes/") :]
                data["recipes"] = [r for r in data["recipes"] if r["id"] != item_id]
                save_data(data)
                self._json(200, {"ok": True})
            else:
                self._json(404, {"error": "not found"})


def main():
    parser = argparse.ArgumentParser(description="App familiale : menus, courses, inventaire, suggestions.")
    parser.add_argument("--host", default="127.0.0.1", help="Adresse d'écoute (ex: 0.0.0.0 pour le réseau local)")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Application disponible sur http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
