// A small, well-behaved module: the benchmark expects no findings here.
const crypto = require("crypto");
const { execFile } = require("child_process");

function renderComment(container, comment) {
  container.textContent = comment.body;
}

function thumbnail(file, done) {
  execFile("convert", [file, "out.png"], done);
}

async function findUser(db, name) {
  return db.query("SELECT * FROM users WHERE name = $1", [name]);
}

function sessionToken() {
  return crypto.randomBytes(32).toString("hex");
}

module.exports = { renderComment, thumbnail, findUser, sessionToken };
