require("@nomicfoundation/hardhat-toolbox");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.28",
  networks: {
    besu: {
      url: "http://localhost:8545", // Your Besu RPC URL
      accounts: [
        // Add multiple private keys here
        "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63", // Your current account
        "0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3", // Additional account 1
        "0xae6ae8e5ccbfb04590405997ee2d52d2b330726137b875053c36d94e974d162f", // Additional account 2
      ],
      chainId: 1337, // Adjust based on your Besu setup
      gasPrice: 0,
      gas: 6000000,
    },
    // Keep your other networks
    localhost: {
      url: "http://127.0.0.1:8545"
    }
  },
};