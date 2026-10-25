const express = require("express");
const Database = require("better-sqlite3");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const cookieParser = require("cookie-parser");
const path = require("path");

const PORT = process.env.PORT || 3000;
const SECRET = process.env.JWT_SECRET || "change-me-before-going-live";
const ADMIN_EMAIL = (process.env.ADMIN_EMAIL || "").toLowerCase(); // this account sees all orders

/* ---------- Database ---------- */
const db = new Database(path.join(__dirname, "data.db"));
db.exec(`
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, hash TEXT NOT NULL, phone TEXT, address TEXT);
CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY, category TEXT NOT NULL, name TEXT NOT NULL, descr TEXT, price_cents INTEGER NOT NULL, tags TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, address TEXT NOT NULL, phone TEXT, notes TEXT, total_cents INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'new', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS order_items(order_id INTEGER NOT NULL, item_id INTEGER NOT NULL, name TEXT NOT NULL, qty INTEGER NOT NULL, price_cents INTEGER NOT NULL, note TEXT);
`);

// Starter menu (only inserted when the table is empty). Prices are in cents.
if (!db.prepare("SELECT 1 FROM items").get()) {
  const ins = db.prepare("INSERT INTO items(category,name,descr,price_cents,tags) VALUES(?,?,?,?,?)");
  [
    ["Burgers", "The Ember Classic", "Smashed beef patty, aged cheddar, pickles, red onion and house sauce on a toasted potato bun.", 950, "gf"],
    ["Burgers", "Smokehouse", "Beef patty, smoked bacon, smoked cheddar, crispy onion ring and oak BBQ sauce.", 1150, ""],
    ["Burgers", "Double Oak", "Two patties, American cheese, slow-caramelized onions and mustard mayo.", 1250, ""],
    ["Burgers", "Hot Honey Chicken", "Buttermilk fried chicken thigh, hot honey, crunchy slaw and dill pickles.", 1050, ""],
    ["Burgers", "Garden Smash", "Plant-based patty, vegan cheese, lettuce, tomato, pickles and smoky ketchup.", 1000, "vegan,gf"],
    ["Sides", "Skin-on Fries", "Hand-cut and sea-salted.", 350, "vegan,gf"],
    ["Sides", "Sweet Potato Fries", "Served with smoky dip.", 450, "vegan,gf"],
    ["Sides", "Onion Rings", "Thick-cut and beer-battered.", 450, "vegan"],
    ["Sides", "Chili Cheese Fries", "Fries topped with beef chili, melted cheddar and scallions.", 550, "gf"],
    ["Drinks", "Fresh Lemonade", "Squeezed daily, lightly sweet.", 350, "vegan,gf"],
    ["Drinks", "Craft Cola", "Cane sugar, bottled.", 300, "vegan,gf"],
    ["Drinks", "Thick Shake", "Vanilla, chocolate or salted caramel (write your choice in the item details).", 550, "gf"],
    ["Desserts", "Skillet Cookie", "Warm chocolate chip cookie with a scoop of vanilla ice cream.", 550, ""],
    ["Desserts", "Apple Hand Pie", "Flaky crust, cinnamon apples, dusted with sugar.", 450, "vegan"]
  ].forEach(r => ins.run(...r));
}

/* ---------- Helpers ---------- */
const app = express();
app.use(express.json({ limit: "50kb" }));
app.use(cookieParser());
app.use(express.static(path.join(__dirname, "public")));

const userByEmail = db.prepare("SELECT * FROM users WHERE email=?");
const userById = db.prepare("SELECT * FROM users WHERE id=?");
const clean = (v, max) => String(v ?? "").trim().slice(0, max);
const isAdmin = u => !!u && !!ADMIN_EMAIL && u.email === ADMIN_EMAIL;
const publicUser = u => ({ id: u.id, name: u.name, email: u.email, phone: u.phone || "", address: u.address || "", isAdmin: isAdmin(u) });

