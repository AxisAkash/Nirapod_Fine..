// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @title AuditRegistry
/// @notice Tamper-evident record for Nirapod Fine. It stores fingerprints (hashes) only. No name, receipt, amount,
///         offence or any other readable detail of a case or a person is ever written here.
/// @dev Two kinds of entry, both append-only:
///      - a case record: three hashes (case, dataset, result) written after a traffic fine has been checked;
///      - a dataset anchor: the fingerprint of one version of the legal rules, plus a fingerprint for each rule in it,
///        written once when that version is activated. A version can never be anchored twice.
contract AuditRegistry {
    struct CaseRecord {
        bytes32 caseHash;
        bytes32 datasetHash;
        bytes32 resultHash;
        uint64 timestamp;
    }

    struct DatasetAnchor {
        bytes32 sourceHash; // fingerprint of the source documents the rules were built from
        bytes32 contentHash; // fingerprint of the whole rule set
        uint64 timestamp;
        bool exists;
    }

    /// @notice The account allowed to write. It is fixed at deployment and cannot be changed.
    address public immutable owner;

    CaseRecord[] private _cases;
    mapping(bytes32 => DatasetAnchor) private _datasets;
    mapping(bytes32 => bytes32[]) private _labelHashes;
    mapping(bytes32 => bytes32[]) private _leafHashes;

    event CaseRecorded(uint256 indexed id, bytes32 caseHash, bytes32 datasetHash, bytes32 resultHash, uint64 timestamp);
    event DatasetAnchored(bytes32 indexed versionKey, bytes32 sourceHash, bytes32 contentHash, uint256 ruleCount, uint64 timestamp);

    error NotOwner();
    error EmptyHash();
    error NoSuchRecord(uint256 id);
    error AlreadyAnchored(bytes32 versionKey);
    error BadRuleList();

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    // ---------------------------------------------------------------- case records
    function recordCase(bytes32 caseHash, bytes32 datasetHash, bytes32 resultHash) external onlyOwner returns (uint256 id) {
        if (caseHash == 0 || datasetHash == 0 || resultHash == 0) revert EmptyHash();
        id = _cases.length;
        uint64 ts = uint64(block.timestamp);
        _cases.push(CaseRecord(caseHash, datasetHash, resultHash, ts));
        emit CaseRecorded(id, caseHash, datasetHash, resultHash, ts);
    }

    function caseCount() external view returns (uint256) {
        return _cases.length;
    }

    function getCase(uint256 id) external view returns (CaseRecord memory) {
        if (id >= _cases.length) revert NoSuchRecord(id);
        return _cases[id];
    }

    // ---------------------------------------------------------------- dataset anchors
    /// @param versionKey SHA-256 of the dataset version's id
    /// @param labelHashes SHA-256 of each rule's label (for example "offence:87"); lets a check name an altered rule
    /// @param leafHashes SHA-256 of each rule's full content, in the same order as labelHashes
    function anchorDataset(bytes32 versionKey, bytes32 sourceHash, bytes32 contentHash, bytes32[] calldata labelHashes, bytes32[] calldata leafHashes)
        external
        onlyOwner
    {
        if (_datasets[versionKey].exists) revert AlreadyAnchored(versionKey);
        if (versionKey == 0 || contentHash == 0) revert EmptyHash();
        if (labelHashes.length == 0 || labelHashes.length != leafHashes.length) revert BadRuleList();
        uint64 ts = uint64(block.timestamp);
        _datasets[versionKey] = DatasetAnchor(sourceHash, contentHash, ts, true);
        _labelHashes[versionKey] = labelHashes;
        _leafHashes[versionKey] = leafHashes;
        emit DatasetAnchored(versionKey, sourceHash, contentHash, labelHashes.length, ts);
    }

    function getDataset(bytes32 versionKey) external view returns (DatasetAnchor memory anchor, uint256 ruleCount) {
        return (_datasets[versionKey], _leafHashes[versionKey].length);
    }

    function getRules(bytes32 versionKey) external view returns (bytes32[] memory labelHashes, bytes32[] memory leafHashes) {
        return (_labelHashes[versionKey], _leafHashes[versionKey]);
    }
}
