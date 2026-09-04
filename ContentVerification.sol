// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ContentVerification
 * @dev Stores tamper-evident SHA-256 canonical content fingerprints on Polygon Amoy Testnet.
 */
contract ContentVerification {
    
    struct Record {
        uint256 timestamp;
        address uploader;
        bool exists;
    }
    
    // Mapping from 32-byte content hash -> Record
    mapping(bytes32 => Record) private records;
    
    event RecordRegistered(
        bytes32 indexed contentHash,
        uint256 timestamp,
        address indexed uploader
    );
    
    /**
     * @dev Registers a new canonical content hash on-chain.
     * @param contentHash SHA-256 fingerprint as bytes32
     */
    function registerRecord(bytes32 contentHash) external {
        require(!records[contentHash].exists, "Record already registered on-chain");
        
        records[contentHash] = Record({
            timestamp: block.timestamp,
            uploader: msg.sender,
            exists: true
        });
        
        emit RecordRegistered(contentHash, block.timestamp, msg.sender);
    }
    
    /**
     * @dev Audits and verifies if a content hash exists on-chain.
     * @param contentHash SHA-256 fingerprint to query
     */
    function verifyRecord(bytes32 contentHash) external view returns (
        bool exists,
        uint256 timestamp,
        address uploader
    ) {
        Record memory record = records[contentHash];
        return (record.exists, record.timestamp, record.uploader);
    }
}
