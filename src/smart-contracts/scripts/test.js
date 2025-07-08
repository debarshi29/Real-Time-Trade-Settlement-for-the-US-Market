const { ethers } = require("hardhat");

async function main() {
  try {
    const [deployer] = await ethers.getSigners();
    console.log("Deployer:", deployer.address);
    console.log("Balance:", (await ethers.provider.getBalance(deployer.address)).toString());
    
    // Check current block to confirm mining is working
    const currentBlock = await ethers.provider.getBlockNumber();
    console.log("Current block number:", currentBlock);
    
    console.log("Sending test transaction...");
    const tx = await deployer.sendTransaction({
      to: "0x1234567890123456789012345678901234567890", // Valid recipient
      value: ethers.parseEther ? ethers.parseEther("0.01") : ethers.utils.parseEther("0.01"),
      gasLimit: 21000,
      gasPrice: 875000000, // This matches your network
    });
    
    console.log("Tx hash:", tx.hash);
    console.log("Waiting for confirmation...");
    
    // Since mining is working, this should complete quickly
    const receipt = await tx.wait();
    console.log("✅ Test transaction confirmed!");
    console.log("Block number:", receipt.blockNumber);
    console.log("Gas used:", receipt.gasUsed.toString());
    console.log("Status:", receipt.status === 1 ? "Success" : "Failed");
    console.log("Transaction fee:", (receipt.gasUsed * BigInt(875000000)).toString(), "wei");
    
  } catch (error) {
    console.error("❌ Error details:");
    console.error("Message:", error.message);
    if (error.code) console.error("Code:", error.code);
    if (error.reason) console.error("Reason:", error.reason);
    
    // If timeout, check if transaction was actually mined
    if (error.message.includes("timeout")) {
      console.log("Checking if transaction was mined despite timeout...");
      try {
        const receipt = await ethers.provider.getTransactionReceipt(tx.hash);
        if (receipt) {
          console.log("✅ Transaction was actually mined!");
          console.log("Block:", receipt.blockNumber, "Status:", receipt.status === 1 ? "Success" : "Failed");
        }
      } catch (e) {
        console.log("Transaction not found in any block");
      }
    }
    throw error;
  }
}

main().catch((error) => {
  console.error("Script failed:", error.message);
  process.exitCode = 1;
});