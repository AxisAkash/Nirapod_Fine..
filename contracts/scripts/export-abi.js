// Copies the compiled contract (ABI + bytecode) next to the backend, so the backend and its tests need no Node tooling.
const fs = require("fs");
const path = require("path");

const artifact = require("../artifacts/contracts/AuditRegistry.sol/AuditRegistry.json");
const out = path.join(__dirname, "..", "..", "backend", "app", "chain", "AuditRegistry.json");
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify({ contractName: artifact.contractName, abi: artifact.abi, bytecode: artifact.bytecode }, null, 2) + "\n");
console.log(`exported ${artifact.contractName} to ${path.relative(process.cwd(), out)}`);
