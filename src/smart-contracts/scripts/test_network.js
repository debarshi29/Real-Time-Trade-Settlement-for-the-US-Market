// scripts/test_network.js
const { ethers } = require("hardhat");

async function main() {
    console.log("🌐 NETWORK CONNECTIVITY TEST");
    console.log("============================");
    
    try {
        // Test basic connection
        console.log("1️⃣ Testing network connection...");
        const network = await ethers.provider.getNetwork();
        console.log("✅ Connected to network:", network.name);
        console.log("📍 Chain ID:", network.chainId.toString());
        
        // Test block information
        console.log("\n2️⃣ Testing block information...");
        const blockNumber = await ethers.provider.getBlockNumber();
        console.log("✅ Current block:", blockNumber);
        
        const block = await ethers.provider.getBlock(blockNumber);
        console.log("✅ Block timestamp:", new Date(Number(block.timestamp) * 1000).toISOString());
        
        // Test account access
        console.log("\n3️⃣ Testing account access...");
        const [deployer] = await ethers.getSigners();
        console.log("✅ Account:", deployer.address);
        
        const balance = await ethers.provider.getBalance(deployer.address);
        console.log("✅ Balance:", ethers.formatEther(balance), "ETH");
        
        if (balance < ethers.parseEther("1")) {
            console.log("⚠️  Low balance detected - may need more ETH for deployments");
        }
        
        // Test transaction capability
        console.log("\n4️⃣ Testing transaction capability...");
        const gasPrice = await ethers.provider.getFeeData();
        console.log("✅ Gas price:", ethers.formatUnits(gasPrice.gasPrice || 0, "gwei"), "gwei");
        
        // Test contract deployment capability (dry run)
        console.log("\n5️⃣ Testing contract deployment (estimation)...");
        try {
            const TokenizedCash = await ethers.getContractFactory("TokenizedCash");
            // Get deployment transaction with no constructor args (TokenizedCash has no constructor parameters)
            const deploymentData = TokenizedCash.getDeployTransaction();
            
            const gasEstimate = await ethers.provider.estimateGas({
                data: deploymentData.data,
                from: deployer.address
            });
            
            console.log("✅ Estimated gas for deployment:", gasEstimate.toString());
            
            const estimatedCost = gasEstimate * (gasPrice.gasPrice || 0n);
            console.log("✅ Estimated deployment cost:", ethers.formatEther(estimatedCost), "ETH");
            
        } catch (error) {
            console.log("❌ Contract deployment estimation failed:", error.message);
            console.log("💡 This is normal - proceeding with main diagnostic...");
        }
        
        console.log("\n🎉 Network connectivity test completed successfully!");
        
    } catch (error) {
        console.log("❌ Network test failed:", error.message);
        
        if (error.message.includes("ECONNREFUSED")) {
            console.log("💡 Solution: Start your Besu node first");
            console.log("   Command: besu --network=dev --miner-enabled --miner-coinbase=0xfe3b557e8fb62b89f4916b721be55ceb828dbd73 --rpc-http-enabled --rpc-http-cors-origins='*' --host-allowlist='*' --rpc-ws-enabled --data-path=besu-data");
        } else if (error.message.includes("network")) {
            console.log("💡 Solution: Check your hardhat.config.js network configuration");
        }
        
        throw error;
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("Network test failed:", error);
        process.exit(1);
    });