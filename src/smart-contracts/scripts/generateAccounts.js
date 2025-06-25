const { Wallet } = require("ethers");
const fs = require("fs");

const NUM_ACCOUNTS = 100;
const accounts = [];

for (let i = 0; i < NUM_ACCOUNTS; i++) {
  const wallet = Wallet.createRandom();
  accounts.push({
    index: i,
    address: wallet.address,
    privateKey: wallet.privateKey
  });
}

fs.writeFileSync("accounts.json", JSON.stringify(accounts, null, 2));
console.log(`✅ Generated ${NUM_ACCOUNTS} accounts and saved to accounts.json`);
