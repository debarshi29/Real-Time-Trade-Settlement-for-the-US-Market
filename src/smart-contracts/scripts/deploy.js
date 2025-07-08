const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with:", deployer.address);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Deployer balance:", hre.ethers.formatEther(balance));

  // Get current gas price and set conservative values
  const feeData = await hre.ethers.provider.getFeeData();
  console.log("Current gas price:", feeData.gasPrice?.toString());

  const gasSettings = {
    gasLimit: 1500000,
    gasPrice: 20000000000, // 20 gwei - adjust as needed
  };

  // If your network supports EIP-1559, use these instead:
  // const gasSettings = {
  //   gasLimit: 1500000,
  //   maxFeePerGas: 20000000000, // 20 gwei
  //   maxPriorityFeePerGas: 1000000000, // 1 gwei
  // };

  const initialSupply = hre.ethers.parseUnits("1000000", 18);

  console.log("Deploying TokenizedCash...");
  const TokenizedCash = await hre.ethers.deployContract("TokenizedCash", [initialSupply], gasSettings);
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