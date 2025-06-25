const hre = require("hardhat");
const { ethers } = hre;

async function main() {
  // Step 0: Signer sanity check
  const signers = await ethers.getSigners();
  if (signers.length < 3) {
    throw new Error("Not enough signers defined in the Besu network config. Check hardhat.config.js.");
  }

  const [deployer, traderA, traderB] = signers;

  console.log("Deployer:", deployer.address);
  console.log("Trader A (Seller of Security):", traderA.address);
  console.log("Trader B (Buyer with Cash):", traderB.address);

  // 🧠 TODO: Replace with actual deployed TokenizedSecurity address
  const TSEC_ADDRESS = "0xYourTokenizedSecurityAddressHere";

  // Get deployed contracts
  const TokenizedCash = await ethers.getContractAt("TokenizedCash", "0xF5f0b6c754226E67B723226C72d9451f9E2b68B5");
  const TokenizedSecurity = await ethers.getContractAt("TokenizedSecurity", TSEC_ADDRESS);
  const AtomicSwap = await ethers.getContractAt("AtomicSwap", "0xdF65C3d00b1021Fd667831D79915cB0321915AbC");

  // Trade params
  const amountTSEC = ethers.utils.parseEther("10");     // TraderA sells 10 securities
  const amountTCASH = ethers.utils.parseEther("1000");  // TraderB pays 1000 cash

  // Step 1: Approve swap contract
  console.log("\n🔐 Approving contracts...");
  const approve1 = await TokenizedSecurity.connect(traderA).approve(AtomicSwap.address, amountTSEC);
  await approve1.wait();
  const approve2 = await TokenizedCash.connect(traderB).approve(AtomicSwap.address, amountTCASH);
  await approve2.wait();
  console.log("✅ Approvals done.");

  // Step 2: Initialize Trade
  console.log("\n📤 Initializing trade...");
  const txInit = await AtomicSwap.connect(deployer).initTrade(
    traderA.address,
    traderB.address,
    TokenizedSecurity.address,
    amountTSEC,
    TokenizedCash.address,
    amountTCASH
  );
  const receipt = await txInit.wait();

  // Read emitted tradeId
  const tradeId = receipt.events?.find(e => e.event === "TradeInitialized")?.args?.tradeId;
  if (!tradeId) {
    throw new Error("Trade ID not found in event logs");
  }
  console.log("📄 Trade initialized with ID:", tradeId.toString());

  // Step 3: Execute Trade
  console.log("\n🚀 Executing atomic swap...");
  const txExec = await AtomicSwap.connect(deployer).executeTrade(tradeId);
  await txExec.wait();
  console.log("✅ Trade executed successfully.");

  // Final balances
  const balA_sec = await TokenizedSecurity.balanceOf(traderA.address);
  const balB_sec = await TokenizedSecurity.balanceOf(traderB.address);
  const balA_cash = await TokenizedCash.balanceOf(traderA.address);
  const balB_cash = await TokenizedCash.balanceOf(traderB.address);

  console.log("\n📊 Final Balances:");
  console.log("TraderA - Securities:", ethers.utils.formatEther(balA_sec));
  console.log("TraderA - Cash:", ethers.utils.formatEther(balA_cash));
  console.log("TraderB - Securities:", ethers.utils.formatEther(balB_sec));
  console.log("TraderB - Cash:", ethers.utils.formatEther(balB_cash));
}

// Execute and catch any errors
main().catch((error) => {
  console.error("❌ Script failed:", error);
  process.exit(1);
});
