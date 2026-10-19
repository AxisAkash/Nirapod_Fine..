// Deploys AuditRegistry to the running node and writes its address to deployments/<network>.json for the backend.
const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const registry = await (await hre.ethers.getContractFactory("AuditRegistry")).deploy();
  await registry.waitForDeployment();
  const net = await hre.ethers.provider.getNetwork();
  const info = {
    network: hre.network.name,
    chainId: Number(net.chainId),
    address: await registry.getAddress(),
    deployer: deployer.address,
    deployedAt: new Date().toISOString(),
  };
  const dir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, `${hre.network.name}.json`), JSON.stringify(info, null, 2) + "\n");
  console.log(`AuditRegistry deployed to ${info.address} on ${info.network} (chain ${info.chainId})`);
  console.log(`The backend must write with this account: ${deployer.address}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
