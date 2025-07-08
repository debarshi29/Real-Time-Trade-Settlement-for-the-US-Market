const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with:", deployer.address);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Deployer balance:", hre.ethers.formatEther(balance));

  const feeData = await hre.ethers.provider.getFeeData();
  console.log("Current gas price:", feeData.gasPrice?.toString());

  // Use much higher gas price to ensure transaction processes
  const gasSettings = {
    gasLimit: 3000000,
    gasPrice: 20000000000, // 20 gwei - very high to force processing
  };

  const initialSupply = hre.ethers.parseUnits("1000000", 18);

  console.log("Deploying TokenizedCash...");
  const TokenizedCash = await hre.ethers.deployContract("TokenizedCash", [initialSupply], gasSettings);
  
  console.log("Transaction hash:", TokenizedCash.deploymentTransaction()?.hash);
  console.log("Waiting for deployment...");
  
  await TokenizedCash.waitForDeployment();
  console.log("TokenizedCash deployed at:", TokenizedCash.target);

  console.log("Deploying AtomicSwap...");
  const AtomicSwap = await hre.ethers.deployContract("AtomicSwap", [], gasSettings);
  await AtomicSwap.waitForDeployment();
  console.log("AtomicSwap deployed at:", AtomicSwap.target);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});