function startSession(res, u) {
  const token = jwt.sign({ uid: u.id }, SECRET, { expiresIn: "7d" });
  res.cookie("token", token, { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", maxAge: 7 * 864e5 });
}

// Slow down password guessing: 10 attempts per 15 minutes per IP
const tries = new Map();
function tooMany(req) {
  const now = Date.now();
  const list = (tries.get(req.ip) || []).filter(t => now - t < 9e5);
  tries.set(req.ip, list);
  if (list.length >= 10) return true;
  list.push(now);
  return false;
}

app.use((req, res, next) => {
  try { req.user = userById.get(jwt.verify(req.cookies.token, SECRET).uid) || null; } catch { req.user = null; }
  next();
});
const needUser = (req, res, next) => req.user ? next() : res.status(401).json({ error: "Please sign in first." });
const needAdmin = (req, res, next) => isAdmin(req.user) ? next() : res.status(403).json({ error: "Staff only." });

/* ---------- Accounts ---------- */
app.post("/api/register", (req, res) => {
  if (tooMany(req)) return res.status(429).json({ error: "Too many attempts. Try again in a few minutes." });
  const name = clean(req.body.name, 80), email = clean(req.body.email, 120).toLowerCase();
  const password = String(req.body.password || ""), phone = clean(req.body.phone, 30);
  if (!name || !/^\S+@\S+\.\S+$/.test(email)) return res.status(400).json({ error: "Enter your name and a valid email." });
  if (password.length < 8) return res.status(400).json({ error: "Password must be at least 8 characters." });
  if (userByEmail.get(email)) return res.status(409).json({ error: "This email already has an account. Sign in instead." });
  const id = db.prepare("INSERT INTO users(name,email,hash,phone) VALUES(?,?,?,?)").run(name, email, bcrypt.hashSync(password, 10), phone).lastInsertRowid;
  const u = userById.get(id);
  startSession(res, u);
  res.json({ user: publicUser(u) });
});

app.post("/api/login", (req, res) => {
  if (tooMany(req)) return res.status(429).json({ error: "Too many attempts. Try again in a few minutes." });
  const u = userByEmail.get(clean(req.body.email, 120).toLowerCase());
  if (!u || !bcrypt.compareSync(String(req.body.password || ""), u.hash)) return res.status(401).json({ error: "Wrong email or password." });
  startSession(res, u);
  res.json({ user: publicUser(u) });
});

app.post("/api/logout", (req, res) => { res.clearCookie("token"); res.json({ ok: true }); });
app.get("/api/me", (req, res) => res.json({ user: req.user ? publicUser(req.user) : null }));

/* ---------- Menu: prices are only sent to signed-in customers ---------- */
app.get("/api/menu", (req, res) => {
  const rows = db.prepare("SELECT * FROM items ORDER BY id").all();
  res.json(rows.map(r => ({
    id: r.id, category: r.category, name: r.name, descr: r.descr,
    tags: r.tags ? r.tags.split(",") : [],
    ...(req.user ? { price: r.price_cents } : {})
  })));
});

/* ---------- Orders ---------- */
app.post("/api/orders", needUser, (req, res) => {
  const address = clean(req.body.address, 300), phone = clean(req.body.phone, 30), notes = clean(req.body.notes, 500);
  if (!address) return res.status(400).json({ error: "Please write your delivery address." });
  const lines = Array.isArray(req.body.items) ? req.body.items.slice(0, 50) : [];
  const getItem = db.prepare("SELECT * FROM items WHERE id=?");
  let total = 0;
  const rows = [];
  for (const l of lines) {
    const qty = Math.floor(Number(l.qty));
    if (!Number.isInteger(Number(l.id)) || !(qty >= 1 && qty <= 20)) continue;
    const it = getItem.get(Number(l.id));
    if (!it) continue;
    total += it.price_cents * qty; // total is always calculated here, never trusted from the browser
    rows.push([it.id, it.name, qty, it.price_cents, clean(l.note, 200)]);
  }
  if (!rows.length) return res.status(400).json({ error: "Your cart is empty." });

  const place = db.transaction(() => {
    const oid = db.prepare("INSERT INTO orders(user_id,address,phone,notes,total_cents) VALUES(?,?,?,?,?)").run(req.user.id, address, phone, notes, total).lastInsertRowid;
    const ins = db.prepare("INSERT INTO order_items(order_id,item_id,name,qty,price_cents,note) VALUES(?,?,?,?,?,?)");
    rows.forEach(r => ins.run(oid, ...r));
    db.prepare("UPDATE users SET address=?, phone=? WHERE id=?").run(address, phone || req.user.phone || "", req.user.id);
    return oid;
  });
  res.json({ orderId: place(), total });
});

const ORDER_SQL = "SELECT o.*, u.name AS customer, u.email FROM orders o JOIN users u ON u.id=o.user_id";
app.get("/api/orders", needUser, (req, res) => {
  const rows = isAdmin(req.user)
    ? db.prepare(ORDER_SQL + " ORDER BY o.id DESC LIMIT 100").all()
    : db.prepare(ORDER_SQL + " WHERE o.user_id=? ORDER BY o.id DESC LIMIT 50").all(req.user.id);
  const lines = db.prepare("SELECT name, qty, price_cents, note FROM order_items WHERE order_id=?");
  res.json({ staff: isAdmin(req.user), orders: rows.map(r => ({ ...r, items: lines.all(r.id) })) });
});

const STATUSES = ["new", "preparing", "on the way", "delivered", "cancelled"];
app.patch("/api/orders/:id", needUser, needAdmin, (req, res) => {
  if (!STATUSES.includes(req.body.status)) return res.status(400).json({ error: "Unknown status." });
  db.prepare("UPDATE orders SET status=? WHERE id=?").run(req.body.status, Number(req.params.id));
  res.json({ ok: true });
});

app.listen(PORT, () => console.log("Menu site running at http://localhost:" + PORT));
