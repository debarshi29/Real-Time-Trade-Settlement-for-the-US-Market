const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with:", deployer.address);

  const initialSupply = hre.ethers.parseUnits("1000000", 18);

  const TokenizedCash = await hre.ethers.deployContract("TokenizedCash", [initialSupply], {
    gasLimit: 3000000
  });
  await TokenizedCash.waitForDeployment();
  console.log("TokenizedCash deployed at:", TokenizedCash.target);

  const AtomicSwap = await hre.ethers.deployContract("AtomicSwap", {}, {
    gasLimit: 3000000
  });
  await AtomicSwap.waitForDeployment();
  console.log("AtomicSwap deployed at:", AtomicSwap.target);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
