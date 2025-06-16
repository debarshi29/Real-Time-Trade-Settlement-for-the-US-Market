require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: "0.8.28",
  networks: {
    besu: {
      setTimeout: 200000, // 200 seconds
  url: "http://localhost:8545",
  accounts: [
    "0x8f2a55949018a6a6823bf6ef1b3262c1b5fc313bcd99e5e9d6a6c3b6d0a7e3cc"
  ],
  chainId: 1337,        // dev mode default
  gas: 3000000,         // fixed gas value
  gasPrice: 0           // Besu in dev mode doesn't charge gas
}

  }
};
