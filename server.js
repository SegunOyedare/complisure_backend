require("dotenv").config();

const express = require("express");
const cors = require("cors");
const mongoose = require("mongoose");
const jwt = require("jsonwebtoken");
const bcrypt = require("bcryptjs");
const stripe = require("stripe")(process.env.STRIPE_KEY);

const app = express();

app.use(cors());
app.use(express.json());

// =========================
// DATABASE CONNECT
// =========================
mongoose
  .connect(process.env.MONGO_URL)
  .then(() => console.log("MongoDB connected ✔"))
  .catch((err) => console.log("MongoDB error:", err));

// =========================
// MODELS
// =========================
const UserSchema = new mongoose.Schema({
  name: String,
  password: String,
  role: { type: String, default: "user" },
  workspaceId: String,
  plan: { type: String, default: "free" },
  trialStart: { type: Date, default: Date.now },
});

const User = mongoose.model("User", UserSchema);

const ProjectSchema = new mongoose.Schema({
  name: String,
  workspaceId: String,
});

const Project = mongoose.model("Project", ProjectSchema);

const WorkspaceSchema = new mongoose.Schema({
  name: String,
  ownerId: String,
  members: [String],
});

const Workspace = mongoose.model("Workspace", WorkspaceSchema);

const InviteSchema = new mongoose.Schema({
  email: String,
  workspaceId: String,
  status: { type: String, default: "pending" },
});

const Invite = mongoose.model("Invite", InviteSchema);

const SubscriptionSchema = new mongoose.Schema({
  userId: String,
  plan: { type: String, default: "free" },
  status: { type: String, default: "inactive" },
});

const Subscription = mongoose.model("Subscription", SubscriptionSchema);

// =========================
// AUTH MIDDLEWARE
// =========================
function authMiddleware(req, res, next) {
  const authHeader = req.headers.authorization;
  if (!authHeader) return res.status(401).json({ message: "No token" });

  const token = authHeader.split(" ")[1];

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    return res.status(401).json({ message: "Invalid token" });
  }
}

// =========================
// TRIAL CHECK (14 DAYS)
// =========================
function isTrialActive(user) {
  const now = new Date();
  const diffDays =
    (now - new Date(user.trialStart)) / (1000 * 60 * 60 * 24);

  return diffDays <= 14;
}

// =========================
// AUTH ROUTES
// =========================
app.post("/register", async (req, res) => {
  const hashed = await bcrypt.hash(req.body.password, 10);

  const user = new User({
    name: req.body.name,
    password: hashed,
  });

  await user.save();
  res.json({ message: "User created" });
});

app.post("/login", async (req, res) => {
  const user = await User.findOne({ name: req.body.name });

  if (!user) return res.status(400).json({ message: "User not found" });

  const match = await bcrypt.compare(req.body.password, user.password);

  if (!match) return res.status(400).json({ message: "Wrong password" });

  const token = jwt.sign(
    {
      user_id: user._id,
      name: user.name,
      role: user.role,
    },
    process.env.JWT_SECRET,
    { expiresIn: "1h" }
  );

  res.json({
    access_token: token,
    user: { name: user.name, id: user._id },
  });
});

// =========================
// PROJECTS (TRIAL PROTECTED)
// =========================
app.get("/projects", authMiddleware, async (req, res) => {
  const user = await User.findById(req.user.user_id);

  const allowed = user.plan === "pro" || isTrialActive(user);

  if (!allowed) {
    return res.status(403).json({ message: "Trial expired" });
  }

  const projects = await Project.find({
    workspaceId: user.workspaceId,
  });

  res.json(projects);
});

app.post("/projects", authMiddleware, async (req, res) => {
  const user = await User.findById(req.user.user_id);

  const project = new Project({
    name: req.body.name,
    workspaceId: user.workspaceId,
  });

  await project.save();
  res.json(project);
});

app.delete("/projects/:id", authMiddleware, async (req, res) => {
  await Project.findByIdAndDelete(req.params.id);
  res.json({ message: "deleted" });
});

// =========================
// WORKSPACE
// =========================
app.post("/workspace", authMiddleware, async (req, res) => {
  const workspace = new Workspace({
    name: req.body.name,
    ownerId: req.user.user_id,
    members: [req.user.user_id],
  });

  await workspace.save();

  await User.findByIdAndUpdate(req.user.user_id, {
    workspaceId: workspace._id,
  });

  res.json(workspace);
});

app.get("/workspace", authMiddleware, async (req, res) => {
  const user = await User.findById(req.user.user_id);
  const workspace = await Workspace.findById(user.workspaceId);
  res.json(workspace);
});

// =========================
// INVITES
// =========================
app.post("/invite", authMiddleware, async (req, res) => {
  const invite = new Invite(req.body);
  await invite.save();
  res.json(invite);
});

app.get("/invites", authMiddleware, async (req, res) => {
  const user = await User.findById(req.user.user_id);

  const invites = await Invite.find({
    email: user.name,
    status: "pending",
  });

  res.json(invites);
});

app.post("/invite/accept", authMiddleware, async (req, res) => {
  const invite = await Invite.findById(req.body.inviteId);

  invite.status = "accepted";
  await invite.save();

  await User.findByIdAndUpdate(req.user.user_id, {
    workspaceId: invite.workspaceId,
  });

  const workspace = await Workspace.findById(invite.workspaceId);

  if (!workspace.members.includes(req.user.user_id)) {
    workspace.members.push(req.user.user_id);
  }

  await workspace.save();

  res.json({ message: "joined" });
});

// =========================
// STRIPE
// =========================
app.post("/create-checkout", authMiddleware, async (req, res) => {
  const session = await stripe.checkout.sessions.create({
    payment_method_types: ["card"],
    mode: "subscription",
    line_items: [
      {
        price_data: {
          currency: "usd",
          product_data: { name: "Pro Plan" },
          unit_amount: 500,
          recurring: { interval: "month" },
        },
        quantity: 1,
      },
    ],
    success_url: "http://localhost:5173/success",
    cancel_url: "http://localhost:5173/cancel",
  });

  res.json({ url: session.url });
});

// =========================
// START SERVER
// =========================
const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});