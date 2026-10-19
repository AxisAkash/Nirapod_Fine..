const { expect } = require("chai");
const { ethers } = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-toolbox/network-helpers");

const h = (n) => ethers.zeroPadValue(ethers.toBeHex(n), 32); // a recognisable 32-byte value
const sha = (s) => ethers.sha256(ethers.toUtf8Bytes(s));

async function deploy() {
  const [owner, other] = await ethers.getSigners();
  const registry = await (await ethers.getContractFactory("AuditRegistry")).deploy();
  return { registry, owner, other };
}

describe("AuditRegistry: case records", () => {
  it("remembers who deployed it, and that cannot change", async () => {
    const { registry, owner } = await loadFixture(deploy);
    expect(await registry.owner()).to.equal(owner.address);
    expect(registry.interface.fragments.filter((f) => f.type === "function").map((f) => f.name)).to.not.include.members(["transferOwnership", "setOwner"]);
  });

  it("stores the three hashes and a timestamp, and announces them", async () => {
    const { registry } = await loadFixture(deploy);
    await expect(registry.recordCase(h(1), h(2), h(3))).to.emit(registry, "CaseRecorded");
    const rec = await registry.getCase(0);
    expect([rec.caseHash, rec.datasetHash, rec.resultHash]).to.deep.equal([h(1), h(2), h(3)]);
    expect(rec.timestamp).to.be.gt(0);
    expect(await registry.caseCount()).to.equal(1);
  });

  it("gives each record its own sequential id, and keeps every earlier one", async () => {
    const { registry } = await loadFixture(deploy);
    for (let i = 1; i <= 5; i++) await registry.recordCase(h(i), h(100), h(200 + i));
    expect(await registry.caseCount()).to.equal(5);
    expect((await registry.getCase(0)).caseHash).to.equal(h(1));
    expect((await registry.getCase(4)).resultHash).to.equal(h(205));
  });

  it("accepts the same case recorded again as a new record (a correction), never overwriting", async () => {
    const { registry } = await loadFixture(deploy);
    await registry.recordCase(h(1), h(2), h(3));
    await registry.recordCase(h(1), h(2), h(4));
    expect((await registry.getCase(0)).resultHash).to.equal(h(3));
    expect((await registry.getCase(1)).resultHash).to.equal(h(4));
  });

  it("only lets the owner write", async () => {
    const { registry, other } = await loadFixture(deploy);
    await expect(registry.connect(other).recordCase(h(1), h(2), h(3))).to.be.revertedWithCustomError(registry, "NotOwner");
  });

  it("refuses an empty hash", async () => {
    const { registry } = await loadFixture(deploy);
    const zero = ethers.ZeroHash;
    for (const args of [[zero, h(2), h(3)], [h(1), zero, h(3)], [h(1), h(2), zero]]) {
      await expect(registry.recordCase(...args)).to.be.revertedWithCustomError(registry, "EmptyHash");
    }
  });

  it("reports a record that does not exist", async () => {
    const { registry } = await loadFixture(deploy);
    await expect(registry.getCase(0)).to.be.revertedWithCustomError(registry, "NoSuchRecord");
  });

  it("anyone can read records", async () => {
    const { registry, other } = await loadFixture(deploy);
    await registry.recordCase(h(1), h(2), h(3));
    expect((await registry.connect(other).getCase(0)).caseHash).to.equal(h(1));
  });
});

describe("AuditRegistry: dataset anchors", () => {
  const labels = ["offence:87", "offence:90", "exception:s30-emergency"].map(sha);
  const leaves = [h(11), h(12), h(13)];
  const key = sha("version-1");

  it("anchors a version with a fingerprint for each rule", async () => {
    const { registry } = await loadFixture(deploy);
    await expect(registry.anchorDataset(key, h(7), h(8), labels, leaves)).to.emit(registry, "DatasetAnchored");
    const [anchor, count] = await registry.getDataset(key);
    expect([anchor.exists, anchor.sourceHash, anchor.contentHash, count]).to.deep.equal([true, h(7), h(8), 3n]);
    const [lh, fh] = await registry.getRules(key);
    expect([...lh]).to.deep.equal(labels);
    expect([...fh]).to.deep.equal(leaves);
  });

  it("can never anchor the same version twice, so a tampered copy cannot be blessed", async () => {
    const { registry } = await loadFixture(deploy);
    await registry.anchorDataset(key, h(7), h(8), labels, leaves);
    await expect(registry.anchorDataset(key, h(7), h(99), labels, [h(1), h(2), h(3)])).to.be.revertedWithCustomError(registry, "AlreadyAnchored");
    expect((await registry.getDataset(key))[0].contentHash).to.equal(h(8));
  });

  it("only lets the owner anchor", async () => {
    const { registry, other } = await loadFixture(deploy);
    await expect(registry.connect(other).anchorDataset(key, h(7), h(8), labels, leaves)).to.be.revertedWithCustomError(registry, "NotOwner");
  });

  it("refuses empty or mismatched rule lists and empty hashes", async () => {
    const { registry } = await loadFixture(deploy);
    await expect(registry.anchorDataset(key, h(7), h(8), [], [])).to.be.revertedWithCustomError(registry, "BadRuleList");
    await expect(registry.anchorDataset(key, h(7), h(8), labels, [h(1)])).to.be.revertedWithCustomError(registry, "BadRuleList");
    await expect(registry.anchorDataset(key, h(7), ethers.ZeroHash, labels, leaves)).to.be.revertedWithCustomError(registry, "EmptyHash");
    await expect(registry.anchorDataset(ethers.ZeroHash, h(7), h(8), labels, leaves)).to.be.revertedWithCustomError(registry, "EmptyHash");
  });

  it("says plainly when a version was never anchored", async () => {
    const { registry } = await loadFixture(deploy);
    const [anchor, count] = await registry.getDataset(sha("never"));
    expect(anchor.exists).to.equal(false);
    expect(count).to.equal(0n);
  });

  it("anchors a realistic dataset (57 rules) within a sensible gas budget", async () => {
    const { registry } = await loadFixture(deploy);
    const ls = Array.from({ length: 57 }, (_, i) => sha(`rule:${i}`));
    const fs = Array.from({ length: 57 }, (_, i) => h(1000 + i));
    const receipt = await (await registry.anchorDataset(sha("v-big"), h(7), h(8), ls, fs)).wait();
    expect(receipt.gasUsed).to.be.lt(6_000_000n);
  });
});

describe("AuditRegistry: what it cannot do", () => {
  it("has no way to change or delete anything once written", async () => {
    const { registry } = await loadFixture(deploy);
    const writers = registry.interface.fragments.filter((f) => f.type === "function" && !["view", "pure"].includes(f.stateMutability)).map((f) => f.name);
    expect(writers.sort()).to.deep.equal(["anchorDataset", "recordCase"]);
  });

  it("takes only hashes as input: nothing readable can be stored", async () => {
    const { registry } = await loadFixture(deploy);
    const rc = registry.interface.getFunction("recordCase");
    expect(rc.inputs.map((i) => i.type)).to.deep.equal(["bytes32", "bytes32", "bytes32"]);
    const ad = registry.interface.getFunction("anchorDataset");
    expect(ad.inputs.map((i) => i.type)).to.deep.equal(["bytes32", "bytes32", "bytes32", "bytes32[]", "bytes32[]"]);
  });
});
