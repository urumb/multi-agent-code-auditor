const { exec } = require("child_process");
const db = require("./db");

const API_KEY = "sk_live_9f8e7d6c5b4a";  // EXPECT: security

function renderComment(container, comment) {
  container.innerHTML = "<p>" + comment.body + "</p>";  // EXPECT: security
}

function convert(file, res) {
  exec("convert " + file + " out.png", (err) => res.send(err ? "fail" : "ok"));  // EXPECT: security
}

async function findUser(name) {
  return db.query("SELECT * FROM users WHERE name = '" + name + "'");  // EXPECT: security
}

function calculate(expr) {
  return eval(expr);  // EXPECT: security
}

function sessionToken() {
  return Math.random().toString(36).slice(2);  // EXPECT: security
}

function renderSafe(container, comment) {
  container.textContent = comment.body;
}

module.exports = { renderComment, convert, findUser, calculate, sessionToken, renderSafe, API_KEY };
