require("@nomicfoundation/hardhat-toolbox");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.28",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    besu: {
      url: "http://localhost:8545",
      accounts: [
        "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63",
        "0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3",
        "0xae6ae8e5ccbfb04590405997ee2d52d2b330726137b875053c36d94e974d162f",
      ],
      chainId: 1981,
      gasPrice: 875000000, // Free gas for dev network
      gas: 5000000,
      timeout: 60000, // 60 second timeout
      // Additional Besu-specific settings
      allowUnlimitedContractSize: true, // For large contracts
      blockGasLimit: 6000000,
      // Network stability settings
      httpHeaders: {
        "Content-Type": "application/json"
      }
    },
    localhost: {
      url: "http://127.0.0.1:8545",
      timeout: 60000
    }
  },
  // Helpful for debugging
  mocha: {
    timeout: 60000
  }
};